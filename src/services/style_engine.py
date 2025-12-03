"""
Style Engine Service
====================

Maps image styles to Vertex AI prompt modifiers for enhanced generation quality.
Handles prompt construction, negative prompts, and dimension calculations.
"""

import logging
from typing import Dict, Optional, Tuple, Any
from math import gcd

logger = logging.getLogger(__name__)


# ============================================================================
# Style-to-Prompt Mapping Configuration
# ============================================================================

STYLE_PROMPT_MODIFIERS: Dict[str, Dict[str, Any]] = {
    'realistic': {
        'name': 'Realistic',
        'description': 'Photorealistic imagery with natural lighting and textures',
        'recommended_for': ['business', 'corporate', 'professional', 'presentations'],
        'prefix': 'photorealistic, professional photography, natural lighting, highly detailed, ',
        'suffix': ', high resolution, detailed textures, realistic colors, sharp focus',
        'negative': 'cartoon, illustration, drawing, painting, anime, artistic interpretation, sketch, digital art',
        'archetype': 'conceptual_metaphor',  # Map to existing archetype
        'guidance_scale': 7.5
    },
    'illustration': {
        'name': 'Illustration',
        'description': 'Digital art and illustration style',
        'recommended_for': ['creative', 'educational', 'playful', 'infographics'],
        'prefix': 'digital illustration, vector art style, clean lines, vibrant colors, ',
        'suffix': ', modern illustration, graphic design aesthetic, crisp edges',
        'negative': 'photograph, photorealistic, 3D render, realistic, photo, camera',
        'archetype': 'minimalist_vector_art',
        'guidance_scale': 8.0
    },
    'abstract': {
        'name': 'Abstract',
        'description': 'Artistic, abstract interpretation of concepts',
        'recommended_for': ['creative', 'artistic', 'conceptual', 'backgrounds'],
        'prefix': 'abstract art, artistic interpretation, creative visualization, conceptual, ',
        'suffix': ', expressive, artistic style, non-representational, imaginative',
        'negative': 'photorealistic, literal, representational, realistic, detailed, precise',
        'archetype': 'conceptual_metaphor',
        'guidance_scale': 6.0
    },
    'minimal': {
        'name': 'Minimal',
        'description': 'Clean, minimalist design with simple shapes',
        'recommended_for': ['modern', 'tech', 'startup', 'clean', 'icons'],
        'prefix': 'minimalist design, simple shapes, flat design, clean composition, ',
        'suffix': ', negative space, geometric, elegant simplicity, modern design',
        'negative': 'complex, detailed, busy, cluttered, ornate, realistic, photographic',
        'archetype': 'minimalist_vector_art',
        'guidance_scale': 9.0
    },
    'photo': {
        'name': 'Photo',
        'description': 'Stock photography style for business presentations',
        'recommended_for': ['business', 'corporate', 'marketing', 'stock'],
        'prefix': 'professional stock photo, business photography, commercial quality, ',
        'suffix': ', polished, corporate aesthetic, high quality, professional lighting',
        'negative': 'amateur, artistic, illustration, cartoon, low quality, blurry, grainy',
        'archetype': 'spot_illustration',
        'guidance_scale': 7.0
    }
}


# ============================================================================
# Color Scheme Modifiers
# ============================================================================

COLOR_SCHEME_MODIFIERS: Dict[str, str] = {
    'warm': 'warm color palette, orange tones, red hues, golden lighting, amber accents',
    'cool': 'cool color palette, blue tones, cyan hues, cold lighting, silver accents',
    'neutral': 'neutral colors, grayscale tones, muted palette, balanced colors, earth tones',
    'vibrant': 'vibrant colors, saturated hues, bold color palette, high contrast, vivid'
}


# ============================================================================
# Lighting Modifiers
# ============================================================================

LIGHTING_MODIFIERS: Dict[str, str] = {
    'natural': 'natural lighting, daylight, ambient light, outdoor lighting, soft shadows',
    'studio': 'studio lighting, professional lighting setup, controlled environment, even illumination',
    'dramatic': 'dramatic lighting, high contrast, chiaroscuro, deep shadows, spotlight effect',
    'soft': 'soft lighting, diffused light, gentle shadows, even illumination, flattering light'
}


# ============================================================================
# Quality Tier Resolutions
# ============================================================================

QUALITY_RESOLUTIONS: Dict[str, int] = {
    'draft': 512,
    'standard': 1024,
    'high': 1536,
    'ultra': 2048
}


# ============================================================================
# Standard Negative Prompts (Applied to All Styles)
# ============================================================================

STANDARD_NEGATIVE_PROMPTS = [
    'low quality',
    'blurry',
    'distorted',
    'watermark',
    'text',
    'logo',
    'signature',
    'artifacts',
    'noise',
    'grain',
    'pixelated',
    'deformed',
    'ugly',
    'duplicate',
    'morbid',
    'mutilated'
]


