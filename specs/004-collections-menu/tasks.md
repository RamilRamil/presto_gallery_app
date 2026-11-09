# Tasks: Batch Upload, Collections and the Device Menu

**Input**: [plan.md](plan.md), [spec.md](spec.md)
**Tests**: required by the constitution (Principle III).

## Phase 1: Setup

- [x] T001 Add `collection`, `upload-queue`, `device-menu`; update `show-mode`, `device-settings` in `knowledge/domain.okf.json`

## Phase 2: User Story 1 - Upload many files (P1)

**Independent test**: 20 files uploaded with one press, and the Presto never jumps to them.

- [x] T002 [P] [US1] Add queue transitions in `web/js/l3-pipeline.js` with tests in `web/test/queue.test.mjs`
- [x] T003 [US1] Add `show=0` to `POST /api/media` and `/api/scenes` in `device/gallery/l5_app.py`, `device/gallery/l3_playlist.py` with tests
- [x] T004 [US1] Add the queue list, batch upload, cancel and retry in `web/js/l5-ui.js`, `web/js/l5-api.js`, `web/index.html`, `web/style.css`

## Phase 3: User Story 2 - Collections (P1)

**Independent test**: a Collection of 3 items with different Tags plays alone.

- [x] T005 [US2] Add the Collection data and ops in `device/gallery/model.py`, `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py`, `device/gallery/l4_codecs.py` with tests
- [x] T006 [US2] Add the collection routes and `collection=<id>` in `device/gallery/l5_app.py`
- [x] T007 [US2] Add the collections panel, library multi-select, filter and show mode in `web/js/l5-ui.js`, `web/js/l5-api.js`, `web/index.html`

## Phase 4: User Story 3 - Device menu (P1)

**Independent test**: with no network, choose a Collection on the device; it survives a restart.

- [x] T008 [P] [US3] Add the 5×7 Latin and Cyrillic font in `device/gallery/l1_font.py` with tests
- [x] T009 [US3] Add the menu state machine in `device/gallery/l3_menu.py` with tests in `tests/device/test_device_menu.py`
- [x] T010 [US3] Add drawing and the touch loop in `device/gallery/l5_menu.py`; open it from `device/gallery/l5_app.py`

## Phase 5: User Story 5 and batch setup (P1)

**Independent test**: set a grid and Tags on the first file, change one file by hand, upload; each
file has the expected setup. "Изменить" changes name, Tags and Collections in one save.

- [x] T015 Update `upload-queue` in `knowledge/domain.okf.json`
- [x] T016 [P] [US5] Add `set_item_collections` and op `editItem` in `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py`, PATCH in `device/gallery/l5_app.py`, with tests
- [x] T017 [P] [US1] Add the relative CropView in `web/js/l1-primitives.js`; `referenceEntry`, `entrySetup`, `changeSetup`, `resetEntry` and `toggleTag` in `web/js/l3-pipeline.js`, with tests
- [x] T018 [US1] Use per-file setup in the queue and upload in `web/js/l5-ui.js`, `web/index.html`, `web/style.css`
- [x] T019 [US5] Add toggling Tag labels and the edit form in `web/js/l5-ui.js`, `web/index.html`, `web/style.css`
- [ ] T020 Run pytest, `node --test` and the simulator end to end, then copy to the Presto

- [x] T021 Mount microSD with the corrected driver and copy a flash gallery to it in `device/gallery/l5_sd.py`, with tests

## Phase 6: Polish

- [x] T011 [P] Update layer guards in `tests/device/test_device_layers.py`
- [x] T012 [P] Update `docs/device-setup.md`, `README.md`
- [x] T013 Run pytest, `node --test` and the simulator end to end
- [ ] T014 Copy to the Presto and check on the real device
