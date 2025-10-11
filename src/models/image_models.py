"""
Image Build Agent v2.0 - Data Models
====================================

Pydantic models for image generation requests and responses.
"""

from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


class AspectRatio(BaseModel):
    """Custom aspect ratio specification."""
    width: int = Field(..., gt=0, description="Width in ratio units")
    height: int = Field(..., gt=0, description="Height in ratio units")

    @property
    def ratio_string(self) -> str:
        """Get ratio as string (e.g., '2:7')."""
        return f"{self.width}:{self.height}"

    @property
    def decimal_value(self) -> float:
        """Get decimal aspect ratio."""
        return self.width / self.height

    @classmethod
    def from_string(cls, ratio_str: str) -> "AspectRatio":
        """Create from string like '2:7' or '16:9'."""
        width, height = map(int, ratio_str.split(':'))
        return cls(width=width, height=height)


class ImageGenerationRequest(BaseModel):
    """Request model for image generation."""

    # Core requirements
    prompt: str = Field(..., min_length=10, max_length=1000, description="Image generation prompt")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio (e.g., '16:9', '2:7', '1:1')")

    # Optional parameters
    archetype: str = Field(
        default="spot_illustration",
        description="Image archetype for styling (minimalist_vector_art, conceptual_metaphor, etc.)"
    )
    negative_prompt: Optional[str] = Field(
        default="blurry, low quality, distorted, text, watermark",
        description="What to avoid in the image"
    )

    # Processing options
    options: Dict[str, Any] = Field(
        default_factory=lambda: {
            "remove_background": False,
            "crop_anchor": "center",  # center, top, bottom, left, right, smart
            "quality": "high",  # high, medium
            "store_in_cloud": True,
        },
        description="Processing options"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for tracking"
    )

    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        """Validate aspect ratio format."""
        try:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError("Aspect ratio must be in format 'width:height'")
            width, height = map(int, parts)
            if width <= 0 or height <= 0:
                raise ValueError("Aspect ratio dimensions must be positive")
            return v
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid aspect ratio format: {e}")


class ImageGenerationResponse(BaseModel):
    """Response model for image generation."""

    success: bool = Field(..., description="Whether generation succeeded")
    image_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique image ID")

    # URLs (if stored in cloud)
    urls: Optional[Dict[str, str]] = Field(
        None,
        description="URLs for accessing images (original, cropped, transparent)"
    )

    # Base64 data (for immediate use)
    base64_data: Optional[Dict[str, str]] = Field(
        None,
        description="Base64 encoded images (original, cropped, transparent)"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation metadata (model, aspect_ratio, processing_time, etc.)"
    )

    # Error info (if failed)
    error: Optional[str] = Field(None, description="Error message if generation failed")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImageRecord(BaseModel):
    """Database record for generated image."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    aspect_ratio: str
    archetype: str

    # Storage URLs
    original_url: Optional[str] = None
    cropped_url: Optional[str] = None
    transparent_url: Optional[str] = None

    # Technical details
    source_aspect_ratio: str  # The Imagen ratio used for generation
    target_aspect_ratio: str  # The requested custom ratio
    crop_anchor: str = "center"

    # Metadata
    model: str = "imagen-3.0-generate-002"
    platform: str = "vertex-ai"
    generation_time_ms: Optional[int] = None
    file_sizes: Dict[str, int] = Field(default_factory=dict)

    # Options
    background_removed: bool = False
    has_transparent: bool = False

    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str = "2.0.0"
    services: Dict[str, bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
