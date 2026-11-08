# Tasks: Full-Screen Pictures and Scenes

**Input**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/http-api.md](contracts/http-api.md)
**Tests**: required by the constitution (Principle III).

## Phase 1: Setup

- [ ] T001 Amend `.specify/memory/constitution.md` to v1.2.0 with the new grid sizes
- [ ] T002 [P] Add `scene`, `access-password` and update `grid`, `media-item`, `show-mode` in `knowledge/domain.okf.json`

## Phase 2: Foundational

- [ ] T003 [P] Extend `GRID_SIZES` in `src/presto_pic_loader/l1_primitives.py`, `device/gallery/l4_codecs.py`, `web/js/l1-primitives.js`
- [ ] T004 Add golden cases for Grids 40 and 80 in `src/presto_pic_loader/golden.py`; regenerate `tests/golden/`
- [ ] T005 Add `kind`, `flagged`, `error`, `scene_item` and mode `scenes` in `device/gallery/model.py`

## Phase 3: User Story 1 - Full-screen pictures (P1)

**Independent test**: a Grid 60 picture covers all edge pixels of the screen.

- [ ] T006 [US1] Add `blit_frame` in `device/gallery/l5_blit.py`
- [ ] T007 [US1] Use the blit, with rectangle fallback, in `play_item` in `device/gallery/l5_app.py`
- [ ] T008 [P] [US1] Add `gridLimits` in `web/js/l3-pipeline.js` with tests in `web/test/l3l4.test.mjs`
- [ ] T009 [US1] Add grid options, default 60, hint and warning in `web/index.html`, `web/js/l5-ui.js`; size canvases to the art

## Phase 4: User Story 2 - Password (P1)

**Independent test**: every `/api/*` request without the password gets 401 and no data.

- [ ] T010 [P] [US2] Add `bearer_token`, `password_matches` in `device/gallery/l4_codecs.py` with tests in `tests/device/test_device_pure.py`
- [ ] T011 [US2] Add the auth check, attempt limit and `passwordSet` in `device/gallery/l5_app.py`; add `WEB_PASSWORD` to `device/secrets.example.py`
- [ ] T012 [US2] Add the bearer header and 401 handling in `web/js/l5-api.js`; login form, log out and warning in `web/js/l5-ui.js`, `web/index.html`, `web/style.css`
- [ ] T013 [US2] Return 404 for missing static files and encoded `..` in `device/gallery/l5_app.py`

## Phase 5: User Story 3 - Scenes (P2)

**Independent test**: `scene_storm.py` uploaded unchanged plays full-screen, then the next item shows.

- [ ] T014 [P] [US3] Add `scene_rect` in `device/gallery/l3_scene.py` with tests
- [ ] T015 [P] [US3] Add `validate_scene_source` and catalog defaults in `device/gallery/l4_codecs.py` with tests
- [ ] T016 [US3] Extend `filter_by_mode`, `build_playlist`, `apply_command`, add `slide_limit_ms`, `item_by_id` in `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py` with tests
- [ ] T017 [US3] Add `device/pixel.py` and tests in `tests/device/test_device_pixel.py`
- [ ] T018 [US3] Add `pump`, `make_stop`, `run_scene` in `device/gallery/l5_scene.py`, `device/gallery/l5_clock.py`
- [ ] T019 [US3] Add `POST /api/scenes`, Scene deletion and the play dispatch in `device/gallery/l5_app.py`
- [ ] T020 [US3] Add Scene upload, the `scenes` mode and library display in `web/js/l5-api.js`, `web/js/l5-ui.js`, `web/index.html`

## Phase 6: User Story 4 - Bad Scenes (P2)

**Independent test**: a crashing Scene and a never-stopping Scene are both flagged and skipped.

- [ ] T021 [US4] Add the `flag`/`unflag` ops and tests in `device/gallery/l3_playlist.py`, `device/gallery/l2_catalog.py`
- [ ] T022 [US4] Add the running marker, boot check and error flagging in `device/gallery/l5_scene.py`, `device/gallery/l5_app.py`
- [ ] T023 [US4] Add the flagged state and "Включить" in `web/js/l5-ui.js`

## Phase 7: Polish

- [ ] T024 [P] Update layer guards in `tests/device/test_device_layers.py`
- [ ] T025 [P] Add `docs/scene-format.md`; update `docs/device-setup.md`, `docs/bin-format.md`, `README.md`
- [ ] T026 Run pytest, `node --test` and the simulator end to end
- [ ] T027 Copy to the Presto and run `quickstart.md` on the real device

## Dependencies

Phases 1–2 first. US1, US2 are independent. US3 needs US2 (Scene upload requires the password). US4 needs US3.

## Phase 8: User Story 5 - Choose the part of the picture (P2)

**Independent test**: drag and zoom a wide photo to its left edge; the upload shows exactly that part.

- [ ] T028 Add `crop-view` to `knowledge/domain.okf.json`
- [ ] T029 [P] [US5] Add `defaultCropView`, `cropSide`, `clampCropView`, `panCropView`, `zoomCropView`, `cropWindow` in `web/js/l1-primitives.js` with tests in `web/test/l1.test.mjs`
- [ ] T030 [US5] Add `cropRgbWindow` in `web/js/l2-image-ops.js` and route `cropRgb` through it, with tests in `web/test/l2.test.mjs`
- [ ] T031 [US5] Pass the view through `pixelize` and `pixelizeFile` in `web/js/l3-pipeline.js`
- [ ] T032 [US5] Add drag, wheel, pinch, slider, reset and the fast preview in `web/js/l5-ui.js`, `web/index.html`, `web/style.css`; raise the decode limit to 2048 px
- [ ] T033 [US5] Check in the browser pane at desktop and phone width, then on the real Presto
