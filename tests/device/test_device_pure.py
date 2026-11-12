import struct

import pytest

from gallery import l1_primitives as l1
from gallery import l2_catalog as l2
from gallery import l3_playlist as l3
from gallery import l3_scene
from gallery import l4_codecs as l4
from gallery.model import default_settings, device_state, empty_catalog, media_item, scene_item


def item(media_id, frames=1, tags=(), name="pic"):
    return media_item(media_id, name, tags, frames, 32, 1090, 0)


def scene(media_id, tags=()):
    return scene_item(media_id, "scene", tags, 100, 0)


def catalog_of(*items):
    catalog = empty_catalog()
    for i in items:
        catalog = l2.add_item(catalog, i)
    return catalog


# --- layer 1 ---

def test_normalize_tag():
    assert l1.normalize_tag("  Winter   Sky ") == "winter sky"
    assert l1.normalize_tag("коты") == "коты"
    for bad in ("", " ", "a" * 25, "a,b", "x/y"):
        with pytest.raises(ValueError):
            l1.normalize_tag(bad)


def test_normalize_tags_sorted_unique():
    assert l1.normalize_tags(["b", "A", "a "]) == ["a", "b"]


def test_normalize_name():
    assert l1.normalize_name(" my  cat ") == "my cat"
    with pytest.raises(ValueError):
        l1.normalize_name("")


def test_new_media_id_unique_and_hex():
    first = l1.new_media_id(42, set())
    assert len(first) == 8 and int(first, 16) >= 0
    assert l1.new_media_id(42, {first}) != first


def test_geometry():
    assert [(l1.cell_size(g), l1.screen_offset(g)) for g in (16, 32, 64)] == \
        [(30, 0), (15, 0), (7, 16)]


# --- layer 2 ---

def test_add_find_remove():
    catalog = catalog_of(item("a1"), item("b2", tags=["Cats"]))
    assert l2.find_item(catalog, "b2")["tags"] == ["cats"]
    with pytest.raises(ValueError):
        l2.add_item(catalog, item("a1"))
    assert [i["mediaId"] for i in l2.remove_item(catalog, "a1")["items"]] == ["b2"]
    with pytest.raises(KeyError):
        l2.remove_item(catalog, "zz")


def test_rename_and_set_tags_return_new_catalog():
    catalog = catalog_of(item("a1"))
    renamed = l2.rename_item(catalog, "a1", " new ")
    assert l2.find_item(renamed, "a1")["name"] == "new"
    assert l2.find_item(catalog, "a1")["name"] == "pic"  # original untouched
    tagged = l2.set_tags(catalog, "a1", ["x", "y"])
    assert l2.find_item(tagged, "a1")["tags"] == ["x", "y"]


def test_all_tags_and_filter_by_mode():
    catalog = catalog_of(item("a", 1, ["cats"]), item("b", 5, ["cats", "winter"]), item("c", 1))
    assert l2.all_tags(catalog) == [{"label": "cats", "count": 2}, {"label": "winter", "count": 1}]
    ids = lambda mode, tags=(): [i["mediaId"] for i in l2.filter_by_mode(catalog, mode, tags)]
    assert ids("all") == ["a", "b", "c"]
    assert ids("images") == ["a", "c"]
    assert ids("animations") == ["b"]
    assert ids("tags", ["winter", "dogs"]) == ["b"]
    assert ids("tags", []) == []


# --- layer 3 ---

def test_validate_settings():
    s = l3.validate_settings({"showMode": "tags", "selectedTags": ["Cats"], "slideSeconds": 1})
    assert s == {"showMode": "tags", "selectedTags": ["cats"], "selectedCollection": None,
                 "slideSeconds": 3, "shuffle": False, "brightness": 100,
                 "ambientLeds": True}
    for bad in ({"showMode": "x"}, {"slideSeconds": "10"}, {"slideSeconds": True}):
        with pytest.raises(ValueError):
            l3.validate_settings(bad)


def test_shuffle_is_permutation_and_deterministic():
    values = list(range(10))
    once = l3.shuffled(values, 7)
    assert sorted(once) == values and once == l3.shuffled(values, 7) and once != values


def test_build_playlist_and_navigation():
    catalog = catalog_of(item("a"), item("b", 3), item("c"))
    settings = dict(default_settings(), showMode="images")
    playlist = l3.build_playlist(catalog, settings, 1)
    assert playlist == ["a", "c"]
    assert l3.next_index(playlist, 1) == 0 and l3.prev_index(playlist, 0) == 1
    assert l3.next_index([], 0) == 0


