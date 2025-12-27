"""
Layout Generation Service
=========================

Main orchestrator for the Layout Service image generation endpoint.
Coordinates all services to generate, process, and store AI images.
"""

import logging
import time
import uuid
from typing import Optional

from ..models.layout_service_models import (
    LayoutImageGenerateRequest,
    LayoutImageGenerateResponse,
    LayoutImageResponseData,
    GeneratedImageData,
    LayoutImageMetadata,
    LayoutImageUsage,
    LayoutImageError,
    ErrorCodes,
    QUALITY_RESOLUTIONS,
    QUALITY_CREDITS
)
from .vertex_ai_service import VertexAIImageGenerator
from .storage_service import SupabaseStorageService
from .credits_service import CreditsService
from .style_engine import (
    build_enhanced_prompt,
    get_negative_prompt,
    calculate_dimensions_from_grid,
    calculate_dimensions_from_ratio,
    select_imagen_source_ratio,
    simplify_aspect_ratio,
    get_style_config
)
from .thumbnail_service import generate_thumbnail, get_image_dimensions
from .aspect_ratio_engine import crop_image_to_aspect_ratio, get_aspect_ratio_strategy

logger = logging.getLogger(__name__)


class LayoutGenerationService:
    """
    Main service orchestrating image generation for Layout Service.

    Workflow:
    1. Validate request
    2. Check credits availability
    3. Build enhanced prompt using style engine
    4. Determine aspect ratio and dimensions
    5. Generate image with Vertex AI
    6. Crop to exact aspect ratio (if needed)
    7. Generate thumbnail
    8. Upload images to Supabase Storage
    9. Record usage and deduct credits
    10. Return formatted response
    """

    def __init__(
        self,
        vertex_ai_generator: Optional[VertexAIImageGenerator] = None,
        storage_service: Optional[SupabaseStorageService] = None,
        credits_service: Optional[CreditsService] = None,
        enable_credits: bool = True,
        thumbnail_size: int = 256
    ):
        """
        Initialize layout generation service.

        Args:
            vertex_ai_generator: Vertex AI generator (auto-created if None)
            storage_service: Supabase storage service (auto-created if None)
            credits_service: Credits tracking service (auto-created if None)
            enable_credits: Whether to enforce credit limits
            thumbnail_size: Size for generated thumbnails
        """
        self.vertex_ai = vertex_ai_generator or VertexAIImageGenerator()
        self.storage = storage_service or SupabaseStorageService()
        self.credits = credits_service
        self.enable_credits = enable_credits and credits_service is not None
        self.thumbnail_size = thumbnail_size

        # Lazy init credits service if not provided
        if self.enable_credits and not self.credits:
            try:
                self.credits = CreditsService()
            except Exception as e:
                logger.warning(f"Could not initialize CreditsService: {e}")
                self.enable_credits = False

        logger.info(
            f"Initialized LayoutGenerationService "
            f"(credits_enabled={self.enable_credits}, thumbnail_size={thumbnail_size})"
        )

    async def generate(
        self,
        request: LayoutImageGenerateRequest
    ) -> LayoutImageGenerateResponse:
        """
        Generate image for Layout Service.

        Args:
            request: Layout image generation request

        Returns:
            Layout image generation response
        """
        start_time = time.time()
        generation_id = str(uuid.uuid4())

        try:
            logger.info(f"Starting layout generation (ID: {generation_id})")
            logger.info(f"Request: style={request.config.style}, quality={request.config.quality}")

            # ================================================================
            # Step 1: Validate request and check credits
            # ================================================================
            credits_required = QUALITY_CREDITS.get(request.config.quality, 2)

            if self.enable_credits and self.credits:
                remaining = self.credits.get_remaining_credits(request.presentationId)

                if remaining < credits_required:
                    logger.warning(
                        f"Insufficient credits for {request.presentationId}: "
                        f"required={credits_required}, available={remaining}"
                    )
                    return self._error_response(
                        code=ErrorCodes.INSUFFICIENT_CREDITS,
                        message=f"Not enough credits. Required: {credits_required}, Available: {remaining}",
                        retryable=False
                    )

            # ================================================================
            # Step 2: Build enhanced prompt
            # ================================================================
            enhanced_prompt = build_enhanced_prompt(
                user_prompt=request.prompt,
                style=request.config.style,
                color_scheme=request.options.colorScheme if request.options else None,
                lighting=request.options.lighting if request.options else None,
                brand_colors=request.context.brandColors
            )

            negative_prompt = get_negative_prompt(
                style=request.config.style,
                custom_negative=request.options.negativePrompt if request.options else None
            )

            logger.info(f"Enhanced prompt: {enhanced_prompt[:100]}...")

            # ================================================================
            # Step 3: Determine aspect ratio and dimensions
            # ================================================================
            if request.config.aspectRatio == 'custom':
                # Use grid dimensions for custom ratio
                target_ratio = simplify_aspect_ratio(
                    request.constraints.gridWidth,
                    request.constraints.gridHeight
                )
                target_width, target_height = calculate_dimensions_from_grid(
                    request.constraints.gridWidth,
                    request.constraints.gridHeight,
                    request.config.quality
                )
            else:
                # Use preset ratio
                target_ratio = request.config.aspectRatio
                target_width, target_height = calculate_dimensions_from_ratio(
                    request.config.aspectRatio,
                    request.config.quality
                )

            # Select best Imagen source ratio
            source_ratio = select_imagen_source_ratio(target_ratio)
            requires_crop = source_ratio != target_ratio

            logger.info(
                f"Aspect ratio: target={target_ratio}, source={source_ratio}, "
                f"dimensions={target_width}x{target_height}, crop_needed={requires_crop}"
            )

            # ================================================================
            # Step 4: Generate image with Vertex AI
            # ================================================================
            generation_result = await self.vertex_ai.generate_image(
                prompt=enhanced_prompt,
                aspect_ratio=source_ratio,
                negative_prompt=negative_prompt,
                model_name=None  # Use default model
            )

            if not generation_result.get("success"):
                error_msg = generation_result.get("error", "Image generation failed")
                logger.error(f"Vertex AI generation failed: {error_msg}")

                # Record failed generation (no credits charged)
                if self.enable_credits and self.credits:
                    self.credits.record_failed_generation(
                        generation_id=generation_id,
                        presentation_id=request.presentationId,
                        slide_id=request.slideId,
                        element_id=request.elementId,
                        quality=request.config.quality,
                        style=request.config.style,
                        prompt=request.prompt,
                        error_code=ErrorCodes.GENERATION_FAILED,
                        error_message=error_msg
                    )

                return self._error_response(
                    code=ErrorCodes.GENERATION_FAILED,
                    message=error_msg,
                    retryable=True
                )

            image_bytes = generation_result["image_bytes"]
            model_used = generation_result.get("metadata", {}).get("model", "imagen-3.0-fast-generate")

            logger.info(f"Image generated successfully ({len(image_bytes)} bytes)")

            # ================================================================
            # Step 5: Crop to target aspect ratio (if needed)
            # ================================================================
            final_image_bytes = image_bytes

            if requires_crop:
                logger.info(f"Cropping from {source_ratio} to {target_ratio}")
                try:
                    final_image_bytes = crop_image_to_aspect_ratio(
                        image_bytes=image_bytes,
                        target_ratio_str=target_ratio,
                        anchor="center"  # Could make configurable
                    )
                    logger.info(f"Cropped image: {len(final_image_bytes)} bytes")
                except Exception as e:
                    logger.error(f"Cropping failed: {e}")
                    # Continue with uncropped image
                    final_image_bytes = image_bytes

            # Get actual dimensions
            actual_width, actual_height = get_image_dimensions(final_image_bytes)

            # ================================================================
            # Step 6: Generate thumbnail
            # ================================================================
            try:
                thumbnail_bytes = generate_thumbnail(
                    image_bytes=final_image_bytes,
                    max_size=self.thumbnail_size
                )
                logger.info(f"Generated thumbnail: {len(thumbnail_bytes)} bytes")
            except Exception as e:
                logger.error(f"Thumbnail generation failed: {e}")
                # Create a simple fallback (use the full image as thumbnail)
                thumbnail_bytes = final_image_bytes

            # ================================================================
            # Step 7: Upload to Supabase Storage
            # ================================================================
            upload_result = self.storage.upload_with_thumbnail(
                generation_id=generation_id,
                image_bytes=final_image_bytes,
                thumbnail_bytes=thumbnail_bytes,
                folder="layout-images"
            )

            if not upload_result.get("success"):
                error_msg = upload_result.get("error", "Storage upload failed")
                logger.error(f"Upload failed: {error_msg}")

                # Record failed generation
                if self.enable_credits and self.credits:
                    self.credits.record_failed_generation(
                        generation_id=generation_id,
                        presentation_id=request.presentationId,
                        slide_id=request.slideId,
                        element_id=request.elementId,
                        quality=request.config.quality,
                        style=request.config.style,
                        prompt=request.prompt,
                        error_code=ErrorCodes.STORAGE_ERROR,
                        error_message=error_msg
                    )

                return self._error_response(
                    code=ErrorCodes.STORAGE_ERROR,
                    message=error_msg,
                    retryable=True
                )

            image_url = upload_result["image_url"]
            thumbnail_url = upload_result["thumbnail_url"]

            logger.info(f"Images uploaded: {image_url}")

            # ================================================================
            # Step 8: Deduct credits and record usage
            # ================================================================
            generation_time_ms = int((time.time() - start_time) * 1000)
            credits_remaining = 0

            if self.enable_credits and self.credits:
                # Deduct credits
                self.credits.deduct_credits(request.presentationId, credits_required)

                # Get remaining balance
                credits_remaining = self.credits.get_remaining_credits(request.presentationId)

                # Record usage
                self.credits.record_usage(
                    generation_id=generation_id,
                    presentation_id=request.presentationId,
                    slide_id=request.slideId,
                    element_id=request.elementId,
                    credits_used=credits_required,
                    quality=request.config.quality,
                    style=request.config.style,
                    prompt=request.prompt,
                    enhanced_prompt=enhanced_prompt,
                    image_url=image_url,
                    thumbnail_url=thumbnail_url,
                    width=actual_width,
                    height=actual_height,
                    generation_time_ms=generation_time_ms,
                    model=model_used,
                    provider="vertex-ai",
                    status="completed"
                )

            # ================================================================
            # Step 9: Build response
            # ================================================================
            image_data = GeneratedImageData(
                id=f"img-{generation_id[:8]}",
                url=image_url,
                thumbnailUrl=thumbnail_url,
                width=actual_width,
                height=actual_height,
                format="png",
                sizeBytes=len(final_image_bytes)
            )

            metadata = LayoutImageMetadata(
                prompt=request.prompt,
                style=request.config.style,
                aspectRatio=target_ratio,
                dimensions={"width": actual_width, "height": actual_height},
                provider="vertex-ai",
                model=model_used,
                generationTime=generation_time_ms
            )

            usage = LayoutImageUsage(
                creditsUsed=credits_required,
                creditsRemaining=credits_remaining
            )

            response_data = LayoutImageResponseData(
                generationId=generation_id,
                images=[image_data],
                metadata=metadata,
                usage=usage
            )

            logger.info(
                f"Layout generation completed (ID: {generation_id}) - "
                f"{generation_time_ms}ms, {credits_required} credits"
            )

            return LayoutImageGenerateResponse(
                success=True,
                data=response_data
            )

        except Exception as e:
            logger.error(f"Layout generation failed: {e}", exc_info=True)

            # Record failed generation
            if self.enable_credits and self.credits:
                try:
                    self.credits.record_failed_generation(
                        generation_id=generation_id,
                        presentation_id=request.presentationId,
                        slide_id=request.slideId,
                        element_id=request.elementId,
                        quality=request.config.quality,
                        style=request.config.style,
                        prompt=request.prompt,
                        error_code=ErrorCodes.INTERNAL_ERROR,
                        error_message=str(e)
                    )
                except Exception:
                    pass  # Don't fail on recording error

            return self._error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=str(e),
                retryable=True
            )

    def _error_response(
        self,
        code: str,
        message: str,
        retryable: bool,
        suggestion: Optional[str] = None
    ) -> LayoutImageGenerateResponse:
        """
        Create an error response.

        Args:
            code: Error code
            message: Error message
            retryable: Whether request can be retried
            suggestion: Optional suggestion for resolving error

        Returns:
            Error response
        """
        error = LayoutImageError(
            code=code,
            message=message,
            retryable=retryable,
            suggestion=suggestion
        )

        return LayoutImageGenerateResponse(
            success=False,
            error=error
        )


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("LayoutGenerationService module loaded")
    print("To test, run the FastAPI server and call /api/ai/image/generate")
