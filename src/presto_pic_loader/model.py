"""DATA: immutable domain types. No behaviour; usable from every layer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from PIL import Image


class RgbColor(NamedTuple):
    red: int
    green: int
    blue: int


class Size(NamedTuple):
    width: int
    height: int


class FitMode(str, Enum):
    CROP = "crop"
    FIT = "fit"


@dataclass(frozen=True)
class PixelizeSettings:
    grid_size: int
    color_count: int
    palette_name: str  # "adaptive" or a preset name such as "pico-8"
    preset_palette: tuple[RgbColor, ...] | None
    fit_mode: FitMode
    dither: bool
    background_color: RgbColor


@dataclass(frozen=True)
class SourceImage:
    name: str
    image: Image.Image  # RGB, alpha already flattened


@dataclass(frozen=True)
class Frame:
    indices: bytes  # width*height palette indices, row-major
    duration_ms: int = 0


@dataclass(frozen=True)
class PixelArt:
    width: int
    height: int
    palette: tuple[RgbColor, ...]
    frames: tuple[Frame, ...]
