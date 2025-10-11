"""
Vertex AI Image Generation Service
===================================

Wrapper for Google Cloud Vertex AI Imagen 3 image generation.
Adapted from v1.0 with enhancements for v2.0.
"""

import os
import base64
import logging
from typing import Dict, Any, Optional
from io import BytesIO

try:
    import vertexai
    from vertexai.preview.vision_models import ImageGenerationModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class VertexAIImageGenerator:
    """
    Service for generating images using Google Cloud Vertex AI Imagen 3.
    """

    def __init__(self, project_id: Optional[str] = None, location: Optional[str] = None):
        """
        Initialize Vertex AI image generator.

        Args:
            project_id: Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: Vertex AI location (defaults to VERTEX_AI_LOCATION env var or us-central1)
        """
        if not VERTEX_AI_AVAILABLE:
            raise ImportError("google-cloud-aiplatform not installed. Run: pip install google-cloud-aiplatform")

        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set (env var or constructor)")

        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")

        # Handle base64-encoded credentials (for Railway/cloud deployments)
        creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_env:
            # Check if it's base64-encoded (Railway environment)
            try:
                # Try to decode as base64
                decoded = base64.b64decode(creds_env)
                # If successful, write to temporary file
                import tempfile
                import json

                # Verify it's valid JSON
                creds_json = json.loads(decoded)

                # Create temp file
                temp_creds = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(creds_json, temp_creds)
                temp_creds.flush()
                temp_creds.close()

                # Update environment to point to temp file
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds.name
                logger.info(f"Decoded base64 credentials and wrote to temporary file")

            except (base64.binascii.Error, json.JSONDecodeError, ValueError):
                # Not base64 or not valid JSON, assume it's a file path
                logger.info(f"Using credentials from file path: {creds_env}")
                pass

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Load model
        self.model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

        logger.info(f"Initialized Vertex AI Imagen (project: {self.project_id}, location: {self.location})")

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1
    ) -> Dict[str, Any]:
        """
        Generate image using Vertex AI Imagen 3.

        Args:
            prompt: Image generation prompt
            aspect_ratio: Aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9)
            negative_prompt: What to avoid in the image
            number_of_images: Number of images to generate (default 1)

        Returns:
            Dictionary with:
            - success: bool
            - image_bytes: bytes (if successful)
            - base64: base64 string (if successful)
            - metadata: dict with generation info
            - error: str (if failed)
        """
        try:
            logger.info(f"Generating image with Imagen 3 (aspect_ratio: {aspect_ratio})")
            logger.info(f"Prompt: {prompt[:100]}...")

            # Generate image
            response = self.model.generate_images(
                prompt=prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                language="en",
                # Note: negative_prompt might not be supported yet
                # Check Vertex AI docs for latest parameters
            )

            # Extract image
            if response and hasattr(response, 'images') and len(response.images) > 0:
                generated_image = response.images[0]
                image_bytes = generated_image._image_bytes

                # Convert to base64
                img_base64 = base64.b64encode(image_bytes).decode('utf-8')

                logger.info(f"Successfully generated image ({len(image_bytes)} bytes)")

                return {
                    "success": True,
                    "image_bytes": image_bytes,
                    "base64": img_base64,
                    "metadata": {
                        "model": "imagen-3.0-generate-002",
                        "aspect_ratio": aspect_ratio,
                        "prompt": prompt,
                        "platform": "vertex-ai",
                        "size_bytes": len(image_bytes)
                    }
                }
            else:
                logger.warning("No images generated")
                return {
                    "success": False,
                    "error": "No images generated by Vertex AI"
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Imagen 3 generation failed: {error_msg}")

            # Provide helpful error messages
            if "403" in error_msg or "permission" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Permission denied. Check Vertex AI API is enabled and you have permissions."
                }
            elif "401" in error_msg or "authentication" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Authentication failed. Check GOOGLE_APPLICATION_CREDENTIALS or gcloud auth."
                }
            elif "quota" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Quota exceeded. Check your Vertex AI quota limits."
                }
            else:
                return {
                    "success": False,
                    "error": f"Vertex AI error: {error_msg}"
                }


def remove_white_background(image_bytes: bytes, threshold: int = 240) -> bytes:
    """
    Remove white background from image using color threshold.

    Args:
        image_bytes: Raw image bytes
        threshold: RGB threshold for white detection (default 240)

    Returns:
        Bytes of transparent PNG
    """
    if not PIL_AVAILABLE:
        logger.warning("PIL not available, cannot remove background")
        return image_bytes

    try:
        # Open image
        img = Image.open(BytesIO(image_bytes))

        # Convert to RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Get pixel data
        data = img.getdata()

        # Create new data with transparency
        new_data = []
        for item in data:
            # Check if pixel is white-ish
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                # Make it transparent
                new_data.append((255, 255, 255, 0))
            else:
                # Keep original
                new_data.append(item)

        # Update image
        img.putdata(new_data)

        # Save to bytes
        output = BytesIO()
        img.save(output, format='PNG')

        logger.info("Background removal successful")

        return output.getvalue()

    except Exception as e:
        logger.error(f"Background removal failed: {e}")
        return image_bytes


def should_remove_background(archetype: str) -> bool:
    """
    Determine if background should be removed based on archetype.

    Args:
        archetype: Image archetype

    Returns:
        True if background should be removed
    """
    bg_removal_archetypes = {
        'minimalist_vector_art',
        'symbolic_representation',
        'icon',
        'logo'
    }

    return archetype.lower() in bg_removal_archetypes
