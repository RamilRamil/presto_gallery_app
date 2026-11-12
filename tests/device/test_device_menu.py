"""DeviceMenu, font and Collections: pure logic, no hardware."""
import pytest

from gallery import l1_font, l2_catalog as l2, l3_keyboard, l3_menu as menu, l3_playlist as l3, l4_codecs as l4
from gallery.model import default_settings, device_state, empty_catalog, media_item, scene_item

INFO = {"address": "192.168.1.57", "freeBytes": 1048576}


def item(media_id, frames=1, tags=()):
    return media_item(media_id, "pic", tags, frames, 60, 100, 0)


def catalog_of(*items):
    catalog = empty_catalog()
    for i in items:
        catalog = l2.add_item(catalog, i)
    return catalog


def press(state, label, catalog, settings):
    """Tap the cell with this label; a settings command comes back as its settings."""
    following, command = press_cell(state, label, catalog, settings)
    return following, command["settings"] if command else None


def press_cell(state, label, catalog, settings):
    for cell in menu.menu_view(state, catalog, settings, INFO)["cells"]:
        if cell["label"].startswith(label):
            return menu.menu_tap(state, cell["x"] + 1, cell["y"] + 1, catalog, settings, INFO)
    raise AssertionError("no cell " + label)


def labels_of(state, catalog, settings=None):
    return [c["label"] for c in menu.menu_view(state, catalog, settings or default_settings(), INFO)["cells"]]


# --- font ---

@pytest.mark.parametrize("text", [
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ",
    "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789 -_.,:;!?()/+#'\"%&=<>*@",
])
def test_every_expected_character_has_its_own_glyph(text):
    unknown = l1_font.glyph_rows("☃")
    for char in text:
        rows = l1_font.glyph_rows(char)
        assert len(rows) == 7 and all(0 <= r < 32 for r in rows)
        if char != "?":
            assert rows != unknown, char


def test_cyrillic_glyphs_are_distinct_where_they_should_be():
    assert l1_font.glyph_rows("Ж") != l1_font.glyph_rows("О")
    assert l1_font.glyph_rows("А") == l1_font.glyph_rows("A")
    assert l1_font.glyph_rows("я") != l1_font.glyph_rows("и")


def test_fit_text():
    assert l1_font.fit_text("кот", 5) == "кот"
    assert l1_font.fit_text("абвгдеж", 5) == "абвг…"


# --- Collections ---

def collected():
    catalog = catalog_of(item("a", tags=["x"]), item("b", tags=["y"]), scene_item("s", "n", [], 9, 0))
    catalog = l2.add_collection(catalog, "c1", " Вечер ")
    return l2.add_to_collection(catalog, "c1", ["b", "a", "b", "missing"])


def test_collection_keeps_order_and_skips_duplicates():
    assert l2.find_collection(collected(), "c1") == {"collectionId": "c1", "name": "Вечер", "mediaIds": ["b", "a"]}


def test_collection_names_are_unique_ignoring_case():
    with pytest.raises(ValueError):
        l2.add_collection(collected(), "c2", "вечер")
    with pytest.raises(ValueError):
        l2.rename_collection(l2.add_collection(collected(), "c2", "Утро"), "c2", "ВЕЧЕР")
    assert l2.find_collection(l2.rename_collection(collected(), "c1", "Вечер"), "c1")["name"] == "Вечер"


def test_collection_filter_excludes_flagged_and_unknown():
    catalog = l2.add_to_collection(collected(), "c1", ["s"])
    assert [i["mediaId"] for i in l2.filter_by_mode(catalog, "collection", [], "c1")] == ["b", "a", "s"]
    flagged = l2.set_flag(catalog, "s", True, "boom")
    assert [i["mediaId"] for i in l2.filter_by_mode(flagged, "collection", [], "c1")] == ["b", "a"]
    assert l2.filter_by_mode(catalog, "collection", [], "nope") == []


def test_deleting_items_cleans_collections_and_deleting_collection_keeps_items():
    catalog = l2.remove_item(collected(), "a")
    assert l2.find_collection(catalog, "c1")["mediaIds"] == ["b"]
    catalog = l2.remove_collection(catalog, "c1")
    assert catalog["collections"] == [] and len(catalog["items"]) == 2
    with pytest.raises(KeyError):
        l2.remove_collection(catalog, "c1")


