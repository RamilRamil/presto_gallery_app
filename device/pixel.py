# LAYER 5 (actions): drawing helpers for Scenes (docs/scene-format.md).
# Same names as the old pixel.py, but bound to the app's Presto and stretched over the whole screen.

from gallery.l3_scene import scene_rect

GRID = 32
SCREEN = 240

presto = None
display = None


def bind(shared_presto):
    global presto, display
    presto = shared_presto
    display = shared_presto.display


def make_pen(red, green, blue):
    return display.create_pen(red, green, blue)


def block(x, y, w, h, pen):
    left, top, width, height = scene_rect(x, y, w, h, GRID, SCREEN)
    display.set_pen(pen)
    display.rectangle(left, top, width, height)


def pix(x, y, pen):
    block(x, y, 1, 1, pen)
