"""LAYER 4 (calculations): PixelArt <-> bytes. The format abstraction barrier.

PrestoBinFormat v1 is described byte by byte in docs/bin-format.md.
"""
from __future__ import annotations

import io
import struct

from PIL import Image

from .l1_primitives import cell_size
from .model import Frame, PixelArt, RgbColor

MAGIC = b"PPXA"
FORMAT_VERSION = 1
HEADER = struct.Struct("<4sBBHHHHBB")  # 16 bytes
FRAME_HEADER = struct.Struct("<H")


def encode_presto_bin(art: PixelArt) -> bytes:
    header = HEADER.pack(MAGIC, FORMAT_VERSION, 0, art.width, art.height,
                         len(art.palette), len(art.frames), cell_size(art.width), 0)
    palette = bytes(channel for color in art.palette for channel in color)
    frames = b"".join(FRAME_HEADER.pack(f.duration_ms) + f.indices for f in art.frames)
    return header + palette + frames


def decode_presto_bin(data: bytes) -> PixelArt:
    """Reference decoder (what the MicroPython player does); raises ValueError."""
    if len(data) < HEADER.size:
        raise ValueError("file too short")
    magic, version, _flags, width, height, palette_size, frame_count, _cell, _r = \
        HEADER.unpack_from(data)
    if magic != MAGIC or version != FORMAT_VERSION:
        raise ValueError("not a PrestoBinFormat v1 file")
    pos = HEADER.size
    palette = tuple(RgbColor(*data[pos + 3 * i: pos + 3 * i + 3]) for i in range(palette_size))
    pos += 3 * palette_size
    frames = []
    for _ in range(frame_count):
        (duration,) = FRAME_HEADER.unpack_from(data, pos)
        pos += FRAME_HEADER.size
        frames.append(Frame(bytes(data[pos: pos + width * height]), duration))
        pos += width * height
    if pos != len(data):
        raise ValueError("file length does not match header")
    return PixelArt(width, height, palette, tuple(frames))


def encode_preview_png(art: PixelArt, preview_scale: int = 8, frame_index: int = 0) -> bytes:
    image = Image.new("P", (art.width, art.height))
    image.putpalette([channel for color in art.palette for channel in color])
    image.putdata(list(art.frames[frame_index].indices))
    big = image.resize((art.width * preview_scale, art.height * preview_scale),
                       Image.Resampling.NEAREST)
    buffer = io.BytesIO()
    big.save(buffer, format="PNG")
    return buffer.getvalue()
