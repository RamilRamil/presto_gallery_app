# Feature Specification: Presto Wi-Fi Gallery

**Feature Branch**: `002-presto-wifi-gallery`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "Presto подключается к Wi-Fi, через веб-интерфейс закидываю в него
картинки и гифки. Режимы: слайд-шоу картинок, слайд-шоу гифок, слайд-шоу выборки по тегам
(к каждому медиафайлу можно прикрепить один или несколько тегов). Без отдельного сервера:
веб-интерфейс и хранение на самом Presto."

> Terms follow `knowledge/domain.okf.json`. New terms: MediaItem, Tag, Catalog, ShowMode,
> Playlist, DeviceSettings, WebUi, DeviceApp, HttpApi, MediaStorage, GoldenVector.
> Existing: SourceImage, PixelizeSettings, PixelArt, Frame, Palette, PrestoBinFormat.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload a picture from the browser and see it on Presto (Priority: P1)

The Presto is on the home Wi-Fi and shows its address on screen. The user opens that address
on a phone or laptop, picks a PNG/JPEG/WebP, sees a live pixel preview while changing grid,
colors/palette, crop/fit and dithering, presses "Upload". The picture is stored on the Presto
and appears in the slideshow.

**Why this priority**: replaces the "write a scene in code and flash it over USB" workflow; it is
the core of the request.

**Independent Test**: with only this story built, upload one photo from a phone and see it
drawn on the Presto within a few seconds, and still there after a power cycle.

**Acceptance Scenarios**:

1. **Given** Presto is powered with Wi-Fi credentials configured, **When** it boots, **Then** it
   connects and shows its address (IP and `presto.local`) for a few seconds, then starts the slideshow.
2. **Given** the WebUi is open, **When** the user selects a picture and changes settings, **Then**
   the preview updates without contacting the device, using the same look as the desktop tool.
3. **Given** the user presses Upload, **Then** the MediaItem is saved on the device, listed in the
   WebUi with a thumbnail, and shown on the Presto right away ("show now").
4. **Given** the device restarts, **Then** all MediaItems, Tags and DeviceSettings are kept.
5. **Given** Wi-Fi is unavailable, **Then** the Presto still plays the stored slideshow and retries
   the connection in the background.

---

### User Story 2 - Upload animated GIFs (Priority: P1)

Same flow for an animated GIF: every frame is converted with one shared Palette and its own
frame duration, and the Presto plays the animation.

**Why this priority**: explicitly requested; the .bin format already supports frames.

**Independent Test**: upload a 20-frame GIF; the Presto plays it with the original timing
(±20 ms per frame) and the WebUi thumbnail animates.

**Acceptance Scenarios**:

1. **Given** an animated GIF, **When** converted, **Then** the MediaItem has frameCount = number of
   GIF frames, durations copied from the GIF (0/missing → 100 ms), one Palette for all frames.
2. **Given** a GIF over the limits (more than 256 frames or a .bin over 1 MB), **Then** the WebUi
   refuses it before upload and explains which limit was hit.

---

### User Story 3 - Tags and show modes (Priority: P2)

Each MediaItem has zero or more Tags (assigned at upload, editable later). The user selects the
ShowMode: **all**, **images** (frameCount = 1), **animations** (frameCount > 1) or **tags**
(items having at least one of the selected Tags), plus slide duration and shuffle on/off.

**Independent Test**: tag 3 of 6 items "cats", choose mode "tags: cats"; the Presto cycles only
those 3.

**Acceptance Scenarios**:

1. **Given** items with tags, **When** the user adds/removes a tag on an item, **Then** the change is
   saved and immediately affects the running Playlist.
2. **Given** mode "tags" with Tags {cats, winter}, **Then** the Playlist contains items tagged cats
   OR winter.
3. **Given** a ShowMode whose Playlist is empty, **Then** the Presto shows "nothing to show for
   <mode>" and the WebUi warns before saving.
4. **Given** slide duration 10 s, **Then** a still image stays 10 s; an animation plays whole loops
   until at least 10 s have passed (at least one full loop).
5. **Given** shuffle on, **Then** every item is shown once per round in random order.

---

### User Story 4 - Manage the library (Priority: P2)

The WebUi lists all MediaItems (thumbnail, name, tags, frames, size), filters by tag, and lets
the user rename, delete, "show now", and see free storage.