# ============================================================================
# Style Engine Functions
# ============================================================================

def get_style_config(style: str) -> Dict[str, Any]:
    """
    Get configuration for a specific style.

    Args:
        style: Style name (realistic, illustration, abstract, minimal, photo)

    Returns:
        Style configuration dictionary

    Raises:
        ValueError: If style is not recognized
    """
    if style not in STYLE_PROMPT_MODIFIERS:
        raise ValueError(f"Unknown style: {style}. Valid styles: {list(STYLE_PROMPT_MODIFIERS.keys())}")

    return STYLE_PROMPT_MODIFIERS[style]


def build_enhanced_prompt(
    user_prompt: str,
    style: str,
    color_scheme: Optional[str] = None,
    lighting: Optional[str] = None,
    brand_colors: Optional[list] = None,
    presentation_context: Optional[str] = None
) -> str:
    """
    Build an enhanced prompt with style modifiers.

    Args:
        user_prompt: User's original prompt
        style: Image style
        color_scheme: Optional color scheme (warm, cool, neutral, vibrant)
        lighting: Optional lighting style (natural, studio, dramatic, soft)
        brand_colors: Optional list of brand color hex codes
        presentation_context: Optional presentation title/theme for context

    Returns:
        Enhanced prompt string

    Example:
        Input:
            user_prompt: "A team meeting in a modern office"
            style: "realistic"
            color_scheme: "warm"
            lighting: "natural"

        Output:
            "photorealistic, professional photography, natural lighting, highly detailed,
             A team meeting in a modern office,
             warm color palette, orange tones, red hues, golden lighting, amber accents,
             natural lighting, daylight, ambient light, outdoor lighting, soft shadows,
             high resolution, detailed textures, realistic colors, sharp focus"
    """
    style_config = get_style_config(style)

    # Start with style prefix
    parts = [style_config['prefix'].strip()]

    # Add user prompt
    parts.append(user_prompt.strip())

    # Add color scheme if specified
    if color_scheme and color_scheme in COLOR_SCHEME_MODIFIERS:
        parts.append(COLOR_SCHEME_MODIFIERS[color_scheme])

    # Add lighting if specified
    if lighting and lighting in LIGHTING_MODIFIERS:
        parts.append(LIGHTING_MODIFIERS[lighting])

    # Add brand color hints if specified
    if brand_colors and len(brand_colors) > 0:
        color_hint = f"incorporating {' and '.join(brand_colors[:2])} color accents"
        parts.append(color_hint)

    # Add style suffix
    parts.append(style_config['suffix'].strip())

    # Join all parts
    enhanced_prompt = ', '.join(parts)

    logger.info(f"Built enhanced prompt for style '{style}': {enhanced_prompt[:100]}...")

    return enhanced_prompt


def get_negative_prompt(
    style: str,
    custom_negative: Optional[str] = None
) -> str:
    """
    Build negative prompt for a style.

    Args:
        style: Image style
        custom_negative: Optional custom negative prompt from user

    Returns:
        Complete negative prompt string
    """
    style_config = get_style_config(style)

    # Combine style-specific negatives with standard negatives
    negatives = []

    # Add style-specific negatives
    if style_config.get('negative'):
        negatives.append(style_config['negative'])

    # Add standard negatives
    negatives.extend(STANDARD_NEGATIVE_PROMPTS)

    # Add custom negatives
    if custom_negative:
        negatives.append(custom_negative.strip())

    return ', '.join(negatives)


def get_archetype_for_style(style: str) -> str:
    """
    Get the corresponding archetype for a style.

    This maps the Layout Service styles to existing Vertex AI archetypes
    that work well with the style.

    Args:
        style: Layout Service style name

    Returns:
        Corresponding archetype name
    """
    style_config = get_style_config(style)
    return style_config.get('archetype', 'spot_illustration')


def get_guidance_scale(style: str) -> float:
    """
    Get recommended guidance scale for a style.

    Args:
        style: Image style

    Returns:
        Guidance scale value (1.0-20.0)
    """
    style_config = get_style_config(style)
    return style_config.get('guidance_scale', 7.5)


