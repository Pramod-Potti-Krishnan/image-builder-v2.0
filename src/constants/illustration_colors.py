"""
Image Builder v2.0 - Illustration Color Palette

Defines the standardized dark color palette for illustration generation.
Used when converting images to clean illustrations with Gemini.
"""

from typing import Dict, List, Tuple


# =============================================================================
# Dark Colors for Image Segments
# =============================================================================

DARK_COLORS: Dict[str, Dict] = {
    "purple": {
        "hex": "#805AA0",
        "rgba": "rgba(128, 90, 160, 1.0)",
        "rgb": (128, 90, 160),
    },
    "blue": {
        "hex": "#2980B9",
        "rgba": "rgba(41, 128, 185, 1.0)",
        "rgb": (41, 128, 185),
    },
    "red": {
        "hex": "#C0392B",
        "rgba": "rgba(192, 57, 43, 1.0)",
        "rgb": (192, 57, 43),
    },
    "green": {
        "hex": "#27AE60",
        "rgba": "rgba(39, 174, 96, 1.0)",
        "rgb": (39, 174, 96),
    },
    "yellow": {
        "hex": "#D39E1E",
        "rgba": "rgba(211, 158, 30, 1.0)",
        "rgb": (211, 158, 30),
    },
    "cyan": {
        "hex": "#0097A7",
        "rgba": "rgba(0, 151, 167, 1.0)",
        "rgb": (0, 151, 167),
    },
    "orange": {
        "hex": "#E65100",
        "rgba": "rgba(230, 81, 0, 1.0)",
        "rgb": (230, 81, 0),
    },
    "teal": {
        "hex": "#00796B",
        "rgba": "rgba(0, 121, 107, 1.0)",
        "rgb": (0, 121, 107),
    },
    "pink": {
        "hex": "#C2185B",
        "rgba": "rgba(194, 24, 91, 1.0)",
        "rgb": (194, 24, 91),
    },
    "indigo": {
        "hex": "#3949AB",
        "rgba": "rgba(57, 73, 171, 1.0)",
        "rgb": (57, 73, 171),
    },
}

# Ordered list of dark color names (for indexed access)
DARK_COLOR_ORDER: List[str] = [
    "purple", "blue", "red", "green", "yellow",
    "cyan", "orange", "teal", "pink", "indigo"
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_color_by_index(index: int) -> Dict:
    """
    Get a color by index (0-9).
    Wraps around if index > 9.

    Args:
        index: Color index (0-9, wraps for higher values)

    Returns:
        Dict with name, index, hex, rgba, rgb
    """
    color_name = DARK_COLOR_ORDER[index % len(DARK_COLOR_ORDER)]
    return {
        "name": color_name,
        "index": index % len(DARK_COLOR_ORDER),
        **DARK_COLORS[color_name]
    }


def get_all_dark_hex_colors() -> List[str]:
    """
    Get list of all dark colors as hex values in order.

    Returns:
        List of hex color strings
    """
    return [DARK_COLORS[name]["hex"] for name in DARK_COLOR_ORDER]


def get_colors_for_segments(num_segments: int) -> List[str]:
    """
    Get hex colors for a specified number of segments.

    Args:
        num_segments: Number of color segments needed (1-10)

    Returns:
        List of hex color strings
    """
    num_segments = min(max(1, num_segments), 10)
    return [DARK_COLORS[DARK_COLOR_ORDER[i]]["hex"] for i in range(num_segments)]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex string to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#805AA0")

    Returns:
        Tuple of (r, g, b) integers
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
