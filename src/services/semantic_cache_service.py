"""
Semantic Image Cache Service
============================

Two-tier semantic caching for AI-generated slide background images.

Architecture:
- TIER 1: Fast keyword count using PostgreSQL GIN index (< 10ms)
- TIER 2: Vector similarity search using pgvector IVFFlat (~50ms)

Key Design Principles:
1. Topic-Based Relevance: Only check cache if SPECIFIC topics match
   - ❌ Wrong: "religious domain has 500 images" (but none about Hinduism)
   - ✅ Right: "hinduism-related images = 50" (actually relevant)

2. Probability Curve: More relevant images = higher chance to use cache
   - < 10 images: SKIP cache (not enough data)
   - 10-50 images: 50% chance to check Tier 2
   - 50-100 images: 80% chance
   - 100+ images: 95% chance

3. Pre-computed Embeddings: Generated at cache time, not query time
   - Cache write: Generate embedding (~100ms one-time cost)
   - Cache read: Only query embedding generated (~100ms)
"""

import logging
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

from .embedding_service import EmbeddingService, get_embedding_service


@dataclass
class CachedImage:
    """Represents a cached image from semantic search."""
    id: str
    image_url: str
    cropped_url: Optional[str]
    prompt_text: str
    similarity: float
    hit_count: int
    quality_score: float

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "CachedImage":
        """Create CachedImage from database row."""
        return cls(
            id=str(row["id"]),
            image_url=row["image_url"],
            cropped_url=row.get("cropped_url"),
            prompt_text=row["prompt_text"],
            similarity=row.get("similarity", 0.0),
            hit_count=row.get("hit_count", 0),
            quality_score=row.get("quality_score", 0.0)
        )