def test_reposition_keeps_current():
    assert l3.reposition(["a", "b", "c"], 1, ["c", "b"]) == 1
    assert l3.reposition(["a", "b"], 0, ["b"]) == 0


def test_slide_plan():
    assert l3.slide_plan([0], 10) == {"loops": 1, "holdMs": 10000}
    assert l3.slide_plan([100, 100, 100], 10) == {"loops": 34, "holdMs": 0}
    assert l3.slide_plan([3000, 9000], 3) == {"loops": 1, "holdMs": 0}


def test_apply_command_flow():
    state = device_state(empty_catalog(), default_settings(), [], 0)
    state = l3.apply_command(state, {"op": "upload", "item": item("a")}, 1)
    state = l3.apply_command(state, {"op": "upload", "item": item("b", 4, ["cats"])}, 1)
    assert state["playlist"] == ["a", "b"] and state["index"] == 1  # upload = show now
    state = l3.apply_command(state, {"op": "next"}, 1)
    assert state["index"] == 0
    settings = dict(default_settings(), showMode="tags", selectedTags=["dogs"])
    state = l3.apply_command(state, {"op": "setSettings", "settings": settings}, 1)
    assert state["playlist"] == []
    state = l3.apply_command(state, {"op": "show", "mediaId": "b"}, 1)
    assert state["playlist"] == ["b"] and state["index"] == 0
    state = l3.apply_command(state, {"op": "setTags", "mediaId": "a", "tags": ["dogs"]}, 1)
    assert state["playlist"] == ["a"]
    state = l3.apply_command(state, {"op": "remove", "mediaId": "a"}, 1)
    assert state["playlist"] == [] and len(state["catalog"]["items"]) == 1
    with pytest.raises(ValueError):
        l3.apply_command(state, {"op": "dance"}, 1)


# --- layer 4 ---

