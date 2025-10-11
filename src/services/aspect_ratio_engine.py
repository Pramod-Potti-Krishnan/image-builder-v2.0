"""
Custom Aspect Ratio Engine
===========================

Handles intelligent selection of source aspect ratios and cropping
to achieve custom target aspect ratios.

Strategy:
1. Select best Imagen-supported ratio (1:1, 3:4, 4:3, 9:16, 16:9)
2. Generate image at that ratio
3. Intelligently crop to target custom ratio
"""

import logging
from typing import Tuple, Literal
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

# Imagen 3 supported aspect ratios
IMAGEN_SUPPORTED_RATIOS = {
    "1:1": (1, 1),
    "3:4": (3, 4),
    "4:3": (4, 3),
    "9:16": (9, 16),
    "16:9": (16, 9)
}

CropAnchor = Literal["center", "top", "bottom", "left", "right", "smart"]


def parse_aspect_ratio(ratio_str: str) -> Tuple[int, int]:
    """
    Parse aspect ratio string to tuple.

    Args:
        ratio_str: Aspect ratio like "16:9" or "2:7"

    Returns:
        Tuple of (width, height)
    """
    try:
        width, height = map(int, ratio_str.split(':'))
        return (width, height)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid aspect ratio format: {ratio_str}")


def get_decimal_ratio(ratio_tuple: Tuple[int, int]) -> float:
    """Convert ratio tuple to decimal value."""
    return ratio_tuple[0] / ratio_tuple[1]


def is_imagen_supported(ratio_str: str) -> bool:
    """Check if aspect ratio is natively supported by Imagen."""
    return ratio_str in IMAGEN_SUPPORTED_RATIOS


def select_source_ratio(target_ratio_str: str) -> str:
    """
    Select the best Imagen-supported source ratio for a target custom ratio.

    Strategy:
    - Generate at a ratio that will contain the target ratio
    - Choose ratio that minimizes wasted space
    - For portrait targets, prefer portrait source ratios
    - For landscape targets, prefer landscape source ratios

    Args:
        target_ratio_str: Target aspect ratio (e.g., "2:7", "21:9")

    Returns:
        Best Imagen-supported ratio as string (e.g., "16:9")
    """
    # If target is already supported, use it directly
    if is_imagen_supported(target_ratio_str):
        logger.info(f"Target ratio {target_ratio_str} is natively supported by Imagen")
        return target_ratio_str

    target_ratio = parse_aspect_ratio(target_ratio_str)
    target_decimal = get_decimal_ratio(target_ratio)

    # Determine if target is portrait or landscape
    is_portrait = target_decimal < 1.0
    is_square = abs(target_decimal - 1.0) < 0.01

    # Define candidate ratios based on target orientation
    if is_square:
        candidates = ["1:1"]
    elif is_portrait:
        # Portrait: prefer 9:16 > 3:4 > 1:1
        candidates = ["9:16", "3:4", "1:1"]
    else:
        # Landscape: prefer 16:9 > 4:3 > 1:1
        candidates = ["16:9", "4:3", "1:1"]

    # Find the best candidate that can contain the target
    best_ratio = candidates[0]
    min_waste = float('inf')

    for candidate_str in IMAGEN_SUPPORTED_RATIOS.keys():
        candidate = IMAGEN_SUPPORTED_RATIOS[candidate_str]
        candidate_decimal = get_decimal_ratio(candidate)

        # Check if candidate can contain target
        # For landscape (w > h): source should be >= target ratio
        # For portrait (w < h): source should be <= target ratio
        can_contain = False
        if is_portrait:
            can_contain = candidate_decimal <= target_decimal
        else:
            can_contain = candidate_decimal >= target_decimal

        if not can_contain:
            continue

        # Calculate wasted space (simplified metric)
        waste = abs(candidate_decimal - target_decimal)

        if waste < min_waste:
            min_waste = waste
            best_ratio = candidate_str

    logger.info(f"Selected source ratio {best_ratio} for target {target_ratio_str}")
    return best_ratio


