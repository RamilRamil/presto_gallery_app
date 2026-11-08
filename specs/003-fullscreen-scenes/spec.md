# Feature Specification: Full-Screen Pictures and Scenes

**Feature Branch**: `003-fullscreen-scenes`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Хочу использовать весь экран, без чёрной рамки. И хочу, чтобы скрипты-сцены (анимация кодом, `run(stop)` через `pixel`) тоже можно было закинуть через веб-интерфейс. Личные фото не должны быть доступны посторонним."

> Terms follow `knowledge/domain.okf.json`. New terms: Scene, AccessPassword.
> Existing: MediaItem, Tag, Catalog, ShowMode, Playlist, DeviceSettings, Grid, WebUi, DeviceApp,
> HttpApi, MediaStorage, PixelizeSettings, PrestoBinFormat.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pictures fill the whole screen (Priority: P1)

The user picks a Grid that divides the screen evenly (40, 60, 80, 120 or 240) and the picture
covers all 240×240 pixels, with no black frame. The finest Grid looks like an ordinary photo; the
coarser ones keep the pixel-art look.

**Why this priority**: the black frame was the first thing the user noticed on the real device.

**Independent Test**: upload one photo at Grid 60; the outermost row and column of screen pixels
on all four sides show the picture.

**Acceptance Scenarios**:

1. **Given** Grid 40, 60, 80, 120 or 240 and crop mode, **When** the picture is shown, **Then** it
   covers the whole screen with square cells of 6, 4, 3, 2 or 1 px.
2. **Given** a MediaItem uploaded earlier with Grid 16, 32 or 64, **When** it is shown, **Then** it
   looks as before, with no re-upload.
3. **Given** an animated GIF at Grid 240, **When** it plays, **Then** frame timing stays within
   ±20 ms of the original for frame durations of 100 ms or more.
4. **Given** the user selects Grid 120 or 240, **Then** the WebUi warns that the device will keep a
   clearly recognizable picture, and shows the resulting size and frame limit.

---

### User Story 2 - Protect the gallery with a password (Priority: P1)

The owner sets an AccessPassword once in the device's secrets file. Without it nobody on the
network can list, download, change or delete anything.

**Why this priority**: the library holds personal photos, and Scene upload (Story 3) would
otherwise let any device on the network run code on the Presto.

**Independent Test**: with an AccessPassword set, request every HttpApi endpoint without the
password: each is refused and reveals no name, tag or picture. Repeat with the password: all work.

**Acceptance Scenarios**:

1. **Given** an AccessPassword is set, **When** the WebUi is opened, **Then** it asks for the
   password before showing the library, status or settings.
2. **Given** a wrong password, **Then** the request is refused, and repeated guesses are slowed to
   at most one attempt per second.
3. **Given** the correct password, **Then** the WebUi remembers it until the browser tab is closed
   or the user presses "Log out".
4. **Given** no AccessPassword is set, **Then** the gallery works as before and the WebUi shows a
   visible warning, and Scene upload is refused with an explanation.

---

### User Story 3 - Upload a Scene and see it in the slideshow (Priority: P2)

The user picks a Scene file (a script that draws an animation in code, in the same form as the
existing `scene_*.py` files), gives it a name and Tags, and uploads it. The Scene runs on the
Presto as one more slide, filling the whole screen.

**Why this priority**: explicitly requested; it brings the user's existing scenes into one gallery.

**Independent Test**: upload an existing `scene_storm.py` unchanged through the WebUi; it plays
full-screen on the Presto, then the slideshow moves to the next item.

**Acceptance Scenarios**:

1. **Given** a Scene written for the 32-cell `pixel` drawing helpers, **When** it runs, **Then** it
   covers the whole screen, with no change to its source, and neighbouring cells differ in width
   by at most 1 px.
2. **Given** a Playlist with pictures and Scenes, **When** the slide time passes, **Then** the
   Scene stops and the next item is shown.
3. **Given** a Scene is the only item in the Playlist, **Then** it keeps running without restarting.
4. **Given** ShowMode **scenes**, **Then** only Scenes play; **all** includes Scenes; **images** and
   **animations** exclude them; **tags** includes Scenes having a selected Tag.
5. **Given** a Scene is running, **When** the WebUi is used, **Then** it stays responsive, and
   tap, long press and "show now" behave as for any other item.
6. **Given** a Scene file with a syntax error, or without a `run(stop)` function, or over 64 KB,
   **Then** the upload is refused with a clear message and nothing is stored.

---

### User Story 4 - A bad Scene cannot break the device (Priority: P2)