def test_old_catalog_loads_without_collections_and_round_trips():
    old = '{"formatVersion": 1, "items": []}'
    assert l4.catalog_from_json(old)["collections"] == []
    assert l4.catalog_from_json(l4.catalog_to_json(collected())) == collected()


def show_state(catalog):
    settings = l3.validate_settings({"showMode": "collection", "selectedCollection": "c1"})
    return device_state(catalog, settings, l3.build_playlist(catalog, settings, 1), 0)


def test_show_mode_collection_and_fallback_after_delete():
    state = show_state(collected())
    assert state["playlist"] == ["b", "a"]
    state = l3.apply_command(state, {"op": "deleteCollection", "collectionId": "c1"}, 1)
    assert state["settings"]["showMode"] == "all" and state["settings"]["selectedCollection"] is None


def test_unknown_collection_falls_back_instead_of_failing():
    state = device_state(collected(), default_settings(), [], 0)
    settings = dict(default_settings(), showMode="collection", selectedCollection="gone")
    state = l3.apply_command(state, {"op": "setSettings", "settings": settings}, 1)
    assert state["settings"]["showMode"] == "all"


def test_silent_upload_keeps_current_item_and_can_join_a_collection():
    state = device_state(collected(), default_settings(), ["a", "b", "s"], 1)
    command = {"op": "upload", "item": item("n"), "show": False, "collectionId": "c1"}
    state = l3.apply_command(state, command, 1)
    assert state["playlist"][state["index"]] == "b"
    assert l2.find_collection(state["catalog"], "c1")["mediaIds"] == ["b", "a", "n"]
    state = l3.apply_command(state, {"op": "upload", "item": item("m")}, 1)
    assert state["playlist"][state["index"]] == "m"
    with pytest.raises(KeyError):
        l3.apply_command(state, {"op": "upload", "item": item("z"), "collectionId": "nope"}, 1)


def test_bulk_operations():
    state = device_state(collected(), default_settings(), ["a", "b", "s"], 0)
    state = l3.apply_command(state, {"op": "addTag", "mediaIds": ["a", "s", "zz"], "tag": "New"}, 1)
    items = {i["mediaId"]: i for i in state["catalog"]["items"]}
    assert items["a"]["tags"] == ["new", "x"] and items["s"]["tags"] == ["new"] and items["b"]["tags"] == ["y"]
    with pytest.raises(ValueError):
        l3.apply_command(state, {"op": "addTag", "mediaIds": ["a"], "tag": ""}, 1)
    state = l3.apply_command(state, {"op": "removeItems", "mediaIds": ["a", "s", "zz"]}, 1)
    assert [i["mediaId"] for i in state["catalog"]["items"]] == ["b"]
    assert state["playlist"] == ["b"]
    assert l2.find_collection(state["catalog"], "c1")["mediaIds"] == ["b"]


# --- menu ---

def test_main_menu_marks_current_and_blocks_empty_modes():
    catalog = collected()
    view = menu.menu_view(menu.menu_open(default_settings()), catalog, default_settings(), INFO)
    cells = {c["label"]: c for c in view["cells"]}
    assert cells["Всё"]["marked"] and cells["Всё"]["note"] == "3"
    assert cells["Гифки"]["action"] is None and cells["Гифки"]["note"] == "пусто"
    assert all(c["height"] >= 40 for c in view["cells"])


def test_choosing_a_mode_closes_the_menu():
    settings = default_settings()
    next_menu, changed = press(menu.menu_open(settings), "Картинки", collected(), settings)
    assert next_menu is None and changed["showMode"] == "images"


def test_tapping_nothing_or_a_disabled_cell_changes_nothing():
    catalog, settings = collected(), default_settings()
    state = menu.menu_open(settings)
    assert menu.menu_tap(state, 239, 2, catalog, settings, INFO) == (state, None)
    assert press(state, "Гифки", catalog, settings) == (state, None)


