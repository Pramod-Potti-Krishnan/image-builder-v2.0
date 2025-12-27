"""
Layout Service Models
=====================

Pydantic models for the Layout Service image generation endpoint.
These models define the request/response schema for `/api/ai/image/generate`.
"""

from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid


# ============================================================================
# Enums and Types
# ============================================================================

ImageStyle = Literal['realistic', 'illustration', 'abstract', 'minimal', 'photo']
AspectRatioType = Literal['16:9', '4:3', '1:1', '9:16', 'custom']
ImageQuality = Literal['draft', 'standard', 'high', 'ultra']
ColorScheme = Literal['warm', 'cool', 'neutral', 'vibrant']
LightingStyle = Literal['natural', 'studio', 'dramatic', 'soft']


# ============================================================================
# Request Models
# ============================================================================

class LayoutImageContext(BaseModel):
    """Context about the presentation for style consistency."""

    presentationTitle: str = Field(..., description="Title of the presentation")
    presentationTheme: Optional[str] = Field(None, description="Theme/template of the presentation")
    slideTitle: Optional[str] = Field(None, description="Title of the current slide")
    slideIndex: int = Field(..., ge=0, description="Index of the current slide (0-based)")
    brandColors: Optional[List[str]] = Field(
        None,
        max_length=5,
        description="Brand colors as hex codes (e.g., ['#FF5733', '#33FF57'])"
    )
    existingImages: Optional[List[str]] = Field(
        None,
        description="URLs of other images in the deck for style consistency"
    )


class LayoutImageConfig(BaseModel):
    """Configuration for image generation."""

    style: ImageStyle = Field(..., description="Visual style for the image")
    aspectRatio: AspectRatioType = Field(default="16:9", description="Aspect ratio of the image")
    quality: ImageQuality = Field(default="standard", description="Resolution quality tier")


class LayoutImageConstraints(BaseModel):
    """Grid constraints for the image element."""

    gridWidth: int = Field(..., ge=1, le=12, description="Element width in grid units (1-12)")
    gridHeight: int = Field(..., ge=1, le=8, description="Element height in grid units (1-8)")

    @property
    def aspect_ratio_decimal(self) -> float:
        """Calculate aspect ratio from grid dimensions."""
        return self.gridWidth / self.gridHeight

    @property
    def aspect_ratio_string(self) -> str:
        """Get simplified aspect ratio string."""
        from math import gcd
        divisor = gcd(self.gridWidth, self.gridHeight)
        w = self.gridWidth // divisor
        h = self.gridHeight // divisor
        return f"{w}:{h}"


class LayoutImageOptions(BaseModel):
    """Optional advanced settings for image generation."""

    negativePrompt: Optional[str] = Field(
        None,
        max_length=500,
        description="What to avoid in the generated image"
    )
    seed: Optional[int] = Field(None, description="Seed for reproducibility")
    guidanceScale: Optional[float] = Field(
        None,
        ge=1.0,
        le=20.0,
        description="Prompt adherence strength (1-20)"
    )
    colorScheme: Optional[ColorScheme] = Field(None, description="Color palette preference")
    lighting: Optional[LightingStyle] = Field(None, description="Lighting style")


class LayoutImageGenerateRequest(BaseModel):
    """
    Request model for Layout Service image generation.

    Example:
    ```json
    {
        "prompt": "A modern office with happy employees collaborating",
        "presentationId": "pres-123",
        "slideId": "slide-456",
        "elementId": "elem-789",
        "context": {
            "presentationTitle": "Q4 Business Review",
            "slideTitle": "Team Culture",
            "slideIndex": 5,
            "brandColors": ["#0066CC", "#FF9900"]
        },
        "config": {
            "style": "photo",
            "aspectRatio": "custom",
            "quality": "high"
        },
        "constraints": {
            "gridWidth": 6,
            "gridHeight": 4
        },
        "options": {
            "colorScheme": "warm",
            "lighting": "natural"
        }
    }
    ```
    """

    # Required fields
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Description of desired image"
    )
    presentationId: str = Field(..., description="Unique presentation identifier")
    slideId: str = Field(..., description="Unique slide identifier")
    elementId: str = Field(..., description="Unique element identifier")

    # Context
    context: LayoutImageContext = Field(..., description="Presentation context")

    # Configuration
    config: LayoutImageConfig = Field(..., description="Image configuration")

    # Constraints
    constraints: LayoutImageConstraints = Field(..., description="Grid constraints")

    # Optional settings
    options: Optional[LayoutImageOptions] = Field(None, description="Advanced options")

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is meaningful."""
        if v and len(v.strip()) < 10:
            raise ValueError("Prompt must be at least 10 characters")
        return v.strip()


# ============================================================================
# Response Models
# ============================================================================

class GeneratedImageData(BaseModel):
    """Data for a generated image."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique image ID")
    url: str = Field(..., description="CDN URL to full image")
    thumbnailUrl: str = Field(..., description="URL to 256px thumbnail")
    width: int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")
    format: Literal['png', 'jpeg', 'webp'] = Field(default="png", description="Image format")
    sizeBytes: int = Field(..., gt=0, description="File size in bytes")
    expiresAt: Optional[str] = Field(None, description="URL expiration time (if temporary)")


