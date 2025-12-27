"""
Image Generation Service - Main Orchestrator
============================================

Orchestrates the complete image generation workflow:
0. Check semantic cache for similar images (NEW - two-tier caching)
1. Select optimal source aspect ratio
2. Generate image with Vertex AI (Gemini or Imagen)
3. Crop to target aspect ratio (if needed)
4. Apply background removal (if requested)
5. Upload to Supabase Storage
6. Cache result for future semantic matching (NEW)
7. Return URLs and metadata

Supports two image generation backends:
- Gemini 2.5 Flash Image (default) - via google-genai SDK
- Imagen 3 (fallback) - via google-cloud-aiplatform SDK
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
from .vertex_ai_service import VertexAIImageGenerator, remove_white_background, should_remove_background
from .aspect_ratio_engine import get_aspect_ratio_strategy, crop_image_to_aspect_ratio
from .storage_service import SupabaseStorageService
from .database_service import ImageDatabaseService

# Gemini Image Generator (optional - graceful fallback to Imagen)
try:
    from .gemini_image_service import GeminiImageGenerator
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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
        Initialize image generation service.

        Args:
            vertex_ai_generator: Vertex AI generator instance (auto-created if None)
            storage_service: Supabase storage service (auto-created if None)
            database_service: Database service for metadata (auto-created if None)
            semantic_cache_service: Semantic cache for hero slides (auto-created if None)
            enable_semantic_cache: Whether to use semantic caching (default True)

        Environment Variables:
            IMAGE_GENERATOR: "gemini" (default) or "imagen" - selects image generation backend
            GEMINI_MODEL: Gemini model to use (default: gemini-2.5-flash-image)
        """
        # Select image generator based on IMAGE_GENERATOR env var
        image_generator_type = os.getenv("IMAGE_GENERATOR", "gemini").lower()

        if vertex_ai_generator:
            # Use provided generator (for testing/custom config)
            self.vertex_ai = vertex_ai_generator
            self.generator_type = "custom"
        elif image_generator_type == "gemini" and GEMINI_AVAILABLE:
            # Default: Use Gemini 2.5 Flash Image
            try:
                self.vertex_ai = GeminiImageGenerator()
                self.generator_type = "gemini"
                logger.info("Using Gemini 2.5 Flash Image generator")
            except Exception as e:
                logger.warning(f"Gemini initialization failed, falling back to Imagen: {e}")
                self.vertex_ai = VertexAIImageGenerator()
                self.generator_type = "imagen"
        else:
            # Fallback: Use Imagen 3
            self.vertex_ai = VertexAIImageGenerator()
            self.generator_type = "imagen"
            if image_generator_type == "gemini" and not GEMINI_AVAILABLE:
                logger.warning("Gemini not available (google-genai not installed), using Imagen")
            else:
                logger.info("Using Imagen 3 generator")

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

        logger.info(
            f"Initialized Image Generation Service "
            f"(generator: {self.generator_type}, "
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

            # Step 2: Generate image with Vertex AI
            generation_result = await self.vertex_ai.generate_image(
                prompt=request.prompt,
                aspect_ratio=source_ratio,
                negative_prompt=request.negative_prompt,
                model_name=request.model
            )

            if not generation_result["success"]:
                return ImageGenerationResponse(
                    success=False,
                    image_id=image_id,
                    error=generation_result["error"]
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
                "generator": self.generator_type,
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
