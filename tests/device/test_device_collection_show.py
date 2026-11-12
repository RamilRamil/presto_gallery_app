"""CollectionShowSettings: what is stored, what is refused, when it applies, and the "Показ" menu screen."""
import pytest

from gallery import l2_catalog as l2, l3_menu as menu, l3_playlist as l3, l4_codecs as l4
from gallery.model import default_settings, device_state, empty_catalog, media_item, scene_item

INFO = {"address": "192.168.1.57", "freeBytes": 1048576}
IDS = ["p%d" % n for n in range(8)]


def library():
    catalog = empty_catalog()
    for media_id in IDS:
        catalog = l2.add_item(catalog, media_item(media_id, "pic", [], 1, 60, 100, 0))
    catalog = l2.add_item(catalog, scene_item("s", "storm", [], 9, 0))
    catalog = l2.add_collection(catalog, "c", "Фото")
    return l2.add_to_collection(catalog, "c", IDS)


def showing(catalog, collection_id="c", **general):
    return dict(default_settings(), showMode="collection", selectedCollection=collection_id, **general)


def own(catalog, collection_id="c"):
    return l2.collection_show(l2.find_collection(catalog, collection_id))


# --- D2: store, clear, refuse ---

def test_a_collection_has_no_own_values_at_first():
    assert own(library()) == {"slideSeconds": None, "shuffle": None}


def test_own_values_are_stored_and_cleared_one_by_one():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60, "shuffle": True})
    assert own(catalog) == {"slideSeconds": 60, "shuffle": True}
    catalog = l2.set_collection_show(catalog, "c", {"shuffle": None})
    assert own(catalog) == {"slideSeconds": 60, "shuffle": None}
    assert "shuffle" not in l2.find_collection(catalog, "c")  # cleared means the key is gone


def test_slide_time_is_kept_within_the_general_limits():
    assert own(l2.set_collection_show(library(), "c", {"slideSeconds": 1}))["slideSeconds"] == 3
    assert own(l2.set_collection_show(library(), "c", {"slideSeconds": 9999}))["slideSeconds"] == 600


@pytest.mark.parametrize("changes", [
    {"slideSeconds": "60"}, {"slideSeconds": 1.5}, {"slideSeconds": True}, {"shuffle": 1}, {"shuffle": "yes"},
    {"brightness": 50},
])
def test_bad_values_are_refused(changes):
    with pytest.raises(ValueError):
        l2.set_collection_show(library(), "c", changes)


def test_unknown_collection_is_refused():
    with pytest.raises(KeyError):
        l2.set_collection_show(library(), "nope", {"shuffle": True})


def test_damaged_stored_values_count_as_none():
    catalog = library()
    catalog["collections"][0] = dict(catalog["collections"][0], slideSeconds="x", shuffle="maybe")
    assert own(catalog) == {"slideSeconds": None, "shuffle": None}


def test_own_values_survive_rename_adding_items_and_saving():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 30, "shuffle": False})
    catalog = l2.rename_collection(catalog, "c", "Лето")
    catalog = l2.remove_from_collection(catalog, "c", "p0")
    catalog = l4.catalog_from_json(l4.catalog_to_json(catalog))
    assert own(catalog) == {"slideSeconds": 30, "shuffle": False}


# --- D3: when own values apply ---

def test_own_values_apply_while_the_collection_is_shown():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60, "shuffle": True})
    shown = l3.show_settings(catalog, showing(catalog))
    assert shown["slideSeconds"] == 60 and shown["shuffle"] is True


def test_only_set_values_override():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60})
    settings = showing(catalog, shuffle=True)
    shown = l3.show_settings(catalog, settings)
    assert shown["slideSeconds"] == 60 and shown["shuffle"] is True


def test_without_own_values_the_general_settings_are_used_as_they_are():
    catalog, settings = library(), showing(library())
    assert l3.show_settings(catalog, settings) is settings


@pytest.mark.parametrize("mode", ["all", "images", "animations", "scenes", "tags"])
def test_other_show_modes_ignore_own_values(mode):
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60, "shuffle": True})
    settings = dict(default_settings(), showMode=mode, selectedCollection="c", selectedTags=["x"])
    assert l3.show_settings(catalog, settings) is settings


def test_own_order_decides_the_playlist():
    catalog = l2.set_collection_show(library(), "c", {"shuffle": True})
    assert l3.build_playlist(catalog, showing(catalog), 7) == l3.shuffled(IDS, 7) != IDS
    catalog = l2.set_collection_show(catalog, "c", {"shuffle": False})
    assert l3.build_playlist(catalog, showing(catalog, shuffle=True), 7) == IDS


def test_command_keeps_the_item_on_screen_and_the_general_settings():
    catalog = library()
    settings = showing(catalog)
    state = device_state(catalog, settings, l3.build_playlist(catalog, settings, 1), 3)
    state = l3.apply_command(state, {"op": "setCollectionShow", "collectionId": "c", "shuffle": True,
                                     "slideSeconds": 120}, 5)
    assert state["playlist"] == l3.shuffled(IDS, 5)
    assert state["playlist"][state["index"]] == "p3"
    assert state["settings"] is settings and settings["slideSeconds"] == 10
    assert own(state["catalog"]) == {"slideSeconds": 120, "shuffle": True}