A Scene that crashes, runs out of memory or hangs must not make the Presto unusable.

**Independent Test**: upload a Scene that raises an error and one that loops forever without
calling `stop`. The first is flagged and skipped. After a power cycle the second is flagged and
skipped, and the WebUi can delete it.

**Acceptance Scenarios**:

1. **Given** a Scene raises an error, **Then** the slideshow continues with the next item and the
   WebUi flags the Scene with the error text.
2. **Given** a Scene never calls `stop` and the user power-cycles the device, **Then** at the next
   start the Scene is flagged as not responding and is skipped until the user re-enables or
   re-uploads it.
3. **Given** a flagged Scene, **Then** it can be deleted from the WebUi.

---

### User Story 5 - Choose the part of the picture (Priority: P2)

In crop mode the user chooses which square part of the picture is used: moves it and zooms in or
out, directly on the preview, on a phone or a computer.

**Why this priority**: a center crop often cuts off the subject of the photo.

**Independent Test**: take a wide photo with the subject at the left edge, drag and zoom until only
the subject is visible, upload; the Presto shows exactly that part.

**Acceptance Scenarios**:

1. **Given** a picture in crop mode, **When** it is opened, **Then** the view starts as the largest
   centered square, the same result as before this feature.
2. **Given** the preview, **When** the user drags it with a mouse or a finger, **Then** the chosen
   part moves, and it can never go beyond the edges of the picture.
3. **Given** the preview, **When** the user moves the zoom slider, turns the mouse wheel or pinches
   with two fingers, **Then** the chosen part gets smaller or larger, from the whole short side up
   to 8× zoom.
4. **Given** the user finishes moving, **Then** the preview shows the exact pixel result that will
   be uploaded.
5. **Given** an animated GIF, **Then** the same chosen part applies to all its frames.
6. **Given** "Сбросить", **Then** the view returns to the centered square. Choosing another file also
   resets it. Changing grid, colors or dithering keeps it.
7. **Given** fit mode, **Then** the same controls work: at 1× the whole picture is visible with
   margins in the background color and can be moved within them; zooming in enlarges it inside the
   square, up to 8×, and it can be moved. Switching between crop and fit resets the view.

### Edge Cases

- Uploading a Scene while another Scene runs: the upload may take longer, must complete.
- Scene that draws directly to the display instead of through the `pixel` helpers: it runs, but its
  drawing is not stretched by the helpers.
- Scene that sleeps a long time between `stop` calls: the WebUi and slide change wait until the
  next call. This is documented for Scene authors.
- Scene that hangs after it has already called `stop`: it is not flagged automatically. The WebUi
  works until the hang is reached, so it can be deleted after a power cycle.
- Deleting or changing settings while a Scene runs: the Scene stops at its next `stop` call.
- AccessPassword changed in the secrets file: takes effect after restart; the WebUi asks again.
- Requests with encoded path traversal (`%2e%2e`) get "not found", never a server error.
- Grid 240 GIF over the frame limit: refused before upload, as for any over-limit GIF.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Allowed Grid sizes MUST be 16, 32, 40, 60, 64, 80, 120, 240 in the WebUi and the
  desktop tool; both MUST keep passing the shared golden vectors, extended to the new sizes.
- **FR-002**: The DeviceApp MUST accept and play any MediaItem of an allowed Grid; items of Grid 16,
  32 and 64 already stored MUST keep working without conversion.
- **FR-003**: The WebUi default Grid MUST be 60. The desktop default stays 32.
- **FR-004**: The WebUi MUST warn at Grid 120 and 240 that a recognizable picture is stored on the
  device, and MUST show the estimated size and maximum GIF frames for the chosen Grid.
- **FR-005**: If an AccessPassword is configured, every HttpApi request MUST present it, otherwise
  the request is refused without revealing data. The WebUi page and its scripts contain no user
  data and MAY load without it.
- **FR-006**: Failed password attempts MUST be limited to one per second.
- **FR-007**: The WebUi MUST keep the password only for the lifetime of the browser tab and offer
  "Log out".
- **FR-008**: The AccessPassword MUST be set in the device's secrets file, never through the WebUi.
- **FR-009**: Without an AccessPassword the WebUi MUST warn, and Scene upload MUST be refused.
- **FR-010**: A Scene is a MediaItem kind with a name and 0..n Tags; existing catalog entries are
  treated as pictures with no migration step.
- **FR-011**: Scene upload MUST check before storing: size at most 64 KB, valid syntax on the
  device, a top-level `run` function. A partial or rejected upload leaves nothing behind.
