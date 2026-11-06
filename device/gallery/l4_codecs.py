# LAYER 4 (calculations): bytes/JSON <-> data. PrestoBinFormat v1 reader (docs/bin-format.md).

import json
import struct

from .l1_primitives import cell_size
from .model import CATALOG_FORMAT_VERSION, default_settings, empty_catalog

MAGIC = b"PPXA"
HEADER_FORMAT = "<4sBBHHHHBB"
HEADER_SIZE = 16
MAX_UPLOAD_BYTES = 1024 * 1024
GRID_SIZES = (16, 32, 64)


def parse_bin_header(data):
    """First 16+ bytes -> header dict; raises ValueError."""
    if len(data) < HEADER_SIZE:
        raise ValueError("file too short")
    magic, version, flags, width, height, palette_size, frame_count, _cell, _r = \
        struct.unpack(HEADER_FORMAT, bytes(data[:HEADER_SIZE]))
    if magic != MAGIC or version != 1:
        raise ValueError("not a PrestoBinFormat v1 file")
    if width != height or width not in GRID_SIZES:
        raise ValueError("unsupported size")
    if not 1 <= palette_size <= 256 or frame_count < 1:
        raise ValueError("bad palette size or frame count")
    frame_size = width * height
    frames_offset = HEADER_SIZE + 3 * palette_size
    return {
        "width": width, "height": height, "flags": flags, "paletteSize": palette_size,
        "frameCount": frame_count, "cellSize": cell_size(width), "frameSize": frame_size,
        "framesOffset": frames_offset,
        "totalSize": frames_offset + frame_count * (2 + frame_size),
    }


def frame_offset(header, index):
    """Byte offset of frame `index` (its 2-byte duration comes first)."""
    return header["framesOffset"] + index * (2 + header["frameSize"])


def read_palette(data, header):
    """Bytes holding at least header + palette -> list of (r, g, b)."""
    start = HEADER_SIZE
    return [tuple(data[start + 3 * i: start + 3 * i + 3]) for i in range(header["paletteSize"])]


def read_frame_duration(data):
    return struct.unpack("<H", bytes(data[:2]))[0]


def validate_upload(head, total_length):
    """Check an upload from its first bytes and its length; returns the header."""
    if total_length > MAX_UPLOAD_BYTES:
        raise ValueError("file larger than 1 MB")
    header = parse_bin_header(head)
    if header["totalSize"] != total_length:
        raise ValueError("file length does not match header")
    return header


def catalog_to_json(catalog):
    return json.dumps(catalog)


def catalog_from_json(text):
    """Tolerant load: bad/unknown content gives an empty catalog, bad items are skipped."""
    try:
        data = json.loads(text)
    except ValueError:
        return empty_catalog()
    if not isinstance(data, dict) or data.get("formatVersion") != CATALOG_FORMAT_VERSION:
        return empty_catalog()
    keys = ("mediaId", "name", "tags", "frameCount", "gridSize", "byteSize", "createdAt")
    items = [i for i in data.get("items", []) if isinstance(i, dict) and all(k in i for k in keys)]
    return {"formatVersion": CATALOG_FORMAT_VERSION, "items": items}


def settings_to_json(settings):
    return json.dumps(settings)


def settings_from_json(text):
    try:
        data = json.loads(text)
    except ValueError:
        return default_settings()
    settings = default_settings()
    if isinstance(data, dict):
        for key in settings:
            if key in data:
                settings[key] = data[key]
    return settings
