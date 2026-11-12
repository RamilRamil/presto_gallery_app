# Feature Specification: Scenes mode advances only on a swipe

**Feature Branch**: `009-scenes-manual-advance`
**Created**: 2026-11-12
**Status**: Draft
**Input**: "Вот у меня есть режим сцены, давай сделаем на нем перелистывание только явное"

## User Scenarios & Testing

### User Story 1 - A Scene plays until I swipe (Priority: P1)

The owner picks **Сцены** in the device menu (ShowMode `scenes`). The Scene on the screen keeps
playing for as long as it likes: the Slide time no longer moves to the next one. A swipe to the left
or right moves to the next or previous Scene, as in every other ShowMode.

**Why this priority**: the living Scenes (castle, tower, watch) are meant to be watched, and they
start new random events every run; cutting them off after a Slide time breaks that.

**Independent Test**: choose ShowMode `scenes` with two or more Scenes, wait longer than the Slide
time: the same Scene is still playing. Swipe: the next Scene starts.

**Acceptance Scenarios**:

1. **Given** ShowMode `scenes` with 3 Scenes and Slide time 10 s, **When** 60 s pass, **Then** the first
   Scene is still on the screen and has not restarted.
2. **Given** the same, **When** the owner swipes left, **Then** the next Scene starts; a swipe right
   goes back.
3. **Given** ShowMode `all`, `collection` or `tags` holding Scenes, **When** the Slide time passes,
   **Then** the next item comes as before (this feature changes the `scenes` ShowMode only).
4. **Given** ShowMode `scenes`, **When** the owner changes the ShowMode, a Collection or the catalog
   from the menu or the browser, **Then** the Scene stops and the new Playlist starts, as before.

### Edge Cases

- A Scene that returns by itself (it ends, or fails and is flagged) moves to the next Scene, as now.
- Pause (a tap) keeps working as now; a paused Scene stays paused.
- The Slide time setting stays in the menu and the browser; it still applies to the other ShowModes.
  In ShowMode `scenes` the menu's Slide time row carries the note "сцены: по свайпу".
- A Collection's own Slide time (feature 008) does not apply in ShowMode `scenes`, since that
  ShowMode is not a Collection.

## Requirements

### Functional Requirements

- **FR-001**: In ShowMode `scenes` a Scene MUST NOT be stopped by the Slide time.
- **FR-002**: In ShowMode `scenes` a swipe MUST move to the next or previous Scene, and any change of
  the state (ShowMode, Collection, catalog, settings) MUST stop the Scene, as in the other ShowModes.
- **FR-003**: In every other ShowMode the Slide time MUST work as before.
- **FR-004**: The device menu's settings screen MUST show, while ShowMode is `scenes`, that Scenes
  advance only on a swipe.

### Key Entities

- **ShowMode** `scenes` (existing, knowledge/domain.okf.json): gains the rule "advances only on a swipe".

## Success Criteria

- **SC-001**: In ShowMode `scenes` a Scene runs at least 10 minutes without a restart (checked on the
  Presto with castle64).
- **SC-002**: A swipe moves to the next Scene within 0.3 s (one stop() poll of a 64x64 Scene).
- **SC-003**: Every existing device test still passes.

## Assumptions

- "Явное перелистывание" means a swipe on the screen; Scenes mode has no web "next" button today.
- Only the `scenes` ShowMode changes; making it a per-Collection option is out of scope.
