"""
Image Builder v2.0 - Illustration Generation Service

Main orchestration service for generating illustrations from uploaded images.
Uses Gemini 2.5 Flash to recreate images with standardized colors.
"""

import io
import os
import time
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from PIL import Image

from ..models.illustration_models import IllustrationGenerateResponse
from ..constants.illustration_colors import (
    DARK_COLOR_ORDER,
    get_colors_for_segments,
)
from .illustration_processor import IllustrationProcessor
from .storage_service import SupabaseStorageService
from .thumbnail_service import ThumbnailService

logger = logging.getLogger(__name__)


class IllustrationGenerationService:
    """
    Main orchestration service for illustration generation.

    Workflow:
    1. Receive uploaded image
    2. Get colors for requested unit_count
    3. Call Gemini 2.5 Flash to recreate with standardized colors
    4. Crop to content bounds
    5. Convert dark icons to white
    6. Generate thumbnail
    7. Upload to Supabase Storage
    8. Return public URLs
    """

    def __init__(
        self,
        storage_service: Optional[SupabaseStorageService] = None,
        processor: Optional[IllustrationProcessor] = None,
        thumbnail_size: int = 256
    ):
        """
        Initialize the illustration generation service.

        Args:
            storage_service: Supabase storage service for uploads
            processor: Image processor for crop/color conversion
            thumbnail_size: Size for thumbnail generation (default: 256px)
        """
        self.storage = storage_service
        self.processor = processor or IllustrationProcessor()
        self.thumbnail_size = thumbnail_size
        self.thumbnail_service = ThumbnailService()

        # Gemini client configuration
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-image")
        self._client = None

        logger.info(f"IllustrationGenerationService initialized with model={self.model}")

    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                from google import genai

                self._client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location
                )
                logger.info(f"Initialized Gemini client for project {self.project_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise

        return self._client

    async def generate(
        self,
        image_bytes: bytes,
        unit_count: int = 5,
        aspect_ratio: str = "16:9",
        original_filename: Optional[str] = None
    ) -> IllustrationGenerateResponse:
        """
        Generate an illustration from an uploaded image.

        Args:
            image_bytes: The uploaded image as bytes
            unit_count: Number of color segments (1-10)
            aspect_ratio: Output aspect ratio (e.g., "16:9")
            original_filename: Original filename for metadata

        Returns:
            IllustrationGenerateResponse with URLs and metadata
        """
        start_time = time.time()
        generation_id = str(uuid.uuid4())

        # Validate unit_count
        unit_count = min(max(1, unit_count), 10)

        # Get colors for the requested segments
        colors = get_colors_for_segments(unit_count)

        logger.info(
            f"Starting illustration generation: id={generation_id}, "
            f"unit_count={unit_count}, aspect_ratio={aspect_ratio}"
        )

        try:
            # Step 1: Generate with Gemini
            generated_bytes = await self._generate_with_gemini(
                image_bytes=image_bytes,
                num_segments=unit_count,
                colors=colors,
                aspect_ratio=aspect_ratio
            )

            if generated_bytes is None:
                return IllustrationGenerateResponse(
                    success=False,
                    generation_id=generation_id,
                    error="Gemini generation failed - no image returned",
                    metadata={"unit_count": unit_count, "aspect_ratio": aspect_ratio}
                )

            # Step 2: Process (crop + dark-to-white)
            processed_bytes = self.processor.process(generated_bytes)

            # Step 3: Generate thumbnail
            thumbnail_bytes = self.thumbnail_service.generate(
                processed_bytes,
                max_size=self.thumbnail_size
            )

            # Step 4: Upload to Supabase
            image_url = None
            thumbnail_url = None

            if self.storage:
                try:
                    # Upload original processed image
                    upload_result = self.storage.upload_image(
                        image_bytes=processed_bytes,
                        folder=f"illustrations/{generation_id}",
                        filename="original.png"
                    )
                    if upload_result.get("success"):
                        image_url = upload_result.get("url")

                    # Upload thumbnail
                    if thumbnail_bytes:
                        thumb_result = self.storage.upload_image(
                            image_bytes=thumbnail_bytes,
                            folder=f"illustrations/{generation_id}",
                            filename="thumbnail.png"
                        )
                        if thumb_result.get("success"):
                            thumbnail_url = thumb_result.get("url")

                    logger.info(f"Uploaded illustration to Supabase: {image_url}")

                except Exception as e:
                    logger.error(f"Failed to upload to Supabase: {e}")
                    # Continue without upload - return base64 instead
                    pass

            # Calculate timing
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Build metadata
            metadata = {
                "unit_count": unit_count,
                "aspect_ratio": aspect_ratio,
                "colors_used": colors,
                "generation_time_ms": generation_time_ms,
                "model": self.model
            }
            if original_filename:
                metadata["original_filename"] = original_filename

            logger.info(
                f"Illustration generation complete: id={generation_id}, "
                f"time={generation_time_ms}ms"
            )

            return IllustrationGenerateResponse(
                success=True,
                generation_id=generation_id,
                image_url=image_url,
                thumbnail_url=thumbnail_url,
                metadata=metadata,
                created_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Illustration generation failed: {e}", exc_info=True)
            return IllustrationGenerateResponse(
                success=False,
                generation_id=generation_id,
                error=str(e),
                metadata={"unit_count": unit_count, "aspect_ratio": aspect_ratio}
            )

    async def _generate_with_gemini(
        self,
        image_bytes: bytes,
        num_segments: int,
        colors: List[str],
        aspect_ratio: str = "16:9"
    ) -> Optional[bytes]:
        """
        Generate illustration using Gemini 2.5 Flash Image.

        Args:
            image_bytes: The original image as bytes
            num_segments: Number of segments/sections in the image
            colors: List of hex colors to use
            aspect_ratio: Output aspect ratio

        Returns:
            Generated image as bytes (PNG format) or None on failure
        """
        try:
            from google.genai import types

            client = self._get_client()

            # Convert image to PIL for analysis and ensure it's valid
            original_image = Image.open(io.BytesIO(image_bytes))
            logger.info(f"Original image size: {original_image.size}, mode: {original_image.mode}")

            # Convert to PNG bytes for consistent format
            img_buffer = io.BytesIO()
            if original_image.mode in ('P', 'RGBA', 'LA'):
                original_image = original_image.convert('RGB')
            original_image.save(img_buffer, format='PNG')
            png_bytes = img_buffer.getvalue()

            # Build the prompt
            prompt = self._build_recreation_prompt(num_segments, colors)

            # Create inline_data for the image
            image_part = types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=png_bytes
                )
            )
            text_part = types.Part(text=prompt)

            # Configure for image generation
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio
                )
            )

            logger.info(f"Sending request to Gemini {self.model}")

            # Generate the image - pass contents as list of parts
            response = client.models.generate_content(
                model=self.model,
                contents=[image_part, text_part],
                config=config
            )

            # Extract the generated image
            generated_bytes = self._extract_image_from_response(response)

            if generated_bytes:
                logger.info("Successfully generated image with Gemini")
                return generated_bytes
            else:
                logger.warning("Gemini did not return an image")
                return None

        except Exception as e:
            logger.error(f"Error in Gemini generation: {e}", exc_info=True)
            return None

    def _build_recreation_prompt(self, num_segments: int, colors: List[str]) -> str:
        """
        Build the prompt for image recreation.

        Args:
            num_segments: Number of color segments
            colors: List of hex colors to use

        Returns:
            Prompt string for Gemini
        """
        # Build color list with names
        color_list = []
        for i, hex_color in enumerate(colors):
            color_name = DARK_COLOR_ORDER[i % len(DARK_COLOR_ORDER)].upper()
            color_list.append(f"  {i+1}. {hex_color} ({color_name})")

        return f"""Recreate this infographic as a clean illustration.

CRITICAL COLOR RULES (MUST FOLLOW):
- All icons, symbols, and logos INSIDE colored segments = WHITE (#FFFFFF) only
- DO NOT use black for any icons or logos - use WHITE instead
- Never use black (#000000) for icons, symbols, or graphics

DARK THEME COLORS for segments:
{chr(10).join(color_list)}

TASK:
1. Trace the EXACT outline and shape of each sub-component in the image
2. Fill each sub-component with one of the DARK THEME COLORS above
3. Make ALL icons/symbols/logos inside segments WHITE (#FFFFFF)

RULES:
- Canvas background: WHITE (#FFFFFF)
- Each of the {num_segments} segments gets a DIFFERENT color from the list
- Icons inside colored areas: WHITE only (not black)
- FLAT colors only - no gradients, no shadows
- IGNORE any text in the original image
- Preserve exact shapes and layout
"""

    def _extract_image_from_response(self, response) -> Optional[bytes]:
        """
        Extract image bytes from Gemini response.

        Args:
            response: Gemini API response

        Returns:
            Image bytes or None
        """
        try:
            if hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                return part.inline_data.data
            return None
        except Exception as e:
            logger.error(f"Error extracting image from response: {e}")
            return None