def test_collection_in_three_taps_or_fewer():
    catalog, settings = collected(), default_settings()
    state, _ = press(menu.menu_open(settings), "Коллекции", catalog, settings)
    assert state["screen"] == "collections"
    state, changed = press(state, "Вечер", catalog, settings)
    assert state is None and changed["showMode"] == "collection" and changed["selectedCollection"] == "c1"


def test_paging_and_back():
    catalog = empty_catalog()
    for n in range(6):
        catalog = l2.add_collection(catalog, "c%d" % n, "name%d" % n)
    settings = default_settings()
    state = dict(menu.menu_open(settings), screen="collections")
    state2, _ = press(state, ">", catalog, settings)
    assert state2["page"] == 1
    labels = [c["label"] for c in menu.menu_view(state2, catalog, settings, INFO)["cells"]]
    assert labels[0].startswith("name4")
    assert press(state2, ">", catalog, settings)[0] == state2  # no next page
    back, _ = press(state2, "Назад", catalog, settings)
    assert back["screen"] == "main" and back["page"] == 0


def test_tags_toggle_and_show():
    catalog, settings = collected(), default_settings()
    state = dict(menu.menu_open(settings), screen="tags")
    assert press(state, "Показать", catalog, settings) == (state, None)
    state, _ = press(state, "x", catalog, settings)
    assert state["tags"] == ["x"]
    state, _ = press(state, "y", catalog, settings)
    done, changed = press(state, "Показать", catalog, settings)
    assert done is None and changed["showMode"] == "tags" and sorted(changed["selectedTags"]) == ["x", "y"]
    state, _ = press(state, "x", catalog, settings)
    assert state["tags"] == ["y"]


def test_settings_screen():
    catalog, settings = collected(), default_settings()
    state = dict(menu.menu_open(settings), screen="settings")
    cells = menu.menu_view(state, catalog, settings, INFO)["cells"]
    address = [c for c in cells if c["label"] == "192.168.1.57"]
    assert len(address) == 1 and address[0]["note"] == "свободно 1.0 МБ" and address[0]["action"] is None
    assert press(state, "+", catalog, settings)[1]["slideSeconds"] == 15
    assert press(state, "-", catalog, settings)[1]["slideSeconds"] == 5
    assert press(state, "Перемешать", catalog, settings)[1]["shuffle"] is True
    assert press(state, "Перемешать", catalog, settings)[0] == state
    low = dict(settings, slideSeconds=3)
    assert press(state, "-", catalog, low) == (state, None)


def test_settings_screen_says_scenes_advance_on_a_swipe():
    catalog, settings = collected(), default_settings()
    state = dict(menu.menu_open(settings), screen="settings")

    def notes(current):
        return [c.get("note") for c in menu.menu_view(state, catalog, current, INFO)["cells"]]

    assert menu.SCENES_NOTE in notes(dict(settings, showMode="scenes"))
    assert menu.SCENES_NOTE not in notes(dict(settings, showMode="all"))
    assert press(state, "+", catalog, dict(settings, showMode="scenes"))[1]["slideSeconds"] == 15


def test_long_names_are_cut_to_fit():
    catalog = l2.add_collection(empty_catalog(), "c1", "очень длинное название коллекции")
    settings = default_settings()
    state = dict(menu.menu_open(settings), screen="collections")
    label = menu.menu_view(state, catalog, settings, INFO)["cells"][0]["label"]
    assert len(label) == menu.CHARS_PER_ROW and l1_font.ELLIPSIS in label


# --- library screens ---

def on_item(screen="item", media_id="a"):
    return dict(menu.menu_open(default_settings(), media_id), screen=screen)


def applied(catalog, command):
    settings = default_settings()
    if command["op"] == "createCollection":
        command = dict(command, collectionId="new")
    return l3.apply_command(device_state(catalog, settings, ["a", "b"], 0), command, 1)["catalog"]


def type_text(state, catalog, settings, text):
    for char in text:
        page = next(i for i, p in enumerate(l3_keyboard.PAGES) if char in p[1])
        state = dict(state, keyboard=dict(state["keyboard"], page=page))
        state, _ = press_cell(state, char, catalog, settings)
    return state


