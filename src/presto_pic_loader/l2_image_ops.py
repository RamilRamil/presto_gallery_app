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


def image_pixels(image: Image.Image) -> list[RgbColor]:
    """RGB image -> row-major list of RgbColor."""
    raw = image.convert("RGB").tobytes()
    return [RgbColor(*raw[i:i + 3]) for i in range(0, len(raw), 3)]


# --- Stage B: shared exact quantization (docs/pixelize-algorithm.md) ---------------------

def _channel_range(colors: list[RgbColor]) -> tuple[int, int]:
    """(widest range, channel index) with ties resolved R, G, B."""
    best = (-1, 0)
    for channel in range(3):
        values = [c[channel] for c in colors]
        spread = max(values) - min(values)
        if spread > best[0]:
            best = (spread, channel)
    return best


def _box_mean(colors: list[RgbColor], counts: dict[RgbColor, int]) -> RgbColor:
    total = sum(counts[c] for c in colors)
    return RgbColor(*((sum(c[ch] * counts[c] for c in colors) + total // 2) // total
                      for ch in range(3)))


def median_cut(pixels: list[RgbColor], color_count: int) -> tuple[RgbColor, ...]:
    counts = Counter(pixels)
    unique = sorted(counts)
    if len(unique) <= color_count:
        return tuple(unique)
    boxes = [unique]
    while len(boxes) < color_count:
        best_index, best_key = -1, None
        for index, box in enumerate(boxes):
            if len(box) < 2:
                continue
            key = (_channel_range(box)[0], sum(counts[c] for c in box))
            if best_key is None or key > best_key:
                best_index, best_key = index, key
        if best_index < 0:
            break
        box = boxes[best_index]
        channel = _channel_range(box)[1]
        box = sorted(box, key=lambda c: (c[channel], c[0], c[1], c[2]))
        total = sum(counts[c] for c in box)
        cumulative, k = 0, 0
        for k, color in enumerate(box):
            cumulative += counts[color]
            if 2 * cumulative >= total:
                break
        if k == len(box) - 1:
            k -= 1
        boxes[best_index] = box[:k + 1]
        boxes.append(box[k + 1:])
    palette: list[RgbColor] = []
    for box in boxes:
        mean = _box_mean(box, counts)
        if mean not in palette:
            palette.append(mean)
    return tuple(palette)


def map_nearest(pixels: list[RgbColor], palette: tuple[RgbColor, ...]) -> bytes:
    cache: dict[RgbColor, int] = {}
    out = bytearray()
    for color in pixels:
        if color not in cache:
            cache[color] = nearest_color_index(color, palette)
        out.append(cache[color])
    return bytes(out)


def dither_floyd_steinberg(pixels: list[RgbColor], width: int,
                           palette: tuple[RgbColor, ...]) -> bytes:
    height = len(pixels) // width
    error = [[0, 0, 0] for _ in pixels]
    out = bytearray()
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            value = RgbColor(*(max(0, min(255, pixels[pos][ch] + error[pos][ch]))
                               for ch in range(3)))
            index = nearest_color_index(value, palette)
            out.append(index)
            diff = [value[ch] - palette[index][ch] for ch in range(3)]
            for dx, dy, weight in ((1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and ny < height:
                    target = error[ny * width + nx]
                    for ch in range(3):
                        target[ch] += (diff[ch] * weight) >> 4
    return bytes(out)


def order_palette_by_usage(palette: tuple[RgbColor, ...], frames: list[bytes]
                           ) -> tuple[tuple[RgbColor, ...], list[bytes]]:
    """Drop unused entries, sort by usage desc then RGB asc, remap every frame."""
    usage = Counter(i for frame in frames for i in frame)
    order = sorted(usage, key=lambda i: (-usage[i], palette[i]))
    remap = bytearray(256)
    for new, old in enumerate(order):
        remap[old] = new
    return tuple(palette[i] for i in order), [frame.translate(remap) for frame in frames]


def quantize_frames(frames: list[list[RgbColor]], width: int, color_count: int,
                    preset: tuple[RgbColor, ...] | None, dither: bool
                    ) -> tuple[tuple[RgbColor, ...], list[bytes]]:
    """Stage B for one or more frames sharing one Palette."""
    palette = preset or median_cut([p for frame in frames for p in frame], color_count)
    if dither:
        indices = [dither_floyd_steinberg(frame, width, palette) for frame in frames]
    else:
        indices = [map_nearest(frame, palette) for frame in frames]
    if preset:
        return palette, indices
    return order_palette_by_usage(palette, indices)
