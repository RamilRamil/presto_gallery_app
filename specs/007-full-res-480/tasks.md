# Tasks: Full screen resolution (480×480)

**Input**: [plan.md](plan.md), [spec.md](spec.md)
**Tests**: required by the constitution (Principle III).

## Phase 1: Setup

- [x] T001 Update `presto-screen`, `grid-size`, `scene` in `knowledge/domain.okf.json`
- [x] T002 Check the touch range in full-resolution mode on the board (needs a tap from the user): 0..479 on both axes

## Phase 2: Foundational

- [x] T003 `PRESTO_SCREEN_SIZE = 480` and grid 480 in `device/gallery/l1_primitives.py`, `device/gallery/l4_codecs.py`, `src/presto_pic_loader/l1_primitives.py`, `web/js/l1-primitives.js`; tests; regenerate golden vectors

## Phase 3: User Story 1 + 2 - Photos at 480, old media still right (P1)

- [x] T004 [US1] `full_res=True`, frame offset from l1, `l5_blit.SCREEN` from l1 in `device/gallery/l5_app.py`, `device/gallery/l5_blit.py`; 480 option in `web/index.html`
- [x] T005 [US2] `UI_SCALE` for menu drawing, touch, pause mark and boot text in `device/gallery/l5_menu.py`, `device/gallery/l5_app.py`; tests
- [x] T006 [US2] GIF frames read once into memory in `device/gallery/l5_app.py`

## Phase 4: User Story 3 - Scenes at 480 (P2)

- [x] T007 [US3] `pixel.SCREEN` from l1 in `device/pixel.py`; Scene limit 256 KB in `device/gallery/l4_codecs.py`, `device/gallery/l5_app.py`, `web/js/l3-pipeline.js`; tests

## Phase 5: Polish

- [x] T008 Simulator at 480 in `device/sim/presto.py`
- [x] T009 Update `docs/bin-format.md`, `docs/scene-format.md`, `docs/device-setup.md`
- [x] T010 Run pytest, web tests, simulator check at phone width; time conversion of a 480 photo in the browser
  (desktop Chrome: 0.7 s for a 1600×1200 JPEG at 256 colours; `l3_screen` added so layer 5 reaches the screen size through layer 3)
- [x] T011 Deploy to the Presto: a grid-480 photo, old pictures, menu taps, swipes, Scenes, a 480 GIF (taps need the user's hands)
