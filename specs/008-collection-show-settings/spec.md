# Feature Specification: Show settings per Collection

**Feature Branch**: `008-collection-show-settings` (not created yet: 005, 006 and 007 are uncommitted on `006-scene-speed`)

**Created**: 2026-11-12

**Status**: Draft, waiting for approval

**Input**: "у разных коллекций должны быть свои настройки показа, и их можно менять прямо на устройстве (в
меню на экране Presto), а не только в браузере. Например, порядок (по кругу или вперемешку), время показа
одной картинки, скорость сцен по умолчанию, рамка и подгонка картинки. Хорошо бы, чтобы новые настройки
были видны и в браузере."

## Context: what can be set today

| Setting | Where it lives now | Per Collection in this feature |
|---|---|---|
| Slide time (`slideSeconds`, 3–600 s) | DeviceSettings, one value for everything | **yes**, optional own value |
| Order (`shuffle`: по кругу / вперемешку) | DeviceSettings, one value for everything | **yes**, optional own value |
| Scene speed | stored per Scene (006); a Collection can set all its Scenes at once | **kept as is**, moved into the new "Показ" screen |
| Brightness | DeviceSettings, swipe up/down | no, see Assumptions |
| Fit / frame (FitMode, CropView) | chosen in the browser at upload, baked into the `.bin` | no, see Assumptions |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A Collection plays with its own slide time and order (Priority: P1)

The user has a Collection "Фото" that should change every 60 s in a fixed order, and a Collection "Гифки"
that should change every 10 s in random order. When either Collection is shown, it plays its own way;
everything else keeps the general settings.

**Why this priority**: it is the request itself; without it the other stories have nothing to edit.

**Independent Test**: give a Collection 60 s and "вперемешку", show it: slides change every 60 s in a
shuffled order. Switch to "Всё": slides change at the general time in the general order.

**Acceptance Scenarios**:

1. **Given** a Collection with its own slide time, **When** it is shown, **Then** each item stays on screen
   for that time instead of the general one.
2. **Given** a Collection with its own order, **When** it is shown, **Then** the Playlist is in that order.
3. **Given** a Collection without own values ("как везде"), **When** it is shown, **Then** it plays with the
   general settings, as today.
4. **Given** any other ShowMode (Всё, Картинки, Гифки, Сцены, По тегам), **Then** only the general settings
   apply, even for items that are in a Collection with own values.
5. **Given** own values were set, **When** the device restarts, **Then** they are still there.

---

### User Story 2 - Change a Collection's settings on the device (Priority: P1)

With no phone at hand, the user opens the menu, finds the Collection and changes its slide time and order.

**Why this priority**: explicitly asked for, the device must not need the browser for this.

**Independent Test**: long press, "Ещё" → "Изменить коллекции" → the Collection → "Показ"; turn on own slide
time, press "+" twice, switch order to "вперемешку"; close the menu. If the Collection is the one on screen,
it now plays that way; the browser shows the same values.

**Acceptance Scenarios**:

1. **Given** the Collection card, **Then** it has a "Показ" row that opens the Collection's show screen.
2. **Given** the show screen, **Then** it shows: "Своё время: вкл/выкл"; "−  Слайд N с  +" (active only when
   own time is on, otherwise it shows the general time and is not pressable); "Порядок: как везде / по кругу
   / вперемешку" (a tap moves to the next of the three); and, only when the Collection has Scenes, "Скорость
   сцен: 2x / разная", which opens the existing five-speed screen.
3. **Given** a tap on any of these rows, **Then** the change is saved at once, without a separate save step,
   as the other menu settings are.
4. **Given** "Своё время" is turned on, **Then** the own time starts at the current general time.
5. **Given** "Своё время" is turned off, **Then** the Collection goes back to the general time.
6. **Given** the general "Настройки" screen while a Collection with own values is shown, **Then** it says so
   ("У коллекции свои"), so changing the general time there is not a surprise.

---

### User Story 3 - See and change a Collection's settings in the browser (Priority: P2)

The user sees in the Collections list which ones have own settings, and edits them there.

**Why this priority**: asked for as "хорошо бы"; it reuses the same stored values.

**Independent Test**: change a Collection's order on the device, reload the browser: its row says
"вперемешку". Change its slide time in the browser: the device menu shows the new time.

**Acceptance Scenarios**:

