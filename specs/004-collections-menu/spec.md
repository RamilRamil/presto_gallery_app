# Feature Specification: Batch Upload, Collections and the Device Menu

**Feature Branch**: `004-collections-menu`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Надо ещё научить выбирать файлы пачкой. И ещё надо написать удобное меню для выбора, что именно транслировать на самом Presto. Предлагаю ввести понятие collection, куда можно добавлять изображения с разными тегами."

> Terms follow `knowledge/domain.okf.json`. New terms: Collection, UploadQueue, DeviceMenu.
> Existing: MediaItem, Tag, Scene, Catalog, ShowMode, DeviceSettings, Playlist, CropView, WebUi.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload many files at once (Priority: P1)

The user selects or drops many pictures and GIFs at once. They appear as a queue. What the user sets
on the first file applies to the rest; then any other file can be opened and adjusted by hand. One
button uploads them all.

**Why this priority**: adding photos one by one is the slowest part of filling the gallery.

**Independent Test**: select 20 photos on a phone, press upload; all 20 are in the library, and the
slideshow was not interrupted by each upload.

**Acceptance Scenarios**:

1. **Given** several files are selected or dropped, **Then** each appears in the queue with its name
   and a state: waiting, uploading, done or failed.
2. **Given** the queue, **When** the user changes anything on the reference file (the first picture or
   GIF in the queue): grid, colors, palette, fit, background, dithering, CropView, Tags or target
   Collection, **Then** the change applies to every file that has not set that same value by hand.
3. **Given** another file in the queue, **When** the user opens it and changes a value, **Then** only
   that file and only that value change. It keeps following the reference file for everything else,
   and the row is marked "своё".
4. **Given** a file fails (unreadable, over the limits, no space), **Then** it is marked with the
   reason and the others continue; pressing upload again retries only the failed ones.
5. **Given** the upload runs, **Then** progress "7 из 20" is visible, it can be cancelled, and items
   already uploaded stay. The Presto keeps its current slideshow.
6. **Given** several `.py` files are selected, **Then** they are uploaded as Scenes the same way.
7. **Given** a file with its own values, **When** the user presses "Как у первого", **Then** its own
   values are dropped and it follows the reference file again.
8. **Given** the reference file's CropView, **Then** other files get the same relative position and
   zoom, adapted to their own size and proportions.

---

### User Story 2 - Collections (Priority: P1)

A Collection is a named set of MediaItems the user puts together by hand. Items in one Collection
can have different Tags; an item can be in several Collections. The Presto can show one Collection.

**Why this priority**: Tags describe what a picture is; Collections say what to show together.

**Independent Test**: create "Вечер", add 3 items with different Tags, choose it as the show mode;
the Presto cycles only those 3.

**Acceptance Scenarios**:

1. **Given** the library, **When** the user creates, renames or deletes a Collection, **Then** the
   change is kept across restarts. Deleting a Collection does not delete its MediaItems.
2. **Given** the library, **When** the user ticks several items and chooses "В коллекцию", **Then**
   they are added, skipping those already in it.
3. **Given** the library filtered by a Tag, **When** the user selects all and adds them, **Then** the
   items having it now are added once; later changes of Tags do not change the Collection.
4. **Given** an item is removed from a Collection, **Then** it stays in the library. **Given** an
   item is deleted from the library, **Then** it leaves every Collection.
5. **Given** the library filter by Collection, **Then** only its items are listed.
6. **Given** ShowMode **collection** with a chosen Collection, **Then** the Playlist holds its items
   in the order they were added, or shuffled if shuffle is on; flagged Scenes are left out.
7. **Given** a Collection is deleted while it is being shown, **Then** the mode falls back to **all**.

---

### User Story 3 - Choose what to show on the Presto itself (Priority: P1)

A long press on the screen opens a menu with large rows. Without a phone, the user picks what to
show: everything, pictures, GIFs, Scenes, one Collection, or Tags.

