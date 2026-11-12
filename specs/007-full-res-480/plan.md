# Implementation Plan: Full screen resolution (480×480)

**Branch**: `007-full-res-480` | **Date**: 2026-11-10 | **Spec**: [spec.md](spec.md)

## Summary

The app creates `Presto(full_res=True)`. One constant, the screen size, moves from 240 to 480 in the
places that draw pictures and Scenes. The menu and gestures keep working in their 240 layout: layer 5
scales drawing by 2 and halves touch coordinates, so layer 3 and its tests stay as they are. Grid 480
joins the grid list in the browser, the CLI and the device. The Scene size limit goes to 256 KB.

## Measured on the Presto (2026-11-10)

| | 240 mode | 480 mode |
|---|---|---|
| Framebuffer | 115 200 B | 460 800 B |
| Viper write of every pixel | 16 ms | 66 ms |
| `presto.update()` | 3-16 ms | 24 ms |
| Free memory after start | 8.1 MB | 7.6 MB |

## Technical Context

**Language/Version**: MicroPython 1.26 Presto build · vanilla JS (WebUi) · Python 3 + Pillow (CLI)
**Primary Dependencies**: nothing new
**Storage**: `.bin` v1 unchanged; grid-480 picture ≈ 225 KB per frame
**Testing**: pytest (device layers, CLI, golden vectors) · `node --test` · simulator · the real Presto
**Performance Goals**: SC-001..SC-004
**Constraints**: old media, catalog and Scenes keep working with no migration
**Scale/Scope**: ~150 LOC changed + tests

## Constitution Check (v1.2.0)

| Principle | How | Status |
|---|---|---|
| I Stratified Design | screen size is data in D1; scaling of menu drawing and touch only in D5 | ✅ |
| II OKF | update `presto-screen` (480×480), `grid-size` (adds 480), `scene` (256 KB) | ✅ |
| III Tests | grid list, cell/offset at 480, touch mapping, Scene limit, golden vectors at 480 | ✅ |
| IV Format | `.bin` stays v1; `cellSize` is a hint the device never reads | ✅ |
| V Simplicity | no dependency; one screen constant; menu code untouched | ✅ |
| VI Shared contract | JS and Python grid lists and `cellSize` change together; golden vectors regenerated | ✅ |

## Key decisions

1. **One screen size, 480.** `PRESTO_SCREEN_SIZE = 480` in `l1_primitives.py` and
   `l1-primitives.js`; `l5_blit.SCREEN`, `pixel.SCREEN` and the offset in `l5_app.frame_drawer` read it.
   `cell_size(32) = 15`, `cell_size(64) = 7` (offset 16), `cell_size(480) = 1`. `layout()` packs size in
   9 bits, enough for 480.
2. **Menu stays in 240 units.** `l3_menu*`, `l3_menu_cells` and `l3_gesture` keep their numbers.
   `l5_menu.draw_menu` multiplies every rectangle and the text scale by `UI_SCALE = 2`; `run_menu` and
   `touch_loop` divide `touch.x`, `touch.y` by `UI_SCALE` before calling layer 3. The pause mark and the
   boot message are drawn the same way. So menu and gesture tests need no change, and swipe distances
   keep their size on the glass.
3. **Touch range is checked on the board first** (task T002): the old project's note says the
   FT6236 reports 0..479 in full-resolution mode. If it reports 0..239, `UI_SCALE` for touch becomes 1.
4. **Grid 480** in `GRID_SIZES` (JS, Python CLI, device `l4_codecs`). Nothing else in the pipeline
   changes: it already does 256 colours and Floyd-Steinberg. The browser shows "≈225 KB per frame,
   up to 4 frames" through the existing `gridLimits`.
5. **GIF frames in memory.** `play_item` reads all frames into one buffer when the file is at most
   1 MB and enough memory is free (it always is, files are capped at 1 MB); otherwise it reads per frame
   as now. A 230 KB read from the card would take most of a 100 ms frame.
6. **Scene limit 256 KB** (`MAX_SCENE_BYTES`, the browser check, `docs/scene-format.md`).
7. **Simulator** `device/sim/presto.py`: `SIZE` follows `full_res`, so the preview PNG is 480×480.
8. **Docs**: `bin-format.md` (480 grid, `cellSize` = 480 // width, drawing on 480), `scene-format.md`
   (480 screen, 15 px cells, 256 KB, a 240-era Scene drawing on `display` fills a quarter),
   `device-setup.md` (screen mode).

## Files

```text
device/gallery/l1_primitives.py   PRESTO_SCREEN_SIZE = 480
device/gallery/l4_codecs.py       GRID_SIZES + 480, MAX_SCENE_BYTES = 256 KB
device/gallery/l5_blit.py         SCREEN from l1
device/gallery/l5_menu.py         UI_SCALE drawing and touch
device/gallery/l5_app.py          full_res=True, offset from l1, touch scaling, pause mark, boot text, frames in memory
device/pixel.py                   SCREEN from l1
device/sim/presto.py              480 when full_res
web/js/l1-primitives.js           PRESTO_SCREEN_SIZE = 480, GRID_SIZES + 480
web/index.html                    480 option in the grid list
web/js/l5-ui.js                   Scene limit text
src/presto_pic_loader/            GRID_SIZES + 480, cellSize at 480
tests/                            updated and new tests, golden vectors at 480
docs/, knowledge/domain.okf.json  as in decision 8
```

## Risks

- **Browser speed at 480.** Quantizing 230 400 pixels to 256 colours in JS may take a few seconds on a
  phone. Measured in T010; if it is slow, the convert button shows progress.
- **GIF speed.** 66 ms to write a 480 frame + 24 ms update: frames under ~100 ms play slower than set.
- **Old Scenes drawing on `display`.** Not on this device now; documented.

## Order of work

1. T001 OKF entries. T002 touch range in full-res mode on the board.
2. T003 D1 screen size and grid list (device, CLI, JS) + tests + golden vectors.
3. T004 blit, pixel, `frame_drawer`, `full_res=True`; T005 menu and touch scaling; T006 GIF frames in memory.
4. T007 Scene limit; T008 simulator; T009 docs.
5. T010 pytest, web tests, simulator at phone width; T011 deploy and check on the board: a grid-480
   photo, old pictures, menu taps, swipes, Scenes, a 480 GIF.

After this feature, the 480 Scenes in `PRESTO/scenes480/` follow their own plan.