def make_bin(grid=16, palette=2, frames=1):
    header = struct.pack("<4sBBHHHHBB", b"PPXA", 1, 1 if frames > 1 else 0, grid, grid,
                         palette, frames, 480 // grid, 0)
    body = bytes(range(3 * palette)) + b"".join(
        struct.pack("<H", 100 * (i + 1)) + bytes(grid * grid) for i in range(frames))
    return header + body


def test_parse_bin_header_and_offsets():
    data = make_bin(16, 2, 3)
    header = l4.parse_bin_header(data)
    assert header["frameCount"] == 3 and header["cellSize"] == 30
    assert header["totalSize"] == len(data)
    assert l4.frame_offset(header, 1) == 16 + 6 + 258
    assert l4.read_palette(data, header) == [(0, 1, 2), (3, 4, 5)]
    assert l4.read_frame_duration(data[l4.frame_offset(header, 2):]) == 300


@pytest.mark.parametrize("data", [b"", b"XXXX" + bytes(12), make_bin(16)[:4] + b"\x02" + bytes(11)])
def test_parse_bin_header_rejects(data):
    with pytest.raises(ValueError):
        l4.parse_bin_header(data)


def test_validate_upload():
    data = make_bin(32, 4, 2)
    assert l4.validate_upload(data[:64], len(data))["width"] == 32
    with pytest.raises(ValueError):
        l4.validate_upload(data[:64], len(data) - 1)
    with pytest.raises(ValueError):
        l4.validate_upload(data[:64], 2 * 1024 * 1024)


def test_golden_bins_are_valid_uploads():
    import json
    from pathlib import Path
    for path in (Path(__file__).parents[1] / "golden").glob("*.json"):
        data = bytes.fromhex(json.loads(path.read_text())["expectedBin"])
        assert l4.validate_upload(data[:64], len(data))["totalSize"] == len(data)


def test_catalog_json_round_trip_and_tolerance():
    catalog = catalog_of(item("a", tags=["x"]))
    assert l4.catalog_from_json(l4.catalog_to_json(catalog)) == catalog
    assert l4.catalog_from_json("not json") == empty_catalog()
    broken = '{"formatVersion": 1, "items": [{"mediaId": "a"}, 5]}'
    assert l4.catalog_from_json(broken) == empty_catalog()


def test_settings_json():
    settings = dict(default_settings(), shuffle=True)
    assert l4.settings_from_json(l4.settings_to_json(settings)) == settings
    assert l4.settings_from_json("{bad") == default_settings()
    assert l4.settings_from_json('{"slideSeconds": 30, "evil": 1}')["slideSeconds"] == 30


def test_allocate_media_id_and_tag_counts():
    catalog = catalog_of(item("a", tags=["x"]))
    assert l3.allocate_media_id(catalog, 5) != "a"
    assert l3.tag_counts(catalog) == [{"label": "x", "count": 1}]


# --- full-screen grids and Scenes ---

@pytest.mark.parametrize("grid,cell", [(16, 30), (32, 15), (40, 12), (60, 8), (80, 6), (120, 4), (240, 2), (480, 1)])
def test_full_screen_grids(grid, cell):
    assert (l1.cell_size(grid), l1.screen_offset(grid)) == (cell, 0)
    data = make_bin(grid)
    assert l4.validate_upload(data[:64], len(data))["frameSize"] == grid * grid


@pytest.mark.parametrize("grid", [17, 100, 960])
def test_unknown_grid_rejected(grid):
    with pytest.raises(ValueError):
        l4.parse_bin_header(make_bin(grid))


def test_scene_rect_covers_screen_without_gaps():
    spans = [l3_scene.scene_rect(x, 0, 1, 1, 32, 240) for x in range(32)]
    assert spans[0][0] == 0 and spans[-1][0] + spans[-1][2] == 240
    for (left, _, width, _), (next_left, _, _, _) in zip(spans, spans[1:]):
        assert left + width == next_left
    assert {s[2] for s in spans} == {7, 8}


def test_scene_rect_of_several_cells():
    assert l3_scene.scene_rect(0, 0, 32, 32, 32, 240) == (0, 0, 240, 240)
    assert l3_scene.scene_rect(2, 3, 2, 1, 32, 240) == (15, 22, 15, 8)


def test_filter_by_mode_with_scenes_and_flags():
    catalog = catalog_of(item("a", 1, ["x"]), item("b", 5), scene("s", ["x"]), scene("t"))
    catalog = l2.set_flag(catalog, "t", True, "boom")
    ids = lambda mode, tags=(): [i["mediaId"] for i in l2.filter_by_mode(catalog, mode, tags)]
    assert ids("all") == ["a", "b", "s"]
    assert ids("images") == ["a"]
    assert ids("animations") == ["b"]
    assert ids("scenes") == ["s"]
    assert ids("tags", ["x"]) == ["a", "s"]


def test_set_flag_rules():
    catalog = catalog_of(item("a"), scene("s"))
    flagged = l2.set_flag(catalog, "s", True, "x" * 500)
    assert l2.find_item(flagged, "s")["flagged"] and len(l2.find_item(flagged, "s")["error"]) == 200
    cleared = l2.set_flag(flagged, "s", False, None)
    assert not l2.find_item(cleared, "s")["flagged"] and l2.find_item(cleared, "s")["error"] is None
    with pytest.raises(ValueError):
        l2.set_flag(catalog, "a", True, "no")
    with pytest.raises(KeyError):
        l2.set_flag(catalog, "zz", True, "no")


def test_flag_moves_to_next_item_and_unflag_restores():
    state = device_state(catalog_of(item("a"), scene("s"), item("b")), default_settings(),
                         ["a", "s", "b"], 1)
    state = l3.apply_command(state, {"op": "flag", "mediaId": "s", "error": "boom"}, 1)
    assert state["playlist"] == ["a", "b"] and state["index"] == 1
    with pytest.raises(ValueError):
        l3.apply_command(state, {"op": "show", "mediaId": "s"}, 1)
    state = l3.apply_command(state, {"op": "unflag", "mediaId": "s"}, 1)
    assert state["playlist"] == ["a", "s", "b"]
    state = l3.apply_command(state, {"op": "show", "mediaId": "s"}, 1)
    assert state["index"] == 1


def test_flag_of_the_last_item_empties_playlist():
    state = device_state(catalog_of(scene("s")), default_settings(), ["s"], 0)
    state = l3.apply_command(state, {"op": "flag", "mediaId": "s", "error": "boom"}, 1)
    assert state["playlist"] == [] and state["index"] == 0


def test_slide_limit():
    assert l3.slide_limit_ms(["a"], 10, "all") is None
    for mode in ("all", "animations", "collection", "tags"):
        assert l3.slide_limit_ms(["a", "b"], 10, mode) == 10000


def test_scenes_show_mode_advances_only_on_a_swipe():
    assert l3.slide_limit_ms(["a", "b", "c"], 10, "scenes") is None
    assert l3.slide_limit_ms(["a"], 10, "scenes") is None


def test_scenes_show_mode_is_valid():
    assert l3.validate_settings({"showMode": "scenes"})["showMode"] == "scenes"


def test_validate_scene_source():
    source = "import time\n\ndef run(stop):\n    pass\n"
    assert l4.validate_scene_source(source.encode()) == source
    for bad in (b"def helper():\n    pass\n", b"    def run(stop):\n", b"\xff\xfe def run(\n",
                b"def run(stop):\n" + b"#" * (256 * 1024)):
        with pytest.raises(ValueError):
            l4.validate_scene_source(bad)


def test_bearer_token():
    assert l4.bearer_token("Bearer abc") == "abc"
    for bad in (None, "", "Basic abc", "bearer abc"):
        assert l4.bearer_token(bad) is None


def test_password_matches():
    assert l4.password_matches("secret", "secret")
    for expected, presented in (("secret", "secre"), ("secret", "secret1"), ("secret", "Secret"),
                                ("secret", None), ("", ""), ("", None)):
        assert not l4.password_matches(expected, presented)


def test_old_catalog_gets_scene_fields():
    old = '{"formatVersion": 1, "items": [{"mediaId": "a", "name": "n", "tags": [], ' \
          '"frameCount": 1, "gridSize": 64, "byteSize": 9, "createdAt": 0}]}'
    loaded = l4.catalog_from_json(old)["items"][0]
    assert (loaded["kind"], loaded["flagged"], loaded["error"]) == ("picture", False, None)


def two_collections():
    catalog = catalog_of(item("a"), item("b"))
    catalog = l2.add_collection(catalog, "c1", "one")
    catalog = l2.add_collection(catalog, "c2", "two")
    return l2.add_to_collection(catalog, "c1", ["a", "b"])


def test_set_item_collections_keeps_place_and_appends():
    catalog = l2.add_to_collection(two_collections(), "c2", ["b"])
    changed = l2.set_item_collections(catalog, "a", ["c1", "c2"])
    assert l2.find_collection(changed, "c1")["mediaIds"] == ["a", "b"]
    assert l2.find_collection(changed, "c2")["mediaIds"] == ["b", "a"]
    assert l2.find_collection(catalog, "c2")["mediaIds"] == ["b"]


def test_set_item_collections_removes_from_the_rest():
    changed = l2.set_item_collections(two_collections(), "a", [])
    assert l2.find_collection(changed, "c1")["mediaIds"] == ["b"]


def test_set_item_collections_rejects_bad_input():
    catalog = two_collections()
    with pytest.raises(KeyError):
        l2.set_item_collections(catalog, "missing", [])
    with pytest.raises(KeyError):
        l2.set_item_collections(catalog, "a", ["nope"])
    with pytest.raises(ValueError):
        l2.set_item_collections(catalog, "a", "c1")


def edit_state():
    settings = default_settings()
    catalog = two_collections()
    return device_state(catalog, settings, l3.build_playlist(catalog, settings, 1), 0)


def test_edit_item_changes_everything_at_once():
    state = l3.apply_command(edit_state(), {
        "op": "editItem", "mediaId": "a", "name": "new", "tags": ["Коты", "зима"], "collectionIds": ["c2"],
    }, 1)
    found = l2.find_item(state["catalog"], "a")
    assert (found["name"], found["tags"]) == ("new", ["зима", "коты"])
    assert l2.find_collection(state["catalog"], "c1")["mediaIds"] == ["b"]
    assert l2.find_collection(state["catalog"], "c2")["mediaIds"] == ["a"]


def test_edit_item_leaves_out_what_is_not_sent():
    state = l3.apply_command(edit_state(), {"op": "editItem", "mediaId": "a", "tags": ["x"]}, 1)
    assert l2.find_item(state["catalog"], "a")["name"] == "pic"
    assert l2.find_collection(state["catalog"], "c1")["mediaIds"] == ["a", "b"]


def test_edit_item_with_unknown_collection_is_refused_as_a_whole():
    state = edit_state()
    with pytest.raises(KeyError):
        l3.apply_command(state, {"op": "editItem", "mediaId": "a", "name": "new", "collectionIds": ["nope"]}, 1)
    assert l2.find_item(state["catalog"], "a")["name"] == "pic"


# --- Brightness and Tag management ---

def test_brightness_steps_and_stops_at_the_ends():
    assert l3.brightness_step(50, 1) == 75 and l3.brightness_step(50, -1) == 25
    assert l3.brightness_step(100, 1) == 100 and l3.brightness_step(10, -1) == 10


def test_brightness_is_validated_and_snapped():
    assert l3.validate_settings({})["brightness"] == 100
    assert l3.validate_settings({"brightness": 60})["brightness"] == 50
    assert l3.validate_settings({"brightness": 0})["brightness"] == 10
    with pytest.raises(ValueError):
        l3.validate_settings({"brightness": "max"})
    with pytest.raises(ValueError):
        l3.validate_settings({"brightness": True})


def test_old_settings_file_gets_full_brightness():
    assert l4.settings_from_json('{"slideSeconds": 30}')["brightness"] == 100


def test_set_brightness_keeps_the_slide_order_and_position():
    settings = dict(default_settings(), shuffle=True)
    state = device_state(catalog_of(item("a"), item("b"), item("c")), settings, ["c", "a", "b"], 2)
    changed = l3.apply_command(state, {"op": "setBrightness", "level": 25}, 99)
    assert changed["settings"]["brightness"] == 25
    assert changed["playlist"] is state["playlist"] and changed["index"] == 2
    assert l3.apply_command(changed, {"op": "setBrightness", "level": 25}, 100) is changed


def test_saving_settings_without_brightness_keeps_it():
    state = device_state(empty_catalog(), dict(default_settings(), brightness=25), [], 0)
    state = l3.apply_command(state, {"op": "setSettings", "settings": {"slideSeconds": 30}}, 1)
    assert state["settings"]["brightness"] == 25 and state["settings"]["slideSeconds"] == 30


def tagged():
    return catalog_of(item("a", tags=["cat", "dog"]), item("b", tags=["cat"]), item("c", tags=["dog"]))


def tags_of(catalog):
    return {i["mediaId"]: i["tags"] for i in catalog["items"]}


def test_rename_tag_everywhere_and_merge():
    assert tags_of(l2.rename_tag(tagged(), "cat", " Кот "))["b"] == ["кот"]
    assert tags_of(l2.rename_tag(tagged(), "cat", "dog")) == {"a": ["dog"], "b": ["dog"], "c": ["dog"]}
    with pytest.raises(ValueError):
        l2.rename_tag(tagged(), "cat", "")
    with pytest.raises(KeyError):
        l2.rename_tag(tagged(), "gone", "x")


def test_remove_tag_keeps_items():
    catalog = l2.remove_tag(tagged(), "cat")
    assert tags_of(catalog) == {"a": ["dog"], "b": [], "c": ["dog"]}
    with pytest.raises(KeyError):
        l2.remove_tag(catalog, "cat")


def tag_state(selected):
    settings = dict(default_settings(), showMode="tags", selectedTags=selected)
    return device_state(tagged(), settings, l3.build_playlist(tagged(), settings, 1), 0)


def test_selected_tags_follow_a_rename():
    state = l3.apply_command(tag_state(["cat"]), {"op": "renameTag", "tag": "cat", "newTag": "Кот"}, 1)
    assert state["settings"]["selectedTags"] == ["кот"] and sorted(state["playlist"]) == ["a", "b"]


def test_removing_the_last_selected_tag_shows_everything():
    state = l3.apply_command(tag_state(["cat"]), {"op": "removeTag", "tag": "cat"}, 1)
    assert state["settings"]["showMode"] == "all" and len(state["playlist"]) == 3
    state = l3.apply_command(tag_state(["cat", "dog"]), {"op": "removeTag", "tag": "cat"}, 1)
    assert state["settings"]["showMode"] == "tags" and state["settings"]["selectedTags"] == ["dog"]


def test_create_collection_with_items_at_once():
    state = device_state(tagged(), default_settings(), ["a"], 0)
    command = {"op": "createCollection", "collectionId": "c", "name": "Море", "mediaIds": ["a"]}
    assert l2.find_collection(l3.apply_command(state, command, 1)["catalog"], "c")["mediaIds"] == ["a"]
