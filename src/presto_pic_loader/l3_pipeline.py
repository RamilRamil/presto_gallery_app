"""LAYER 3 (calculations): pixelize(SourceImage, PixelizeSettings) -> PixelArt."""
from __future__ import annotations

from .l1_primitives import GRID_SIZES, PICO8_PALETTE, parse_hex_color
from .l2_image_ops import (
    crop_to_square, decode_image, downscale_to_grid, fit_to_square,
    quantize_adaptive, quantize_to_palette, to_rgb,
)
from .model import FitMode, Frame, PixelArt, PixelizeSettings, RgbColor, SourceImage

PRESET_PALETTES: dict[str, tuple[RgbColor, ...]] = {"pico-8": PICO8_PALETTE}
ADAPTIVE = "adaptive"


def make_settings(grid_size: int = 32, color_count: int = 16, palette_name: str = ADAPTIVE,
                  fit_mode: str = "crop", dither: bool = False,
                  background_color: str = "#000000") -> PixelizeSettings:
    """Validate raw option values; raises ValueError with a user-facing message."""
    if grid_size not in GRID_SIZES:
        raise ValueError(f"grid size must be one of {GRID_SIZES}, got {grid_size}")
    if palette_name != ADAPTIVE and palette_name not in PRESET_PALETTES:
        raise ValueError(f"unknown palette {palette_name!r}; known: {sorted(PRESET_PALETTES)}")
    preset = PRESET_PALETTES.get(palette_name)
    if preset is None and not 2 <= color_count <= 256:
        raise ValueError(f"color count must be 2..256, got {color_count}")
    try:
        fit = FitMode(fit_mode)
    except ValueError:
        raise ValueError(f"fit mode must be 'crop' or 'fit', got {fit_mode!r}") from None
    return PixelizeSettings(
        grid_size=grid_size,
        color_count=len(preset) if preset else color_count,
        palette_name=palette_name,
        preset_palette=preset,
        fit_mode=fit,
        dither=dither,
        background_color=parse_hex_color(background_color),
    )


def load_source_image(name: str, data: bytes, settings: PixelizeSettings) -> SourceImage:
    return SourceImage(name, to_rgb(decode_image(data), settings.background_color))


def pixelize(source: SourceImage, settings: PixelizeSettings) -> PixelArt:
    if settings.fit_mode is FitMode.CROP:
        square = crop_to_square(source.image)
    else:
        square = fit_to_square(source.image, settings.background_color)
    small = downscale_to_grid(square, settings.grid_size)
    if settings.preset_palette is not None:
        palette = settings.preset_palette
        indices = quantize_to_palette(small, palette, settings.dither)
    else:
        palette, indices = quantize_adaptive(small, settings.color_count, settings.dither)
    return PixelArt(settings.grid_size, settings.grid_size, palette, (Frame(indices, 0),))
