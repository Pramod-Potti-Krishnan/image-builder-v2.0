"""Constants for Image Build Agent v2.0"""

from .layout_aspect_ratios import (
    LAYOUT_ASPECT_RATIOS,
    LAYOUT_METADATA,
    LayoutCategory,
    get_aspect_ratio_for_layout,
    get_layout_metadata,
    get_layouts_by_category,
    requires_heavy_cropping,
    get_prompt_tip,
    HERO_LAYOUTS,
    I_SERIES_LAYOUTS,
    HEAVY_CROP_LAYOUTS,
)

from .illustration_colors import (
    DARK_COLORS,
    DARK_COLOR_ORDER,
    get_color_by_index,
    get_all_dark_hex_colors,
    get_colors_for_segments,
    hex_to_rgb,
)

__all__ = [
    "LAYOUT_ASPECT_RATIOS",
    "LAYOUT_METADATA",
    "LayoutCategory",
    "get_aspect_ratio_for_layout",
    "get_layout_metadata",
    "get_layouts_by_category",
    "requires_heavy_cropping",
    "get_prompt_tip",
    "HERO_LAYOUTS",
    "I_SERIES_LAYOUTS",
    "HEAVY_CROP_LAYOUTS",
    # Illustration colors
    "DARK_COLORS",
    "DARK_COLOR_ORDER",
    "get_color_by_index",
    "get_all_dark_hex_colors",
    "get_colors_for_segments",
    "hex_to_rgb",
]