class SemanticImageCacheService:
    """
    Two-tier semantic image cache with fast keyword matching
    and vector similarity search.

    Usage:
        cache = SemanticImageCacheService()

        # Check cache before generating
        cached = await cache.check_cache(
            prompt="Temple scene with Shiva",
            topics=["hinduism", "shiva", "temple"],
            visual_style="professional",
            slide_type="title_slide"
        )

        if cached:
            return cached.image_url  # Use cached image
        else:
            image = await generate_new_image(...)  # Generate new
            await cache.cache_image(...)  # Store for future
    """

    # Probability thresholds for Tier 2 check
    MIN_IMAGES_FOR_CACHE = 10
    THRESHOLD_MEDIUM = 50
    THRESHOLD_HIGH = 100

    # Similarity threshold for cache hit
    DEFAULT_SIMILARITY_THRESHOLD = 0.85

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Initialize semantic cache service.

        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase service key
            embedding_service: EmbeddingService instance (auto-created if None)
        """
        if not SUPABASE_AVAILABLE:
            raise ImportError("supabase not installed. Run: pip install supabase")

        import os
        from dotenv import load_dotenv
        load_dotenv()

        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        # Initialize Supabase client
        self.client: Client = create_client(self.url, self.key)

        # Initialize embedding service (lazy for optional use)
        self._embedding_service = embedding_service
        self._embedding_service_initialized = False

        logger.info("Initialized SemanticImageCacheService")

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get embedding service (lazy initialization)."""
        if self._embedding_service is None and not self._embedding_service_initialized:
            try:
                self._embedding_service = get_embedding_service()
                self._embedding_service_initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize embedding service: {e}")
                self._embedding_service_initialized = True
        return self._embedding_service

    # ==========================================
    # TIER 1: Fast Keyword Count
    # ==========================================

    async def count_relevant_images(
        self,
        topics: List[str],
        visual_style: str,
        slide_type: str
    ) -> int:
        """
        Count images matching topic keywords (TIER 1).

        Uses GIN index for fast array overlap - executes in < 10ms.

        Args:
            topics: List of topic keywords (e.g., ["hinduism", "shiva"])
            visual_style: Visual style filter (professional, illustrated, kids)
            slide_type: Slide type filter (title_slide, section_divider, closing_slide)

        Returns:
            Count of relevant images in cache
        """
        try:
            # Use PostgreSQL function for efficiency
            response = self.client.rpc(
                "count_topic_relevant_images",
                {
                    "p_topics": topics,
                    "p_visual_style": visual_style,
                    "p_slide_type": slide_type
                }
            ).execute()

            count = response.data if response.data else 0
            logger.debug(
                f"Tier 1 count: {count} images for topics={topics}, "
                f"style={visual_style}, type={slide_type}"
            )
            return count

        except Exception as e:
            logger.error(f"Tier 1 count failed: {e}")
            # On error, skip cache (safe fallback)
            return 0

    def should_check_tier2(self, relevant_count: int) -> bool:
        """
        Determine if we should proceed to Tier 2 based on probability curve.

        Probability increases with more relevant images:
        - < 10 images: SKIP (not enough data)
        - 10-50 images: 50% chance
        - 50-100 images: 80% chance
        - 100+ images: 95% chance

        Args:
            relevant_count: Number of topic-relevant images in cache

        Returns:
            True if we should check Tier 2, False to skip cache
        """
        if relevant_count < self.MIN_IMAGES_FOR_CACHE:
            logger.debug(f"Tier 1: Only {relevant_count} images, skipping cache")
            return False

        if relevant_count < self.THRESHOLD_MEDIUM:
            probability = 0.5
        elif relevant_count < self.THRESHOLD_HIGH:
            probability = 0.8
        else:
            probability = 0.95

        should_check = random.random() < probability
        logger.debug(
            f"Tier 1: {relevant_count} images, probability={probability}, "
            f"check_tier2={should_check}"
        )
        return should_check

    # ==========================================
    # TIER 2: Semantic Vector Search
    # ==========================================

    async def find_similar_image(
        self,
        prompt: str,
        topics: List[str],
        visual_style: str,
        slide_type: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Optional[CachedImage]:
        """
        Find semantically similar image using vector search (TIER 2).

        Uses pgvector IVFFlat index for ~50ms query time.
        Embeddings are pre-computed at cache time.

        Args:
            prompt: Image generation prompt
            topics: Topic keywords for filtering
            visual_style: Visual style filter
            slide_type: Slide type filter
            threshold: Minimum similarity threshold (default 0.85)

        Returns:
            CachedImage if found above threshold, None otherwise
        """
        if not self.embedding_service:
            logger.warning("Embedding service not available, skipping Tier 2")
            return None

        try:
            # Generate embedding for query prompt (~100ms)
            query_embedding = await self.embedding_service.generate(prompt)

            # Use PostgreSQL function for similarity search
            response = self.client.rpc(
                "find_similar_images",
                {
                    "p_query_embedding": query_embedding,
                    "p_topics": topics,
                    "p_visual_style": visual_style,
                    "p_slide_type": slide_type,
                    "p_threshold": threshold,
                    "p_limit": 1
                }
            ).execute()

            if response.data and len(response.data) > 0:
                cached = CachedImage.from_row(response.data[0])
                logger.info(
                    f"Tier 2: Found similar image (similarity={cached.similarity:.3f})"
                )
                return cached

            logger.debug("Tier 2: No similar image found above threshold")
            return None

        except Exception as e:
            logger.error(f"Tier 2 search failed: {e}")
            return None

    # ==========================================
    # MAIN ENTRY POINT
    # ==========================================

    async def check_cache(
        self,
        prompt: str,
        topics: List[str],
        visual_style: str,
        slide_type: str,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> Optional[CachedImage]:
        """
        Two-tier cache check - main entry point.

        Returns cached image if found, None otherwise.
        Automatically records hit when cache is used.

        Args:
            prompt: Image generation prompt
            topics: Topic keywords extracted from prompt
            visual_style: Visual style (professional, illustrated, kids)
            slide_type: Slide type (title_slide, section_divider, closing_slide)
            threshold: Similarity threshold (default 0.85)

        Returns:
            CachedImage if cache hit, None for cache miss
        """
        if not topics:
            logger.debug("No topics provided, skipping cache")
            return None

        # TIER 1: Fast keyword count (< 10ms)
        relevant_count = await self.count_relevant_images(
            topics, visual_style, slide_type
        )

        if not self.should_check_tier2(relevant_count):
            return None

        # TIER 2: Semantic search (~100ms for embedding + ~50ms for search)
        cached = await self.find_similar_image(
            prompt, topics, visual_style, slide_type, threshold
        )

        if cached:
            # Record cache hit
            await self.record_hit(cached.id)
            logger.info(
                f"Cache HIT: similarity={cached.similarity:.3f}, "
                f"hits={cached.hit_count + 1}"
            )

        return cached

    async def record_hit(self, cache_id: str) -> None:
        """
        Record a cache hit (increment hit count).

        Args:
            cache_id: UUID of cached image
        """
        try:
            self.client.rpc(
                "increment_cache_hit",
                {"p_cache_id": cache_id}
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to record cache hit: {e}")

    # ==========================================
    # CACHE STORAGE
    # ==========================================

    async def cache_image(
        self,
        prompt: str,
        topics: List[str],
        domain: str,
        visual_style: str,
        slide_type: str,
        image_url: str,
        cropped_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        model_used: Optional[str] = None,
        generation_time_ms: Optional[int] = None,
        archetype: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store newly generated image in cache.

        Embedding is computed HERE (at cache time, not query time).
        This is the key optimization - embeddings are pre-computed.

        Args:
            prompt: Original generation prompt
            topics: Extracted topic keywords
            domain: Content domain (religious, healthcare, tech, etc.)
            visual_style: Visual style used
            slide_type: Slide type
            image_url: URL of generated image
            cropped_url: URL of cropped version (optional)
            thumbnail_url: URL of thumbnail (optional)
            model_used: Imagen model used
            generation_time_ms: Generation time in ms
            archetype: Image archetype
            metadata: Additional metadata

        Returns:
            Cache entry ID if successful, None otherwise
        """
        if not topics:
            logger.warning("No topics provided, skipping cache storage")
            return None

        try:
            # Generate embedding for prompt (one-time cost at cache time)
            embedding = None
            if self.embedding_service:
                try:
                    embedding = await self.embedding_service.generate(prompt)
                except Exception as e:
                    logger.warning(f"Embedding generation failed, caching without: {e}")

            # Build insert data
            insert_data = {
                "prompt_text": prompt,
                "topics": topics,
                "domain": domain,
                "visual_style": visual_style,
                "slide_type": slide_type,
                "image_url": image_url,
            }

            if embedding:
                insert_data["prompt_embedding"] = embedding

            if cropped_url:
                insert_data["cropped_url"] = cropped_url

            if thumbnail_url:
                insert_data["thumbnail_url"] = thumbnail_url

            if model_used:
                insert_data["model_used"] = model_used

            if generation_time_ms:
                insert_data["generation_time_ms"] = generation_time_ms

            if archetype:
                insert_data["archetype"] = archetype

            if metadata:
                insert_data["metadata"] = metadata

            # Insert into cache
            response = self.client.table("semantic_image_cache").insert(
                insert_data
            ).execute()

            if response.data and len(response.data) > 0:
                cache_id = response.data[0]["id"]
                logger.info(
                    f"Cached image: id={cache_id}, topics={topics}, "
                    f"domain={domain}, style={visual_style}"
                )
                return cache_id

            return None

        except Exception as e:
            logger.error(f"Failed to cache image: {e}")
            return None

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    async def get_cache_stats(
        self,
        domain: Optional[str] = None,
        visual_style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cache statistics.

        Args:
            domain: Filter by domain (optional)
            visual_style: Filter by visual style (optional)

        Returns:
            Statistics dictionary
        """
        try:
            query = self.client.table("semantic_cache_stats").select("*")

            if domain:
                query = query.eq("domain", domain)
            if visual_style:
                query = query.eq("visual_style", visual_style)

            response = query.execute()

            return {
                "stats": response.data if response.data else [],
                "total_cached": sum(r.get("total_images", 0) for r in (response.data or [])),
                "total_hits": sum(r.get("total_hits", 0) for r in (response.data or []))
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"stats": [], "total_cached": 0, "total_hits": 0}

    async def get_topic_distribution(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get distribution of topics in cache.

        Args:
            limit: Maximum number of topics to return

        Returns:
            List of topic counts
        """
        try:
            response = self.client.table("semantic_cache_topic_distribution").select(
                "*"
            ).limit(limit).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Failed to get topic distribution: {e}")
            return []


# Singleton instance
_cache_service: Optional[SemanticImageCacheService] = None


def get_semantic_cache_service() -> SemanticImageCacheService:
    """
    Get or create singleton cache service.

    Returns:
        SemanticImageCacheService instance
    """
    global _cache_service

    if _cache_service is None:
        _cache_service = SemanticImageCacheService()

    return _cache_service


def reset_semantic_cache_service():
    """Reset singleton (for testing)."""
    global _cache_service
    _cache_service = None


# For testing
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        cache = SemanticImageCacheService()

        # Test cache check (will likely miss on empty cache)
        result = await cache.check_cache(
            prompt="A serene Hindu temple with Lord Shiva statue at sunset",
            topics=["hinduism", "shiva", "temple"],
            visual_style="professional",
            slide_type="title_slide"
        )

        if result:
            print(f"Cache HIT: {result.image_url}")
        else:
            print("Cache MISS - would generate new image")

        # Get stats
        stats = await cache.get_cache_stats()
        print(f"Cache stats: {stats}")

    asyncio.run(test())
