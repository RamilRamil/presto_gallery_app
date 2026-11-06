import pytest

from presto_pic_loader.l1_primitives import (
    PICO8_PALETTE, cell_size, center_square_box, clamp_channel, color_distance, fit_inside,
    nearest_color_index, parse_hex_color, screen_offset,
)
from presto_pic_loader.model import RgbColor, Size


def test_clamp_channel():
    assert [clamp_channel(v) for v in (-5, 0, 128, 255, 300)] == [0, 0, 128, 255, 255]


def test_color_distance_and_nearest():
    assert color_distance(RgbColor(0, 0, 0), RgbColor(1, 2, 3)) == 14
    palette = (RgbColor(0, 0, 0), RgbColor(255, 255, 255), RgbColor(0, 0, 0))
    assert nearest_color_index(RgbColor(10, 10, 10), palette) == 0
    assert nearest_color_index(RgbColor(200, 220, 240), palette) == 1


def test_parse_hex_color():
    assert parse_hex_color("#FF8000") == RgbColor(255, 128, 0)
    assert parse_hex_color("00ff00") == RgbColor(0, 255, 0)
    for bad in ("#fff", "zzzzzz", ""):
        with pytest.raises(ValueError):
            parse_hex_color(bad)


@pytest.mark.parametrize("grid,cell,offset", [(16, 15, 0), (32, 7, 8), (64, 3, 24)])
def test_cell_size_and_offset(grid, cell, offset):
    assert cell_size(grid) == cell
    assert screen_offset(grid) == offset


def test_center_square_box():
    assert center_square_box(Size(100, 60)) == (20, 0, 80, 60)
    assert center_square_box(Size(60, 101)) == (0, 20, 60, 80)


def test_fit_inside():
    assert fit_inside(Size(100, 60)) == (100, (0, 20))
    assert fit_inside(Size(50, 50)) == (50, (0, 0))


def test_pico8_palette():
    assert len(PICO8_PALETTE) == 16
    assert PICO8_PALETTE[0] == RgbColor(0, 0, 0)
    assert PICO8_PALETTE[8] == RgbColor(0xFF, 0x00, 0x4D)
