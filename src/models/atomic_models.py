"""
Atomic Image Generation Models
==============================

Pydantic models for the atomic image generation endpoint.
This endpoint allows frontend users to directly generate images and add them
as elements to the Layout Service.

Follows patterns established by:
- Text Service: `/v1.2/atomic/`
- Analytics Service: `/api/v1/charts/atomic/`
"""

from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid

from .layout_service_models import (
    ImageStyle,
    ImageQuality,
    ColorScheme,
    LightingStyle,
    ErrorCodes,
    QUALITY_CREDITS
)


# ============================================================================
# Constants
# ============================================================================

# Grid cell size in pixels (matches Layout Service)
GRID_CELL_SIZE = 60

# Grid limits (32x18 grid = 1920x1080 at 60px cells)
MAX_GRID_WIDTH = 32
MAX_GRID_HEIGHT = 18
MIN_GRID_SIZE = 4


# ============================================================================
# Request Models
# ============================================================================

class ImageAtomicContext(BaseModel):
    """Optional context for better image generation."""

    slide_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Title of the current slide for context"
    )
    presentation_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Title of the presentation"
    )
    brand_colors: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="Brand colors as hex codes (e.g., ['#FF5733', '#33FF57'])"
    )

    @field_validator('brand_colors')
    @classmethod
    def validate_brand_colors(cls, v):
        """Validate hex color format."""
        if v:
            for color in v:
                if not color.startswith('#') or len(color) not in [4, 7]:
                    raise ValueError(f"Invalid hex color: {color}")
        return v


class ImageAtomicConfig(BaseModel):
    """Style and quality configuration for image generation."""

    style: ImageStyle = Field(
        default="realistic",
        description="Visual style for the image"
    )
    quality: ImageQuality = Field(
        default="standard",
        description="Resolution quality tier (affects credits: draft=1, standard=2, high=4, ultra=8)"
    )
    color_scheme: Optional[ColorScheme] = Field(
        None,
        description="Color palette preference"
    )
    lighting: Optional[LightingStyle] = Field(
        None,
        description="Lighting style"
    )


class ImageAtomicOptions(BaseModel):
    """Advanced generation options."""

    negative_prompt: Optional[str] = Field(
        None,
        max_length=500,
        description="What to avoid in the generated image"
    )
    seed: Optional[int] = Field(
        None,
        ge=0,
        description="Seed for reproducibility"
    )
    guidance_scale: Optional[float] = Field(
        None,
        ge=1.0,
        le=20.0,
        description="Prompt adherence strength (1-20)"
    )
    remove_background: bool = Field(
        default=False,
        description="Remove background from generated image"
    )


