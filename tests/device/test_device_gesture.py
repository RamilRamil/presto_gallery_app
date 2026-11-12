"""Gesture classification and what each swipe does: pure logic, no hardware."""
import pytest

from gallery import l3_gesture as g
from gallery.model import default_settings


def path(*points):
    """A press through (x, y, held_ms) points."""
    press = g.press_start(points[0][0], points[0][1])
    for x, y, held in points[1:]:
        press = g.press_move(press, x, y, held)
    return press


@pytest.mark.parametrize("end, expected", [
    ((60, 120), g.SWIPE_LEFT), ((180, 120), g.SWIPE_RIGHT), ((120, 60), g.SWIPE_UP), ((120, 180), g.SWIPE_DOWN),
])
def test_swipes_in_four_directions(end, expected):
    assert g.press_end(path((120, 120, 0), (end[0], end[1], 150))) == expected


def test_a_still_finger_is_a_tap_even_with_jitter():
    assert g.press_end(path((120, 120, 0), (128, 115, 60), (124, 122, 120))) == g.TAP


def test_diagonal_counts_along_the_longer_direction():
    assert g.press_end(path((120, 120, 0), (60, 90, 100))) == g.SWIPE_LEFT
    assert g.press_end(path((120, 120, 0), (140, 200, 100))) == g.SWIPE_DOWN


def test_movement_between_tap_and_swipe_does_nothing():
    assert g.press_end(path((120, 120, 0), (150, 120, 100))) is None


def test_long_press_needs_a_still_finger_for_a_second():
    assert not g.is_long_press(path((120, 120, 0), (121, 120, 999)))
    assert g.is_long_press(path((120, 120, 0), (121, 120, 1000)))


def test_slow_swipe_is_never_a_long_press_and_stays_a_swipe():
    press = path((200, 120, 0), (170, 120, 900), (160, 120, 1500), (80, 120, 2500))
    assert not g.is_long_press(press)
    assert g.press_end(press) == g.SWIPE_LEFT


def test_returning_to_the_start_does_not_make_a_tap_or_a_long_press():
    press = path((120, 120, 0), (180, 120, 300), (120, 120, 1200))
    assert not g.is_long_press(press)
    assert g.press_end(press) is None


def test_swipe_commands():
    settings = dict(default_settings(), brightness=50)
    assert g.gesture_command(g.SWIPE_LEFT, settings) == {"op": "next"}
    assert g.gesture_command(g.SWIPE_RIGHT, settings) == {"op": "prev"}
    assert g.gesture_command(g.SWIPE_UP, settings) == {"op": "setBrightness", "level": 75}
    assert g.gesture_command(g.SWIPE_DOWN, settings) == {"op": "setBrightness", "level": 25}
    assert g.gesture_command(g.TAP, settings) is None
    assert g.gesture_command(None, settings) is None
