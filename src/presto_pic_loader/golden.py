"""LAYER 5 (action): write golden vectors to tests/golden/ (constitution VI).

Run: python -m presto_pic_loader.golden
Each vector: grid-sized RGB frames + PixelizeSettings -> expected PrestoBinFormat bytes (hex).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .l3_pipeline import make_settings, pixelize_grid
from .l4_encoders import encode_presto_bin
from .model import RgbColor

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "tests" / "golden"


def _gradient(size: int, shift: int = 0) -> list[RgbColor]:
    return [RgbColor((x * 255) // (size - 1), (y * 255) // (size - 1), ((x + y) * 8 + shift) % 256)
            for y in range(size) for x in range(size)]


def _noise(size: int, seed: int) -> list[RgbColor]:
    state, out = seed, []
    for _ in range(size * size):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        out.append(RgbColor(state & 255, (state >> 8) & 255, (state >> 16) & 255))
    return out


def _few_colors(size: int) -> list[RgbColor]:
    colors = (RgbColor(255, 0, 0), RgbColor(0, 0, 255), RgbColor(250, 250, 250))
    return [colors[(x // 4 + y // 4) % 3] for y in range(size) for x in range(size)]


CASES = [
    ("gradient-32-adaptive16", dict(grid_size=32), [_gradient(32)], [0]),
    ("gradient-32-adaptive16-dither", dict(grid_size=32, dither=True), [_gradient(32)], [0]),
    ("gradient-16-pico8", dict(grid_size=16, palette_name="pico-8"), [_gradient(16)], [0]),
    ("gradient-16-pico8-dither", dict(grid_size=16, palette_name="pico-8", dither=True),
     [_gradient(16)], [0]),
    ("noise-64-adaptive256", dict(grid_size=64, color_count=256), [_noise(64, 7)], [0]),
    ("noise-32-adaptive2-dither", dict(grid_size=32, color_count=2, dither=True),
     [_noise(32, 3)], [0]),
    ("few-colors-16-adaptive8", dict(grid_size=16, color_count=8), [_few_colors(16)], [0]),
    ("animation-16-adaptive4", dict(grid_size=16, color_count=4),
     [_gradient(16, 0), _gradient(16, 80), _noise(16, 1)], [100, 50, 200]),
]


def build_vector(name, kwargs, frames, durations) -> dict:
    settings = make_settings(**kwargs)
    art = pixelize_grid(frames, durations, settings)
    return {
        "name": name,
        "settings": {
            "gridSize": settings.grid_size, "colorCount": settings.color_count,
            "paletteName": settings.palette_name, "fitMode": settings.fit_mode.value,
            "dither": settings.dither,
            "backgroundColor": "#%02x%02x%02x" % settings.background_color,
        },
        "frames": [{"pixels": bytes(c for p in f for c in p).hex(), "durationMs": d}
                   for f, d in zip(frames, durations)],
        "expectedBin": encode_presto_bin(art).hex(),
    }


def build_all() -> list[dict]:
    return [build_vector(*case) for case in CASES]


def gif_fixture(name: str, size: int, interlace: bool) -> tuple[bytes, dict]:
    """Animated GIF made by Pillow + the exact RGB frames it must decode to."""
    import io

    from PIL import Image

    colors = [RgbColor(255, 0, 0), RgbColor(0, 128, 255), RgbColor(250, 250, 250),
              RgbColor(0, 0, 0)]
    frames, images = [], []
    for step in range(3):
        pixels = [colors[(x // 3 + y // 3 + step) % 4] if x < size - step * 2 else colors[3]
                  for y in range(size) for x in range(size)]
        frames.append(pixels)
        image = Image.new("RGB", (size, size))
        image.frombytes(bytes(c for p in pixels for c in p))
        images.append(image)
    buffer = io.BytesIO()
    images[0].save(buffer, format="GIF", save_all=True, append_images=images[1:],
                   duration=[100, 50, 200], loop=0, interlace=interlace)
    vector = {"name": name, "width": size, "height": size,
              "frames": [{"pixels": bytes(c for p in f for c in p).hex(), "delayMs": d}
                         for f, d in zip(frames, [100, 50, 200])]}
    return buffer.getvalue(), vector


GIF_CASES = [("anim-small", 9, False), ("anim-interlaced", 40, True)]


def main() -> int:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    gif_dir = GOLDEN_DIR / "gif"
    gif_dir.mkdir(exist_ok=True)
    for name, size, interlace in GIF_CASES:
        data, vector = gif_fixture(name, size, interlace)
        (gif_dir / f"{name}.gif").write_bytes(data)
        (gif_dir / f"{name}.json").write_text(json.dumps(vector, indent=1) + "\n")
        print(f"wrote gif/{name}.gif")
    for vector in build_all():
        path = GOLDEN_DIR / f"{vector['name']}.json"
        path.write_text(json.dumps(vector, indent=1) + "\n")
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