1. **Given** the Collections list, **Then** each row shows a short summary of own values, e.g. "60 с ·
   вперемешку", or nothing extra when it has none.
2. **Given** a row, **When** the user presses "Показ", **Then** a dialog offers: own slide time (off, or a number
   of seconds 3–600), order (как в настройках / по кругу / вперемешку) and, when there are Scenes, the scene
   speed (moved here from the row, with the same "разная" handling and question as in 006).
3. **Given** the general settings form with ShowMode "Коллекция" and a Collection with own values, **Then**
   the form notes what the Collection overrides.
4. **Given** a value outside 3–600 s, **Then** the device keeps it within 3–600, as for the general time.

---

### Edge Cases

- An old `catalog.json` whose Collections have no own values: everything plays as before, no migration.
- The Collection on screen changes its order: the Playlist is rebuilt and the item on screen stays on screen,
  as when the general order changes today.
- The Collection on screen changes its slide time: the current item restarts with the new time, as when the
  general time changes today.
- A Collection with own values is deleted while shown: the device falls back to "Всё" with the general
  settings, as today.
- A Collection is renamed: its own values stay.
- An item in two Collections plays with the settings of the Collection being shown.
- A Collection with a single item: a Scene keeps running without restarting, as today, whatever the own time.
- Swipes, pause and brightness work as before inside a Collection with own values.
- A stored own value that is broken (not a number, not true/false) is treated as "как везде", so the Collection
  still plays.
- Pressing "−"/"+" uses the same steps as the general slide time (3, 5, 10, 15, 30, 60, 120, 300, 600 s); an own
  time set in the browser between steps moves to the next step on "+" or "−".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A Collection MUST be able to store its own slide time and its own order; each one is optional,
  and a missing value means "как в общих настройках".
- **FR-002**: When ShowMode is "Коллекция", the slide time and order MUST be the Collection's own values where
  set and the general values otherwise. In every other ShowMode only the general values apply.
- **FR-003**: Own values MUST persist across restarts and be the same in the browser and on the device.
- **FR-004**: The device menu MUST let the user set and clear both own values of any Collection, and open the
  existing scene speed of its Scenes, from one "Показ" screen of the Collection card.
- **FR-005**: Each menu change MUST be applied and saved on the tap that makes it.
- **FR-006**: The browser MUST show a summary of own values per Collection and let the user set and clear them.
- **FR-007**: The device MUST refuse a slide time that is not an integer, or an order that is not true, false
  or "как везде", and change nothing; a time outside 3–600 s is clamped.
- **FR-008**: Changing own values MUST NOT change the general settings, and changing the general settings MUST
  NOT change own values.
- **FR-009**: Existing library files MUST keep working without any migration step.
- **FR-010**: The scene speed MUST keep working exactly as in 006 (stored per Scene; the Collection sets all its
  Scenes at once).

### Key Entities

- **CollectionShowSettings** (new): the optional own slide time and order of one Collection. Stored inside the
  Collection, applies only while that Collection is the ShowMode.
- **Collection**: gains optional `slideSeconds` and `shuffle`.
- **DeviceSettings**: unchanged; its slide time and order are now the general values that a Collection may override.
- **SceneSpeed**: unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a Collection at 60 s and the general time at 10 s, the time between slides of the Collection
  is 60 s within 1 s, and 10 s within 1 s after switching to "Всё".
- **SC-002**: The user sets a Collection's own time and order on the device within 7 taps after the long press.
- **SC-003**: The user sets them in the browser in at most 4 actions.
- **SC-004**: A library made before this feature plays and edits with no visible change.
- **SC-005**: A menu tap on the show screen responds as other menu rows do (about 0.4 s with 200 items).

## Assumptions

- Only slide time and order are per Collection. Brightness stays general: it follows the room, not the
  content, and is changed with a swipe.
- Fit and frame (FitMode, CropView) are chosen at upload and baked into the picture file; changing them on the
  device would mean re-encoding, so they are out of scope. A different look means uploading again.
- "Скорость сцен по умолчанию" is served by the existing Collection scene speed from 006, which writes the speed
  of each Scene. A speed that applies only while playing inside one Collection stays out of scope, as decided in 006.
- Own values live in the Collection itself, so one Collection has one set of values whoever edits it.
- There is no per-Tag equivalent; Tags keep the general settings.
