# LAYER 3 (calculations): one finger movement as data. Layer 5 samples the screen and feeds these
# functions; the decision about what the finger did is made only here.

from .l3_playlist import brightness_step

TAP = "tap"
SWIPE_LEFT = "swipeLeft"
SWIPE_RIGHT = "swipeRight"
SWIPE_UP = "swipeUp"
SWIPE_DOWN = "swipeDown"
TAP_SLOP = 20         # px: moving further means this press is no longer a tap or a long press
SWIPE_MIN = 40        # px: the shortest movement that counts as a swipe
LONG_PRESS_MS = 1000


def press_start(x, y):
    return {"startX": x, "startY": y, "x": x, "y": y, "moved": False, "heldMs": 0}


def press_move(press, x, y, held_ms):
    moved = press["moved"] or max(abs(x - press["startX"]), abs(y - press["startY"])) > TAP_SLOP
    return dict(press, x=x, y=y, moved=moved, heldMs=held_ms)


def is_long_press(press):
    return not press["moved"] and press["heldMs"] >= LONG_PRESS_MS


def press_end(press):
    """The Gesture, or None for a movement between a tap and a swipe."""
    if not press["moved"]:
        return TAP
    dx, dy = press["x"] - press["startX"], press["y"] - press["startY"]
    if max(abs(dx), abs(dy)) < SWIPE_MIN:
        return None
    if abs(dx) >= abs(dy):
        return SWIPE_LEFT if dx < 0 else SWIPE_RIGHT
    return SWIPE_UP if dy < 0 else SWIPE_DOWN


def gesture_command(gesture, settings):
    """The apply_command command of a swipe; None for anything else."""
    if gesture == SWIPE_LEFT:
        return {"op": "next"}
    if gesture == SWIPE_RIGHT:
        return {"op": "prev"}
    if gesture in (SWIPE_UP, SWIPE_DOWN):
        direction = 1 if gesture == SWIPE_UP else -1
        return {"op": "setBrightness", "level": brightness_step(settings["brightness"], direction)}
    return None