**Why this priority**: the device should be usable without opening the web interface.

**Independent Test**: with no phone and no Wi-Fi, long-press, choose a Collection; the slideshow
changes to it and the choice survives a restart.

**Acceptance Scenarios**:

1. **Given** the slideshow, **When** the user long-presses for 1 second, **Then** playback pauses and
   the menu opens, showing the current choice.
2. **Given** the main menu, **Then** it offers: Всё, Картинки, Гифки, Сцены, Коллекции, Теги,
   Настройки. Tapping a mode starts it and closes the menu.
3. **Given** "Коллекции", **Then** the list shows each name and item count. Tapping one shows it.
4. **Given** "Теги", **Then** tapping toggles Tags, the selected ones are marked, and "Показать"
   starts them. At least one Tag must be selected for "Показать" to work.
5. **Given** more rows than fit, **Then** there are previous and next page controls.
6. **Given** "Настройки", **Then** the user can change the slide time, turn shuffle on or off, and
   see the address and free storage.
7. **Given** an inner menu, **Then** "Назад" goes one level up, and the top-level "Закрыть" resumes
   the slideshow unchanged. After 20 seconds without a touch the menu closes by itself.
8. **Given** names in Russian or English, **Then** they are readable; names too long for a row are
   cut with an ellipsis.
9. **Given** a choice with nothing to show, **Then** the row says it is empty and cannot start it.
10. **Given** a change from the menu, **Then** the WebUi shows the same state, and the other way round.

---

### User Story 4 - Work on many existing files at once (Priority: P1)

In the library the user ticks files, or selects all those currently listed, then deletes them, adds
a Tag to them or adds them to a Collection in one action.

**Independent Test**: filter by a Tag, select all, add another Tag; every listed item has it. Then
delete them; they disappear from the library, the Playlist and every Collection.

**Acceptance Scenarios**:

1. **Given** the library, **Then** each item has a checkbox and the number selected is visible.
2. **Given** a filter, **When** the user presses "Выбрать все", **Then** only the listed items are
   selected. "Снять" clears the selection.
3. **Given** a selection, **When** the user deletes it and confirms the count, **Then** all those
   items and their files are removed.
4. **Given** a selection and a Tag, **Then** the Tag is added to every item; existing Tags stay.
5. **Given** a selection and a Collection, **Then** the items are added, skipping those already in it.

---

### User Story 5 - Tags as labels, and full editing of a file (Priority: P1)

Wherever Tags are entered for one file, the existing Tags are shown as labels. A click adds a Tag, a
second click removes it, and a new Tag can still be typed after a comma. "Изменить" in the library
opens one form with the name, Tags and Collections of the file.

**Independent Test**: upload with two labels clicked, one clicked off and one new Tag typed; the file
has exactly the expected Tags. Then open "Изменить", remove a Tag and move the file to another
Collection; the library and the Collection show the change after a page reload.

**Acceptance Scenarios**:

1. **Given** existing Tags, **When** the user clicks a label, **Then** the Tag appears in the text
   field and the label is marked. **When** they click it again, **Then** the Tag leaves the field and
   the label is unmarked.
2. **Given** the user types Tags by hand, **Then** labels of Tags typed so far are marked as they
   type, and Tags that do not exist yet are kept.
3. **Given** "Изменить", **Then** one form shows the name, the Tags with labels, and every Collection
   as a label marked if the file is in it. Clicking toggles membership.
4. **Given** the form, **When** the user presses "Сохранить", **Then** name, Tags and Collections
   change together in one save. **When** they cancel, **Then** nothing changes.
5. **Given** the file stays in a Collection, **Then** its position there is unchanged; a Collection it
   newly joins gets it at the end.

### Edge Cases

