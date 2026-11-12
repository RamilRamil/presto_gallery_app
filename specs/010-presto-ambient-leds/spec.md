# Feature Specification: Ambient LEDs follow the screen

**Feature Branch**: `010-presto-ambient-leds` (not created yet: 005–009 are uncommitted on `006-scene-speed`)

**Created**: 2026-11-12

**Status**: Draft, waiting for approval

**Input**: "у presto платы есть диоды сзади, я хочу чтобы они синхронизировались с изображением" and later
"это должна быть общая настройка и должна быть отключаемой".

## Context

The Presto has 7 RGB LEDs on its back (`Presto.NUM_LEDS`), which light the wall behind it. The gallery
creates the board with `Presto(ambient_light=False, ...)`, so today they stay dark. The Presto firmware
already has `presto.auto_ambient_leds(enable)`: once it is on, each `presto.update()` gives every LED the
colour of the part of the screen edge next to it. This is done in the firmware (C), not in Python.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The wall glows with the picture (Priority: P1)

A picture, GIF or Scene is on the screen; the LEDs behind the Presto show the colours of the screen edges,
so the wall is warm behind a sunset and blue behind the sea. In a GIF or Scene they change with the frames.

**Why this priority**: it is the request itself.

**Independent Test**: show a still picture with a red left half and a blue right half: the LEDs on the left
are red and the ones on the right are blue. Show a GIF or a 64x64 Scene from `../PRESTO/scenes480/out/`:
the LEDs change as the frames change.

**Acceptance Scenarios**:

1. **Given** the LEDs are on, **When** a still picture is shown, **Then** each LED has the colour of the screen
   edge near it, and keeps it while the picture stays.
2. **Given** the LEDs are on, **When** a GIF plays, **Then** the LEDs change with every shown frame.
3. **Given** the LEDs are on, **When** a Scene runs (32x32 or 64x64), **Then** the LEDs change with every
   frame it draws, and the Scene keeps its frame time (no visible slowdown, see SC-002).
4. **Given** playback is paused (tap), **Then** the LEDs keep the colours of the paused frame.
5. **Given** the menu is open, **Then** the LEDs follow the menu screen too; it is dark, so they are almost off.
   They return to the picture when the menu closes.
6. **Given** "nothing to show" is on the screen, **Then** the LEDs follow it as well (dark).

---

### User Story 2 - Turn the LEDs off and on (Priority: P1)

The LEDs disturb at night, so the user turns them off on the device or in the browser. They stay off after a
restart until turned on again.

**Why this priority**: the user asked for it explicitly: one general setting that can be switched off.

**Independent Test**: menu → "Ещё" → "Настройки" → "Подсветка: вкл" → tap: the LEDs go dark at once and the
row says "выкл"; restart the Presto: they stay dark; the browser shows the checkbox unchecked.

**Acceptance Scenarios**:

1. **Given** the device "Настройки" screen, **Then** it has the row "Подсветка: вкл / выкл"; a tap switches it
   and saves at once, as "Перемешать" does.
2. **Given** the browser "Что показывать" settings form, **Then** it has the checkbox "Подсветка сзади",
   saved with the other settings by "Сохранить".
3. **Given** the LEDs are turned off, **Then** all 7 LEDs are dark at once (not frozen in their last colour).
4. **Given** the LEDs are turned on, **Then** they take the screen's colours from the next shown frame on;
   a still picture on the screen is lit within about 1 s.
5. **Given** the setting changes, **Then** the item on the screen keeps playing; it does not restart.
6. **Given** the device restarts, **Then** the setting is as it was left.
7. **Given** a `settings.json` from before this feature, **Then** it loads and the LEDs are on.

### Edge Cases

- A request from an older WebUi that does not send the LED value does not change it (as for Brightness).
- A broken stored value (not true/false) → the settings are refused as for any other broken value today
  (the device falls back to default settings), so the LEDs are on.
- Screen Brightness (the backlight) does not change how bright the LEDs are; it is a separate thing.
- The simulator has no LEDs; it accepts the calls and ignores them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The device MUST light the 7 back LEDs with the colours of the nearby screen edges for whatever
  is on the screen, updated with each `presto.update()`, while the setting is on.
- **FR-002**: The colours MUST come from the frame on the screen; Python code MUST NOT add per-frame work for it.
- **FR-003**: DeviceSettings MUST get the boolean `ambientLeds` (default `true`), saved in `settings.json`
  and returned by `GET /api/settings`.
- **FR-004**: When `ambientLeds` is false, all LEDs MUST be dark.
- **FR-005**: `ambientLeds` MUST be one general setting; Collections do not override it.
- **FR-006**: The device "Настройки" screen MUST have a "Подсветка" toggle row; the browser settings form a
  checkbox; both change the same value.
- **FR-007**: `PUT /api/settings` without `ambientLeds` MUST keep the stored value.
- **FR-008**: A change of `ambientLeds` MUST NOT restart the item on the screen (like Brightness).

### Key Entities

- **AmbientLeds** (new in the dictionary): the 7 RGB LEDs on the back of the Presto and the rule "they show
  the edge colours of the screen while DeviceSettings.ambientLeds is on".
- **DeviceSettings**: + `ambientLeds`.

## Success Criteria *(mandatory)*

- **SC-001**: With a two-colour test picture (red left / blue right, or red top / blue bottom), the LEDs on
  each side show that side's colour, checked by eye on the Presto.
- **SC-002**: A 64x64 Scene's frame takes no more than 5 ms longer with the LEDs on than with them off
  (measured on the board: about 120 ms now).
- **SC-003**: After "Подсветка: выкл" all LEDs are dark within 0.5 s and stay dark after a restart.
- **SC-004**: All pytest device tests and `node --test web/test` pass.

## Assumptions

- **Colours by the firmware.** `auto_ambient_leds` samples the screen edge next to each LED. The plan
  checks first on the board that it works with `full_res=True` and with the gallery's own drawing (the
  blitter writes into the framebuffer, then `presto.update()`). If it does not, the plan's fallback does the
  same in Python: the average of a few edge pixels per LED, at most 5 times per second.
- **No LED brightness setting.** The firmware's automatic mode does not have one. It can be added later
  with the Python fallback; not part of this feature.
- **No per-Collection setting**: the user asked for one general switch.
- **The menu is not special**: the LEDs follow it like any other screen. It is dark, so they are almost off.
