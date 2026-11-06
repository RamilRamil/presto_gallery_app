# PrestoBinFormat v1 (`.bin`)

Output of `presto_pic_loader`, input for a future MicroPython player on the Pimoroni Presto.
Terms follow `knowledge/domain.okf.json` (`presto-bin-format`, `pixel-art`, `palette`, `frame`).
Reference encoder/decoder: `src/presto_pic_loader/l4_encoders.py`.

All multi-byte integers are **little-endian, unsigned**. No padding or alignment between sections.

## Layout

```
+-----------------+------------------------+-----------+-----------+-----+
| header 16 bytes | palette 3*paletteSize  | frame 0   | frame 1   | ... |
+-----------------+------------------------+-----------+-----------+-----+
frame i = durationMs (2 bytes) + width*height index bytes
```

### Header (16 bytes)

| Offset | Size | Type | Field | Meaning |
|---|---|---|---|---|
| 0 | 4 | ASCII | magic | `P` `P` `X` `A` (0x50 0x50 0x58 0x41) |
| 4 | 1 | u8 | formatVersion | `1` |
| 5 | 1 | u8 | flags | `0`. Reserved; bit 0 will mean "loop animation". Players MUST ignore unknown bits |
| 6 | 2 | u16 | width | cells horizontally (= gridSize: 16, 32 or 64) |
| 8 | 2 | u16 | height | cells vertically (= gridSize) |
| 10 | 2 | u16 | paletteSize | number of palette entries, 1..256 |
| 12 | 2 | u16 | frameCount | number of frames, ≥ 1 (MVP always writes 1) |
| 14 | 1 | u8 | cellSize | hint: screen pixels per cell = 240 // width (15, 7, 3) |
| 15 | 1 | u8 | reserved | `0` |

`struct` format: `"<4sBBHHHHBB"`.

### Palette (`3 * paletteSize` bytes, from offset 16)

Entry *i* is 3 bytes `R, G, B` (0..255, 8 bit per channel). Order matters: pixel bytes are
indices into this list. Adaptive palettes are sorted most-frequent first; the `pico-8` preset
keeps the canonical PICO-8 order (0 = black … 15 = peach).

### Frames (from offset `16 + 3 * paletteSize`)

Each frame:

| Size | Type | Field | Meaning |
|---|---|---|---|
| 2 | u16 | durationMs | display time; `0` = static image |
| width·height | u8[] | indices | palette index per cell, row-major: row 0 left→right, then row 1, … |

Every index is `< paletteSize`. Total file size is exactly
`16 + 3*paletteSize + frameCount * (2 + width*height)`; a player SHOULD reject other sizes.
Example: grid 32, 16 colors, 1 frame → 16 + 48 + 2 + 1024 = **1090 bytes**.

## Drawing on the 240×240 screen

```
cell   = header.cellSize                 # or 240 // width
offset = (240 - width * cell) // 2       # 0 / 8 / 24 for grids 16 / 32 / 64
cell (x, y) -> rectangle (offset + x*cell, offset + y*cell, cell, cell)
```
The margin around the picture is left to the player (e.g. clear to black).

## MicroPython reading sketch

```python
import struct
from presto import Presto

presto = Presto()                   # normal mode, 240x240
display = presto.display

with open("cat.bin", "rb") as f:
    magic, ver, flags, w, h, n_pal, n_frames, cell, _ = struct.unpack("<4sBBHHHHBB", f.read(16))
    assert magic == b"PPXA" and ver == 1
    pal = f.read(3 * n_pal)
    pens = [display.create_pen(pal[3*i], pal[3*i+1], pal[3*i+2]) for i in range(n_pal)]
    off = (240 - w * cell) // 2
    duration = struct.unpack("<H", f.read(2))[0]   # frame 0
    pixels = f.read(w * h)

for y in range(h):
    for x in range(w):
        display.set_pen(pens[pixels[y * w + x]])
        display.rectangle(off + x * cell, off + y * cell, cell, cell)
presto.update()
```

For animation: read all frames (or stream them), draw frame *i*, wait `durationMs`, repeat.

## Versioning

Any change to header layout or meaning bumps `formatVersion`. Adding frames, using `flags`
bit 0 or non-zero `durationMs` is already valid in v1.