def test_main_menu_keeps_eight_cells_and_leads_to_more():
    catalog, settings = collected(), default_settings()
    state = menu.menu_open(settings, "a")
    assert len(labels_of(state, catalog)) == 8
    state, _ = press(state, "Ещё", catalog, settings)
    assert labels_of(state, catalog)[:4] == ["Эта картинка", "Изменить коллекции", "Изменить теги", "Настройки"]
    state, _ = press(state, "Настройки", catalog, settings)
    assert state["screen"] == "settings"
    assert press(state, "Назад", catalog, settings)[0]["screen"] == "more"


def test_this_picture_cannot_be_opened_when_nothing_is_shown():
    catalog, settings = collected(), default_settings()
    state = dict(menu.menu_open(settings), screen="more")
    assert press(state, "Эта картинка", catalog, settings) == (state, None)


def test_item_tag_toggles_at_once_and_stays_listed():
    catalog, settings = collected(), default_settings()
    state = on_item("itemTags")
    assert [c["marked"] for c in menu.menu_view(state, catalog, settings, INFO)["cells"]][:2] == [True, False]
    state, command = press_cell(state, "x", catalog, settings)
    assert command == {"op": "editItem", "mediaId": "a", "tags": []}
    catalog = applied(catalog, command)
    assert "x" in labels_of(state, catalog)  # no picture has it now, the row can still set it back
    state, command = press_cell(state, "x", catalog, settings)
    assert command["tags"] == ["x"]


def test_item_collection_toggles():
    catalog, settings = l2.add_collection(collected(), "c2", "Утро"), default_settings()
    state, command = press_cell(on_item("itemCollections"), "Утро", catalog, settings)
    assert command == {"op": "editItem", "mediaId": "a", "collectionIds": ["c1", "c2"]}
    assert press_cell(state, "Вечер", catalog, settings)[1]["collectionIds"] == []


def test_new_tag_for_the_item_through_the_keyboard():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(on_item("itemTags"), "+ Новый тег", catalog, settings)
    assert menu.menu_view(state, catalog, settings, INFO)["title"] == "Новый тег"
    state = type_text(state, catalog, settings, "кот")
    state, command = press_cell(state, "ОК", catalog, settings)
    assert state["keyboard"] is None and state["screen"] == "itemTags"
    assert command == {"op": "editItem", "mediaId": "a", "tags": ["x", "кот"]}
    assert l2.find_item(applied(catalog, command), "a")["tags"] == ["x", "кот"]


def test_new_collection_for_the_item_is_one_command():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(on_item("itemCollections"), "+ Новая", catalog, settings)
    state = type_text(state, catalog, settings, "море")
    _, command = press_cell(state, "ОК", catalog, settings)
    assert l2.find_collection(applied(catalog, command), "new")["mediaIds"] == ["a"]


def test_refused_name_keeps_the_keyboard_with_a_message():
    catalog, settings = collected(), default_settings()
    before, _ = press_cell(dict(on_item(), screen="manageCollections"), "+ Новая", catalog, settings)
    before = type_text(before, catalog, settings, "вечер")
    _, command = press_cell(before, "ОК", catalog, settings)
    with pytest.raises(ValueError):
        applied(catalog, command)
    state = menu.menu_rejected(before)
    assert state["keyboard"]["text"] == "вечер"
    assert menu.menu_view(state, catalog, settings, INFO)["title"] == "Имя не подходит"


def test_empty_name_is_refused_by_the_same_path():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(dict(on_item(), screen="manageCollections"), "+ Новая", catalog, settings)
    _, command = press_cell(state, "ОК", catalog, settings)
    with pytest.raises(ValueError):
        applied(catalog, command)


def test_speed_entry_is_for_scenes_only():
    catalog, settings = collected(), default_settings()
    assert not any(label.startswith("Скорость") for label in labels_of(on_item(), catalog, settings))
    assert "Скорость: 1x" in labels_of(on_item(media_id="s"), catalog, settings)


