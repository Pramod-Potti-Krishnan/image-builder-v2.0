"""
Layout Aspect Ratio Constants
=============================

Defines the recommended aspect ratios for each Deckster layout type.
Use these when generating images for specific layouts to minimize cropping.

Usage:
    from src.constants.layout_aspect_ratios import (
        LAYOUT_ASPECT_RATIOS,
        get_aspect_ratio_for_layout,
        LayoutCategory
    )

    # Get ratio for a specific layout
    ratio = get_aspect_ratio_for_layout("H1-structured")  # Returns "16:9"

    # Get all H-series layouts
    h_series = LayoutCategory.HERO_SLIDES
"""

from typing import Dict, Optional
from enum import Enum


class LayoutCategory(str, Enum):
    """Layout categories for grouping."""
    HERO_SLIDES = "hero"          # H-series: Full screen 16:9 backgrounds
    IMAGE_WIDE = "image_wide"     # I1, I2: Wide side images (660x1080)
    IMAGE_NARROW = "image_narrow" # I3, I4: Narrow side images (360x1080)
    VISUAL_TEXT = "visual_text"   # V-series: Visual + text layouts
    CONTENT = "content"           # C-series, L-series: Content slides


# ============================================================================
# LAYOUT TO ASPECT RATIO MAPPING
# ============================================================================

LAYOUT_ASPECT_RATIOS: Dict[str, str] = {
    # -------------------------------------------------------------------------
    # H-Series: Hero/Title Slides - Full Screen 16:9 Background
    # Target: 1920 x 1080 px (entire slide)
    # -------------------------------------------------------------------------
    "H1-generated": "16:9",      # AI-generated title slide
    "H1-structured": "16:9",     # Manual/structured title slide
    "H2-section": "16:9",        # Section divider
    "H3-closing": "16:9",        # Closing/thank you slide
    "L29": "16:9",               # Hero full-bleed layout

    # -------------------------------------------------------------------------
    # I-Series Wide: Side Images (Left or Right)
    # Target: 660 x 1080 px (11:18 ratio ≈ 0.611)
    # Generate at 2:3 (0.667), crop 8% width → minimal quality loss
    # -------------------------------------------------------------------------
    "I1-image-left": "2:3",      # Wide image on left, content on right
    "I2-image-right": "2:3",     # Wide image on right, content on left

    # -------------------------------------------------------------------------
    # I-Series Narrow: Narrow Side Images
    # Target: 360 x 1080 px (1:3 ratio = 0.333)
    # Generate at 9:16 (0.563), crop 41% width → significant cropping ⚠️
    # Prompt tip: Use "centered subject, vertical composition"
    # -------------------------------------------------------------------------
    "I3-image-left-narrow": "9:16",   # Narrow image on left
    "I4-image-right-narrow": "9:16",  # Narrow image on right

    # -------------------------------------------------------------------------
    # V-Series: Visual + Text Layouts
    # V1 Target: 1080 x 840 px (9:7 ratio ≈ 1.286)
    # Generate at 5:4 (1.25), crop ~3% height → minimal quality loss
    # -------------------------------------------------------------------------
    "V1-image-text": "5:4",      # Image left, text right
    "V2-chart-text": "5:4",      # Chart left, text right (if image needed)
    "V3-diagram-text": "5:4",    # Diagram left, text right (if image needed)
    "V4-infographic-text": "5:4", # Infographic left, text right (if image needed)

    # -------------------------------------------------------------------------
    # C-Series: Content Slides (if background images needed)
    # Target: 1920 x 1080 px or content area
    # -------------------------------------------------------------------------
    "C1-text": "16:9",           # Standard content slide
    "C3-chart": "16:9",          # Chart slide
    "C4-infographic": "16:9",    # Infographic slide
    "C5-diagram": "16:9",        # Diagram slide

    # -------------------------------------------------------------------------
    # S-Series: Split Layouts
    # Each visual area: 900 x 600 px (3:2 ratio)
    # -------------------------------------------------------------------------
    "S3-two-visuals": "3:2",     # Two visuals side by side
    "S4-comparison": "3:2",      # Comparison layout

    # -------------------------------------------------------------------------
    # L-Series: Legacy/Backend Layouts
    # -------------------------------------------------------------------------
    "L02": "16:9",               # Left diagram with text right
    "L25": "16:9",               # Main content shell
}


# ============================================================================
# LAYOUT METADATA
# ============================================================================

