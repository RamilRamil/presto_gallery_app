# Feature Specification: Device gestures and library management on the Presto

**Feature Branch**: `005-device-gestures-library`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Жесты на сенсорном экране Presto, фиксированная раскладка. Свайп влево - следующая картинка, свайп вправо - предыдущая, тап - пауза/продолжить слайд-шоу, удержание 1 секунду - меню, свайп вверх/вниз - ярче/темнее. Плюс управление коллекциями и тегами непосредственно с устройства."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Different gestures for different actions (Priority: P1)

The user controls the Presto with one fixed set of gestures. A swipe changes the picture, a tap pauses,
and a long press opens the menu. A slow swipe no longer opens the menu by accident.

**Why this priority**: it is the first thing asked for and it fixes today's accidental menu opening.

**Independent Test**: on the slideshow, swipe left and right, tap twice, hold for a second. Each
gesture does only its own action.

**Acceptance Scenarios**:

1. **Given** the slideshow, **When** the user swipes left, **Then** the next item is shown.
2. **Given** the slideshow, **When** the user swipes right, **Then** the previous item is shown.
3. **Given** the slideshow is running, **When** the user taps anywhere, **Then** the slideshow stops
   changing items and a pause mark appears on the screen.
4. **Given** the slideshow is paused, **When** the user taps, **Then** the mark disappears and the
   next item comes after no more than one full slide time.
5. **Given** the slideshow is paused, **When** the user swipes left or right, **Then** the item changes
   and the slideshow stays paused.
6. **Given** a finger stays still for 1 second, **Then** the menu opens, and lifting the finger does
   not press anything in the menu.
7. **Given** a finger moves slowly across the screen for longer than 1 second, **Then** the menu does
   not open and the movement counts as a swipe.

---

### User Story 2 - Brightness by swiping (Priority: P2)

Swiping up makes the screen brighter and swiping down makes it darker, without interrupting what is shown.

**Why this priority**: useful daily, and independent of the library work.

**Independent Test**: swipe down several times, restart the Presto; the brightness is kept.

**Acceptance Scenarios**:

1. **Given** the slideshow, **When** the user swipes up or down, **Then** brightness moves one level
   among 10, 25, 50, 75 and 100 percent.
2. **Given** the lowest or highest level, **When** the user swipes further, **Then** nothing changes;
   the screen never goes fully dark.
3. **Given** a running animation or Scene and shuffle on, **When** brightness changes, **Then** the
   animation continues without restarting and the slide order does not change.
4. **Given** a brightness level, **When** the Presto restarts or settings are saved from the browser,
   **Then** the level is kept.

---

### User Story 3 - Sort the current picture on the device (Priority: P2)

Without a phone, the user marks the picture on the screen with Tags and adds it to Collections.

**Why this priority**: the most frequent library task while looking at the screen.

**Independent Test**: with no phone, open the menu on a picture, add a Tag and a Collection; both are
visible in the browser library afterwards.

**Acceptance Scenarios**:

1. **Given** the menu was opened on a picture, **When** the user opens "Ещё" and "Эта картинка", **Then**
   its name is shown with entries for its Tags and Collections.
2. **Given** the list of Tags or Collections, **When** the user taps a row, **Then** the picture gains
   or loses it, the row mark changes at once, and the change is saved without a separate save step.
3. **Given** the list of Tags, **When** the user taps "Новый тег" and types a name, **Then** the Tag is
   created and given to this picture. "Новая коллекция" works the same way.
4. **Given** the current show mode is a Collection or Tags, **When** the picture leaves that selection,
   **Then** the menu stays on this picture, and after closing the slideshow continues without it.

---

### User Story 4 - Manage Collections and Tags on the device (Priority: P3)

The user creates, renames and deletes Collections and renames and deletes Tags from the device, and
removes pictures from a Collection.

**Why this priority**: used less often than sorting, and it depends on the same screens.

**Independent Test**: with no phone, create a Collection, rename it, delete it; rename a Tag and check
that every picture has the new name.

**Acceptance Scenarios**:

1. **Given** "Ещё" and "Изменить коллекции", **Then** every Collection is listed with its item count,
   and "Новая коллекция" asks for a name.
2. **Given** a Collection, **Then** the user can rename it, delete it after confirming, and open its
   pictures to remove any of them from it.
3. **Given** a deleted Collection, **Then** its pictures stay in the library. If it was being shown, the
   slideshow switches to showing everything.
