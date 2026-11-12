# Feature Specification: Scene speed

**Feature Branch**: `006-scene-speed`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Настройка скорости сцен. У каждой уже загруженной сцены своя скорость (0.25x, 0.5x, 1x, 2x, 4x), меняется в форме редактирования в браузере и в меню устройства на экране текущей картинки, без правки и перезаливки файла сцены. Сейчас темп задан внутри скрипта через time.sleep."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Change the speed of a Scene from the browser (Priority: P1)

The user opens an uploaded Scene in the library, picks a speed and saves. The Scene plays faster or
slower, and its file stays as it was uploaded.

**Why this priority**: it is the request itself, and the browser form already edits a Scene.

**Independent Test**: upload a Scene, set 2×, watch it play about twice as fast; set 1× and it plays as
before.

**Acceptance Scenarios**:

1. **Given** a Scene in the library, **When** the user opens its edit form, **Then** a speed choice of
   0.25×, 0.5×, 1×, 2× and 4× shows the current speed.
2. **Given** the form, **When** the user picks a speed and saves, **Then** the Scene restarts at the new
   speed, and the speed is kept across restarts of the device.
3. **Given** a picture or a GIF, **When** the user opens the edit form, **Then** no speed choice is shown.
4. **Given** a Scene with a speed other than 1×, **When** the user looks at the library, **Then** the
   card shows the speed.

---

### User Story 2 - Change the speed on the device (Priority: P2)

While a Scene is on the screen, the user changes its speed with no phone at hand.

**Why this priority**: useful when looking at the screen, and it depends on the same stored setting.

**Independent Test**: with no phone, open the menu on a running Scene, choose 0.5×, close the menu; the
Scene plays slower and the browser shows 0.5×.

**Acceptance Scenarios**:

1. **Given** the menu was opened on a Scene, **When** the user opens "Ещё" and "Эта картинка", **Then** a
   "Скорость" entry shows the current speed.
2. **Given** the "Скорость" screen, **When** the user taps a speed, **Then** its mark moves at once and
   the change is saved without a separate save step.
3. **Given** the menu was opened on a picture or a GIF, **Then** there is no "Скорость" entry.

---

### User Story 3 - Set the speed of a whole Collection (Priority: P2)

Added 2026-11-10: "добавь регулировку скорости к коллекции".

The user has a Collection with several Scenes and sets one speed for all of them in one action, in the
browser or on the device, instead of opening each Scene.

**Why this priority**: it saves repeating the same edit per Scene, and it builds on the speed each Scene
already stores.

**Independent Test**: make a Collection with two Scenes and a picture, set 2× for the Collection; both
Scenes show 2× in the library and play faster, and the picture has no speed.

**Acceptance Scenarios**:

1. **Given** a Collection with Scenes, **When** the user opens it in the browser or in the device menu,
   **Then** a speed choice shows the common speed of its Scenes, or "разная" when they differ.
2. **Given** that choice, **When** the user picks a speed, **Then** every Scene that is in the Collection
   at that moment gets this speed, and each Scene's own speed shows the new value.
3. **Given** a Collection without Scenes, **Then** no speed choice is shown.
4. **Given** Scenes with different speeds, **When** the user picks one speed in the browser, **Then** the
   browser asks first, because the separate speeds are replaced.
5. **Given** a Collection speed was set, **When** the user changes one of its Scenes, **Then** only that
   Scene changes and the Collection shows "разная".

---

### Edge Cases

- A Scene in two Collections has one speed: the Collection set last decides it.
- A Scene added to a Collection after its speed was set keeps its own speed.
- A flagged Scene in the Collection gets the speed too, as with a single Scene.
- A Scene whose pace does not come from pauses (it counts real time, or has no pauses at all): the
  setting has no effect, and the Scene runs normally. The browser says that the speed changes the pauses.
- A Scene that takes longer to draw a frame than its pause: speeding up stops helping once the pause is
  used up. The Scene does not fail.
- A slow speed makes pauses up to 4 times longer: touches, browser requests and slide changes MUST NOT
  wait for them.
- The slide time is not affected: a Scene at 4× is on screen for as long as a Scene at 1×.
- Library entries from before this feature, and a stored speed that is not one of the five, play at 1×.
- A Scene uploaded again is a new item and starts at 1×.
- Pause keeps working at any speed.
- The speed of a Scene that was flagged as broken can be changed, and it applies once the Scene is enabled.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each Scene MUST have its own speed, one of 0.25×, 0.5×, 1×, 2×, 4×, with 1× as the default.
- **FR-002**: Speed MUST change the length of the pauses a Scene makes: a pause is divided by the speed.
- **FR-003**: Changing the speed MUST NOT change or require uploading the Scene file.
- **FR-004**: At 1× a Scene MUST run exactly as it does today.
- **FR-005**: The browser edit form MUST offer the speed for Scenes only.
- **FR-006**: The library MUST show a speed other than 1× on the Scene's card.
- **FR-007**: The device menu MUST offer the speed for the current item when it is a Scene.
- **FR-008**: The speed MUST persist across restarts and appear in both the browser and the device.
- **FR-009**: The device MUST refuse a speed that is not one of the five, and a speed for an item that is
  not a Scene, and change nothing.
- **FR-010**: During a Scene at a speed other than 1×, touches and browser requests MUST be served at
  least every 100 ms of pause, whatever the speed.
- **FR-011**: Existing library files MUST keep working without any migration step.
- **FR-012**: The browser and the device menu MUST offer one speed for a Collection that has at least one
  Scene, and setting it MUST set the speed of every Scene in that Collection in one step.
- **FR-013**: Pictures and GIFs in the Collection MUST NOT change.
- **FR-014**: The device MUST refuse a Collection speed that is not one of the five, or a Collection
  without Scenes, and change nothing.
- **FR-015**: The Collection MUST show the common speed of its Scenes, or that they differ.

### Key Entities

- **SceneSpeed**: how fast a Scene plays, relative to its own pauses. One of five values, stored per Scene.
- **Scene**: gains an optional SceneSpeed; its file is unchanged.
- **Collection**: stores no speed of its own. Its speed is a way to set the SceneSpeed of its Scenes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a Scene whose frames are mostly pauses, the time between frames at 2× is half of that at
  1×, within 15%, and at 0.5× it is double, within 15%.
- **SC-002**: The user changes the speed of a Scene in the browser in at most 4 actions, without uploading anything.
- **SC-003**: The user changes the speed on the device within 4 taps after the long press.
- **SC-004**: At 0.25×, a touch on a Scene is noticed within 300 ms in 19 of 20 attempts.
- **SC-005**: A library made before this feature plays and edits with no visible change.
- **SC-006**: The user sets the speed of all Scenes of a Collection in at most 2 actions in the browser, and
  within 5 taps after the long press on the device.

## Assumptions

- The five values are fixed; a free value is out of scope.
- Speed applies to Scenes only. Changing the frame timing of GIFs is out of scope.
- Saving a new speed restarts the Scene, as any edit of the item does today.
- Only pauses made during `run` change. Pauses made while the file loads stay as written.
- Scene authors keep setting the pace with pauses, as all current Scenes do.
- A Collection speed is set once for the Scenes it has now. Playing a Scene at one speed inside a Collection
  and at another outside it is out of scope.
- On the device a tap applies the Collection speed at once, without asking, as the speed of one Scene does.
