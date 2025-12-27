"""
Gemini 2.5 Flash Image Service
==============================

Wrapper for Google Cloud Vertex AI Gemini 2.5 Flash Image generation.
Drop-in replacement for VertexAIImageGenerator (Imagen).

Uses google-genai SDK with Vertex AI mode.
"""

import os
import base64
import logging
import json
import tempfile
from typing import Dict, Any, Optional
from io import BytesIO

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class GeminiImageGenerator:
    """
    Service for generating images using Google Cloud Vertex AI Gemini models.
    API-compatible with VertexAIImageGenerator for easy migration.
    """

    # Supported aspect ratios for Gemini 2.5 Flash Image
    SUPPORTED_RATIOS = [
        "1:1", "2:3", "3:2", "3:4", "4:3",
        "4:5", "5:4", "9:16", "16:9", "21:9"
    ]

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize Gemini image generator.

        Args:
            project_id: Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            location: Vertex AI location (defaults to VERTEX_AI_LOCATION env var or us-central1)
            default_model: Default Gemini model to use (defaults to gemini-2.5-flash-image)
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai not installed. Run: pip install google-genai>=1.56.0"
            )

        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set (env var or constructor)")

        self.location = location or os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.default_model = default_model or os.getenv(
            "GEMINI_MODEL", "gemini-2.5-flash-image"
        )

        # Handle base64-encoded credentials (for Railway/cloud deployments)
        self._setup_credentials()

        # Initialize Vertex AI client
        self.client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location
        )

        logger.info(
            f"Initialized Gemini Image Generator "
            f"(project: {self.project_id}, location: {self.location}, "
            f"model: {self.default_model})"
        )

    def _setup_credentials(self):
        """Handle base64-encoded credentials for cloud deployments."""
        creds_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_env:
            try:
                # Try to decode as base64 (Railway environment)
                decoded = base64.b64decode(creds_env)
                creds_json = json.loads(decoded)

                # Create temp file for credentials
                temp_creds = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False
                )
                json.dump(creds_json, temp_creds)
                temp_creds.flush()
                temp_creds.close()

                # Update environment to point to temp file
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds.name
                logger.info("Decoded base64 credentials and wrote to temporary file")

            except (base64.binascii.Error, json.JSONDecodeError, ValueError):
                # Not base64 or not valid JSON, assume it's a file path
                logger.info(f"Using credentials from file path: {creds_env}")

    def _validate_aspect_ratio(self, aspect_ratio: str) -> str:
        """
        Validate and normalize aspect ratio.

        Args:
            aspect_ratio: Requested aspect ratio (e.g., "16:9")

        Returns:
            Validated aspect ratio string
        """
        if aspect_ratio in self.SUPPORTED_RATIOS:
            return aspect_ratio

        # Try to find closest match
        logger.warning(
            f"Aspect ratio '{aspect_ratio}' not directly supported. "
            f"Supported: {self.SUPPORTED_RATIOS}"
        )
        return aspect_ratio  # Let the API handle the error

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        number_of_images: int = 1,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate image using Gemini 2.5 Flash Image.

        API-compatible with VertexAIImageGenerator.generate_image()

        Args:
            prompt: Image generation prompt
            aspect_ratio: One of: 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9
            negative_prompt: What to avoid (merged into prompt as "Avoid: ...")
            number_of_images: Ignored - Gemini returns 1 image per request
            model_name: Model to use (defaults to self.default_model)

        Returns:
            Dict with: success, image_bytes, base64, metadata, error
        """
        selected_model = model_name or self.default_model
        validated_ratio = self._validate_aspect_ratio(aspect_ratio)

        try:
            logger.info(
                f"Generating image with {selected_model} "
                f"(aspect_ratio: {validated_ratio})"
            )
            logger.info(f"Prompt: {prompt[:100]}...")

            # Handle negative prompt by merging into main prompt
            enhanced_prompt = prompt
            if negative_prompt:
                enhanced_prompt = f"{prompt}. Avoid: {negative_prompt}"
                logger.info(f"Merged negative prompt: {negative_prompt[:50]}...")

            # Configure image generation
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=validated_ratio
                )
            )

            # Generate image (synchronous call)
            response = self.client.models.generate_content(
                model=selected_model,
                contents=enhanced_prompt,
                config=config
            )

            # Check for safety blocks
            if response.candidates and response.candidates[0].finish_reason:
                finish_reason = str(response.candidates[0].finish_reason).upper()
                if "SAFETY" in finish_reason:
                    logger.warning(f"Image blocked by safety filter: {finish_reason}")
                    return {
                        "success": False,
                        "error": f"Image blocked by safety filter: {finish_reason}"
                    }

            # Extract image from response
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        img_base64 = base64.b64encode(image_bytes).decode('utf-8')

                        # Get dimensions if PIL available
                        dimensions = None
                        if PIL_AVAILABLE:
                            try:
                                img = Image.open(BytesIO(image_bytes))
                                dimensions = f"{img.size[0]}x{img.size[1]}"
                            except Exception:
                                pass

                        logger.info(
                            f"Successfully generated image "
                            f"({len(image_bytes)} bytes, {dimensions or 'unknown size'})"
                        )

                        return {
                            "success": True,
                            "image_bytes": image_bytes,
                            "base64": img_base64,
                            "metadata": {
                                "model": selected_model,
                                "aspect_ratio": validated_ratio,
                                "prompt": prompt,
                                "platform": "vertex-ai-gemini",
                                "size_bytes": len(image_bytes),
                                "dimensions": dimensions
                            }
                        }

            logger.warning("No image in response")
            return {
                "success": False,
                "error": "No image generated by Gemini"
            }

        except Exception as e:
            return self._handle_error(e)

    def _handle_error(self, e: Exception) -> Dict[str, Any]:
        """Convert exceptions to error response dict."""
        error_msg = str(e)
        logger.error(f"Gemini generation failed: {error_msg}")

        # Provide helpful error messages
        if "SAFETY" in error_msg.upper():
            return {
                "success": False,
                "error": "Image blocked by safety filter. Try rephrasing the prompt."
            }
        elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return {
                "success": False,
                "error": "Rate limit exceeded. Please try again in a minute."
            }
        elif "403" in error_msg or "permission" in error_msg.lower():
            return {
                "success": False,
                "error": "Permission denied. Ensure Vertex AI API is enabled."
            }
        elif "401" in error_msg or "authentication" in error_msg.lower():
            return {
                "success": False,
                "error": "Authentication failed. Check GOOGLE_APPLICATION_CREDENTIALS."
            }
        elif "404" in error_msg or "not found" in error_msg.lower():
            return {
                "success": False,
                "error": f"Model not found. Check model name: {self.default_model}"
            }
        else:
            return {
                "success": False,
                "error": f"Gemini error: {error_msg}"
            }


# Export for compatibility
__all__ = ["GeminiImageGenerator"]
