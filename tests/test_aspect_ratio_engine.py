"""
Tests for Aspect Ratio Engine
==============================
"""

import pytest
from src.services.aspect_ratio_engine import (
    parse_aspect_ratio,
    get_decimal_ratio,
    is_imagen_supported,
    select_source_ratio,
    get_aspect_ratio_strategy,
    calculate_crop_box
)


class TestAspectRatioEngine:
    """Test suite for aspect ratio engine."""

    def test_parse_aspect_ratio(self):
        """Test aspect ratio parsing."""
        assert parse_aspect_ratio("16:9") == (16, 9)
        assert parse_aspect_ratio("2:7") == (2, 7)
        assert parse_aspect_ratio("1:1") == (1, 1)

        with pytest.raises(ValueError):
            parse_aspect_ratio("invalid")

        with pytest.raises(ValueError):
            parse_aspect_ratio("16-9")

    def test_get_decimal_ratio(self):
        """Test decimal ratio calculation."""
        assert get_decimal_ratio((16, 9)) == pytest.approx(1.777, rel=0.01)
        assert get_decimal_ratio((9, 16)) == pytest.approx(0.5625, rel=0.01)
        assert get_decimal_ratio((1, 1)) == 1.0

    def test_is_imagen_supported(self):
        """Test Imagen support detection."""
        assert is_imagen_supported("16:9") is True
        assert is_imagen_supported("1:1") is True
        assert is_imagen_supported("9:16") is True
        assert is_imagen_supported("3:4") is True
        assert is_imagen_supported("4:3") is True

        assert is_imagen_supported("2:7") is False
        assert is_imagen_supported("21:9") is False

    def test_select_source_ratio_portrait(self):
        """Test source ratio selection for portrait orientations."""
        # Portrait ratios should use 9:16 or 3:4
        assert select_source_ratio("2:7") == "9:16"
        assert select_source_ratio("3:5") == "3:4"
        assert select_source_ratio("9:21") == "9:16"

    def test_select_source_ratio_landscape(self):
        """Test source ratio selection for landscape orientations."""
        # Landscape ratios should use 16:9 or 4:3
        assert select_source_ratio("21:9") == "16:9"
        assert select_source_ratio("5:3") == "4:3"

    def test_select_source_ratio_square(self):
        """Test source ratio selection for square-ish ratios."""
        assert select_source_ratio("1:1") == "1:1"

    def test_get_aspect_ratio_strategy_supported(self):
        """Test strategy for supported ratios."""
        strategy = get_aspect_ratio_strategy("16:9")

        assert strategy["source_ratio"] == "16:9"
        assert strategy["requires_crop"] is False
        assert strategy["target_ratio"] == (16, 9)

    def test_get_aspect_ratio_strategy_custom(self):
        """Test strategy for custom ratios."""
        strategy = get_aspect_ratio_strategy("2:7")

        assert strategy["source_ratio"] == "9:16"
        assert strategy["requires_crop"] is True
        assert strategy["target_ratio"] == (2, 7)
        assert "crop" in strategy["strategy"].lower()

    def test_calculate_crop_box_center(self):
        """Test crop box calculation with center anchor."""
        source_size = (1600, 900)  # 16:9
        target_ratio = (2, 7)  # Portrait

        left, top, right, bottom = calculate_crop_box(source_size, target_ratio, "center")

        # Verify dimensions
        width = right - left
        height = bottom - top
        ratio = width / height

        expected_ratio = 2 / 7
        assert ratio == pytest.approx(expected_ratio, rel=0.01)

        # Verify centering
        assert left >= 0
        assert top >= 0
        assert right <= source_size[0]
        assert bottom <= source_size[1]

    def test_calculate_crop_box_top(self):
        """Test crop box calculation with top anchor."""
        source_size = (1600, 900)
        target_ratio = (16, 9)

        left, top, right, bottom = calculate_crop_box(source_size, target_ratio, "top")

        assert top == 0  # Should be anchored to top

    def test_calculate_crop_box_bottom(self):
        """Test crop box calculation with bottom anchor."""
        source_size = (1600, 900)
        target_ratio = (16, 9)

        left, top, right, bottom = calculate_crop_box(source_size, target_ratio, "bottom")

        assert bottom == source_size[1]  # Should be anchored to bottom

    def test_calculate_crop_box_smart(self):
        """Test smart crop box calculation."""
        source_size = (1600, 900)
        target_ratio = (1, 1)

        left, top, right, bottom = calculate_crop_box(source_size, target_ratio, "smart")

        # Smart should behave like center for now
        width = right - left
        height = bottom - top
        assert width == height  # Square crop


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
