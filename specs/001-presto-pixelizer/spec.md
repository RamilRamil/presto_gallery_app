# Feature Specification: Presto Pixelizer (MVP)

**Feature Branch**: `001-presto-pixelizer`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Инструмент превращает изображение любого размера в пиксель-арт для
Pimoroni Presto: inbox/ → одна команда → outbox/ (превью PNG + .bin). Настройки: сетка 16/32/64,
число цветов или готовая палитра (PICO-8), crop/fit, дизеринг. GIF — не в MVP, но формат готов к кадрам."

> Terms in this spec follow `knowledge/domain.okf.json` (SourceImage, Grid, Palette, PixelArt,
> Frame, PixelizeSettings, PreviewPng, PrestoBinFormat, Inbox, Outbox, Cli, Layer).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert a picture with defaults (Priority: P1)

The user drops a photo (any size, PNG/JPEG/WebP) into Inbox and runs one command. For each
SourceImage, Outbox gets `<name>.preview.png` (big visible pixels) and `<name>.bin` ready to copy
to the Presto.

**Why this priority**: this is the whole value of the tool; everything else is tuning.

**Independent Test**: put one 1920×1080 JPEG into `inbox/`, run the command with no options,
check that both files appear and the .bin decodes to a 32×32 PixelArt with ≤16 colors.

**Acceptance Scenarios**:

1. **Given** `inbox/cat.jpg`, **When** the command runs with defaults, **Then** `outbox/cat.preview.png`
   and `outbox/cat.bin` exist; the PixelArt is 32×32, center-cropped, ≤16 colors, no dithering.
2. **Given** three images in Inbox, **When** the command runs, **Then** all three are converted and
   a one-line summary per file is printed.
3. **Given** Inbox contains a `.txt` file and a corrupted `.png`, **When** the command runs,
   **Then** the `.txt` is ignored, the corrupted file is reported as an error, the other files are
   still converted, and the command exits with a non-zero code.

---

### User Story 2 - Tune the look (Priority: P2)

The user chooses Grid size (16/32/64), the number of colors (2–256) or a preset Palette
(PICO-8), FitMode (crop/fit) and Dithering (on/off) via command options.

**Why this priority**: different pictures need different settings; without them the output is
often ugly.

**Independent Test**: run the same image with `--grid 64 --palette pico-8 --fit fit --dither`
and verify the result: 64×64, every color is one of the 16 PICO-8 colors, letterbox stripes in the
background color, preview differs from the non-dithered run.

**Acceptance Scenarios**:

1. **Given** a wide image, **When** run with `fit`, **Then** the whole picture is visible and the
   empty area is filled with the background color (black by default).
2. **Given** `--palette pico-8`, **Then** the Palette in the .bin is exactly the 16 PICO-8 colors
   in their canonical order and every index is < 16.
3. **Given** `--colors 4`, **Then** the Palette has at most 4 entries.
4. **Given** an invalid value (`--grid 20`, `--colors 1`, both `--colors` and `--palette`),
   **Then** the command refuses with a clear message and writes nothing.

---

### User Story 3 - Play the file on the Presto later (Priority: P3)

A developer writes a MicroPython player for Presto using only `docs/bin-format.md`.

**Why this priority**: the player is a separate future project, but the format must be ready now.

**Independent Test**: a reference decoder written from the document alone (in the tests)
reads every produced .bin back into identical PixelArt.

**Acceptance Scenarios**:

1. **Given** the document, **Then** it lists every header byte offset, type, endianness, the palette
   layout, the frame layout and how to draw at cellSize on the 240×240 screen.
2. **Given** a future animated file with N frames, **Then** it fits the same format version 1
   without changing the header layout (frameCount and per-frame duration already exist).

### Edge Cases

- Image smaller than the Grid (e.g. 10×10 → 32): upscaled, still produces a valid result.
- Images with transparency: transparent areas become the background color.
- Image with fewer unique colors than `--colors`: Palette is shorter; that is valid.
- Name clash (`cat.png` and `cat.jpg`): the first in sorted order gets `cat.*`, the next gets
  the extension appended (`cat_jpg.bin`, `cat_jpg.preview.png`).
- Outbox missing: created automatically. Existing outputs are overwritten.
- Empty Inbox: message "no images in inbox/", exit code 0.
- Animated GIF/WebP input: not accepted in MVP (GIF extension ignored; animated WebP uses
  first frame only).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Cli MUST process every file with extension .png/.jpg/.jpeg/.webp (case-insensitive)
  in Inbox with one command and no required arguments.
- **FR-002**: For each SourceImage the tool MUST write `<stem>.preview.png` and `<stem>.bin` to Outbox.
- **FR-003**: Grid size MUST be one of 16, 32, 64; default 32. PixelArt is gridSize × gridSize.
- **FR-004**: Color selection MUST be either adaptive with colorCount 2–256 (default 16) or a named
  preset Palette; MVP presets: `pico-8`. The two options are mutually exclusive.
- **FR-005**: FitMode MUST be `crop` (default; center square crop) or `fit` (whole image, padded with
  the background color, default black, configurable).
- **FR-006**: Dithering MUST be switchable; default off.
- **FR-007**: PreviewPng MUST show each cell as a square block of previewScale pixels (default 8,
  i.e. 256×256 for Grid 32), with no smoothing.
- **FR-008**: The .bin MUST follow PrestoBinFormat v1: magic, version, size, palette, frame count,
  frames (duration + indices). MVP writes exactly one Frame with duration 0.
- **FR-009**: The format MUST be documented byte by byte in `docs/bin-format.md`.
- **FR-010**: The same input and settings MUST always produce byte-identical outputs.
- **FR-011**: Invalid settings MUST be rejected before any file is written; a bad input file MUST NOT
  stop processing of the others; the exit code is non-zero if any file failed.

### Key Entities

See `knowledge/domain.okf.json`. Main ones: **SourceImage**, **PixelizeSettings** (Grid, Palette
choice, FitMode, Dithering, backgroundColor), **PixelArt** (size, Palette, list of Frame),
**PreviewPng**, **PrestoBinFormat**, **Inbox**, **Outbox**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a fresh checkout, a user converts a picture with one command in under 1 minute
  of their time.
- **SC-002**: A 4000×3000 photo is converted in under 2 seconds on a typical laptop.
- **SC-003**: 100% of produced .bin files decode back to the same PixelArt with a decoder written
  only from the format document.
- **SC-004**: A Grid-32 image file is ≤ 2 KB (header + ≤256 palette entries + 1024 indices).
- **SC-005**: Adding animation later requires no change to the conversion of a single Frame
  and no change to format version 1 header layout.

## Assumptions

- "Normal mode" Presto screen is 240×240; cellSize = floor(240 / gridSize) → 15 / 7 / 3 px; the
  player centers the image (e.g. 224 px + 8 px margin for Grid 32).
- Colors are stored as 8-bit RGB; conversion to the display's pen format is the player's job.
- Downscaling uses area averaging (crisp, representative cell colors).
- Adaptive palettes are ordered deterministically (by frequency, then by value).
- Single user, local machine, no network, no GUI.