def calculate_crop_box(
    source_size: Tuple[int, int],
    target_ratio: Tuple[int, int],
    anchor: CropAnchor = "center"
) -> Tuple[int, int, int, int]:
    """
    Calculate the crop box (left, top, right, bottom) for PIL.

    Args:
        source_size: (width, height) of source image
        target_ratio: (width, height) of target aspect ratio
        anchor: Where to anchor the crop

    Returns:
        (left, top, right, bottom) for PIL.Image.crop()
    """
    source_width, source_height = source_size
    target_w, target_h = target_ratio
    target_decimal = get_decimal_ratio(target_ratio)

    # Calculate target dimensions that fit within source
    # Try fitting by width first
    new_width = source_width
    new_height = int(source_width / target_decimal)

    # If height exceeds source, fit by height instead
    if new_height > source_height:
        new_height = source_height
        new_width = int(source_height * target_decimal)

    # Calculate crop box based on anchor
    if anchor == "center":
        left = (source_width - new_width) // 2
        top = (source_height - new_height) // 2

    elif anchor == "top":
        left = (source_width - new_width) // 2
        top = 0

    elif anchor == "bottom":
        left = (source_width - new_width) // 2
        top = source_height - new_height

    elif anchor == "left":
        left = 0
        top = (source_height - new_height) // 2

    elif anchor == "right":
        left = source_width - new_width
        top = (source_height - new_height) // 2

    elif anchor == "smart":
        # Smart cropping: focus on center of mass or detected subject
        # For v2.0, use center (can be enhanced with ML in future)
        left = (source_width - new_width) // 2
        top = (source_height - new_height) // 2
        logger.info("Smart cropping using center anchor (can be enhanced with subject detection)")

    else:
        # Default to center
        left = (source_width - new_width) // 2
        top = (source_height - new_height) // 2

    right = left + new_width
    bottom = top + new_height

    logger.info(f"Crop box calculated: ({left}, {top}, {right}, {bottom}) from {source_size} to achieve {target_ratio[0]}:{target_ratio[1]}")

    return (left, top, right, bottom)


def crop_image_to_aspect_ratio(
    image_bytes: bytes,
    target_ratio_str: str,
    anchor: CropAnchor = "center"
) -> bytes:
    """
    Crop image to target aspect ratio.

    Args:
        image_bytes: Source image bytes
        target_ratio_str: Target aspect ratio (e.g., "2:7")
        anchor: Where to anchor the crop

    Returns:
        Cropped image bytes
    """
    try:
        # Open image
        img = Image.open(BytesIO(image_bytes))
        source_size = img.size

        # Parse target ratio
        target_ratio = parse_aspect_ratio(target_ratio_str)

        # Calculate crop box
        crop_box = calculate_crop_box(source_size, target_ratio, anchor)

        # Crop
        cropped_img = img.crop(crop_box)

        # Save to bytes
        output = BytesIO()
        cropped_img.save(output, format='PNG', optimize=True)

        logger.info(f"Successfully cropped image from {source_size} to {cropped_img.size}")

        return output.getvalue()

    except Exception as e:
        logger.error(f"Image cropping failed: {e}")
        raise


def get_aspect_ratio_strategy(target_ratio_str: str) -> dict:
    """
    Get the complete strategy for achieving a target aspect ratio.

    Args:
        target_ratio_str: Target aspect ratio

    Returns:
        Dictionary with:
        - source_ratio: Imagen ratio to use for generation
        - requires_crop: Whether cropping is needed
        - target_ratio: Parsed target ratio
        - strategy: Human-readable strategy description
    """
    target_ratio = parse_aspect_ratio(target_ratio_str)
    is_supported = is_imagen_supported(target_ratio_str)

    if is_supported:
        return {
            "source_ratio": target_ratio_str,
            "requires_crop": False,
            "target_ratio": target_ratio,
            "strategy": f"Generate directly at {target_ratio_str} (natively supported)"
        }
    else:
        source_ratio = select_source_ratio(target_ratio_str)
        return {
            "source_ratio": source_ratio,
            "requires_crop": True,
            "target_ratio": target_ratio,
            "strategy": f"Generate at {source_ratio}, then crop to {target_ratio_str}"
        }


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test cases
    test_ratios = ["2:7", "21:9", "16:9", "1:1", "9:21", "3:5"]

    for ratio in test_ratios:
        print(f"\nTarget: {ratio}")
        strategy = get_aspect_ratio_strategy(ratio)
        print(f"  Source: {strategy['source_ratio']}")
        print(f"  Needs crop: {strategy['requires_crop']}")
        print(f"  Strategy: {strategy['strategy']}")
