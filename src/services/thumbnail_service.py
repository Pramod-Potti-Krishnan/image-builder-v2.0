"""
Thumbnail Service
=================

Generates high-quality thumbnails from images using PIL.
Used by the Layout Service to provide preview images.
"""

import logging
from io import BytesIO
from typing import Tuple, Optional

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_THUMBNAIL_SIZE = 256
THUMBNAIL_FORMAT = 'PNG'
THUMBNAIL_QUALITY = 90  # For JPEG/WebP
RESAMPLING_METHOD = Image.Resampling.LANCZOS if PIL_AVAILABLE else None


# ============================================================================
# Thumbnail Generation Functions
# ============================================================================

def generate_thumbnail(
    image_bytes: bytes,
    max_size: int = DEFAULT_THUMBNAIL_SIZE,
    format: str = 'PNG',
    quality: int = THUMBNAIL_QUALITY
) -> bytes:
    """
    Generate a thumbnail from image bytes.

    Uses LANCZOS resampling for high quality downscaling.
    Maintains aspect ratio.

    Args:
        image_bytes: Original image bytes
        max_size: Maximum dimension (width or height) for thumbnail
        format: Output format (PNG, JPEG, WEBP)
        quality: Quality for lossy formats (1-100)

    Returns:
        Thumbnail image bytes

    Raises:
        ImportError: If PIL is not available
        ValueError: If image_bytes is empty or invalid
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is not installed. Run: pip install Pillow")

    if not image_bytes:
        raise ValueError("Empty image bytes provided")

    try:
        # Open image
        img = Image.open(BytesIO(image_bytes))

        # Get original dimensions
        original_width, original_height = img.size

        # Calculate new dimensions maintaining aspect ratio
        new_width, new_height = calculate_thumbnail_dimensions(
            original_width,
            original_height,
            max_size
        )

        # Resize with high quality resampling
        thumbnail = img.resize((new_width, new_height), RESAMPLING_METHOD)

        # Convert to RGB if saving as JPEG
        if format.upper() == 'JPEG' and thumbnail.mode in ('RGBA', 'P'):
            thumbnail = thumbnail.convert('RGB')

        # Save to bytes
        output = BytesIO()

        save_kwargs = {'format': format.upper(), 'optimize': True}
        if format.upper() in ('JPEG', 'WEBP'):
            save_kwargs['quality'] = quality

        thumbnail.save(output, **save_kwargs)

        thumbnail_bytes = output.getvalue()

        logger.info(
            f"Generated thumbnail: {original_width}x{original_height} -> "
            f"{new_width}x{new_height} ({len(thumbnail_bytes)} bytes)"
        )

        return thumbnail_bytes

    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        raise


def calculate_thumbnail_dimensions(
    original_width: int,
    original_height: int,
    max_size: int
) -> Tuple[int, int]:
    """
    Calculate thumbnail dimensions maintaining aspect ratio.

    The larger dimension will be scaled to max_size, and the smaller
    dimension will be scaled proportionally.

    Args:
        original_width: Original image width
        original_height: Original image height
        max_size: Maximum dimension size

    Returns:
        Tuple of (new_width, new_height)

    Example:
        original: 1920x1080, max_size: 256
        result: 256x144 (maintaining 16:9 ratio)
    """
    if original_width <= 0 or original_height <= 0:
        raise ValueError("Invalid image dimensions")

    if original_width > original_height:
        # Landscape: width is max
        new_width = max_size
        new_height = int(original_height * (max_size / original_width))
    elif original_height > original_width:
        # Portrait: height is max
        new_height = max_size
        new_width = int(original_width * (max_size / original_height))
    else:
        # Square
        new_width = max_size
        new_height = max_size

    # Ensure minimum dimensions
    new_width = max(1, new_width)
    new_height = max(1, new_height)

    return (new_width, new_height)


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """
    Get dimensions of an image from bytes.

    Args:
        image_bytes: Image bytes

    Returns:
        Tuple of (width, height)
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is not installed")

    img = Image.open(BytesIO(image_bytes))
    return img.size


