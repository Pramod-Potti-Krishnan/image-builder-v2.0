"""
Atomic Image Generation Service
===============================

Service for handling atomic image generation requests.
Wraps LayoutGenerationService and converts between atomic and layout formats.

Key features:
- Deterministic element_id generation using uuid5
- Grid-to-pixel dimension conversion
- Placeholder mode for testing
- Consistent response format for Layout Service integration
"""

import logging
import time
import uuid
from typing import Optional
from datetime import datetime

from ..models.atomic_models import (
    ImageAtomicRequest,
    ImageAtomicResponse,
    ImageAtomicMetadata,
    ImageAtomicPosition,
    GRID_CELL_SIZE,
    QUALITY_CREDITS
)
from ..models.layout_service_models import (
    LayoutImageGenerateRequest,
    LayoutImageContext,
    LayoutImageConfig,
    LayoutImageConstraints,
    LayoutImageOptions,
    ErrorCodes,
    QUALITY_RESOLUTIONS
)
from .layout_generation_service import LayoutGenerationService

logger = logging.getLogger(__name__)

# Namespace UUID for deterministic element ID generation
# This ensures the same slide_id + image_index always produces the same element_id
ELEMENT_ID_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


class AtomicImageGenerationService:
    """
    Service for atomic image generation.

    Provides a simplified interface for frontend applications to generate
    images with automatic element_id generation for Layout Service integration.
    """

    def __init__(
        self,
        layout_service: LayoutGenerationService
    ):
        """
        Initialize atomic generation service.

        Args:
            layout_service: LayoutGenerationService instance for actual generation
        """
        self.layout_service = layout_service
        logger.info("Initialized AtomicImageGenerationService")

    def _generate_element_id(self, slide_id: str, image_index: int = 0) -> str:
        """
        Generate deterministic element ID for Layout Service.

        Uses UUID5 (SHA-1 based) to generate a deterministic ID from slide_id + index.
        Format: image_{8-char-hex}

        Args:
            slide_id: Unique slide identifier
            image_index: Index for multiple images on same slide

        Returns:
            Element ID in format: image_a1b2c3d4
        """
        # Create unique identifier from slide_id and image_index
        unique_key = f"{slide_id}:image:{image_index}"

        # Generate UUID5 (deterministic)
        element_uuid = uuid.uuid5(ELEMENT_ID_NAMESPACE, unique_key)

        # Take first 8 characters of hex representation
        element_id = f"image_{element_uuid.hex[:8]}"

        logger.debug(f"Generated element_id: {element_id} for slide={slide_id}, index={image_index}")

        return element_id

    def _to_layout_request(
        self,
        atomic_request: ImageAtomicRequest,
        element_id: str
    ) -> LayoutImageGenerateRequest:
        """
        Convert atomic request to layout service request.

        Args:
            atomic_request: Atomic generation request
            element_id: Generated element ID

        Returns:
            LayoutImageGenerateRequest for the layout service
        """
        # Build context from atomic context
        context = LayoutImageContext(
            presentationTitle=atomic_request.context.presentation_title if atomic_request.context else "Untitled",
            slideTitle=atomic_request.context.slide_title if atomic_request.context else None,
            slideIndex=atomic_request.image_index,
            brandColors=atomic_request.context.brand_colors if atomic_request.context else None
        )

        # Build config from atomic config
        config_data = atomic_request.config or {}
        config = LayoutImageConfig(
            style=config_data.style if hasattr(config_data, 'style') else "realistic",
            aspectRatio=atomic_request.aspect_ratio_override or "custom",
            quality=config_data.quality if hasattr(config_data, 'quality') else "standard"
        )

        # Build constraints from grid dimensions
        # Scale down to 1-12 range for layout service (it uses 12-column grid)
        # We map our 32-column grid to the 12-column layout service grid
        scaled_width = min(12, max(1, atomic_request.grid_width // 3 + 1))
        scaled_height = min(8, max(1, atomic_request.grid_height // 3 + 1))

        constraints = LayoutImageConstraints(
            gridWidth=scaled_width,
            gridHeight=scaled_height
        )

        # Build options from atomic options
        options = None
        if atomic_request.options:
            options = LayoutImageOptions(
                negativePrompt=atomic_request.options.negative_prompt,
                seed=atomic_request.options.seed,
                guidanceScale=atomic_request.options.guidance_scale,
                colorScheme=config_data.color_scheme if hasattr(config_data, 'color_scheme') else None,
                lighting=config_data.lighting if hasattr(config_data, 'lighting') else None
            )

        return LayoutImageGenerateRequest(
            prompt=atomic_request.prompt,
            presentationId=atomic_request.presentation_id,
            slideId=atomic_request.slide_id,
            elementId=element_id,
            context=context,
            config=config,
            constraints=constraints,
            options=options
        )

    def _to_atomic_response(
        self,
        layout_response,
        element_id: str,
        atomic_request: ImageAtomicRequest,
        generation_time_ms: int
    ) -> ImageAtomicResponse:
        """
        Convert layout service response to atomic response.

        Args:
            layout_response: Response from LayoutGenerationService
            element_id: Generated element ID
            atomic_request: Original atomic request
            generation_time_ms: Total generation time

        Returns:
            ImageAtomicResponse
        """
        if not layout_response.success:
            # Error response
            error_info = layout_response.error
            return ImageAtomicResponse(
                success=False,
                error=error_info.message if error_info else "Generation failed",
                error_code=error_info.code if error_info else ErrorCodes.GENERATION_FAILED,
                retryable=error_info.retryable if error_info else True
            )

        # Success response
        data = layout_response.data
        image_data = data.images[0] if data.images else None

        if not image_data:
            return ImageAtomicResponse(
                success=False,
                error="No image data in response",
                error_code=ErrorCodes.GENERATION_FAILED,
                retryable=True
            )

        # Build metadata
        config = atomic_request.config or {}
        metadata = ImageAtomicMetadata(
            generation_time_ms=generation_time_ms,
            model_used=data.metadata.model if data.metadata else "unknown",
            grid_dimensions={
                "width": atomic_request.grid_width,
                "height": atomic_request.grid_height
            },
            actual_dimensions={
                "width": image_data.width,
                "height": image_data.height
            },
            aspect_ratio=data.metadata.aspectRatio if data.metadata else atomic_request.calculated_aspect_ratio,
            style_applied=config.style if hasattr(config, 'style') else "realistic",
            provider=data.metadata.provider if data.metadata else "vertex-ai",
            credits_used=data.usage.creditsUsed if data.usage else 0
        )

        return ImageAtomicResponse(
            success=True,
            image_url=image_data.url,
            thumbnail_url=image_data.thumbnailUrl,
            element_id=element_id,
            component_type="IMAGE",
            position=atomic_request.position,  # Include position for Layout Service Element API
            metadata=metadata
        )

    def _placeholder_response(
        self,
        element_id: str,
        atomic_request: ImageAtomicRequest
    ) -> ImageAtomicResponse:
        """
        Generate placeholder response without AI generation.

        Useful for testing and development.

        Args:
            element_id: Generated element ID
            atomic_request: Original atomic request

        Returns:
            ImageAtomicResponse with placeholder data
        """
        config = atomic_request.config or {}

        # Generate placeholder dimensions based on quality
        quality = config.quality if hasattr(config, 'quality') else "standard"
        base_res = QUALITY_RESOLUTIONS.get(quality, 1024)

        # Calculate dimensions maintaining aspect ratio
        grid_ratio = atomic_request.grid_width / atomic_request.grid_height
        if grid_ratio >= 1.0:
            width = base_res
            height = int(base_res / grid_ratio)
        else:
            height = base_res
            width = int(base_res * grid_ratio)

        # Ensure even dimensions
        width = width if width % 2 == 0 else width + 1
        height = height if height % 2 == 0 else height + 1

        # Placeholder URLs
        placeholder_url = f"https://placehold.co/{width}x{height}/1a73e8/ffffff?text=Image+Placeholder"
        thumbnail_url = f"https://placehold.co/256x{int(256/grid_ratio)}/1a73e8/ffffff?text=Thumb"

        metadata = ImageAtomicMetadata(
            generation_time_ms=50,  # Simulated fast response
            model_used="placeholder",
            grid_dimensions={
                "width": atomic_request.grid_width,
                "height": atomic_request.grid_height
            },
            actual_dimensions={
                "width": width,
                "height": height
            },
            aspect_ratio=atomic_request.calculated_aspect_ratio,
            style_applied=config.style if hasattr(config, 'style') else "realistic",
            provider="placeholder",
            credits_used=0  # No credits used for placeholders
        )

        return ImageAtomicResponse(
            success=True,
            image_url=placeholder_url,
            thumbnail_url=thumbnail_url,
            element_id=element_id,
            component_type="IMAGE",
            position=atomic_request.position,  # Include position for Layout Service Element API
            metadata=metadata
        )

    async def generate(
        self,
        request: ImageAtomicRequest
    ) -> ImageAtomicResponse:
        """
        Generate an image from an atomic request.

        Args:
            request: Atomic image generation request

        Returns:
            ImageAtomicResponse with image URLs and element_id
        """
        start_time = time.time()

        try:
            # Generate element ID (deterministic)
            element_id = self._generate_element_id(
                request.slide_id,
                request.image_index
            )

            logger.info(
                f"Atomic generation: slide={request.slide_id}, "
                f"element_id={element_id}, grid={request.grid_width}x{request.grid_height}"
            )

            # Handle placeholder mode
            if request.placeholder_mode:
                logger.info(f"Placeholder mode: returning placeholder for {element_id}")
                return self._placeholder_response(element_id, request)

            # Convert to layout request
            layout_request = self._to_layout_request(request, element_id)

            # Generate image using layout service
            layout_response = await self.layout_service.generate(layout_request)

            # Calculate total time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Convert to atomic response
            response = self._to_atomic_response(
                layout_response,
                element_id,
                request,
                generation_time_ms
            )

            if response.success:
                logger.info(
                    f"Atomic generation complete: element_id={element_id}, "
                    f"time={generation_time_ms}ms"
                )
            else:
                logger.warning(
                    f"Atomic generation failed: element_id={element_id}, "
                    f"error={response.error_code}"
                )

            return response

        except Exception as e:
            logger.error(f"Atomic generation error: {e}", exc_info=True)

            return ImageAtomicResponse(
                success=False,
                error=str(e),
                error_code=ErrorCodes.INTERNAL_ERROR,
                retryable=True
            )


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test element ID generation
    service = AtomicImageGenerationService.__new__(AtomicImageGenerationService)

    # Test determinism
    id1 = service._generate_element_id("slide-001", 0)
    id2 = service._generate_element_id("slide-001", 0)
    id3 = service._generate_element_id("slide-001", 1)
    id4 = service._generate_element_id("slide-002", 0)

    print(f"Same slide+index: {id1} == {id2} ? {id1 == id2}")
    print(f"Same slide, diff index: {id1} != {id3} ? {id1 != id3}")
    print(f"Diff slide, same index: {id1} != {id4} ? {id1 != id4}")
