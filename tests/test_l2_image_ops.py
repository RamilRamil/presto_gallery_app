from PIL import Image

from imaging import png_bytes
from presto_pic_loader.l1_primitives import PICO8_PALETTE
from presto_pic_loader.l2_image_ops import (
    crop_to_square, decode_image, dither_floyd_steinberg, downscale_to_grid, fit_to_square,
    image_pixels, map_nearest, median_cut, order_palette_by_usage, quantize_frames, to_rgb,
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


BLACK = RgbColor(0, 0, 0)
WHITE = RgbColor(255, 255, 255)


def test_image_pixels():
    image = Image.new("RGB", (2, 1), RED)
    assert image_pixels(image) == [RED, RED]


def test_median_cut_few_colors_returns_unique_sorted():
    assert median_cut([RED, BLACK, RED], 16) == (BLACK, RED)


def test_median_cut_splits_widest_channel_at_weighted_median():
    pixels = [RgbColor(0, 0, 0)] * 3 + [RgbColor(10, 0, 0)] + [RgbColor(200, 0, 0)] * 2
    # one split on R; cumulative 3 of 6 reaches half at the first color
    assert median_cut(pixels, 2) == (RgbColor(0, 0, 0), RgbColor(137, 0, 0))


def test_median_cut_limit_and_determinism(gradient):
    pixels = image_pixels(downscale_to_grid(gradient, 32))
    palette = median_cut(pixels, 8)
    assert len(palette) == 8 and median_cut(pixels, 8) == palette


def test_map_nearest():
    pixels = [RgbColor(250, 5, 70), RgbColor(3, 3, 3)]
    assert map_nearest(pixels, PICO8_PALETTE) == bytes([8, 0])


def test_dither_floyd_steinberg_known_values():
    gray = [RgbColor(128, 128, 128)] * 4
    # 128 -> white (e=-127): right += -56, down-left -24, down -40, down-right -8
    assert dither_floyd_steinberg(gray, 2, (BLACK, WHITE)) == bytes([1, 0, 0, 1])


def test_dither_differs_from_plain(gradient):
    pixels = image_pixels(downscale_to_grid(gradient, 32))
    plain = map_nearest(pixels, PICO8_PALETTE[:4])
    dithered = dither_floyd_steinberg(pixels, 32, PICO8_PALETTE[:4])
    assert plain != dithered and max(dithered) < 4


def test_order_palette_by_usage_drops_unused():
    palette, frames = order_palette_by_usage((RED, BLACK, WHITE), [bytes([1, 1, 0]), bytes([1])])
    assert palette == (BLACK, RED) and frames == [bytes([0, 0, 1]), bytes([0])]


def test_quantize_frames_shares_palette_across_frames():
    frame_a, frame_b = [RED] * 4, [BLACK] * 4
    palette, indices = quantize_frames([frame_a, frame_b], 2, 16, None, False)
    assert palette == (BLACK, RED) and indices == [bytes([1] * 4), bytes([0] * 4)]


def test_quantize_frames_preset_keeps_order():
    palette, indices = quantize_frames([[RED]], 1, 16, PICO8_PALETTE, True)
    assert palette == PICO8_PALETTE and indices == [bytes([8])]
