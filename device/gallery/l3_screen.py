# LAYER 3 (calculations): where pictures and the DeviceMenu sit on the Presto screen.
# The DeviceMenu and Gestures are laid out in UI units; layer 5 converts them to screen pixels here.

from .l1_primitives import PRESTO_SCREEN_SIZE, UI_SCALE, screen_offset

SCREEN_SIZE = PRESTO_SCREEN_SIZE


def picture_margin(grid_size):
    """Top-left margin in pixels that centres a picture of this grid on the screen."""
    return screen_offset(grid_size, SCREEN_SIZE)


def to_screen(units):
    """UI units -> screen pixels."""
    return units * UI_SCALE


def to_ui(pixels):
    """Screen pixels from the touch panel -> UI units."""
    return pixels // UI_SCALE