def test_command_with_a_bad_value_changes_nothing():
    catalog = library()
    state = device_state(catalog, showing(catalog), IDS, 0)
    with pytest.raises(ValueError):
        l3.apply_command(state, {"op": "setCollectionShow", "collectionId": "c", "slideSeconds": "x"}, 1)
    assert own(state["catalog"]) == {"slideSeconds": None, "shuffle": None}


def test_deleted_collection_falls_back_to_the_general_settings():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60})
    state = device_state(catalog, showing(catalog), IDS, 0)
    state = l3.apply_command(state, {"op": "deleteCollection", "collectionId": "c"}, 1)
    assert state["settings"]["showMode"] == "all"
    assert l3.show_settings(state["catalog"], state["settings"])["slideSeconds"] == 10


# --- DeviceMenu: the "Показ" screen ---

def show_screen():
    return dict(menu.menu_open(default_settings(), "p0"), screen="collectionShow", target="c")


def view(state, catalog, settings):
    return menu.menu_view(state, catalog, settings, INFO)["cells"]


def tap(state, label, catalog, settings):
    for cell in view(state, catalog, settings):
        if cell["label"].startswith(label):
            return menu.menu_tap(state, cell["x"] + 1, cell["y"] + 1, catalog, settings, INFO)
    raise AssertionError("no cell " + label)


def labels(state, catalog, settings):
    return [c["label"] for c in view(state, catalog, settings)]


def apply(catalog, command):
    return l3.apply_command(device_state(catalog, default_settings(), IDS, 0), command, 1)["catalog"]


def test_the_card_opens_the_show_screen():
    state = dict(show_screen(), screen="collectionCard")
    state, command = tap(state, "Показ", library(), default_settings())
    assert command is None and state["screen"] == "collectionShow"


def test_without_own_time_the_general_time_is_shown_and_cannot_change():
    settings = dict(default_settings(), slideSeconds=15)
    cells = view(show_screen(), library(), settings)
    by_label = dict((c["label"], c) for c in cells)
    assert "Своё время: выкл" in by_label and "Порядок: как везде" in by_label
    assert by_label["Слайд 15 с"]["note"] == "как везде"
    assert by_label["-"]["action"] is None and by_label["+"]["action"] is None


def test_turning_own_time_on_starts_at_the_general_time_then_steps():
    catalog, settings = library(), dict(default_settings(), slideSeconds=15)
    state, command = tap(show_screen(), "Своё время", catalog, settings)
    assert command == {"op": "setCollectionShow", "collectionId": "c", "slideSeconds": 15}
    catalog = apply(catalog, command)
    assert "Своё время: вкл" in labels(state, catalog, settings)
    state, command = tap(state, "+", catalog, settings)
    assert command["slideSeconds"] == 30
    catalog = apply(catalog, command)
    state, command = tap(state, "-", catalog, settings)
    assert command["slideSeconds"] == 15
    state, command = tap(state, "Своё время", catalog, settings)
    assert command == {"op": "setCollectionShow", "collectionId": "c", "slideSeconds": None}
    assert settings["slideSeconds"] == 15  # the general time never changes here


def test_an_own_time_between_steps_moves_to_the_next_step():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 42})
    assert tap(show_screen(), "+", catalog, default_settings())[1]["slideSeconds"] == 60
    assert tap(show_screen(), "-", catalog, default_settings())[1]["slideSeconds"] == 30


def test_order_goes_round_three_values():
    catalog, settings, state = library(), default_settings(), show_screen()
    seen = []
    for _ in range(3):
        seen.append([l for l in labels(state, catalog, settings) if l.startswith("Порядок")][0])
        state, command = tap(state, "Порядок", catalog, settings)
        catalog = apply(catalog, command)
    assert seen == ["Порядок: как везде", "Порядок: по кругу", "Порядок: вперемешку"]
    assert own(catalog)["shuffle"] is None


def test_show_screen_fits_and_offers_scene_speed_only_with_scenes():
    catalog, settings = library(), default_settings()
    cells = view(show_screen(), catalog, settings)
    assert all(c["y"] + c["height"] <= 240 for c in cells)
    assert all(len(c["label"]) * 12 - 2 <= c["width"] for c in cells)
    assert not any(c["label"].startswith("Сцены") for c in cells)
    catalog = l2.add_to_collection(catalog, "c", ["s"])
    assert "Сцены: 1x" in labels(show_screen(), catalog, settings)


def test_show_screen_of_a_deleted_collection_falls_back():
    catalog = l2.remove_collection(library(), "c")
    assert menu.menu_view(show_screen(), catalog, default_settings(), INFO)["title"] == "Коллекции"


def test_general_settings_say_when_the_collection_overrides_them():
    catalog = l2.set_collection_show(library(), "c", {"slideSeconds": 60})
    state = dict(show_screen(), screen="settings")
    cells = dict((c["label"], c) for c in view(state, catalog, showing(catalog)))
    assert cells["Слайд 10 с"]["note"] == "у коллекции свои"
    assert cells["Перемешать: выкл"]["note"] is None
    cells = dict((c["label"], c) for c in view(state, catalog, default_settings()))
    assert cells["Слайд 10 с"]["note"] is None
