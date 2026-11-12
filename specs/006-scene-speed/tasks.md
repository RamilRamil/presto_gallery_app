# Tasks: Scene speed

**Input**: [plan.md](plan.md), [spec.md](spec.md)
**Tests**: required by the constitution (Principle III).

## Phase 1: Setup

- [x] T001 Add `scene-speed` and update `scene` in `knowledge/domain.okf.json`

## Phase 2: Foundational

- [x] T002 Add `SPEED_PERCENTS`, `item_speed`, `set_speed`, `editItem` with `speedPercent` in `device/gallery/model.py`, `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py`; tests in `tests/device/test_device_scene_speed.py`
- [x] T003 Add `paced_ms`, `speed_label` in `device/gallery/l3_scene.py`, `pace_scene` in `device/gallery/l5_scene.py`; tests in `tests/device/test_device_scene_speed.py`
- [x] T004 Check on the board that replacing `time` in a Scene's globals works

## Phase 3: User Story 1 - Browser (P1)

**Independent test**: set 2× in the edit form; the Scene plays about twice as fast and the file is unchanged.

- [x] T005 [US1] Pass the speed to the Scene and accept `speedPercent` in `device/gallery/l5_app.py`
- [x] T006 [US1] Add the speed field and the card label in `web/index.html`, `web/js/l5-ui.js`

## Phase 4: User Story 2 - Device menu (P2)

**Independent test**: with no phone, choose 0.5× in the menu; the Scene slows down and the browser shows 0.5×.

- [x] T007 [US2] Add the "Скорость" row and the `itemSpeed` screen in `device/gallery/l3_menu_library.py`; tests in `tests/device/test_device_menu.py`

## Phase 5: Polish

- [x] T008 Update `tests/device/test_device_layers.py`, `docs/scene-format.md`
- [x] T009 Run pytest, web tests and a simulator check
- [x] T010 Deploy to the Presto and measure frame timing at 1×, 2×, 4× and 0.25×
- [ ] T011 On the real device: change the speed in the menu and in the browser (needs the user's hands)

## Phase 6: User Story 3 - Collection speed (P2)

**Independent test**: a Collection with two Scenes and a picture, set 2×; both Scenes show 2×, the picture has no speed.

- [x] T012 [US3] Say in `knowledge/domain.okf.json` that a Collection sets the SceneSpeed of its Scenes
- [x] T013 [US3] Add `collection_scenes`, `common_speed`, `set_collection_speed` and the `setCollectionSpeed` command in `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py`; tests in `tests/device/test_device_scene_speed.py`
- [x] T014 [US3] Add the "Скорость" row and the `collectionSpeed` screen in `device/gallery/l3_menu_library.py`; tests in `tests/device/test_device_menu.py`
- [x] T015 [US3] Accept `speedPercent` in `PATCH /api/collections/<id>` in `device/gallery/l5_app.py`; add the speed to the Collection row in `web/js/l5-api.js`, `web/js/l5-ui.js`, `web/style.css`
- [x] T016 Update `docs/scene-format.md`, run pytest, web tests and a simulator check at phone width
- [x] T017 Deploy to the Presto and check that it starts
- [ ] T018 On the real device: set a Collection speed in the menu and in the browser (needs the user's hands)