- Duplicate Collection names are refused. Names follow the rules for MediaItem names.
- A file dropped twice appears twice; the user can remove a queue row before uploading.
- Closing the browser tab during a batch: already uploaded items stay; the rest are not sent.
- Very large queues: pictures are decoded one at a time, so a phone does not hold them all in memory.
- A tap on a row while the menu is redrawing is ignored, not applied to the next screen.
- A long press during a Scene opens the menu at the Scene's next `stop` call.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The WebUi MUST accept several pictures and GIFs at once, by picker and by drag and drop,
  up to 100 files in one queue.
- **FR-002**: Each queue file MUST have a name from its file name by default and a state. Conversion
  settings, CropView, Tags and target Collection MUST follow the reference file, value by value,
  unless the user set that value on this file. The reference is the first picture or GIF in the queue.
- **FR-003**: Uploads MUST run one at a time and MUST NOT change what the Presto is showing.
- **FR-004**: A failed file MUST NOT stop the others; failed files MUST show the reason and be retryable.
- **FR-005**: A Collection MUST have an id, a unique name and an ordered list of media ids; it MUST be
  stored in the Catalog with the same atomic save; older catalogs load with no Collections.
- **FR-006**: The WebUi MUST allow create, rename, delete, add many, remove one, and filter the
  library by Collection. Bulk delete, add Tag and add to Collection MUST each be one request.
- **FR-007**: ShowModes MUST be extended with **collection**, with the chosen Collection in
  DeviceSettings.
- **FR-008**: Removing a MediaItem MUST remove it from every Collection.
- **FR-009**: A long press MUST open the DeviceMenu; tap left and right MUST keep switching slides
  outside the menu. The address moves into "Настройки".
- **FR-010**: The DeviceMenu MUST work with no network and MUST use only data on the device.
- **FR-011**: Touch rows MUST be at least 40 px high.
- **FR-012**: Changes from the DeviceMenu MUST go through the same change path as the WebUi and be saved.
- **FR-013**: The DeviceMenu MUST show Cyrillic and Latin names readably.
- **FR-014**: The HttpApi additions MUST be protected by the AccessPassword like the rest.
- **FR-015**: One-file Tag entry (upload form and "Изменить") MUST offer existing Tags as labels that
  toggle on click, and MUST keep free comma-separated typing. Both stay in step.
- **FR-016**: "Изменить" MUST edit name, Tags and Collection membership of one MediaItem and MUST
  apply them as one change. An unknown Collection MUST refuse the whole change.
- **FR-017**: A working microSD card MUST be used for the gallery. On the first start with a card, a
  gallery on flash MUST be copied to it without changing other files on the card; an interrupted
  copy MUST start over on the next start.

### Key Entities

- **Collection** - a named, ordered, hand-made set of MediaItems; stored in the Catalog.
- **UploadQueue** - files waiting for upload in the browser; not stored on the device.
- **DeviceMenu** - the on-screen menu on the Presto, a tree of screens with pages.
- **ShowMode** - gains **collection**. **DeviceSettings** - gains the selected Collection.

## Success Criteria *(mandatory)*

- **SC-001**: 20 phone photos at Grid 60 are uploaded with one press, in under 2 minutes.
- **SC-002**: During a batch of 20, the Presto never jumps to the uploaded items.
- **SC-003**: A new user picks a Collection on the device in at most 3 taps after the long press.
- **SC-004**: The menu responds to a tap within 300 ms.
- **SC-005**: A Collection of 200 items saves and loads without a visible pause in the slideshow.

## Assumptions

- A Collection holds an explicit list of items. A rule like "everything with this Tag, now and
  later" stays the job of ShowMode **tags**.
- Items in a Collection keep the order they were added; reordering by hand is out of scope.
- Creating or editing Collections happens in the WebUi; the DeviceMenu only chooses what to show.
- The name is still set per file only after upload, through "Изменить". While uploading many files
  each takes the name of its file.
- "Изменить" does not change the picture itself: the original is not stored on the Presto, so grid,
  palette and crop are chosen before upload.
- The bulk "Добавить тег" field stays as it is.