def get_image_format(image_bytes: bytes) -> str:
    """
    Detect the format of an image from bytes.

    Args:
        image_bytes: Image bytes

    Returns:
        Format string (e.g., 'PNG', 'JPEG', 'WEBP')
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is not installed")

    img = Image.open(BytesIO(image_bytes))
    return img.format or 'PNG'


def convert_to_webp(image_bytes: bytes, quality: int = 85) -> bytes:
    """
    Convert image to WebP format for smaller file sizes.

    Args:
        image_bytes: Original image bytes
        quality: WebP quality (1-100)

    Returns:
        WebP image bytes
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is not installed")

    img = Image.open(BytesIO(image_bytes))

    # Convert RGBA to RGB with white background for WebP
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background

    output = BytesIO()
    img.save(output, format='WEBP', quality=quality, optimize=True)

    return output.getvalue()


def create_placeholder(
    width: int,
    height: int,
    color: Tuple[int, int, int] = (240, 240, 240)
) -> bytes:
    """
    Create a solid color placeholder image.

    Useful for generating loading placeholders before actual image is ready.

    Args:
        width: Image width
        height: Image height
        color: RGB color tuple

    Returns:
        PNG image bytes
    """
    if not PIL_AVAILABLE:
        raise ImportError("PIL/Pillow is not installed")

    img = Image.new('RGB', (width, height), color)
    output = BytesIO()
    img.save(output, format='PNG', optimize=True)

    return output.getvalue()


# ============================================================================
# Thumbnail Service Class
# ============================================================================

class ThumbnailService:
    """
    Service class for thumbnail operations.

    Provides a stateful interface with configurable defaults.
    """

    def __init__(
        self,
        default_size: int = DEFAULT_THUMBNAIL_SIZE,
        default_format: str = THUMBNAIL_FORMAT,
        default_quality: int = THUMBNAIL_QUALITY
    ):
        """
        Initialize thumbnail service.

        Args:
            default_size: Default max dimension for thumbnails
            default_format: Default output format
            default_quality: Default quality for lossy formats
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow is not installed. Run: pip install Pillow")

        self.default_size = default_size
        self.default_format = default_format
        self.default_quality = default_quality

        logger.info(
            f"Initialized ThumbnailService (size={default_size}, "
            f"format={default_format}, quality={default_quality})"
        )

    def generate(
        self,
        image_bytes: bytes,
        max_size: Optional[int] = None,
        format: Optional[str] = None,
        quality: Optional[int] = None
    ) -> bytes:
        """
        Generate thumbnail with service defaults.

        Args:
            image_bytes: Original image bytes
            max_size: Override default max size
            format: Override default format
            quality: Override default quality

        Returns:
            Thumbnail bytes
        """
        return generate_thumbnail(
            image_bytes=image_bytes,
            max_size=max_size or self.default_size,
            format=format or self.default_format,
            quality=quality or self.default_quality
        )

    def get_dimensions(self, image_bytes: bytes) -> Tuple[int, int]:
        """Get image dimensions."""
        return get_image_dimensions(image_bytes)

    def get_thumbnail_dimensions(
        self,
        original_width: int,
        original_height: int,
        max_size: Optional[int] = None
    ) -> Tuple[int, int]:
        """Calculate thumbnail dimensions."""
        return calculate_thumbnail_dimensions(
            original_width,
            original_height,
            max_size or self.default_size
        )


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not PIL_AVAILABLE:
        print("PIL not available. Install with: pip install Pillow")
    else:
        # Test dimension calculation
        test_cases = [
            (1920, 1080, 256),  # 16:9 landscape
            (1080, 1920, 256),  # 9:16 portrait
            (1024, 1024, 256),  # 1:1 square
            (3000, 2000, 256),  # 3:2 landscape
        ]

        print("Dimension calculations:")
        for orig_w, orig_h, max_size in test_cases:
            new_w, new_h = calculate_thumbnail_dimensions(orig_w, orig_h, max_size)
            print(f"  {orig_w}x{orig_h} -> {new_w}x{new_h}")

        # Test placeholder creation
        placeholder = create_placeholder(256, 144)
        print(f"\nPlaceholder created: {len(placeholder)} bytes")

        print("\nThumbnailService ready")