**Acceptance Scenarios**:

1. **Given** an item is deleted, **Then** its file is removed and it leaves the Playlist.
2. **Given** storage would be exceeded, **Then** upload is refused with a message; nothing partial
   is left on the device.

---

### User Story 5 - Touch on the device (Priority: P3)

Tap on the right half = next item, left half = previous item. Long press (≥1 s) shows the
address and current mode for 5 s.

### Edge Cases

- Upload interrupted mid-way: the partial file is discarded; Catalog unchanged.
- Two browsers edit at once: last write wins per item; WebUi reloads the list after each change.
- Tag text: trimmed, spaces collapsed, lowercased, 1–24 chars, any script (Cyrillic ok); commas,
  slashes, quotes and `<>` are not allowed. Lowercasing of non-Latin letters is done by the WebUi.
- Duplicate names allowed (items are identified by id, not by name).
- Corrupted .bin on storage: skipped in the Playlist, flagged in the WebUi list.
- No microSD card: flash storage is used with its smaller capacity; WebUi shows the capacity.
- Uploading while an animation plays: playback may stutter briefly, must not crash or reboot.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The DeviceApp MUST join the configured Wi-Fi, announce `presto.local`, and serve the
  WebUi and HttpApi on port 80 of the local network.
- **FR-002**: Conversion (SourceImage → PixelArt → PrestoBinFormat) MUST happen in the browser; the
  device receives finished .bin files only.
- **FR-003**: Browser conversion MUST offer the same PixelizeSettings as the desktop tool (grid
  16/32/64, colors 2–256 or `pico-8`, crop/fit, background color, dithering) and MUST produce
  the same result as the desktop tool for the same grid-sized pixels (see SC-004).
- **FR-004**: Animated GIF input MUST produce a multi-frame PrestoBinFormat v1 file with one Palette.
- **FR-005**: Each MediaItem MUST store: id, name, tags, frameCount, gridSize, byte size, created
  time. The Catalog MUST survive restarts and MUST never be left half-written (atomic save).
- **FR-006**: ShowModes: all, images, animations, tags (OR of selected Tags); slide duration
  3–600 s (default 10); shuffle on/off (default off).
- **FR-007**: The WebUi MUST allow upload, rename, retag, delete, show now, filter by tag, change
  ShowMode, and display free storage.
- **FR-008**: The DeviceApp MUST keep playing while serving HTTP requests.
- **FR-009**: Wi-Fi credentials are set once in a file on the device (`secrets.py`), not via the WebUi.
- **FR-010**: The desktop tool (001) MUST keep working and stays the reference implementation.

### Key Entities

- **MediaItem** — one stored .bin plus metadata; belongs to the Catalog; has 0..n Tags.
- **Tag** — normalized label.
- **Catalog** — all MediaItems; persisted as JSON on MediaStorage.
- **ShowMode** — which MediaItems go into the Playlist.
- **Playlist** — ordered MediaItem ids derived from Catalog + DeviceSettings.
- **DeviceSettings** — ShowMode, selected Tags, slide duration, shuffle.
- **MediaStorage** — microSD if present, otherwise internal flash.

## Success Criteria *(mandatory)*

- **SC-001**: From choosing a file to seeing it on the Presto takes under 15 seconds on a home network.
- **SC-002**: The WebUi works on current Safari (iPhone) and Chrome, with no internet access.
- **SC-003**: Library holds at least 500 grid-32 still images on microSD, or 50 on flash only.
- **SC-004**: On the shared golden vectors, browser and desktop produce byte-identical .bin files;
  on real photos the result differs at most by browser image-decoding/resampling noise.
- **SC-005**: 24 hours of slideshow with occasional uploads causes no crash or reboot.

## Assumptions

- Home LAN is trusted: no login/password on the WebUi in this feature.
- The Presto runs Pimoroni's MicroPython firmware (with the `presto` module), as in the existing
  PRESTO project; the new DeviceApp replaces that project's `main.py` menu of code-drawn scenes.
- The router needs no setup beyond optionally reserving a fixed IP for the Presto.
- Upload of the original image file to the device is not needed; only the .bin is stored.
- Desktop upload from the Python CLI is out of scope (possible follow-up).