def calculate_dimensions_from_grid(
    grid_width: int,
    grid_height: int,
    quality: str
) -> Tuple[int, int]:
    """
    Calculate pixel dimensions from grid dimensions and quality tier.

    Uses the grid ratio to determine output dimensions while ensuring
    the larger dimension matches the quality tier's base resolution.

    Args:
        grid_width: Width in grid units (1-12)
        grid_height: Height in grid units (1-8)
        quality: Quality tier (draft, standard, high, ultra)

    Returns:
        Tuple of (width, height) in pixels

    Example:
        grid_width=6, grid_height=4, quality='high'
        → ratio = 6:4 = 3:2 = 1.5
        → base = 1536
        → width = 1536, height = 1024
    """
    if quality not in QUALITY_RESOLUTIONS:
        raise ValueError(f"Unknown quality tier: {quality}")

    base_resolution = QUALITY_RESOLUTIONS[quality]
    grid_ratio = grid_width / grid_height

    if grid_ratio >= 1.0:
        # Landscape or square: width is the base
        width = base_resolution
        height = int(base_resolution / grid_ratio)
    else:
        # Portrait: height is the base
        height = base_resolution
        width = int(base_resolution * grid_ratio)

    # Ensure dimensions are even (some models require this)
    width = width if width % 2 == 0 else width + 1
    height = height if height % 2 == 0 else height + 1

    logger.info(f"Calculated dimensions: {width}x{height} for grid {grid_width}x{grid_height} at {quality}")

    return (width, height)


def calculate_dimensions_from_ratio(
    aspect_ratio: str,
    quality: str
) -> Tuple[int, int]:
    """
    Calculate pixel dimensions from aspect ratio string and quality tier.

    Args:
        aspect_ratio: Aspect ratio string (e.g., "16:9", "4:3")
        quality: Quality tier (draft, standard, high, ultra)

    Returns:
        Tuple of (width, height) in pixels
    """
    if ':' not in aspect_ratio:
        raise ValueError(f"Invalid aspect ratio format: {aspect_ratio}")

    parts = aspect_ratio.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid aspect ratio format: {aspect_ratio}")

    try:
        ratio_w = int(parts[0])
        ratio_h = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid aspect ratio values: {aspect_ratio}")

    return calculate_dimensions_from_grid(ratio_w, ratio_h, quality)


def simplify_aspect_ratio(width: int, height: int) -> str:
    """
    Simplify aspect ratio to lowest terms.

    Args:
        width: Width value
        height: Height value

    Returns:
        Simplified ratio string (e.g., "3:2", "16:9")
    """
    divisor = gcd(width, height)
    simplified_w = width // divisor
    simplified_h = height // divisor
    return f"{simplified_w}:{simplified_h}"


def select_imagen_source_ratio(target_ratio: str) -> str:
    """
    Select the best Imagen-supported source ratio for a target ratio.

    Imagen natively supports: 1:1, 3:4, 4:3, 9:16, 16:9
    For custom ratios, we select the closest supported ratio.

    Args:
        target_ratio: Target aspect ratio string

    Returns:
        Best Imagen-supported ratio string
    """
    IMAGEN_RATIOS = {
        '1:1': 1.0,
        '3:4': 0.75,
        '4:3': 1.333,
        '9:16': 0.5625,
        '16:9': 1.778
    }

    # Check if already supported
    if target_ratio in IMAGEN_RATIOS:
        return target_ratio

    # Parse target ratio
    if ':' not in target_ratio:
        return '16:9'  # Default

    parts = target_ratio.split(':')
    try:
        target_decimal = int(parts[0]) / int(parts[1])
    except (ValueError, ZeroDivisionError):
        return '16:9'  # Default on error

    # Find closest supported ratio
    best_ratio = '16:9'
    min_diff = float('inf')

    for ratio_str, ratio_decimal in IMAGEN_RATIOS.items():
        diff = abs(target_decimal - ratio_decimal)
        if diff < min_diff:
            min_diff = diff
            best_ratio = ratio_str

    logger.info(f"Selected Imagen source ratio '{best_ratio}' for target '{target_ratio}'")

    return best_ratio


def get_style_names() -> list:
    """Get list of available style names."""
    return list(STYLE_PROMPT_MODIFIERS.keys())


def get_style_descriptions() -> Dict[str, Dict[str, Any]]:
    """Get dictionary of style names to descriptions and recommendations."""
    return {
        name: {
            'description': config['description'],
            'recommended_for': config.get('recommended_for', [])
        }
        for name, config in STYLE_PROMPT_MODIFIERS.items()
    }


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test prompt building
    prompt = build_enhanced_prompt(
        user_prompt="A team meeting in a modern office",
        style="realistic",
        color_scheme="warm",
        lighting="natural"
    )
    print(f"Enhanced prompt:\n{prompt}\n")

    # Test negative prompt
    negative = get_negative_prompt("realistic", "crowded")
    print(f"Negative prompt:\n{negative}\n")

    # Test dimension calculation
    dims = calculate_dimensions_from_grid(6, 4, "high")
    print(f"Dimensions for 6x4 grid at high quality: {dims}")

    # Test ratio selection
    for ratio in ["16:9", "3:2", "5:3", "2:7"]:
        source = select_imagen_source_ratio(ratio)
        print(f"Target {ratio} -> Source {source}")