LAYOUT_METADATA: Dict[str, Dict] = {
    # H-Series
    "H1-generated": {
        "category": LayoutCategory.HERO_SLIDES,
        "target_width": 1920,
        "target_height": 1080,
        "aspect_ratio": "16:9",
        "cropping_needed": False,
        "description": "AI-generated full-bleed title slide"
    },
    "H1-structured": {
        "category": LayoutCategory.HERO_SLIDES,
        "target_width": 1920,
        "target_height": 1080,
        "aspect_ratio": "16:9",
        "cropping_needed": False,
        "description": "Structured title slide with background"
    },
    "H2-section": {
        "category": LayoutCategory.HERO_SLIDES,
        "target_width": 1920,
        "target_height": 1080,
        "aspect_ratio": "16:9",
        "cropping_needed": False,
        "description": "Section divider slide"
    },
    "H3-closing": {
        "category": LayoutCategory.HERO_SLIDES,
        "target_width": 1920,
        "target_height": 1080,
        "aspect_ratio": "16:9",
        "cropping_needed": False,
        "description": "Closing/thank you slide"
    },
    "L29": {
        "category": LayoutCategory.HERO_SLIDES,
        "target_width": 1920,
        "target_height": 1080,
        "aspect_ratio": "16:9",
        "cropping_needed": False,
        "description": "Hero full-bleed layout"
    },

    # I-Series Wide
    "I1-image-left": {
        "category": LayoutCategory.IMAGE_WIDE,
        "target_width": 660,
        "target_height": 1080,
        "aspect_ratio": "2:3",
        "cropping_needed": True,
        "crop_percentage": 8,
        "description": "Wide image on left (660x1080)"
    },
    "I2-image-right": {
        "category": LayoutCategory.IMAGE_WIDE,
        "target_width": 660,
        "target_height": 1080,
        "aspect_ratio": "2:3",
        "cropping_needed": True,
        "crop_percentage": 8,
        "description": "Wide image on right (660x1080)"
    },

    # I-Series Narrow
    "I3-image-left-narrow": {
        "category": LayoutCategory.IMAGE_NARROW,
        "target_width": 360,
        "target_height": 1080,
        "aspect_ratio": "9:16",
        "cropping_needed": True,
        "crop_percentage": 41,
        "prompt_tip": "Use centered subject, vertical composition",
        "description": "Narrow image on left (360x1080) - heavy cropping"
    },
    "I4-image-right-narrow": {
        "category": LayoutCategory.IMAGE_NARROW,
        "target_width": 360,
        "target_height": 1080,
        "aspect_ratio": "9:16",
        "cropping_needed": True,
        "crop_percentage": 41,
        "prompt_tip": "Use centered subject, vertical composition",
        "description": "Narrow image on right (360x1080) - heavy cropping"
    },

    # V-Series
    "V1-image-text": {
        "category": LayoutCategory.VISUAL_TEXT,
        "target_width": 1080,
        "target_height": 840,
        "aspect_ratio": "5:4",
        "cropping_needed": True,
        "crop_percentage": 3,
        "description": "Image left, text insights right (1080x840)"
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_aspect_ratio_for_layout(layout: str) -> str:
    """
    Get the recommended aspect ratio for a layout.

    Args:
        layout: Layout ID (e.g., "H1-structured", "I1-image-left")

    Returns:
        Aspect ratio string (e.g., "16:9", "2:3")
        Defaults to "16:9" for unknown layouts
    """
    return LAYOUT_ASPECT_RATIOS.get(layout, "16:9")


def get_layout_metadata(layout: str) -> Optional[Dict]:
    """
    Get full metadata for a layout.

    Args:
        layout: Layout ID

    Returns:
        Dict with target dimensions, cropping info, tips, etc.
        None if layout not found
    """
    return LAYOUT_METADATA.get(layout)


def get_layouts_by_category(category: LayoutCategory) -> Dict[str, str]:
    """
    Get all layouts in a category with their aspect ratios.

    Args:
        category: LayoutCategory enum value

    Returns:
        Dict of layout_id -> aspect_ratio
    """
    return {
        layout: ratio
        for layout, ratio in LAYOUT_ASPECT_RATIOS.items()
        if LAYOUT_METADATA.get(layout, {}).get("category") == category
    }


def requires_heavy_cropping(layout: str) -> bool:
    """
    Check if a layout requires significant cropping (>20%).

    Args:
        layout: Layout ID

    Returns:
        True if heavy cropping is needed (I3, I4)
    """
    metadata = LAYOUT_METADATA.get(layout, {})
    return metadata.get("crop_percentage", 0) > 20


def get_prompt_tip(layout: str) -> Optional[str]:
    """
    Get prompting tips for layouts that need special consideration.

    Args:
        layout: Layout ID

    Returns:
        Prompt tip string or None
    """
    metadata = LAYOUT_METADATA.get(layout, {})
    return metadata.get("prompt_tip")


# ============================================================================
# CONVENIENCE GROUPINGS
# ============================================================================

# All hero slide layouts (full screen 16:9)
HERO_LAYOUTS = ["H1-generated", "H1-structured", "H2-section", "H3-closing", "L29"]

# All I-series layouts
I_SERIES_LAYOUTS = [
    "I1-image-left", "I2-image-right",
    "I3-image-left-narrow", "I4-image-right-narrow"
]

# Layouts requiring heavy cropping (41% width loss)
HEAVY_CROP_LAYOUTS = ["I3-image-left-narrow", "I4-image-right-narrow"]


# ============================================================================
# EXPORTS
# ============================================================================

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
]