class ImageAtomicRequest(BaseModel):
    """
    Request model for atomic image generation.

    The frontend specifies grid dimensions (60px cells) and this service:
    1. Calculates aspect ratio from grid dimensions
    2. Generates image with AI
    3. Returns CDN URLs and element_id for Layout Service

    Example:
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
    """

    # Required fields
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Description of desired image (10-1000 characters)"
    )
    presentation_id: str = Field(
        ...,
        min_length=1,
        description="Unique presentation identifier (for credits tracking)"
    )
    slide_id: str = Field(
        ...,
        min_length=1,
        description="Unique slide identifier (for element ID generation)"
    )

    # Grid dimensions (60px cells)
    grid_width: int = Field(
        ...,
        ge=MIN_GRID_SIZE,
        le=MAX_GRID_WIDTH,
        description=f"Width in grid units ({MIN_GRID_SIZE}-{MAX_GRID_WIDTH}, each unit = {GRID_CELL_SIZE}px)"
    )
    grid_height: int = Field(
        ...,
        ge=MIN_GRID_SIZE,
        le=MAX_GRID_HEIGHT,
        description=f"Height in grid units ({MIN_GRID_SIZE}-{MAX_GRID_HEIGHT}, each unit = {GRID_CELL_SIZE}px)"
    )

    # Optional fields
    image_index: int = Field(
        default=0,
        ge=0,
        description="Index for multiple images on same slide (affects element_id)"
    )
    aspect_ratio_override: Optional[str] = Field(
        None,
        description="Override calculated aspect ratio (e.g., '16:9', '4:3')"
    )

    # Configuration
    config: Optional[ImageAtomicConfig] = Field(
        default_factory=ImageAtomicConfig,
        description="Style and quality configuration"
    )
    options: Optional[ImageAtomicOptions] = Field(
        default=None,
        description="Advanced generation options"
    )
    context: Optional[ImageAtomicContext] = Field(
        default=None,
        description="Presentation context for better generation"
    )

    # Testing mode
    placeholder_mode: bool = Field(
        default=False,
        description="Return placeholder without AI generation (for testing)"
    )

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is meaningful."""
        if v and len(v.strip()) < 10:
            raise ValueError("Prompt must be at least 10 characters")
        return v.strip()

    @field_validator('aspect_ratio_override')
    @classmethod
    def validate_aspect_ratio(cls, v: Optional[str]) -> Optional[str]:
        """Validate aspect ratio format."""
        if v:
            if ':' not in v:
                raise ValueError("Aspect ratio must be in format 'W:H' (e.g., '16:9')")
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Aspect ratio must be in format 'W:H' (e.g., '16:9')")
            try:
                w, h = int(parts[0]), int(parts[1])
                if w <= 0 or h <= 0:
                    raise ValueError("Aspect ratio values must be positive")
            except ValueError:
                raise ValueError("Aspect ratio values must be integers")
        return v

    @property
    def pixel_width(self) -> int:
        """Calculate pixel width from grid width."""
        return self.grid_width * GRID_CELL_SIZE

    @property
    def pixel_height(self) -> int:
        """Calculate pixel height from grid height."""
        return self.grid_height * GRID_CELL_SIZE

    @property
    def calculated_aspect_ratio(self) -> str:
        """Calculate aspect ratio from grid dimensions."""
        from math import gcd
        divisor = gcd(self.grid_width, self.grid_height)
        w = self.grid_width // divisor
        h = self.grid_height // divisor
        return f"{w}:{h}"


# ============================================================================
# Response Models
# ============================================================================

class ImageAtomicMetadata(BaseModel):
    """Metadata about the image generation."""

    model_config = {"protected_namespaces": ()}

    generation_time_ms: int = Field(
        ...,
        ge=0,
        description="Time taken to generate image in milliseconds"
    )
    model_used: str = Field(
        ...,
        description="AI model used for generation"
    )
    grid_dimensions: Dict[str, int] = Field(
        ...,
        description="Grid dimensions (width, height in grid units)"
    )
    actual_dimensions: Dict[str, int] = Field(
        ...,
        description="Actual image dimensions (width, height in pixels)"
    )
    aspect_ratio: str = Field(
        ...,
        description="Aspect ratio used for generation"
    )
    style_applied: str = Field(
        ...,
        description="Visual style applied"
    )
    provider: str = Field(
        default="vertex-ai",
        description="AI provider used"
    )
    credits_used: int = Field(
        ...,
        ge=0,
        description="Credits consumed for this generation"
    )


class ImageAtomicResponse(BaseModel):
    """
    Response model for atomic image generation.

    Success Example:
    ```json
    {
        "success": true,
        "image_url": "https://cdn.example.com/images/abc123/original.png",
        "thumbnail_url": "https://cdn.example.com/images/abc123/thumb.png",
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
    ```

    Error Example:
    ```json
    {
        "success": false,
        "error": "INSUFFICIENT_CREDITS",
        "error_code": "INSUFFICIENT_CREDITS",
        "retryable": false,
        "timestamp": "2024-01-16T12:00:00Z"
    }
    ```
    """

    # Status
    success: bool = Field(
        ...,
        description="Whether generation succeeded"
    )

    # Success fields (only present when success=true)
    image_url: Optional[str] = Field(
        None,
        description="CDN URL to full-size image"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="CDN URL to thumbnail (256px)"
    )
    element_id: Optional[str] = Field(
        None,
        description="Element ID for Layout Service (format: image_{uuid8})"
    )
    component_type: Literal["IMAGE"] = Field(
        default="IMAGE",
        description="Component type for Layout Service"
    )
    metadata: Optional[ImageAtomicMetadata] = Field(
        None,
        description="Generation metadata"
    )

    # Error fields (only present when success=false)
    error: Optional[str] = Field(
        None,
        description="Human-readable error message"
    )
    error_code: Optional[str] = Field(
        None,
        description="Structured error code"
    )
    retryable: Optional[bool] = Field(
        None,
        description="Whether the request can be retried"
    )

    # Timestamp
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


# ============================================================================
# Health Check Models
# ============================================================================

class AtomicHealthResponse(BaseModel):
    """Health check response for atomic endpoint."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Service health status"
    )
    version: str = Field(
        default="1.0.0",
        description="Atomic endpoint version"
    )
    capabilities: Dict[str, bool] = Field(
        default_factory=dict,
        description="Available capabilities"
    )
    available_styles: List[str] = Field(
        default_factory=list,
        description="List of available image styles"
    )
    grid_limits: Dict[str, int] = Field(
        default_factory=lambda: {
            "min_width": MIN_GRID_SIZE,
            "max_width": MAX_GRID_WIDTH,
            "min_height": MIN_GRID_SIZE,
            "max_height": MAX_GRID_HEIGHT,
            "cell_size_px": GRID_CELL_SIZE
        },
        description="Grid dimension limits"
    )


class StyleInfo(BaseModel):
    """Information about an available style."""

    name: str = Field(..., description="Style identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Style description")
    recommended_for: List[str] = Field(
        default_factory=list,
        description="Recommended use cases"
    )


class StylesResponse(BaseModel):
    """Response for listing available styles."""

    styles: List[StyleInfo] = Field(
        ...,
        description="Available image styles"
    )
    default_style: str = Field(
        default="realistic",
        description="Default style when not specified"
    )
    quality_credits: Dict[str, int] = Field(
        default_factory=lambda: dict(QUALITY_CREDITS),
        description="Credits required per quality tier"
    )
