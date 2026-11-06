"""LAYER 2 (calculations): operations on in-memory Pillow images."""
from __future__ import annotations

import io
from collections import Counter

from PIL import Image

from .l1_primitives import center_square_box, fit_inside, nearest_color_index
from .model import RgbColor, Size


def decode_image(data: bytes) -> Image.Image:
    """Bytes of a PNG/JPEG/WebP -> loaded image (first frame if animated)."""
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def to_rgb(image: Image.Image, background: RgbColor) -> Image.Image:
    """Flatten any mode (incl. transparency) onto `background`, return RGB."""
    rgba = image.convert("RGBA")
    base = Image.new("RGBA", rgba.size, (*background, 255))
    return Image.alpha_composite(base, rgba).convert("RGB")


def crop_to_square(image: Image.Image) -> Image.Image:
    return image.crop(center_square_box(Size(*image.size)))


def fit_to_square(image: Image.Image, background: RgbColor) -> Image.Image:
    side, offset = fit_inside(Size(*image.size))
    square = Image.new("RGB", (side, side), background)
    square.paste(image, offset)
    return square


def downscale_to_grid(image: Image.Image, grid_size: int) -> Image.Image:
    """Area-average each cell (up-scales with BOX too for tiny inputs)."""
    return image.resize((grid_size, grid_size), Image.Resampling.BOX)


def _pixels(image: Image.Image) -> list[RgbColor]:
    raw = image.tobytes()
    return [RgbColor(*raw[i:i + 3]) for i in range(0, len(raw), 3)]


def adaptive_palette(image: Image.Image, color_count: int) -> tuple[RgbColor, ...]:
    """Median-cut palette of used colors, ordered by frequency desc, then RGB asc."""
    quantized = image.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE)
    raw = quantized.getpalette()[: 3 * color_count]
    entries = [RgbColor(*raw[i:i + 3]) for i in range(0, len(raw), 3)]
    counts = Counter(entries[i] for i in quantized.tobytes())
    return tuple(sorted(counts, key=lambda c: (-counts[c], c)))


def quantize_to_palette(image: Image.Image, palette: tuple[RgbColor, ...],
                        dither: bool) -> bytes:
    """RGB image -> palette indices (row-major bytes)."""
    if not dither:
        cache: dict[RgbColor, int] = {}
        out = bytearray()
        for color in _pixels(image):
            if color not in cache:
                cache[color] = nearest_color_index(color, palette)
            out.append(cache[color])
        return bytes(out)
    padded = list(palette) + [palette[0]] * (256 - len(palette))
    palette_image = Image.new("P", (1, 1))
    palette_image.putpalette([channel for color in padded for channel in color])
    quantized = image.quantize(palette=palette_image, dither=Image.Dither.FLOYDSTEINBERG)
    # Padding repeats palette[0], so any index past the real palette means index 0.
    return bytes(i if i < len(palette) else 0 for i in quantized.tobytes())


def quantize_adaptive(image: Image.Image, color_count: int,
                      dither: bool) -> tuple[tuple[RgbColor, ...], bytes]:
    palette = adaptive_palette(image, color_count)
    return palette, quantize_to_palette(image, palette, dither)
