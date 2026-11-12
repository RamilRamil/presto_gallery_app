"""AmbientLeds: the DeviceSettings value, how setSettings treats it, and the "Подсветка" menu row."""
import pytest

from gallery import l2_catalog as l2, l3_menu as menu, l3_playlist as l3, l4_codecs as l4
from gallery.model import default_settings, device_state, empty_catalog, media_item

INFO = {"address": "192.168.1.57", "freeBytes": 1048576}


def playing(**settings):
    catalog = empty_catalog()
    for n in range(6):
        catalog = l2.add_item(catalog, media_item("p%d" % n, "pic", [], 1, 60, 100, 0))
    state = device_state(catalog, dict(default_settings(), shuffle=True, **settings), [], 0)
    state = l3.apply_command(state, {"op": "setSettings", "settings": state["settings"]}, 1)
    return l3.apply_command(state, {"op": "next"}, 2)


def leds_row(settings):
    view = menu.menu_view(dict(menu.menu_open(settings), screen="settings"), empty_catalog(), settings, INFO)
    return [c for c in view["cells"] if c["label"].startswith("Подсветка")]


# --- data and validation ---

def test_leds_are_on_by_default_and_in_an_old_settings_file():
    assert default_settings()["ambientLeds"] is True
    assert l3.validate_settings({})["ambientLeds"] is True
    assert l3.validate_settings(l4.settings_from_json('{"slideSeconds": 30}'))["ambientLeds"] is True


def test_off_is_stored_and_read_back():
    settings = l3.validate_settings(dict(default_settings(), ambientLeds=False))
    assert l3.validate_settings(l4.settings_from_json(l4.settings_to_json(settings)))["ambientLeds"] is False


@pytest.mark.parametrize("bad", [1, 0, "true", None])
def test_only_true_or_false_is_accepted(bad):
    with pytest.raises(ValueError):
        l3.validate_settings({"ambientLeds": bad})


# --- setSettings ---

def test_settings_without_the_led_value_keep_it():
    state = playing(ambientLeds=False)
    changed = l3.apply_command(state, {"op": "setSettings", "settings": {"slideSeconds": 30}}, 3)
    assert changed["settings"]["ambientLeds"] is False and changed["settings"]["slideSeconds"] == 30


def test_start_builds_the_playlist_from_the_saved_settings():
    """At start the app applies the saved settings to an empty Playlist; equal settings must still build it."""
    state = playing()
    assert sorted(state["playlist"]) == ["p%d" % n for n in range(6)]


def test_switching_the_leds_keeps_the_playlist_and_the_item_on_screen():
    state = playing()
    assert state["playlist"]
    changed = l3.apply_command(state, {"op": "setSettings",
                                       "settings": dict(state["settings"], ambientLeds=False)}, 99)
    assert changed["settings"]["ambientLeds"] is False
    assert changed["playlist"] is state["playlist"] and changed["index"] == state["index"]


def test_other_changes_still_rebuild_the_playlist():
    state = playing()
    changed = l3.apply_command(state, {"op": "setSettings",
                                       "settings": dict(state["settings"], ambientLeds=False, shuffle=False)}, 99)
    assert changed["playlist"] is not state["playlist"] and changed["settings"]["shuffle"] is False


def test_quiet_change_is_true_only_for_brightness_and_leds():
    settings = default_settings()
    assert l3.quiet_change(settings, dict(settings, ambientLeds=False, brightness=25))
    assert not l3.quiet_change(settings, dict(settings, ambientLeds=False, slideSeconds=30))


# --- device menu ---

def test_settings_screen_has_the_leds_row():
    on = leds_row(default_settings())
    off = leds_row(dict(default_settings(), ambientLeds=False))
    assert [c["label"] for c in on] == ["Подсветка: вкл"] and on[0]["action"] == ("ambientLeds", None)
    assert [c["label"] for c in off] == ["Подсветка: выкл"]


def test_a_tap_on_the_leds_row_switches_them_and_keeps_the_menu_open():
    settings = default_settings()
    state = dict(menu.menu_open(settings), screen="settings")
    row = leds_row(settings)[0]
    following, command = menu.menu_tap(state, row["x"] + 5, row["y"] + 5, empty_catalog(), settings, INFO)
    assert following == state
    assert command == {"op": "setSettings", "settings": dict(settings, ambientLeds=False)}


def test_settings_screen_still_fits_above_the_back_bar():
    view = menu.menu_view(dict(menu.menu_open(default_settings()), screen="settings"),
                          empty_catalog(), default_settings(), INFO)
    rows = [c for c in view["cells"] if c["label"] != "Назад"]
    assert max(c["y"] + c["height"] for c in rows) <= view["cells"][-1]["y"]
