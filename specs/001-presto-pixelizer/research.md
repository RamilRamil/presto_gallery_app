# Research: Presto Pixelizer

- **Downscale**: Decision `resize(..., Image.BOX)`. Rationale: true area average per cell, crisp. Alternatives: LANCZOS (ringing halos), NEAREST (noisy).
- **Adaptive palette**: Pillow `quantize(colors, method=MEDIANCUT)` + deterministic re-sort. Alternatives: own k-means (slower, more code — YAGNI).
- **Fixed palette mapping**: `quantize(palette=pal_img, dither=FLOYDSTEINBERG|NONE)`. Alternatives: own nearest-color loop (kept only as L1 `color_distance` for tests/no-dither verification).
- **Color storage**: RGB888 in file; Presto converts with `display.create_pen(r,g,b)`. Alternative RGB565 — locks player to one display mode.
- **Endianness**: little-endian (`struct '<'`), native for RP2350 and MicroPython `struct`.
- **PICO-8 palette**: canonical 16 colors 000000,1D2B53,7E2553,008751,AB5236,5F574F,C2C3C7,FFF1E8,FF004D,FFA300,FFEC27,00E436,29ADFF,83769C,FF77A8,FFCCAA.
- **Env**: Pillow missing system-wide → project-local `.venv` via `uv venv` (stays inside the folder).