def test_all_speeds_fit_on_one_screen_inside_it():
    catalog, settings = collected(), default_settings()
    cells = menu.menu_view(on_item("itemSpeed", "s"), catalog, settings, INFO)["cells"]
    speeds = [c for c in cells if c["action"] and c["action"][0] == "itemSpeed"]
    assert [c["label"] for c in speeds] == ["0.25x", "0.5x", "1x", "2x", "4x"]
    assert [c["label"] for c in speeds if c["marked"]] == ["1x"]
    assert all(c["x"] + c["width"] <= 240 and c["y"] + c["height"] <= 198 for c in speeds)


def test_tapping_a_speed_saves_it_and_moves_the_mark():
    catalog, settings = collected(), default_settings()
    state, command = press_cell(on_item("itemSpeed", "s"), "2x", catalog, settings)
    assert state["screen"] == "itemSpeed"
    assert command == {"op": "editItem", "mediaId": "s", "speedPercent": 200}
    catalog = applied(catalog, command)
    cells = menu.menu_view(state, catalog, settings, INFO)["cells"]
    assert [c["label"] for c in cells if c["marked"]] == ["2x"]


def test_speed_screen_goes_back_to_the_item():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(on_item("itemSpeed", "s"), "Назад", catalog, settings)
    assert state["screen"] == "item"


def test_keyboard_cancel_changes_nothing():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(on_item("itemTags"), "+ Новый тег", catalog, settings)
    state, command = press_cell(state, "Отм", catalog, settings)
    assert state["keyboard"] is None and command is None and state["screen"] == "itemTags"


def collection_card():
    return dict(on_item(), screen="collectionCard", target="c1")


def test_collection_rename_starts_from_the_current_name():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(collection_card(), "Переименовать", catalog, settings)
    assert state["keyboard"]["text"] == "Вечер"
    state, command = press_cell(state, "ОК", catalog, settings)
    assert command == {"op": "renameCollection", "collectionId": "c1", "name": "Вечер"}


def test_collection_delete_asks_first_and_keeps_pictures():
    catalog, settings = collected(), default_settings()
    state, command = press_cell(collection_card(), "Удалить", catalog, settings)
    assert command is None and state["screen"] == "confirmCollection"
    assert press_cell(state, "Назад", catalog, settings)[0]["screen"] == "collectionCard"
    state, command = press_cell(state, "Да", catalog, settings)
    assert state["screen"] == "manageCollections"
    catalog = applied(catalog, command)
    assert catalog["collections"] == [] and len(catalog["items"]) == 3


def with_scene():
    return l2.add_to_collection(collected(), "c1", ["s"])


def collection_show_screen():
    return dict(collection_card(), screen="collectionShow")


def test_collection_speed_entry_needs_a_scene():
    settings = default_settings()
    assert not any(label.startswith("Сцены") for label in labels_of(collection_show_screen(), collected(), settings))
    assert "Сцены: 1x" in labels_of(collection_show_screen(), with_scene(), settings)


def test_collection_card_keeps_all_rows_on_screen():
    cells = menu.menu_view(collection_card(), with_scene(), default_settings(), INFO)["cells"]
    assert all(c["y"] + c["height"] <= 240 for c in cells)
    rows = [c["label"] for c in cells]
    assert rows.index("Показ") < rows.index("Удалить")
    assert not any(label.startswith("Скорость") for label in rows)


def test_collection_shows_when_its_scenes_differ():
    catalog = l2.add_item(with_scene(), scene_item("t", "m", [], 9, 0))
    catalog = l2.set_speed(l2.add_to_collection(catalog, "c1", ["t"]), "t", 200)
    settings = default_settings()
    assert "Сцены: разная" in labels_of(collection_show_screen(), catalog, settings)
    cells = menu.menu_view(dict(collection_card(), screen="collectionSpeed"), catalog, settings, INFO)["cells"]
    assert not any(c["marked"] for c in cells)


def test_tapping_a_collection_speed_saves_it_for_its_scenes():
    catalog, settings = with_scene(), default_settings()
    state, command = press_cell(collection_card(), "Показ", catalog, settings)
    assert command is None and state["screen"] == "collectionShow"
    state, command = press_cell(state, "Сцены", catalog, settings)
    assert command is None and state["screen"] == "collectionSpeed"
    state, command = press_cell(state, "0.5x", catalog, settings)
    assert state["screen"] == "collectionSpeed"
    assert command == {"op": "setCollectionSpeed", "collectionId": "c1", "speedPercent": 50}
    catalog = applied(catalog, command)
    assert l2.item_speed(l2.find_item(catalog, "s")) == 50
    cells = menu.menu_view(state, catalog, settings, INFO)["cells"]
    assert [c["label"] for c in cells if c["marked"]] == ["0.5x"]


