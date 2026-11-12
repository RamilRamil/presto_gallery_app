"""The 480 screen: pictures centred, the DeviceMenu drawn twice as large, touches mapped back to UI units."""
import pytest

from gallery import l3_menu as menu, l3_screen as screen, l5_menu
from gallery.model import default_settings, empty_catalog


class RecordingDisplay:
    def __init__(self):
        self.rects = []

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, pen):
        pass

    def clear(self):
        pass

    def rectangle(self, x, y, w, h):
        self.rects.append((x, y, w, h))


class RecordingPresto:
    def __init__(self):
        self.display = RecordingDisplay()

    def update(self):
        pass


def drawn(view, scale):
    presto = RecordingPresto()
    l5_menu.draw_menu(presto, view, scale)
    return presto.display.rects


def main_view():
    return menu.menu_view(menu.menu_open(default_settings(), None), empty_catalog(), default_settings(),
                          {"address": "-", "freeBytes": 0})


def test_screen_is_480_and_ui_units_are_half():
    assert screen.SCREEN_SIZE == 480
    assert screen.to_screen(240) == 480
    assert [screen.to_ui(p) for p in (0, 1, 2, 479)] == [0, 0, 1, 239]


@pytest.mark.parametrize("grid, offset", [(16, 0), (32, 0), (64, 16), (240, 0), (480, 0)])
def test_pictures_are_centred(grid, offset):
    assert screen.picture_margin(grid) == offset


def test_menu_on_480_is_the_240_layout_doubled():
    view = main_view()
    small, large = drawn(view, 1), drawn(view, screen.to_screen(1))
    assert large == [tuple(2 * v for v in rect) for rect in small]
    assert all(x + w <= 480 and y + h <= 480 for x, y, w, h in large)


def test_tap_in_screen_pixels_hits_the_cell_drawn_there():
    view = main_view()
    cell = next(c for c in view["cells"] if c["action"])
    x = screen.to_screen(cell["x"] + cell["width"] // 2) + 1
    y = screen.to_screen(cell["y"] + cell["height"] // 2) + 1
    tapped = menu.menu_tap(menu.menu_open(default_settings(), None), screen.to_ui(x), screen.to_ui(y),
                           empty_catalog(), default_settings(), {"address": "-", "freeBytes": 0})
    untouched = menu.menu_open(default_settings(), None)
    assert tapped != (untouched, None)
