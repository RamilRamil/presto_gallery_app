"""SceneSpeed: what is stored, what is refused, and how a Scene's pauses change."""
import time
from types import SimpleNamespace

import pytest

from gallery import l2_catalog as l2, l3_playlist as l3, l3_scene, l4_codecs as l4, l5_scene
from gallery.model import default_settings, device_state, empty_catalog, media_item, scene_item


def catalog_with_scene():
    catalog = l2.add_item(empty_catalog(), scene_item("s", "storm", [], 9, 0))
    return l2.add_item(catalog, media_item("p", "pic", [], 1, 60, 100, 0))


# --- a Collection sets the speed of its Scenes ---

def catalog_with_collection(members=("s", "t", "p")):
    catalog = l2.add_item(catalog_with_scene(), scene_item("t", "watch", [], 9, 0))
    catalog = l2.add_item(catalog, scene_item("out", "outside", [], 9, 0))
    catalog = l2.add_collection(catalog, "c", "Вечер")
    return l2.add_to_collection(catalog, "c", list(members))


def speeds(catalog):
    return dict((i["mediaId"], l2.item_speed(i)) for i in catalog["items"] if i["kind"] == "scene")


def test_collection_speed_reaches_its_scenes_only():
    catalog = l2.set_collection_speed(catalog_with_collection(), "c", 200)
    assert speeds(catalog) == {"s": 200, "t": 200, "out": 100}
    assert "speedPercent" not in l2.find_item(catalog, "p")


def test_collection_speed_keeps_a_scene_flagged():
    catalog = l2.set_flag(catalog_with_collection(), "s", True, "boom")
    catalog = l2.set_collection_speed(catalog, "c", 50)
    scene = l2.find_item(catalog, "s")
    assert l2.item_speed(scene) == 50 and scene["flagged"] and scene["error"] == "boom"


@pytest.mark.parametrize("percent", [0, 75, 800, "200", None])
def test_collection_speed_refuses_an_unknown_value(percent):
    with pytest.raises(ValueError):
        l2.set_collection_speed(catalog_with_collection(), "c", percent)


def test_collection_speed_refuses_a_collection_without_scenes():
    with pytest.raises(ValueError):
        l2.set_collection_speed(catalog_with_collection(["p"]), "c", 200)


def test_collection_speed_refuses_an_unknown_collection():
    with pytest.raises(KeyError):
        l2.set_collection_speed(catalog_with_collection(), "nope", 200)


def test_common_speed_is_shared_or_none():
    catalog = catalog_with_collection()
    assert l2.common_speed(l2.collection_scenes(catalog, "c")) == 100
    catalog = l2.set_speed(catalog, "s", 400)
    assert l2.common_speed(l2.collection_scenes(catalog, "c")) is None
    assert l2.common_speed([]) is None


def test_set_collection_speed_command_survives_the_catalog_file():
    state = device_state(catalog_with_collection(), default_settings(), [], 0)
    state = l3.apply_command(state, {"op": "setCollectionSpeed", "collectionId": "c", "speedPercent": 400}, 1)
    loaded = l4.catalog_from_json(l4.catalog_to_json(state["catalog"]))
    assert speeds(loaded) == {"s": 400, "t": 400, "out": 100}


def test_a_refused_collection_speed_changes_nothing():
    before = device_state(catalog_with_collection(), default_settings(), [], 0)
    with pytest.raises(ValueError):
        l3.apply_command(before, {"op": "setCollectionSpeed", "collectionId": "c", "speedPercent": 75}, 1)
    assert speeds(before["catalog"]) == {"s": 100, "t": 100, "out": 100}


# --- what is stored ---

def test_new_and_old_scenes_play_at_the_default():
    assert l2.item_speed(scene_item("s", "n", [], 9, 0)) == 100
    assert "speedPercent" not in scene_item("s", "n", [], 9, 0)


@pytest.mark.parametrize("stored", [33, "fast", None, 0])
def test_a_damaged_stored_speed_plays_at_the_default(stored):
    assert l2.item_speed(dict(scene_item("s", "n", [], 9, 0), speedPercent=stored)) == 100


@pytest.mark.parametrize("percent", [25, 50, 100, 200, 400])
def test_set_speed_survives_the_catalog_file(percent):
    catalog = l2.set_speed(catalog_with_scene(), "s", percent)
    loaded = l4.catalog_from_json(l4.catalog_to_json(catalog))
    assert l2.item_speed(l2.find_item(loaded, "s")) == percent


