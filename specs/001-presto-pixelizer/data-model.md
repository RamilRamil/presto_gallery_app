# Data Model (mirrors knowledge/domain.okf.json)

- **RgbColor**(red, green, blue: 0..255) — NamedTuple.
- **Size**(width, height ≥ 1).
- **FitMode**: enum `crop` | `fit`.
- **PixelizeSettings**(gridSize ∈ {16,32,64}, colorCount 2..256, paletteName `adaptive`|`pico-8`, fitMode, dither: bool, backgroundColor: RgbColor). Built only via `make_settings` which validates; frozen.
- **SourceImage**(image: PIL RGB image, name: str) — frozen wrapper.
- **Frame**(indices: bytes len = width·height, durationMs 0..65535).
- **PixelArt**(width, height, palette: tuple[RgbColor,…] 1..256, frames: tuple[Frame,…] ≥1). Invariant: every index < len(palette).
