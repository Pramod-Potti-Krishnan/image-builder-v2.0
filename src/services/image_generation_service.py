"""
Image Generation Service - Main Orchestrator
============================================

Orchestrates the complete image generation workflow:
0. Check semantic cache for similar images (two-tier caching)
1. Select optimal source aspect ratio
2. Generate image with fallback chain (Gemini → Imagen Fast → Imagen Regular)
3. Crop to target aspect ratio (if needed)
4. Apply background removal (if requested)
5. Upload to Supabase Storage
6. Cache result for future semantic matching
7. If ALL generators fail, try semantic cache with lower threshold (0.7)
8. Return URLs and metadata

Supports resilient image generation with fallback chain:
- Primary: Gemini 2.5 Flash Image - via google-genai SDK
- Fallback 1: Imagen 3 Fast - via google-cloud-aiplatform SDK
- Fallback 2: Imagen 3 Regular - via google-cloud-aiplatform SDK
- Last Resort: Semantic cache with 0.7 similarity threshold
"""

import os
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
import uuid

from ..models.image_models import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    BatchImageGenerationRequest,
    BatchImageGenerationResponse,
    ImageRecord
)
from .vertex_ai_service import VertexAIImageGenerator, remove_white_background, should_remove_background, VERTEX_AI_AVAILABLE
from .aspect_ratio_engine import get_aspect_ratio_strategy, crop_image_to_aspect_ratio
from .storage_service import SupabaseStorageService
from .database_service import ImageDatabaseService

# Gemini Image Generator (optional - graceful fallback to Imagen)
try:
    from .gemini_image_service import GeminiImageGenerator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Settings for fallback configuration
try:
    from ..config.settings import get_settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False

# Semantic cache imports (optional - graceful degradation if not available)
try:
    from .semantic_cache_service import SemanticImageCacheService, get_semantic_cache_service
    SEMANTIC_CACHE_AVAILABLE = True
