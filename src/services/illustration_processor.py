"""
Image Builder v2.0 - Illustration Processor

Handles post-processing of generated illustrations:
- Crop to content bounds (remove white canvas)
- Convert dark/black icons to white
"""

import io
import logging
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class IllustrationProcessor:
    """
    Processes generated illustrations to prepare them for use in slides.

    Main operations:
    1. Crop to content bounds (remove excess white canvas)
    2. Convert dark/black icons to white for visibility
    """

    def __init__(self):
        """Initialize the illustration processor with default settings."""
        # Threshold for white detection (higher = more strict)
        self.white_threshold = 250

        # Threshold for dark pixel detection (lower = more strict)
        self.dark_threshold = 60

        # Default margin for cropping
        self.default_margin = 2

    def crop_to_content(self, image_bytes: bytes, margin: int = None) -> bytes:
        """
        Crop image to content bounds, removing excess white canvas.

        This ensures the colored content is the focus and removes
        the vast white canvas that Gemini often generates.

        Args:
            image_bytes: Input image as bytes
            margin: Pixels of margin to add around content (default: 2)

        Returns:
            Cropped image as PNG bytes
        """
        if margin is None:
            margin = self.default_margin

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            pixels = image.load()
            white_threshold = self.white_threshold
            min_x, min_y = image.width, image.height
            max_x, max_y = 0, 0

            # Find bounds of non-white content
            for y in range(image.height):
                for x in range(image.width):
                    r, g, b = pixels[x, y][:3]
                    if not (r >= white_threshold and g >= white_threshold and b >= white_threshold):
                        min_x = min(min_x, x)
                        max_x = max(max_x, x)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y)

            # Handle edge case: no colored content found
            if min_x > max_x or min_y > max_y:
                logger.warning("No colored content found, returning original")
                return image_bytes

            logger.info(
                f"Content bounds detected: x=[{min_x}, {max_x}], y=[{min_y}, {max_y}] "
                f"in {image.size} image"
            )

            # Crop with margin
            left = max(0, min_x - margin)
            top = max(0, min_y - margin)
            right = min(image.width, max_x + margin)
            bottom = min(image.height, max_y + margin)

            cropped = image.crop((left, top, right, bottom))
            logger.info(f"Cropped from {image.size} to {cropped.size} with {margin}px margin")

            output = io.BytesIO()
            cropped.save(output, format='PNG')
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error in crop_to_content: {e}", exc_info=True)
            return image_bytes

    def convert_dark_to_white(self, image_bytes: bytes, dark_threshold: int = None) -> bytes:
        """
        Convert dark/black pixels to white.

        Gemini sometimes generates black icons inside colored segments.
        These should be white for better visibility on the dark backgrounds.

        Args:
            image_bytes: Input image as bytes
            dark_threshold: RGB threshold below which pixels are considered dark (default: 60)

        Returns:
            Image with dark pixels converted to white
        """
        if dark_threshold is None:
            dark_threshold = self.dark_threshold

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode != 'RGBA':
                image = image.convert('RGBA')

            pixels = image.load()
            width, height = image.size
            converted_count = 0

            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]

                    # Skip transparent pixels
                    if a < 128:
                        continue

                    # Check if pixel is dark/black (all channels below threshold)
                    if r < dark_threshold and g < dark_threshold and b < dark_threshold:
                        # Convert to white, preserving alpha
                        pixels[x, y] = (255, 255, 255, a)
                        converted_count += 1

            logger.info(f"Converted {converted_count} dark pixels to white")

            output = io.BytesIO()
            image.save(output, format='PNG')
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error converting dark to white: {e}", exc_info=True)
            return image_bytes

    def process(self, image_bytes: bytes, margin: int = None) -> bytes:
        """
        Full processing pipeline for an illustration.

        Steps:
        1. Crop to content bounds
        2. Convert dark icons to white

        Args:
            image_bytes: Input image as bytes
            margin: Pixels of margin for cropping

        Returns:
            Processed image as PNG bytes
        """
        # Step 1: Crop to content
        cropped = self.crop_to_content(image_bytes, margin)

        # Step 2: Convert dark to white
        processed = self.convert_dark_to_white(cropped)

        return processed

    def get_image_info(self, image_bytes: bytes) -> dict:
        """
        Get information about an image.

        Args:
            image_bytes: Image as bytes

        Returns:
            Dict with width, height, mode, format info
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            return {
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": image.format,
                "size_bytes": len(image_bytes)
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}
