# Tasks: Device gestures and library management on the Presto

**Input**: [plan.md](plan.md), [spec.md](spec.md)
**Tests**: required by the constitution (Principle III).

## Phase 1: Setup

- [x] T001 Add `gesture`, `brightness`, `pause`, `on-screen-keyboard`; update `device-menu`, `device-settings` in `knowledge/domain.okf.json`

## Phase 2: User Story 1 - Gestures (P1)

**Independent test**: swipes, a tap and a long press each do only their own action.

- [x] T002 [P] [US1] Add the classifier in `device/gallery/l3_gesture.py` with tests in `tests/device/test_device_gesture.py`
- [x] T003 [US1] Use gestures, Pause and the pause mark in `device/gallery/l5_app.py` and `device/gallery/l5_scene.py`

## Phase 3: User Story 2 - Brightness (P2)

**Independent test**: brightness survives a restart and never restarts the current item.

- [x] T004 [US2] Add levels and `setBrightness`, keep the level on browser saves, in `device/gallery/model.py`, `device/gallery/l3_playlist.py`; tests in `tests/device/test_device_pure.py`
- [x] T005 [US2] Apply the backlight in `device/gallery/l5_app.py` and `device/sim/presto.py`

## Phase 4: User Story 3 - Sort the current picture (P2)

**Independent test**: a Tag and a Collection added on the device show up in the browser.

- [x] T006 [P] [US3] Add the keyboard in `device/gallery/l3_keyboard.py` with tests in `tests/device/test_device_keyboard.py`
- [x] T007 [US3] Add shared cells and the current-item screens in `device/gallery/l3_menu_cells.py`, `device/gallery/l3_menu_library.py`, `device/gallery/l3_menu.py`; tests in `tests/device/test_device_menu.py`
- [x] T008 [US3] Apply menu commands and draw keys in `device/gallery/l5_menu.py`

## Phase 5: User Story 4 - Manage Collections and Tags (P3)

**Independent test**: create, rename and delete a Collection; rename a Tag everywhere.

- [x] T009 [US4] Add `rename_tag`, `remove_tag`, `renameTag`, `removeTag` in `device/gallery/l2_catalog.py`, `device/gallery/l3_playlist.py`; tests in `tests/device/test_device_pure.py`
- [x] T010 [US4] Add the management and confirmation screens in `device/gallery/l3_menu_library.py`; tests in `tests/device/test_device_menu.py`

## Phase 6: Polish

- [x] T011 Update `tests/device/test_device_layers.py`, `docs/device-setup.md`, `README.md`
- [x] T012 Run pytest and a simulator check of gestures, Pause and Brightness
- [x] T013 Deploy to the Presto and check that the app starts and the backlight call works
- [ ] T014 On the real device: each gesture 20 times, the menu, the keyboard (needs the user's hands)