except ImportError:
    SEMANTIC_CACHE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Main service orchestrating the complete image generation workflow.

    Includes two-tier semantic caching for hero slide backgrounds:
    - TIER 1: Fast keyword matching (< 10ms)
    - TIER 2: Semantic vector similarity (~50ms)
    """

    def __init__(
        self,
        vertex_ai_generator: Optional[VertexAIImageGenerator] = None,
        storage_service: Optional[SupabaseStorageService] = None,
        database_service: Optional[ImageDatabaseService] = None,
        semantic_cache_service: Optional["SemanticImageCacheService"] = None,
        enable_semantic_cache: bool = True
    ):
        """
        Initialize image generation service with resilient fallback chain.

        Args:
            vertex_ai_generator: Vertex AI generator instance (auto-created if None)
            storage_service: Supabase storage service (auto-created if None)
            database_service: Database service for metadata (auto-created if None)
            semantic_cache_service: Semantic cache for hero slides (auto-created if None)
            enable_semantic_cache: Whether to use semantic caching (default True)

        Environment Variables:
            IMAGE_GENERATOR: "gemini" (default) or "imagen" - selects primary backend
            GEMINI_MODEL: Gemini model to use (default: gemini-2.5-flash-image)
            ENABLE_GENERATOR_FALLBACK: Enable fallback chain (default: True)
        """
        # Load settings for fallback configuration
        self.settings = get_settings() if SETTINGS_AVAILABLE else None
        self.enable_fallback = (
            self.settings.enable_generator_fallback if self.settings else True
        )
        self.max_retries = self.settings.max_retries if self.settings else 2
        self.retry_delay_base = self.settings.retry_delay_base if self.settings else 1.0
        self.fallback_similarity_threshold = (
            self.settings.fallback_similarity_threshold if self.settings else 0.7
        )

        # Initialize PRIMARY generator
        self.primary_generator = None
        self.primary_generator_type = None

        # Initialize FALLBACK generators list
        self.fallback_generators: List[Dict[str, Any]] = []

        if vertex_ai_generator:
            # Use provided generator (for testing/custom config)
            self.primary_generator = vertex_ai_generator
            self.primary_generator_type = "custom"
        else:
            # Try to initialize Gemini as primary
            if GEMINI_AVAILABLE:
                try:
                    self.primary_generator = GeminiImageGenerator()
                    self.primary_generator_type = "gemini"
                    logger.info("Primary generator: Gemini 2.5 Flash Image")
                except Exception as e:
                    logger.warning(f"Gemini initialization failed: {e}")

            # Initialize Imagen generators as fallbacks (if available)
            if VERTEX_AI_AVAILABLE and self.enable_fallback:
                try:
                    # Imagen 3 Fast (fallback 1)
                    imagen_fast = VertexAIImageGenerator(
                        default_model="imagen-3.0-fast-generate-001"
                    )
                    self.fallback_generators.append({
                        "generator": imagen_fast,
                        "model": "imagen-3.0-fast-generate-001",
                        "name": "imagen-fast"
                    })
                    logger.info("Fallback 1: Imagen 3 Fast initialized")

                    # Imagen 3 Regular (fallback 2)
                    imagen_regular = VertexAIImageGenerator(
                        default_model="imagen-3.0-generate-001"
                    )
                    self.fallback_generators.append({
                        "generator": imagen_regular,
                        "model": "imagen-3.0-generate-001",
                        "name": "imagen-regular"
                    })
                    logger.info("Fallback 2: Imagen 3 Regular initialized")

                except Exception as e:
                    logger.warning(f"Imagen fallback initialization failed: {e}")

        # If no primary, use first fallback as primary
        if not self.primary_generator and self.fallback_generators:
            first_fallback = self.fallback_generators.pop(0)
            self.primary_generator = first_fallback["generator"]
            self.primary_generator_type = first_fallback["name"]
            logger.info(f"Using {first_fallback['name']} as primary (Gemini unavailable)")

        # Legacy compatibility: expose as self.vertex_ai
        self.vertex_ai = self.primary_generator
        self.generator_type = self.primary_generator_type or "unknown"

        self.storage = storage_service or SupabaseStorageService()
        self.database = database_service or ImageDatabaseService()

        # Initialize semantic cache (optional - graceful degradation)
        self.semantic_cache = None
        self.semantic_cache_enabled = enable_semantic_cache and SEMANTIC_CACHE_AVAILABLE

        if self.semantic_cache_enabled:
            try:
                self.semantic_cache = semantic_cache_service or get_semantic_cache_service()
                logger.info("Semantic image cache enabled")
            except Exception as e:
                logger.warning(f"Semantic cache not available: {e}")
                self.semantic_cache_enabled = False

        # Log configuration
        fallback_info = ", ".join([f["name"] for f in self.fallback_generators]) if self.fallback_generators else "none"
        logger.info(
            f"Initialized Image Generation Service "
            f"(primary: {self.primary_generator_type}, "
            f"fallbacks: [{fallback_info}], "
            f"cache_fallback_threshold: {self.fallback_similarity_threshold}, "
            f"semantic_cache: {'enabled' if self.semantic_cache_enabled else 'disabled'})"
        )

    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        Generate image according to request specifications.

        Includes semantic cache check for hero slide backgrounds.
        Cache lookup requires metadata with: topics, visual_style, slide_type, domain

        Args:
            request: Image generation request

        Returns:
            Image generation response with URLs and metadata
        """
        start_time = time.time()
        image_id = str(uuid.uuid4())

        try:
            logger.info(f"Starting image generation (ID: {image_id})")
            logger.info(f"Request: aspect_ratio={request.aspect_ratio}, archetype={request.archetype}")

            # Step 0: Check semantic cache (for hero slides with proper metadata)
            cache_result = await self._check_semantic_cache(request)
            if cache_result:
                # Cache HIT - return cached image
                generation_time_ms = int((time.time() - start_time) * 1000)
                logger.info(
                    f"Semantic cache HIT in {generation_time_ms}ms "
                    f"(similarity: {cache_result.get('similarity', 0):.3f})"
                )
                return ImageGenerationResponse(
                    success=True,
                    image_id=cache_result.get("cache_id", image_id),
                    urls={
                        "original": cache_result["image_url"],
                        "cropped": cache_result.get("cropped_url")
                    },
                    metadata={
                        "cache_hit": True,
                        "similarity": cache_result.get("similarity", 0),
                        "generation_time_ms": generation_time_ms,
                        "prompt": request.prompt,
                        "archetype": request.archetype,
                        "source": "semantic_cache"
                    }
                )

            # Step 1: Determine aspect ratio strategy
            strategy = get_aspect_ratio_strategy(request.aspect_ratio)
            source_ratio = strategy["source_ratio"]
            requires_crop = strategy["requires_crop"]

            logger.info(f"Aspect ratio strategy: {strategy['strategy']}")

            # Step 2: Generate image with fallback chain
            generation_result = await self._generate_with_fallback(
                prompt=request.prompt,
                aspect_ratio=source_ratio,
                negative_prompt=request.negative_prompt,
                model=request.model
            )

            if not generation_result["success"]:
                # ALL generators failed - try cache fallback with lower threshold
                cache_fallback = await self._try_cache_fallback(request)
                if cache_fallback:
                    generation_time_ms = int((time.time() - start_time) * 1000)
                    logger.info(
                        f"Cache FALLBACK hit in {generation_time_ms}ms "
                        f"(similarity: {cache_fallback.get('similarity', 0):.3f}, "
                        f"generators_attempted: {generation_result.get('generators_attempted', [])})"
                    )
                    return ImageGenerationResponse(
                        success=True,
                        image_id=cache_fallback.get("cache_id", image_id),
                        urls={
                            "original": cache_fallback["image_url"],
                            "cropped": cache_fallback.get("cropped_url")
                        },
                        metadata={
                            "cache_hit": True,
                            "cache_fallback": True,
                            "similarity": cache_fallback.get("similarity", 0),
                            "generation_time_ms": generation_time_ms,
                            "prompt": request.prompt,
                            "archetype": request.archetype,
                            "source": "semantic_cache_fallback",
                            "generators_attempted": generation_result.get("generators_attempted", [])
                        }
                    )

                # Final failure - all generators and cache failed
                return ImageGenerationResponse(
                    success=False,
                    image_id=image_id,
                    error=generation_result["error"],
                    metadata={
                        "generators_attempted": generation_result.get("generators_attempted", []),
                        "cache_fallback_attempted": True
                    }
                )

            original_bytes = generation_result["image_bytes"]
            logger.info(f"Image generated successfully ({len(original_bytes)} bytes)")

            # Step 3: Crop to target aspect ratio (if needed)
            cropped_bytes = None
            if requires_crop:
                crop_anchor = request.options.get("crop_anchor", "center")
                logger.info(f"Cropping to target ratio {request.aspect_ratio} (anchor: {crop_anchor})")

                cropped_bytes = crop_image_to_aspect_ratio(
                    image_bytes=original_bytes,
                    target_ratio_str=request.aspect_ratio,
                    anchor=crop_anchor
                )

                logger.info(f"Image cropped successfully ({len(cropped_bytes)} bytes)")

            # Step 4: Apply background removal (if requested)
            transparent_bytes = None
            should_remove_bg = request.options.get("remove_background", False)

            # Auto-detect for certain archetypes
            if not should_remove_bg:
                should_remove_bg = should_remove_background(request.archetype)

            if should_remove_bg:
                logger.info("Applying background removal")

                # Remove background from final image (cropped if available, otherwise original)
                source_for_transparency = cropped_bytes if cropped_bytes else original_bytes
                transparent_bytes = remove_white_background(source_for_transparency)

                logger.info(f"Background removed ({len(transparent_bytes)} bytes)")

            # Step 5: Upload to cloud storage (if enabled)
            urls = {}
            store_in_cloud = request.options.get("store_in_cloud", True)

            if store_in_cloud:
                logger.info("Uploading images to Supabase Storage")

                images_to_upload = {"original": original_bytes}

                if cropped_bytes:
                    images_to_upload["cropped"] = cropped_bytes

                if transparent_bytes:
                    images_to_upload["transparent"] = transparent_bytes

                upload_result = self.storage.upload_multiple_versions(
                    image_id=image_id,
                    images=images_to_upload,
                    folder="generated"
                )

                if upload_result["success"]:
                    urls = upload_result["urls"]
                    logger.info(f"Images uploaded successfully ({len(urls)} versions)")
                else:
                    logger.warning(f"Upload failed: {upload_result.get('error')}")

            # Step 6: Prepare response
            generation_time_ms = int((time.time() - start_time) * 1000)

            metadata = {
                "model": generation_result["metadata"].get("model", request.model),
                "platform": generation_result["metadata"].get("platform", "vertex-ai"),
                "generator": generation_result.get("generator_used", self.generator_type),
                "generator_used": generation_result.get("generator_used", self.generator_type),
                "fallback_used": generation_result.get("fallback_used", False),
                "generators_attempted": generation_result.get("generators_attempted", []),
                "source_aspect_ratio": source_ratio,
                "target_aspect_ratio": request.aspect_ratio,
                "cropped": requires_crop,
                "background_removed": transparent_bytes is not None,
                "generation_time_ms": generation_time_ms,
                "prompt": request.prompt,
                "archetype": request.archetype,
                "file_sizes": {
                    "original": len(original_bytes),
                    "cropped": len(cropped_bytes) if cropped_bytes else None,
                    "transparent": len(transparent_bytes) if transparent_bytes else None
                }
            }

            # Include base64 data if cloud storage is disabled
            base64_data = None
            if not store_in_cloud:
                base64_data = {
                    "original": generation_result["base64"],
                    "cropped": None,  # Could encode cropped_bytes if needed
                    "transparent": None  # Could encode transparent_bytes if needed
                }

            response = ImageGenerationResponse(
                success=True,
                image_id=image_id,
                urls=urls if urls else None,
                base64_data=base64_data,
                metadata=metadata
            )

            # Step 7: Save to database (if storage was successful)
            if store_in_cloud and urls:
                try:
                    db_result = self.database.save_image_record(
                        image_id=image_id,
                        prompt=request.prompt,
                        aspect_ratio=request.aspect_ratio,
                        archetype=request.archetype,
                        source_aspect_ratio=source_ratio,
                        target_aspect_ratio=request.aspect_ratio,
                        urls=urls,
                        paths=upload_result.get("paths", {}),
                        negative_prompt=request.negative_prompt,
                        crop_anchor=request.options.get("crop_anchor", "center"),
                        model=generation_result["metadata"].get("model", request.model),
                        platform="vertex-ai",
                        generation_time_ms=generation_time_ms,
                        original_size_bytes=len(original_bytes),
                        cropped_size_bytes=len(cropped_bytes) if cropped_bytes else None,
                        transparent_size_bytes=len(transparent_bytes) if transparent_bytes else None,
                        background_removed=transparent_bytes is not None,
                        cropped=requires_crop,
                        metadata=metadata
                    )

                    if db_result["success"]:
                        logger.info(f"Saved image metadata to database: {image_id}")
                    else:
                        logger.warning(f"Failed to save to database: {db_result.get('error')}")
                except Exception as e:
                    logger.error(f"Database save error (non-fatal): {e}")

                # Step 8: Store in semantic cache (for hero slides with metadata)
                await self._store_in_semantic_cache(
                    request=request,
                    urls=urls,
                    generation_time_ms=generation_time_ms,
                    model_used=generation_result["metadata"].get("model", request.model)
                )

            logger.info(f"Image generation completed in {generation_time_ms}ms")

            return response

        except Exception as e:
            logger.error(f"Image generation failed: {e}", exc_info=True)
            return ImageGenerationResponse(
                success=False,
                image_id=image_id,
                error=str(e),
                metadata={"generation_time_ms": int((time.time() - start_time) * 1000)}
            )

    async def generate_batch(
        self,
        batch_request: BatchImageGenerationRequest
    ) -> BatchImageGenerationResponse:
        """
        Generate multiple images with automatic rate limiting using semaphore.

        This method prevents hitting Vertex AI concurrent request limits by
        using a semaphore to control how many images are generated simultaneously.

        Args:
            batch_request: Batch generation request with list of image requests

        Returns:
            Batch generation response with results for each image
        """
        batch_start_time = time.time()
        batch_id = str(uuid.uuid4())

        logger.info(f"Starting batch generation (ID: {batch_id}, count: {len(batch_request.requests)}, max_concurrent: {batch_request.max_concurrent})")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(batch_request.max_concurrent)

        async def generate_with_limit(request: ImageGenerationRequest, index: int) -> ImageGenerationResponse:
            """Generate single image with semaphore rate limiting."""
            async with semaphore:  # Acquire semaphore slot
                logger.info(f"[Batch {batch_id}] Generating image {index+1}/{len(batch_request.requests)}...")

                try:
                    result = await self.generate(request)
                    logger.info(f"[Batch {batch_id}] Completed image {index+1}/{len(batch_request.requests)} - Success: {result.success}")
                    return result
                except Exception as e:
                    logger.error(f"[Batch {batch_id}] Error generating image {index+1}: {e}")
                    return ImageGenerationResponse(
                        success=False,
                        error=str(e)
                    )

        # Generate all images with automatic rate limiting
        tasks = [
            generate_with_limit(req, i)
            for i, req in enumerate(batch_request.requests)
        ]

        # Execute all tasks concurrently (semaphore controls actual concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Count successes and failures
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        batch_duration = time.time() - batch_start_time

        logger.info(
            f"Batch generation completed (ID: {batch_id}) - "
            f"Total: {len(results)}, Successful: {successful}, Failed: {failed}, "
            f"Duration: {batch_duration:.1f}s"
        )

        return BatchImageGenerationResponse(
            success=failed == 0,  # Success only if all succeeded
            total_requests=len(batch_request.requests),
            successful=successful,
            failed=failed,
            results=results,
            batch_id=batch_id
        )

    # ==========================================
    # SEMANTIC CACHE HELPER METHODS
    # ==========================================

    async def _check_semantic_cache(
        self,
        request: ImageGenerationRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Check semantic cache for similar image.

        Cache lookup requires metadata with:
        - topics: List of topic keywords
        - visual_style: Visual style (professional, illustrated, kids)
        - slide_type: Slide type (title_slide, section_divider, closing_slide)

        Args:
            request: Image generation request

        Returns:
            Dict with image_url, cropped_url, similarity if cache hit, None otherwise
        """
        if not self.semantic_cache_enabled or not self.semantic_cache:
            return None

        # Extract cache-required metadata
        metadata = request.metadata or {}
        topics = metadata.get("topics", [])
        visual_style = metadata.get("visual_style")
        slide_type = metadata.get("slide_type")

        # Skip cache if required metadata is missing
        if not topics or not visual_style or not slide_type:
            logger.debug(
                f"Skipping cache check: missing metadata "
                f"(topics={bool(topics)}, style={bool(visual_style)}, type={bool(slide_type)})"
            )
            return None

        try:
            # Perform two-tier cache lookup
            cached = await self.semantic_cache.check_cache(
                prompt=request.prompt,
                topics=topics,
                visual_style=visual_style,
                slide_type=slide_type
            )

            if cached:
                return {
                    "cache_id": cached.id,
                    "image_url": cached.image_url,
                    "cropped_url": cached.cropped_url,
                    "similarity": cached.similarity,
                    "hit_count": cached.hit_count
                }

            return None

        except Exception as e:
            logger.warning(f"Semantic cache check failed (non-fatal): {e}")
            return None

    async def _store_in_semantic_cache(
        self,
        request: ImageGenerationRequest,
        urls: Dict[str, str],
        generation_time_ms: int,
        model_used: str
    ) -> None:
        """
        Store generated image in semantic cache for future reuse.

        Only stores if required metadata is present:
        - topics: Topic keywords
        - visual_style: Visual style used
        - slide_type: Type of hero slide
        - domain: Content domain

        Args:
            request: Original generation request
            urls: Generated image URLs
            generation_time_ms: Generation time in ms
            model_used: Imagen model used
        """
        if not self.semantic_cache_enabled or not self.semantic_cache:
            return

        # Extract cache-required metadata
        metadata = request.metadata or {}
        topics = metadata.get("topics", [])
        visual_style = metadata.get("visual_style")
        slide_type = metadata.get("slide_type")
        domain = metadata.get("domain", "default")

        # Skip caching if required metadata is missing
        if not topics or not visual_style or not slide_type:
            logger.debug(
                f"Skipping cache storage: missing metadata "
                f"(topics={bool(topics)}, style={bool(visual_style)}, type={bool(slide_type)})"
            )
            return

        try:
            cache_id = await self.semantic_cache.cache_image(
                prompt=request.prompt,
                topics=topics,
                domain=domain,
                visual_style=visual_style,
                slide_type=slide_type,
                image_url=urls.get("original", ""),
                cropped_url=urls.get("cropped"),
                model_used=model_used,
                generation_time_ms=generation_time_ms,
                archetype=request.archetype,
                metadata={
                    "aspect_ratio": request.aspect_ratio,
                    "negative_prompt": request.negative_prompt
                }
            )

            if cache_id:
                logger.info(
                    f"Cached image for future semantic matching: "
                    f"topics={topics}, style={visual_style}, type={slide_type}"
                )

        except Exception as e:
            logger.warning(f"Semantic cache storage failed (non-fatal): {e}")

    # ==========================================
    # FALLBACK CHAIN HELPER METHODS
    # ==========================================

    async def _generate_with_fallback(
        self,
        prompt: str,
        aspect_ratio: str,
        negative_prompt: Optional[str],
        model: Optional[str]
    ) -> Dict[str, Any]:
        """
        Try generators in order: Primary → Fallback 1 → Fallback 2.

        Args:
            prompt: Image generation prompt
            aspect_ratio: Target aspect ratio
            negative_prompt: Negative prompt (optional)
            model: Model override (optional)

        Returns:
            Dict with success, image_bytes, metadata, generator_used, fallback_used
        """
        attempted = []
        last_error = None

        # Step 1: Try primary generator with retries
        if self.primary_generator:
            result = await self._try_generator_with_retry(
                generator=self.primary_generator,
                generator_name=self.primary_generator_type,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
                max_retries=self.max_retries
            )
            attempted.append(self.primary_generator_type)

            if result["success"]:
                result["generator_used"] = self.primary_generator_type
                result["fallback_used"] = False
                result["generators_attempted"] = attempted
                return result

            last_error = result.get("error")
            logger.warning(f"Primary generator ({self.primary_generator_type}) failed: {last_error}")

        # Step 2: Try fallback generators
        if self.enable_fallback:
            for fallback in self.fallback_generators:
                result = await self._try_generator_with_retry(
                    generator=fallback["generator"],
                    generator_name=fallback["name"],
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    model_override=fallback["model"],
                    max_retries=1  # Fewer retries for fallbacks
                )
                attempted.append(fallback["name"])

                if result["success"]:
                    result["generator_used"] = fallback["name"]
                    result["fallback_used"] = True
                    result["generators_attempted"] = attempted
                    logger.info(f"Fallback generator ({fallback['name']}) succeeded")
                    return result

                last_error = result.get("error")
                logger.warning(f"Fallback generator ({fallback['name']}) failed: {last_error}")

        # Step 3: All generators failed
        return {
            "success": False,
            "error": f"All generators failed. Last error: {last_error}",
            "generators_attempted": attempted,
            "fallback_used": False
        }

    async def _try_generator_with_retry(
        self,
        generator,
        generator_name: str,
        prompt: str,
        aspect_ratio: str,
        negative_prompt: Optional[str],
        model_override: Optional[str] = None,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Try generator with exponential backoff retries.

        Args:
            generator: Generator instance (Gemini or Imagen)
            generator_name: Name for logging
            prompt: Image prompt
            aspect_ratio: Target aspect ratio
            negative_prompt: Negative prompt (optional)
            model_override: Override model name (optional)
            max_retries: Maximum retry attempts

        Returns:
            Dict with success, image_bytes/error, metadata
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = await generator.generate_image(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    negative_prompt=negative_prompt,
                    model_name=model_override
                )

                if result["success"]:
                    return result

                last_error = result.get("error", "Unknown error")

                # Check if error is retryable
                if not self._is_retryable_error(last_error):
                    logger.info(f"Non-retryable error from {generator_name}: {last_error}")
                    break

            except Exception as e:
                last_error = str(e)

            # Wait before retry (exponential backoff)
            if attempt < max_retries:
                delay = (2 ** attempt) * self.retry_delay_base
                logger.info(
                    f"Retry {attempt + 1}/{max_retries} for {generator_name} in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        return {"success": False, "error": last_error}

    def _is_retryable_error(self, error: str) -> bool:
        """
        Check if error is transient and worth retrying.

        Args:
            error: Error message string

        Returns:
            True if error is retryable (rate limit, timeout, etc.)
        """
        retryable_patterns = [
            "429", "rate limit", "quota", "exceeded",
            "503", "service unavailable", "unavailable",
            "timeout", "timed out",
            "connection", "network",
            "temporarily", "try again",
            "overloaded", "capacity"
        ]
        error_lower = error.lower()
        return any(pattern in error_lower for pattern in retryable_patterns)

    async def _try_cache_fallback(
        self,
        request: ImageGenerationRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Try semantic cache with lower threshold as last resort.

        This is called when ALL generators have failed.
        Uses a lower similarity threshold (0.7 vs 0.85) to increase
        chances of finding a usable cached image.

        Args:
            request: Original image generation request

        Returns:
            Dict with image_url, cropped_url, similarity if found, None otherwise
        """
        if not self.semantic_cache_enabled or not self.semantic_cache:
            return None

        # Extract cache-required metadata
        metadata = request.metadata or {}
        topics = metadata.get("topics", [])
        visual_style = metadata.get("visual_style")
        slide_type = metadata.get("slide_type")

        # Skip if required metadata is missing
        if not topics or not visual_style or not slide_type:
            logger.debug("Cache fallback: missing required metadata")
            return None

        try:
            logger.info(
                f"Attempting cache fallback with threshold {self.fallback_similarity_threshold}"
            )

            # Use find_similar_image directly with lower threshold
            # (bypasses probability curve from Tier 1)
            cached = await self.semantic_cache.find_similar_image(
                prompt=request.prompt,
                topics=topics,
                visual_style=visual_style,
                slide_type=slide_type,
                threshold=self.fallback_similarity_threshold
            )

            if cached:
                # Record the cache hit
                await self.semantic_cache.record_hit(cached.id)

                logger.info(
                    f"Cache fallback HIT: similarity={cached.similarity:.3f} "
                    f"(threshold={self.fallback_similarity_threshold})"
                )

                return {
                    "cache_id": cached.id,
                    "image_url": cached.image_url,
                    "cropped_url": cached.cropped_url,
                    "similarity": cached.similarity,
                    "hit_count": cached.hit_count
                }

            logger.info("Cache fallback: no similar image found")
            return None

        except Exception as e:
            logger.warning(f"Cache fallback failed: {e}")
            return None


# For testing
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def test():
        service = ImageGenerationService()

        request = ImageGenerationRequest(
            prompt="A beautiful sunset over mountains",
            aspect_ratio="2:7",
            archetype="conceptual_metaphor",
            options={
                "remove_background": False,
                "crop_anchor": "center",
                "store_in_cloud": True
            }
        )

        response = await service.generate(request)
        print(f"Success: {response.success}")
        if response.urls:
            print(f"URLs: {response.urls}")
        if response.error:
            print(f"Error: {response.error}")

    # asyncio.run(test())  # Uncomment to test
    print("Image Generation Service ready")
