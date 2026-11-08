"""LAYER 1 (calculations): color and size primitives."""
from __future__ import annotations

from .model import RgbColor, Size

PRESTO_SCREEN_SIZE = 240
GRID_SIZES = (16, 32, 40, 60, 64, 80, 120, 240)

PICO8_PALETTE: tuple[RgbColor, ...] = tuple(
    RgbColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    for h in (
        "000000", "1D2B53", "7E2553", "008751", "AB5236", "5F574F", "C2C3C7", "FFF1E8",
        "FF004D", "FFA300", "FFEC27", "00E436", "29ADFF", "83769C", "FF77A8", "FFCCAA",
    )
)


def clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


def color_distance(a: RgbColor, b: RgbColor) -> int:
    """Squared Euclidean distance in RGB."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def nearest_color_index(color: RgbColor, palette: tuple[RgbColor, ...]) -> int:
    """Index of the closest palette entry; ties go to the lowest index."""
    return min(range(len(palette)), key=lambda i: (color_distance(color, palette[i]), i))


def parse_hex_color(text: str) -> RgbColor:
    """'#RRGGBB' or 'RRGGBB' -> RgbColor; raises ValueError."""
    digits = text.strip().removeprefix("#")
    if len(digits) != 6:
        raise ValueError(f"color must look like #RRGGBB, got {text!r}")
    try:
        return RgbColor(int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))
    except ValueError:
        raise ValueError(f"color must look like #RRGGBB, got {text!r}") from None


def cell_size(grid_size: int, screen_size: int = PRESTO_SCREEN_SIZE) -> int:
    return screen_size // grid_size


def screen_offset(grid_size: int, screen_size: int = PRESTO_SCREEN_SIZE) -> int:
    """Margin that centers grid_size*cell_size pixels on the screen."""
    return (screen_size - grid_size * cell_size(grid_size, screen_size)) // 2


def center_square_box(size: Size) -> tuple[int, int, int, int]:
    """(left, top, right, bottom) of the largest centered square."""
    side = min(size.width, size.height)
    left = (size.width - side) // 2
    top = (size.height - side) // 2
    return (left, top, left + side, top + side)


def fit_inside(size: Size) -> tuple[int, tuple[int, int]]:
    """Side of the square that contains `size`, and the paste offset that centers it."""
    side = max(size.width, size.height)
    return side, ((side - size.width) // 2, (side - size.height) // 2)
