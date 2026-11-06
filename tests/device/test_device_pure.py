import struct

import pytest

from gallery import l1_primitives as l1
from gallery import l2_catalog as l2
from gallery import l3_playlist as l3
from gallery import l4_codecs as l4
from gallery.model import default_settings, device_state, empty_catalog, media_item


def item(media_id, frames=1, tags=(), name="pic"):
    return media_item(media_id, name, tags, frames, 32, 1090, 0)


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
        [(15, 0), (7, 8), (3, 24)]


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
    assert s == {"showMode": "tags", "selectedTags": ["cats"], "slideSeconds": 3, "shuffle": False}
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
                         palette, frames, 240 // grid, 0)
    body = bytes(range(3 * palette)) + b"".join(
        struct.pack("<H", 100 * (i + 1)) + bytes(grid * grid) for i in range(frames))
    return header + body


def test_parse_bin_header_and_offsets():
    data = make_bin(16, 2, 3)
    header = l4.parse_bin_header(data)
    assert header["frameCount"] == 3 and header["cellSize"] == 15
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