@pytest.mark.parametrize("percent", [0, 75, 800, "200", None])
def test_set_speed_refuses_an_unknown_value(percent):
    with pytest.raises(ValueError):
        l2.set_speed(catalog_with_scene(), "s", percent)


def test_set_speed_is_for_scenes_only():
    with pytest.raises(ValueError):
        l2.set_speed(catalog_with_scene(), "p", 200)
    with pytest.raises(KeyError):
        l2.set_speed(catalog_with_scene(), "missing", 200)


def test_edit_item_with_a_bad_speed_changes_nothing():
    catalog = catalog_with_scene()
    state = device_state(catalog, default_settings(), ["s"], 0)
    with pytest.raises(ValueError):
        l3.apply_command(state, {"op": "editItem", "mediaId": "s", "name": "new", "speedPercent": 75}, 1)
    assert l2.find_item(state["catalog"], "s")["name"] == "storm"


def test_edit_item_sets_the_speed():
    state = device_state(catalog_with_scene(), default_settings(), ["s"], 0)
    changed = l3.apply_command(state, {"op": "editItem", "mediaId": "s", "speedPercent": 400}, 1)
    assert l2.item_speed(l2.find_item(changed["catalog"], "s")) == 400


# --- arithmetic and labels ---

@pytest.mark.parametrize("percent, expected", [(25, 400), (50, 200), (100, 100), (200, 50), (400, 25)])
def test_paced_ms_divides_by_the_speed(percent, expected):
    assert l3_scene.paced_ms(100, percent) == expected


@pytest.mark.parametrize("percent, label", [(25, "0.25x"), (50, "0.5x"), (100, "1x"), (200, "2x"), (400, "4x")])
def test_speed_label(percent, label):
    assert l3_scene.speed_label(percent) == label


# --- pausing ---

@pytest.fixture
def clock(monkeypatch):
    slept = []
    fake = SimpleNamespace(sleep=lambda seconds: slept.append(round(seconds * 1000)),
                           sleep_ms=lambda ms: None, ticks_ms=lambda: 77, slept=slept)
    monkeypatch.setattr(l5_scene, "time", fake)
    return fake


def never():
    return False


def test_default_speed_leaves_the_scene_alone(clock):
    namespace = {"time": clock, "nap": clock.sleep}
    l5_scene.pace_scene(namespace, 100, never)
    assert namespace["time"] is clock and namespace["nap"] is clock.sleep


def test_module_under_any_name_is_paced_and_keeps_other_functions(clock):
    namespace = {"t": clock}
    l5_scene.pace_scene(namespace, 200, never)
    namespace["t"].sleep(0.1)
    assert clock.slept == [50]
    assert namespace["t"].ticks_ms() == 77


def test_directly_imported_sleep_is_paced(clock):
    namespace = {"sleep": clock.sleep}
    l5_scene.pace_scene(namespace, 400, never)
    namespace["sleep"](0.1)
    assert clock.slept == [25]


def test_other_names_are_not_touched(clock):
    namespace = {"frames": 5, "run": print}
    l5_scene.pace_scene(namespace, 200, never)
    assert namespace == {"frames": 5, "run": print}


def test_a_long_pause_keeps_calling_stop(clock):
    stops = []

    def stop():
        stops.append(1)
        return False

    namespace = {"time": clock}
    l5_scene.pace_scene(namespace, 25, stop)
    namespace["time"].sleep(0.1)  # 400 ms at 0.25x
    assert clock.slept == [100, 100, 100, 100]
    assert len(stops) == 3


def test_a_long_pause_ends_when_the_scene_must_stop(clock):
    namespace = {"time": clock}
    l5_scene.pace_scene(namespace, 25, lambda: True)
    namespace["time"].sleep(0.5)
    assert clock.slept == [100]


@pytest.mark.parametrize("percent, expected", [(100, 100), (200, 50)])
def test_run_scene_paces_an_unchanged_scene_file(tmp_path, monkeypatch, percent, expected):
    path = tmp_path / "scene.py"
    path.write_text("import time\n\ndef run(stop):\n    time.sleep(0.1)\n")
    slept = []
    monkeypatch.setattr(time, "sleep", lambda seconds: slept.append(round(seconds * 1000)))
    assert l5_scene.run_scene(str(path), never, percent) is None
    assert slept == [expected]
