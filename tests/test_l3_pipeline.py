import pytest
from PIL import Image

from conftest import png_bytes
from presto_pic_loader.l1_primitives import PICO8_PALETTE
from presto_pic_loader.l3_pipeline import load_source_image, make_settings, pixelize
from presto_pic_loader.model import FitMode, RgbColor


def test_make_settings_defaults():
    s = make_settings()
    assert (s.grid_size, s.color_count, s.palette_name, s.fit_mode, s.dither) == \
        (32, 16, "adaptive", FitMode.CROP, False)
    assert s.background_color == RgbColor(0, 0, 0) and s.preset_palette is None


def test_make_settings_preset():
    s = make_settings(palette_name="pico-8")
    assert s.preset_palette == PICO8_PALETTE and s.color_count == 16


@pytest.mark.parametrize("kwargs", [
    {"grid_size": 20}, {"color_count": 1}, {"color_count": 257},
    {"palette_name": "nes"}, {"fit_mode": "stretch"}, {"background_color": "red"},
])
def test_make_settings_rejects(kwargs):
    with pytest.raises(ValueError):
        make_settings(**kwargs)


def test_load_source_image(gradient):
    source = load_source_image("g.png", png_bytes(gradient.convert("RGBA")), make_settings())
    assert source.name == "g.png" and source.image.mode == "RGB"


@pytest.mark.parametrize("grid", [16, 32, 64])
def test_pixelize_defaults(gradient, grid):
    settings = make_settings(grid_size=grid)
    art = pixelize(load_source_image("g", png_bytes(gradient), settings), settings)
    assert (art.width, art.height, len(art.frames)) == (grid, grid, 1)
    assert len(art.frames[0].indices) == grid * grid
    assert max(art.frames[0].indices) < len(art.palette) <= 16
    assert art.frames[0].duration_ms == 0


def test_pixelize_pico8_fit_dither(gradient):
    settings = make_settings(grid_size=64, palette_name="pico-8", fit_mode="fit",
                             dither=True, background_color="#FF004D")
    art = pixelize(load_source_image("g", png_bytes(gradient), settings), settings)
    assert art.palette == PICO8_PALETTE
    assert art.frames[0].indices[0] == 8  # letterbox stripe in background color


def test_pixelize_deterministic(gradient):
    settings = make_settings(color_count=8, dither=True)
    source = load_source_image("g", png_bytes(gradient), settings)
    assert pixelize(source, settings) == pixelize(source, settings)


def test_pixelize_tiny_image():
    settings = make_settings()
    tiny = Image.new("RGB", (3, 2), (10, 200, 30))
    art = pixelize(load_source_image("t", png_bytes(tiny), settings), settings)
    assert art.palette == (RgbColor(10, 200, 30),) and set(art.frames[0].indices) == {0}
