"""
Atomic Image Generation Routes
==============================

FastAPI router for atomic image generation endpoints.
Provides simplified interface for frontend applications to generate images
with automatic element_id generation for Layout Service integration.

Endpoints:
- POST /api/v1/images/atomic/generate - Generate image
- GET /api/v1/images/atomic/health - Health check with capabilities
- GET /api/v1/images/atomic/styles - List available styles
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from ..models.atomic_models import (
    ImageAtomicRequest,
    ImageAtomicResponse,
    AtomicHealthResponse,
    StylesResponse,
    StyleInfo,
    MIN_GRID_SIZE,
    MAX_GRID_WIDTH,
    MAX_GRID_HEIGHT,
    GRID_CELL_SIZE
)
from ..models.layout_service_models import QUALITY_CREDITS
from ..services.atomic_generation_service import AtomicImageGenerationService
from ..services.style_engine import get_style_names, get_style_descriptions, STYLE_PROMPT_MODIFIERS

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/api/v1/images/atomic",
    tags=["Atomic Image Generation"]
)

# Global service instance (injected from main.py)
_atomic_service: Optional[AtomicImageGenerationService] = None


def get_atomic_service() -> AtomicImageGenerationService:
    """Dependency to get atomic service instance."""
    if _atomic_service is None:
        raise HTTPException(
            status_code=503,
            detail="Atomic image generation service not initialized"
        )
    return _atomic_service


def set_atomic_service(service: AtomicImageGenerationService):
    """Set the atomic service instance (called from main.py)."""
    global _atomic_service
    _atomic_service = service
    logger.info("Atomic image generation service configured")


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/generate",
    response_model=ImageAtomicResponse,
    summary="Generate image with automatic element ID",
    description="""
Generate an AI image and return URLs with an element_id for Layout Service integration.

**Features:**
- Grid-based dimensions (60px cells, 32x18 max grid)
- Automatic aspect ratio calculation
- Deterministic element_id generation
- Multiple quality tiers with credits
- Placeholder mode for testing

**Example Request:**
```json
{
    "prompt": "Modern office with team collaboration",
    "presentation_id": "pres-001",
    "slide_id": "slide-005",
    "grid_width": 16,
    "grid_height": 9,
    "config": {
        "style": "realistic",
        "quality": "standard"
    }
}
```

**Element ID Format:** `image_{uuid8}` (deterministic from slide_id + image_index)
"""
)
async def generate_atomic_image(
    request: ImageAtomicRequest,
    service: AtomicImageGenerationService = Depends(get_atomic_service)
) -> ImageAtomicResponse:
    """
    Generate an image from an atomic request.

    The element_id is deterministically generated from slide_id and image_index,
    ensuring the same request always produces the same element_id.
    """
    try:
        logger.info(
            f"Atomic generate request: prompt='{request.prompt[:50]}...', "
            f"grid={request.grid_width}x{request.grid_height}, "
            f"placeholder={request.placeholder_mode}"
        )

        response = await service.generate(request)

        if not response.success:
            logger.warning(f"Atomic generation failed: {response.error_code} - {response.error}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Atomic generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    response_model=AtomicHealthResponse,
    summary="Health check with capabilities",
    description="Returns service health status, available styles, and grid limits."
)
async def health_check() -> AtomicHealthResponse:
    """
    Health check endpoint for atomic image generation.

    Returns:
    - Service status (healthy/degraded/unhealthy)
    - Available capabilities
    - Available styles
    - Grid dimension limits
    """
    try:
        # Check if service is available
        service_available = _atomic_service is not None

        # Determine status
        if service_available:
            status = "healthy"
        else:
            status = "unhealthy"

        # Get available styles
        available_styles = get_style_names()

        return AtomicHealthResponse(
            status=status,
            version="1.0.0",
            capabilities={
                "image_generation": service_available,
                "placeholder_mode": True,
                "background_removal": False,  # Not yet implemented in atomic
                "thumbnail_generation": service_available
            },
            available_styles=available_styles,
            grid_limits={
                "min_width": MIN_GRID_SIZE,
                "max_width": MAX_GRID_WIDTH,
                "min_height": MIN_GRID_SIZE,
                "max_height": MAX_GRID_HEIGHT,
                "cell_size_px": GRID_CELL_SIZE
            }
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return AtomicHealthResponse(
            status="unhealthy",
            version="1.0.0",
            capabilities={},
            available_styles=[],
            grid_limits={}
        )


@router.get(
    "/styles",
    response_model=StylesResponse,
    summary="List available image styles",
    description="Returns all available image styles with descriptions and recommendations."
)
async def list_styles() -> StylesResponse:
    """
    List all available image styles.

    Returns style information including:
    - Style name and display name
    - Description
    - Recommended use cases
    - Credits per quality tier
    """
    try:
        styles = []
        style_descriptions = get_style_descriptions()

        for name, config in STYLE_PROMPT_MODIFIERS.items():
            desc = style_descriptions.get(name, {})
            styles.append(StyleInfo(
                name=name,
                display_name=config.get('name', name.title()),
                description=config.get('description', ''),
                recommended_for=config.get('recommended_for', [])
            ))

        return StylesResponse(
            styles=styles,
            default_style="realistic",
            quality_credits=dict(QUALITY_CREDITS)
        )

    except Exception as e:
        logger.error(f"Error listing styles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OpenAPI Documentation Extras
# ============================================================================

# Add example responses for better documentation
generate_atomic_image.responses = {
    200: {
        "description": "Successful image generation",
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "image_url": "https://storage.example.com/images/abc123/original.png",
                    "thumbnail_url": "https://storage.example.com/images/abc123/thumb.png",
                    "element_id": "image_a1b2c3d4",
                    "component_type": "IMAGE",
                    "metadata": {
                        "generation_time_ms": 4523,
                        "model_used": "imagen-3.0-fast-generate-001",
                        "grid_dimensions": {"width": 16, "height": 9},
                        "actual_dimensions": {"width": 1024, "height": 576},
                        "aspect_ratio": "16:9",
                        "style_applied": "realistic",
                        "provider": "vertex-ai",
                        "credits_used": 2
                    },
                    "timestamp": "2024-01-16T12:00:00Z"
                }
            }
        }
    },
    400: {
        "description": "Invalid request",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error": "Prompt must be at least 10 characters",
                    "error_code": "INVALID_PROMPT",
                    "retryable": False,
                    "timestamp": "2024-01-16T12:00:00Z"
                }
            }
        }
    },
    503: {
        "description": "Service unavailable",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Atomic image generation service not initialized"
                }
            }
        }
    }
}
