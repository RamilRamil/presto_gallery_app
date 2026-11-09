"""DeviceMenu, font and Collections: pure logic, no hardware."""
import pytest

from gallery import l1_font, l2_catalog as l2, l3_menu as menu, l3_playlist as l3, l4_codecs as l4
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
    """Tap the cell with this label."""
    for cell in menu.menu_view(state, catalog, settings, INFO)["cells"]:
        if cell["label"].startswith(label):
            return menu.menu_tap(state, cell["x"] + 1, cell["y"] + 1, catalog, settings, INFO)
    raise AssertionError("no cell " + label)


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
    labels = [c["label"] for c in menu.menu_view(state, catalog, settings, INFO)["cells"]]
    assert "192.168.1.57" in labels and "Свободно 1.0 МБ" in labels
    assert press(state, "+", catalog, settings)[1]["slideSeconds"] == 15
    assert press(state, "-", catalog, settings)[1]["slideSeconds"] == 5
    assert press(state, "Перемешать", catalog, settings)[1]["shuffle"] is True
    assert press(state, "Перемешать", catalog, settings)[0] == state
    low = dict(settings, slideSeconds=3)
    assert press(state, "-", catalog, low) == (state, None)


def test_long_names_are_cut_to_fit():
    catalog = l2.add_collection(empty_catalog(), "c1", "очень длинное название коллекции")
    settings = default_settings()
    state = dict(menu.menu_open(settings), screen="collections")
    label = menu.menu_view(state, catalog, settings, INFO)["cells"][0]["label"]
    assert len(label) == menu.CHARS_PER_ROW and l1_font.ELLIPSIS in label
