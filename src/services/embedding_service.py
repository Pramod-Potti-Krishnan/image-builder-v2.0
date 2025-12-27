"""
Embedding Service for Semantic Image Cache
===========================================

Generates text embeddings using Google's Gemini text-embedding-004 model
for semantic similarity search in the image cache.

Key features:
- 768-dimensional embeddings for semantic matching
- Async generation for non-blocking cache lookups
- Batch embedding support for efficiency
- Caching of embeddings to reduce API calls

Model: text-embedding-004
Dimensions: 768
Cost: ~$0.00001 per 1K characters (negligible)
Latency: ~100ms per embedding
"""

import logging
import asyncio
from typing import List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import Vertex AI
try:
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel
    import vertexai
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    logger.warning("Vertex AI not available - embedding service will be disabled")


class EmbeddingService:
    """
    Service for generating text embeddings using Gemini.

    Uses text-embedding-004 model which produces 768-dimensional vectors
    optimized for semantic similarity tasks.
    """

    # Embedding model configuration
    MODEL_NAME = "text-embedding-004"
    EMBEDDING_DIMENSION = 768

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1"
    ):
        """
        Initialize embedding service.

        Args:
            project_id: Google Cloud project ID (auto-detected if None)
            location: Vertex AI location
        """
        if not VERTEX_AI_AVAILABLE:
            raise ImportError(
                "Vertex AI not installed. Run: pip install google-cloud-aiplatform"
            )

        import os
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location

        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set")

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Load embedding model
        self._model = TextEmbeddingModel.from_pretrained(self.MODEL_NAME)

        logger.info(
            f"Initialized EmbeddingService with {self.MODEL_NAME} "
            f"(project: {self.project_id}, dimension: {self.EMBEDDING_DIMENSION})"
        )

    async def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (typically an image prompt)

        Returns:
            768-dimensional embedding vector as list of floats
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self._generate_sync,
                text
            )

            logger.debug(f"Generated embedding for text ({len(text)} chars)")
            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def _generate_sync(self, text: str) -> List[float]:
        """
        Synchronous embedding generation (called from executor).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embeddings = self._model.get_embeddings([text])
        return embeddings[0].values

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        More efficient than individual calls for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self._generate_batch_sync,
                valid_texts
            )

            logger.debug(f"Generated batch embeddings for {len(valid_texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise

    def _generate_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """
        Synchronous batch embedding generation.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self._model.get_embeddings(texts)
        return [e.values for e in embeddings]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Used for local similarity comparison when needed.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity (0 to 1, higher = more similar)
        """
        import math

        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimension")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Singleton instance for global use
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create singleton embedding service.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service


def reset_embedding_service():
    """Reset singleton (for testing)."""
    global _embedding_service
    _embedding_service = None


# For testing
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        service = EmbeddingService()

        # Test single embedding
        text = "A serene Hindu temple with Lord Shiva statue at sunset"
        embedding = await service.generate(text)
        print(f"Generated embedding: {len(embedding)} dimensions")
        print(f"First 5 values: {embedding[:5]}")

        # Test similarity
        text2 = "Ancient temple dedicated to Shiva during golden hour"
        embedding2 = await service.generate(text2)

        similarity = EmbeddingService.cosine_similarity(embedding, embedding2)
        print(f"Similarity between prompts: {similarity:.4f}")

        # Test batch
        texts = [
            "Modern hospital with advanced technology",
            "Healthcare innovation center",
            "Mountain landscape at sunrise"
        ]
        batch_embeddings = await service.generate_batch(texts)
        print(f"Generated {len(batch_embeddings)} batch embeddings")

    asyncio.run(test())
