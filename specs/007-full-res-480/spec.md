# Feature Specification: Full screen resolution (480×480)

**Feature Branch**: `007-full-res-480` (not created yet: 005 and 006 are uncommitted on `006-scene-speed`)
**Created**: 2026-11-10
**Status**: Draft, waiting for approval
**Input**: "экран 480 на 480? я тогда хочу иметь возможность фотографии закидывать в этом разрешении тоже"; "Сцены в 480"

## Context

The Presto panel has 480×480 pixels. The gallery runs the display in its 240×240 mode, where every
pixel is a 2×2 square. This feature switches the whole gallery to 480×480, adds a 480 grid so a photo
keeps every screen pixel, and lets Scenes draw at 480×480.

## User Scenarios & Testing

### User Story 1 - Upload a photo at 480×480 (Priority: P1)

I pick a photo in the browser, choose the 480 grid and 256 colours, and upload it. On the Presto it
fills the screen at full sharpness.

**Independent test**: upload one photo at grid 480; up close the screen shows single-pixel detail.

1. **Given** grid 480 is chosen, **when** I upload, **then** the preview and the device show the photo
   480×480 with no border, using up to 256 colours (dithering optional, as for other grids).
2. **Given** an animated GIF at grid 480, **then** it is accepted while the file fits the 1 MB limit
   (up to 4 frames) and refused with a clear message when it does not.
3. **Given** grid 480, **then** the browser says the file size (about 225 KB per frame).

### User Story 2 - Everything I already have still looks right (Priority: P1)

**Independent test**: after the update every existing picture, GIF, Scene and menu screen looks as
before or better, and every tap and swipe still works.

1. **Given** existing pictures at grids 16-240, **then** they fill the same area as before; grid 32 and
   16 now fill the screen exactly with no border (480 divides by them), the others keep their border.
2. **Given** the device menu, **then** it looks the same and every button reacts where it is drawn.
3. **Given** swipes and the long press, **then** they work as before.
4. **Given** an existing Scene, **then** it plays as before; its 32 cells are now exactly 15 px each.
5. **Given** a GIF, **then** it plays at its own frame times when those are 100 ms or longer;
   faster frames play as fast as the device can draw them.

### User Story 3 - Scenes at 480×480 (Priority: P2)

1. **Given** a Scene that draws on `display` directly, **then** it gets a 480×480 screen.
2. **Given** a Scene file up to 256 KB, **then** it is accepted (the limit was 64 KB).

### Edge Cases

- A Scene written for the old 240 screen that draws on `display` directly fills only the top-left
  quarter. The three Scenes on the device use only the `pixel` helpers, so they are not affected.
- The microSD is slow for large GIF frames: a GIF that fits in memory is read once, not every loop.
- Not enough free memory for a 480 GIF: it plays by reading frames from the card, slower.

## Requirements

- **FR-001** The device draws at 480×480 (firmware full-resolution mode) for pictures, Scenes and the menu.
- **FR-002** Grid 480 is added to the allowed grid sizes in the browser, the command-line tool and the device.
- **FR-003** A picture of grid N is drawn with cell `480 // N` and centred, as before with 240.
- **FR-004** The menu keeps its layout, scaled 2×; touches are read in 480 coordinates and mapped to it.
- **FR-005** Swipe and tap distances keep their size on the glass (they double in pixels).
- **FR-006** The `pixel` helpers keep a 32-cell grid, stretched over 480×480; `display` is 480×480.
- **FR-007** Scene files up to 256 KB are accepted.
- **FR-008** `.bin` stays format version 1; only the `cellSize` hint is now `480 // width`. Old files load unchanged.
- **FR-009** The simulator renders 480×480.

## Success Criteria

- **SC-001** A grid-480 photo appears within 1.5 s of its slide start.
- **SC-002** Every existing item in the gallery plays after the update with no re-upload.
- **SC-003** Every menu button can be pressed on the real device on the first try.
- **SC-004** A 4-frame GIF at grid 480 loops at 100 ms per frame or faster once loaded.

## Assumptions

- 256 colours with optional dithering is good enough for photos on this screen; a true-colour format
  (65 536 colours, 450 KB per frame) is not part of this feature.
- The menu does not get finer text now; it is the same menu at double size.
