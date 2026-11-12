# Implementation Plan: Scenes mode advances only on a swipe

**Branch**: `009-scenes-manual-advance` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

## Summary

The gallery stops a Scene through `make_stop`, whose time limit comes from
`l3_playlist.slide_limit_ms(playlist, slide_seconds)`: None (no limit) when the Playlist has one item,
otherwise the Slide time. A swipe already stops the Scene at once by waking the play loop. So the
change is one rule in that pure function: no limit when ShowMode is `scenes`, plus a note in the
menu.

## Technical Context

MicroPython 1.26 on the Presto, the gallery of `device/gallery/`; tests with pytest on the Mac
(`tests/device/`). No new files on the board; no change to settings.json or catalog.json.

## Constitution Check

- I. Stratified Design: the rule lives in layer 3 (`l3_playlist.slide_limit_ms`, pure); layer 5
  (`l5_app.play_scene`) only passes the ShowMode in. The menu note is in layer 3 (`l3_menu`).
- II. Dictionary: `knowledge/domain.okf.json` ShowMode `scenes` gets the rule in its description.
- III. Tests: pure tests first.
- V. Simplicity: no new setting.

## Changes

1. `device/gallery/l3_playlist.py`: `slide_limit_ms(playlist, slide_seconds, show_mode)` returns None
   also when `show_mode == "scenes"`.
2. `device/gallery/l5_app.py`, `play_scene`: pass `self.state["settings"]["showMode"]`.
3. `device/gallery/l3_menu.py`, `_settings_view`: in ShowMode `scenes` the Slide time row gets the
   note "сцены: по свайпу" (the note slot 008 added for "у коллекции свои").
4. `knowledge/domain.okf.json`: the rule in ShowMode `scenes`.
5. `docs/scene-format.md` (or device-setup): one line on how Scenes mode advances.

## Tests

- `tests/device/test_device_pure.py`: `slide_limit_ms` is None for `scenes` with many items, the Slide
  time for `all`, `collection`, `tags`, None for one item as before.
- `tests/device/test_device_menu.py`: the settings view shows the note in ShowMode `scenes` and not in
  `all`.
- The whole device suite and `node --test web/test` pass.
- On the Presto: copy the three changed files, choose Сцены, check SC-001 and SC-002 by eye.

## Note

Feature 008 (Collection show settings) is uncommitted in the same files' neighbours; this change is
made on top of it and touches only the lines above.