def test_collection_speed_screen_goes_back_to_the_show_screen():
    catalog, settings = with_scene(), default_settings()
    state = dict(collection_card(), screen="collectionSpeed")
    state = press_cell(state, "Назад", catalog, settings)[0]
    assert state["screen"] == "collectionShow"
    assert press_cell(state, "Назад", catalog, settings)[0]["screen"] == "collectionCard"


def test_removing_a_picture_from_a_collection():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(collection_card(), "Картинки", catalog, settings)
    state, command = press_cell(state, "pic", catalog, settings)
    assert command == {"op": "removeFromCollection", "collectionId": "c1", "mediaId": "b"}


def test_tag_rename_goes_through_the_keyboard_and_forgets_the_old_selection():
    catalog, settings = collected(), default_settings()
    state = dict(menu.menu_open(dict(settings, selectedTags=["x"]), "a"), screen="tagCard", target="x")
    state, _ = press_cell(state, "Переименовать", catalog, settings)
    state, command = press_cell(state, "ОК", catalog, settings)
    assert command == {"op": "renameTag", "tag": "x", "newTag": "x"}
    assert state["screen"] == "manageTags" and state["tags"] == []


def test_tag_delete_asks_first():
    catalog, settings = collected(), default_settings()
    state, _ = press_cell(dict(on_item(), screen="tagCard", target="x"), "Удалить", catalog, settings)
    assert state["screen"] == "confirmTag"
    state, command = press_cell(state, "Да", catalog, settings)
    assert command == {"op": "removeTag", "tag": "x"} and state["screen"] == "manageTags"


@pytest.mark.parametrize("screen, target, expected", [
    ("itemTags", None, "more"), ("collectionCard", "gone", "manageCollections"), ("tagCard", "gone", "manageTags"),
])
def test_screen_of_something_deleted_falls_back(screen, target, expected):
    catalog, settings = collected(), default_settings()
    state = dict(on_item(screen, "gone"), target=target)
    following, command = menu.menu_tap(state, 239, 2, catalog, settings, INFO)
    assert following["screen"] == expected and command is None
    assert menu.menu_view(state, catalog, settings, INFO)["cells"]


def test_every_library_screen_has_large_cells_and_can_go_back():
    catalog = l2.add_collection(collected(), "c2", "очень длинное название коллекции")
    settings = default_settings()
    for screen in ("more", "item", "itemTags", "itemCollections", "manageCollections", "collectionCard",
                   "collectionItems", "confirmCollection", "manageTags", "tagCard", "confirmTag"):
        target = "x" if screen in ("tagCard", "confirmTag") else "c1"
        state = dict(on_item(screen), target=target)
        view = menu.menu_view(state, catalog, settings, INFO)
        assert all(c["height"] >= 40 and c["y"] + c["height"] <= 240 for c in view["cells"]), screen
        assert len(view["title"]) <= 19, screen
        assert all(len(c["label"]) <= 18 for c in view["cells"]), screen
        assert "Назад" in [c["label"] for c in view["cells"]], screen


def test_long_lists_are_paged_on_library_screens():
    catalog = empty_catalog()
    for n in range(7):
        catalog = l2.add_collection(catalog, "c%d" % n, "name%d" % n)
    settings = default_settings()
    state = dict(menu.menu_open(settings), screen="manageCollections")
    assert labels_of(state, catalog)[:4] == ["name0 (0)", "name1 (0)", "name2 (0)", "+ Новая коллекция"]
    state, _ = press_cell(state, ">", catalog, settings)
    assert labels_of(state, catalog)[0] == "name3 (0)"


def test_timeouts_are_longer_while_managing():
    settings = default_settings()
    assert menu.menu_timeout_ms(menu.menu_open(settings)) == 20000
    assert menu.menu_timeout_ms(on_item("itemTags")) == 60000