4. **Given** "Изменить теги", **When** a Tag is renamed, **Then** every picture with it gets the new
   name. If that name already exists the two Tags merge.
5. **Given** a Tag is deleted after confirming, **Then** it is removed from every picture and the
   pictures stay.
6. **Given** a Collection name that already exists or an empty name, **When** the user confirms it,
   **Then** the keyboard stays open with a short message and nothing changes.

---

### Edge Cases

- A movement too long for a tap but too short for a swipe does nothing.
- A diagonal swipe counts along its longer direction.
- A tap during a Scene takes effect at the Scene's next `stop` call; a fast swipe during a Scene may be
  missed, and the long press stays the reliable way to the menu.
- The picture being edited is deleted from the browser while its screen is open: the menu returns to
  "Ещё" and shows nothing about the missing picture.
- A Tag that was being shown is renamed or deleted: the selection follows it; if no selected Tag is left, the slideshow shows everything.
- A Tag or Collection list longer than a screen is split into pages.
- The menu was opened when nothing is shown: "Эта картинка" cannot be pressed.
- Typing is slow: management and keyboard screens wait 60 seconds without a touch, and closing by
  timeout drops only the unconfirmed text.
- The browser and the device change the same Collection: each change is applied in turn and the last wins.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The device MUST treat a swipe left as next and a swipe right as previous.
- **FR-002**: A tap anywhere MUST toggle pause. Tapping left or right MUST no longer change the item.
- **FR-003**: A finger held still for 1 second MUST open the DeviceMenu. Movement MUST cancel the long press.
- **FR-004**: Swipes up and down MUST step brightness through 10, 25, 50, 75, 100 percent.
- **FR-005**: Brightness MUST persist across restarts and MUST survive saving settings from the browser.
- **FR-006**: Changing brightness MUST NOT restart the current item or change the slide order.
- **FR-007**: While paused, the slideshow MUST NOT advance by itself; animations and Scenes keep playing.
- **FR-008**: Pause MUST show a mark on pictures and animations and MUST NOT persist across restarts.
  Choosing what to show in the menu MUST end the pause.
- **FR-009**: The menu MUST reach all current destinations; the main screen replaces "Настройки" with
  "Ещё", which leads to "Эта картинка", "Изменить коллекции", "Изменить теги" and "Настройки".
- **FR-010**: Choosing a Collection to show MUST still take at most 3 taps after the long press.
- **FR-011**: For the item on screen when the menu opened, the user MUST be able to toggle each Tag and
  each Collection, each change being saved at once.
- **FR-012**: The user MUST be able to create, rename and delete Collections and remove items from them.
- **FR-013**: The user MUST be able to create Tags on an item, rename Tags everywhere and delete Tags everywhere.
- **FR-014**: Deleting a Collection or a Tag MUST ask for confirmation and MUST NOT delete any picture.
- **FR-015**: The device MUST provide an on-screen keyboard with Russian letters, Latin letters and
  digits, with keys of at least 40 by 40 px, and the same name rules as the browser.
- **FR-016**: Changes made on the device MUST appear in the browser library, and the other way round.
- **FR-017**: Existing library data and settings files MUST keep working without any migration step.

### Key Entities

- **Gesture**: one finger movement classified as tap, long press or swipe in one of four directions.
- **Brightness**: a level of the screen, one of five, part of DeviceSettings.
- **Pause**: a temporary state of the slideshow, not stored.
- **OnScreenKeyboard**: pages of keys for entering a name on the device.
- **DeviceMenu**: gains the "Ещё" screens for managing the current item, Collections and Tags.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On pictures and animations, at least 19 of 20 attempts of each gesture do the intended action.
- **SC-002**: A slow swipe never opens the menu in 20 attempts.
- **SC-003**: The screen responds to a swipe or tap within 300 ms on pictures.
- **SC-004**: The user adds the current picture to an existing Collection within 5 taps after the long press.
- **SC-005**: The user types a 10-letter Russian name with no more than 15 key presses on average.
- **SC-006**: A menu row or key responds within 500 ms with a 200-item library.

## Assumptions

- The layout is fixed; choosing gestures in settings is out of scope.
- Pause holds the slideshow on the current item while animation continues. Freezing a GIF frame is out of scope.
- The on-screen keyboard is included, because creating and renaming from the device needs it.
- Letters are typed in lower case on the device; capitals can be set in the browser. Tags are lower case anyway.
- Deleting pictures, renaming pictures and reordering Collections stay in the browser.
- The browser does not get a brightness or pause control in this feature.