- **FR-012**: The DeviceApp MUST run unmodified Scenes that use the `pixel` helpers `presto`,
  `display`, `GRID`, `make_pen`, `block`, `pix`, and MUST stretch their 32-cell output over the
  whole screen with cell widths differing by at most 1 px.
- **FR-013**: A Scene runs for the slide duration (no limit if it is the only Playlist item) and
  MUST be stopped through its `stop` callback by the end of slide time, a tap, or a change from
  the WebUi.
- **FR-014**: While a Scene runs and calls `stop`, the HttpApi, touch handling and Wi-Fi retry MUST
  keep working.
- **FR-015**: ShowModes MUST be extended with **scenes**; other modes behave as in the User Story 3
  scenarios.
- **FR-016**: Errors raised by a Scene, including out-of-memory, MUST be caught; the Scene is flagged
  with the error text and the slideshow continues.
- **FR-017**: If the device restarts before a running Scene has made its first `stop` call, that
  Scene MUST be flagged as not responding and skipped until re-enabled or re-uploaded. Switching
  the device off during a Scene that already called `stop` MUST NOT flag it.
- **FR-018**: The WebUi MUST let the user upload a Scene, see its flagged state and error, re-enable,
  retag, rename, delete and "show now". Scenes have no thumbnail; a placeholder is shown.
- **FR-019**: Requests with a path that decodes to a parent-directory reference MUST be answered
  "not found".
- **FR-020**: The existing Features 001 and 002 MUST keep working unless changed above.
- **FR-021**: In crop and fit modes the WebUi MUST let the user choose a view by moving it (mouse,
  one finger) and zooming it (slider, mouse wheel, two-finger pinch), from 1× to 8×.
- **FR-022**: In crop mode the chosen square MUST stay inside the picture. In fit mode the picture
  MUST stay inside the square along any side where it is smaller than the square, and MUST cover the
  square along any side where it is larger.
- **FR-023**: The default view MUST give the same result as the existing center crop or fit, so the
  shared golden vectors and the desktop tool are not affected.
- **FR-024**: While the user is moving the view the preview MUST follow without visible delay; when
  the movement ends, it MUST show the exact result that will be uploaded.
- **FR-025**: Pictures MUST keep enough resolution for zooming: up to 2048 px on the long side.

### Key Entities

- **Scene** — a stored script drawing an animation in code; a MediaItem kind; has a name, Tags, a
  flagged state and optional error text.
- **AccessPassword** — the single secret that grants access to the HttpApi; set on the device.
- **MediaItem** — gains a kind: picture (a stored .bin) or Scene.
- **ShowMode** — gains **scenes**.
- **Grid** — gains 40, 60, 80, 120, 240.
- **CropView** — the chosen square part of a picture: its center and zoom. Exists only in the WebUi
  while a picture is being prepared; it is not stored on the device.

## Success Criteria *(mandatory)*

- **SC-001**: At Grid 40, 60, 80, 120 and 240, 100% of the screen's edge pixels show the picture.
- **SC-002**: A 240×240 animation with 100 ms frames plays within ±20 ms per frame.
- **SC-003**: With an AccessPassword set, 100% of HttpApi endpoints refuse requests without it and
  reveal no names, tags or media.
- **SC-004**: All four existing scenes from the old project run unmodified and fill the screen.
- **SC-005**: While a Scene runs, the WebUi status answers within 3 seconds.
- **SC-006**: After a hung Scene, the device is usable again after one power cycle, with no USB
  access or reflashing.
- **SC-007**: 24 hours of a mixed slideshow with Scenes causes no crash or reboot.
- **SC-008**: On a phone, choosing a part of a photo takes one drag and one pinch, and the final
  preview appears within 1 second after the finger is lifted at Grid 60.

## Assumptions

- A Scene is trusted code. It can read everything on the device, including the Wi-Fi password and
  all media, and can use the network; there is no sandbox. The AccessPassword decides who may
  upload one, and the owner must upload only Scenes they trust.
- The password travels over plain HTTP inside the local network and can be read by someone able to
  intercept that traffic; encryption is out of scope. The home network and the router's access rule
  remain part of the protection.
- Anyone with physical USB access can read the device; storage is not encrypted.
- One shared password, no user accounts.
- In-browser Scene editing, Scene thumbnails and bulk import are out of scope.
- Choosing a part of the picture is a WebUi feature; the desktop tool keeps its center crop.
- Scenes authored for other Grids work through the same helpers; only 32-cell scenes exist today.
