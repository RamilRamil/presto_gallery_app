from PIL import Image

from conftest import png_bytes
from presto_pic_loader.l1_primitives import PICO8_PALETTE
from presto_pic_loader.l2_image_ops import (
    adaptive_palette, crop_to_square, decode_image, downscale_to_grid, fit_to_square,
    quantize_adaptive, quantize_to_palette, to_rgb,
)
from presto_pic_loader.model import RgbColor

RED = RgbColor(255, 0, 0)


def test_decode_image(gradient):
    assert decode_image(png_bytes(gradient)).size == (120, 80)


def test_to_rgb_flattens_transparency():
    image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    image.putpixel((1, 0), (0, 0, 255, 255))
    rgb = to_rgb(image, RED)
    assert rgb.mode == "RGB"
    assert [rgb.getpixel((0, 0)), rgb.getpixel((1, 0))] == [RED, (0, 0, 255)]


def test_crop_to_square(gradient):
    square = crop_to_square(gradient)
    assert square.size == (80, 80)
    assert square.getpixel((0, 0)) == gradient.getpixel((20, 0))


def test_fit_to_square_pads_with_background(gradient):
    square = fit_to_square(gradient, RED)
    assert square.size == (120, 120)
    assert square.getpixel((0, 0)) == RED
    assert square.getpixel((0, 20)) == gradient.getpixel((0, 0))


def test_downscale_averages_and_upscales():
    image = Image.new("RGB", (4, 4), (0, 0, 0))
    for x in range(2):
        for y in range(4):
            image.putpixel((x, y), (200, 200, 200))
    small = downscale_to_grid(image, 2)
    assert [small.getpixel((x, y)) for y in range(2) for x in range(2)] == [(200, 200, 200), (0, 0, 0)] * 2
    assert downscale_to_grid(Image.new("RGB", (3, 3)), 16).size == (16, 16)


def test_adaptive_palette_limit_and_order(gradient):
    palette = adaptive_palette(gradient, 8)
    assert 1 <= len(palette) <= 8
    assert adaptive_palette(gradient, 8) == palette  # deterministic


def test_adaptive_palette_shorter_for_few_colors():
    image = Image.new("RGB", (4, 1), RED)
    image.putpixel((0, 0), (0, 0, 0))
    assert adaptive_palette(image, 16) == (RED, RgbColor(0, 0, 0))  # by frequency


def test_quantize_to_palette_nearest():
    image = Image.new("RGB", (2, 1))
    image.putdata([(250, 5, 70), (3, 3, 3)])
    assert quantize_to_palette(image, PICO8_PALETTE, dither=False) == bytes([8, 0])


def test_quantize_dither_stays_in_palette(gradient):
    small = downscale_to_grid(gradient, 32)
    plain = quantize_to_palette(small, PICO8_PALETTE[:4], dither=False)
    dithered = quantize_to_palette(small, PICO8_PALETTE[:4], dither=True)
    assert len(dithered) == 32 * 32 and max(dithered) < 4
    assert plain != dithered


def test_quantize_adaptive(gradient):
    palette, indices = quantize_adaptive(downscale_to_grid(gradient, 16), 4, dither=False)
    assert len(indices) == 256 and max(indices) < len(palette) <= 4
