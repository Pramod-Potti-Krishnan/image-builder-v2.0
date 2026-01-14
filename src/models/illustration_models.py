"""
Image Builder v2.0 - Illustration Generation Models

Pydantic models for the illustration generation endpoint.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from pydantic import BaseModel, Field


class IllustrationGenerateResponse(BaseModel):
    """Response model for illustration generation."""

    success: bool = Field(
        ...,
        description="Whether generation succeeded"
    )
    generation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique generation ID"
    )

    # URLs
    image_url: Optional[str] = Field(
        None,
        description="Public Supabase URL for processed image"
    )
    thumbnail_url: Optional[str] = Field(
        None,
        description="Public Supabase URL for thumbnail (256px)"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Generation metadata including colors used, timing, etc."
    )

    # Error info
    error: Optional[str] = Field(
        None,
        description="Error message if generation failed"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of generation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "generation_id": "550e8400-e29b-41d4-a716-446655440000",
                "image_url": "https://example.supabase.co/storage/v1/object/public/illustrations/550e8400.../original.png",
                "thumbnail_url": "https://example.supabase.co/storage/v1/object/public/illustrations/550e8400.../thumbnail.png",
                "metadata": {
                    "unit_count": 5,
                    "aspect_ratio": "16:9",
                    "colors_used": ["#805AA0", "#2980B9", "#C0392B", "#27AE60", "#D39E1E"],
                    "generation_time_ms": 5200,
                    "original_filename": "my_diagram.png"
                },
                "error": None,
                "created_at": "2024-01-13T12:00:00Z"
            }
        }