class LayoutImageMetadata(BaseModel):
    """Metadata about the generation."""

    prompt: str = Field(..., description="Final prompt sent to model")
    style: ImageStyle = Field(..., description="Style used")
    aspectRatio: str = Field(..., description="Aspect ratio used")
    dimensions: Dict[str, int] = Field(..., description="Width and height in pixels")
    provider: str = Field(default="vertex-ai", description="AI provider used")
    model: str = Field(..., description="Specific model version")
    seed: Optional[int] = Field(None, description="Seed used for generation")
    generationTime: int = Field(..., description="Generation time in milliseconds")


class LayoutImageUsage(BaseModel):
    """Usage and credits information."""

    creditsUsed: int = Field(..., ge=0, description="Credits consumed for this generation")
    creditsRemaining: int = Field(..., ge=0, description="Credits remaining for presentation")


class LayoutImageError(BaseModel):
    """Error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    retryable: bool = Field(..., description="Whether the request can be retried")
    contentPolicyViolation: Optional[bool] = Field(
        None,
        description="True if blocked by content policy"
    )
    suggestion: Optional[str] = Field(None, description="Suggestion for resolving the error")


class LayoutImageResponseData(BaseModel):
    """Successful response data."""

    generationId: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="UUID for tracking/regeneration"
    )
    images: List[GeneratedImageData] = Field(..., description="List of generated images")
    metadata: LayoutImageMetadata = Field(..., description="Generation metadata")
    usage: LayoutImageUsage = Field(..., description="Credits usage")


class LayoutImageGenerateResponse(BaseModel):
    """
    Response model for Layout Service image generation.

    Success Example:
    ```json
    {
        "success": true,
        "data": {
            "generationId": "550e8400-e29b-41d4-a716-446655440000",
            "images": [{
                "id": "img-001",
                "url": "https://cdn.example.com/images/550e8400/original.png",
                "thumbnailUrl": "https://cdn.example.com/images/550e8400/thumb.png",
                "width": 1536,
                "height": 1024,
                "format": "png",
                "sizeBytes": 2457600
            }],
            "metadata": {
                "prompt": "A modern office...",
                "style": "photo",
                "aspectRatio": "3:2",
                "dimensions": {"width": 1536, "height": 1024},
                "provider": "vertex-ai",
                "model": "imagen-3.0-fast-generate",
                "generationTime": 4523
            },
            "usage": {
                "creditsUsed": 4,
                "creditsRemaining": 96
            }
        }
    }
    ```

    Error Example:
    ```json
    {
        "success": false,
        "error": {
            "code": "INSUFFICIENT_CREDITS",
            "message": "Not enough credits remaining",
            "retryable": false
        }
    }
    ```
    """

    success: bool = Field(..., description="Whether generation succeeded")
    data: Optional[LayoutImageResponseData] = Field(None, description="Response data if successful")
    error: Optional[LayoutImageError] = Field(None, description="Error info if failed")

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Error Code Constants
# ============================================================================

class ErrorCodes:
    """Standard error codes for image generation."""

    INVALID_PROMPT = "INVALID_PROMPT"
    INVALID_STYLE = "INVALID_STYLE"
    INVALID_ASPECT_RATIO = "INVALID_ASPECT_RATIO"
    INVALID_DIMENSIONS = "INVALID_DIMENSIONS"
    CONTENT_POLICY = "CONTENT_POLICY"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    GENERATION_FAILED = "GENERATION_FAILED"
    STORAGE_ERROR = "STORAGE_ERROR"
    THUMBNAIL_ERROR = "THUMBNAIL_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# ============================================================================
# Quality Configuration Constants
# ============================================================================

QUALITY_RESOLUTIONS = {
    'draft': 512,
    'standard': 1024,
    'high': 1536,
    'ultra': 2048
}

QUALITY_CREDITS = {
    'draft': 1,
    'standard': 2,
    'high': 4,
    'ultra': 8
}
