import io
import struct

import pytest
from PIL import Image

from presto_pic_loader.l4_encoders import decode_presto_bin, encode_presto_bin, encode_preview_png
from presto_pic_loader.model import Frame, PixelArt, RgbColor

ART = PixelArt(
    width=2, height=2,
    palette=(RgbColor(1, 2, 3), RgbColor(250, 251, 252)),
    frames=(Frame(bytes([0, 1, 1, 0]), 0),),
)


def test_bin_layout_byte_by_byte():
    data = encode_presto_bin(ART)
    assert data[0:4] == b"PPXA"
    assert data[4] == 1 and data[5] == 0
    assert struct.unpack_from("<HHHH", data, 6) == (2, 2, 2, 1)
    assert data[14] == 240 and data[15] == 0  # cellSize = 480 // 2
    assert data[16:22] == bytes([1, 2, 3, 250, 251, 252])
    assert data[22:24] == b"\x00\x00"
    assert data[24:] == bytes([0, 1, 1, 0])
    assert len(data) == 16 + 6 + 2 + 4


def test_bin_size_for_grid32_16_colors():
    art = PixelArt(32, 32, tuple(RgbColor(i, i, i) for i in range(16)),
                   (Frame(bytes(1024), 0),))
    assert len(encode_presto_bin(art)) == 1090


def test_round_trip_multi_frame():
    art = PixelArt(2, 2, ART.palette, (ART.frames[0], Frame(bytes([1, 1, 0, 0]), 120)))
    assert decode_presto_bin(encode_presto_bin(art)) == art


@pytest.mark.parametrize("data", [b"", b"XXXX" + bytes(30), encode_presto_bin(ART)[:-1]])
def test_decode_rejects_bad_files(data):
    with pytest.raises(ValueError):
        decode_presto_bin(data)


def test_preview_png_big_pixels():
    image = Image.open(io.BytesIO(encode_preview_png(ART, preview_scale=8))).convert("RGB")
    assert image.size == (16, 16)
    assert image.getpixel((0, 0)) == (1, 2, 3) and image.getpixel((7, 7)) == (1, 2, 3)
    assert image.getpixel((8, 0)) == (250, 251, 252)


def test_encoders_deterministic():
    assert encode_preview_png(ART) == encode_preview_png(ART)
    assert encode_presto_bin(ART) == encode_presto_bin(ART)
