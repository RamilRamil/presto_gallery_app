# LAYER 5 (actions): draws the DeviceMenu and reads the touch screen for it.

import asyncio

from .l3_menu import glyph_rows, menu_open, menu_tap, menu_view, text_size
from .l5_clock import ticks_diff, ticks_ms

MENU_TIMEOUT_MS = 20000
LABEL_SCALE = 2
NOTE_SCALE = 1


def draw_text(display, text, x, y, scale):
    """Draw with our font using the current pen; one rectangle per run of set bits in a row."""
    for char in text:
        for row, bits in enumerate(glyph_rows(char)):
            column = 0
            while column < 5:
                if bits & (0x10 >> column):
                    start = column
                    while column < 5 and bits & (0x10 >> column):
                        column += 1
                    display.rectangle(x + start * scale, y + row * scale, (column - start) * scale, scale)
                else:
                    column += 1
        x += 6 * scale


def draw_menu(presto, view):
    display = presto.display
    background = display.create_pen(8, 10, 20)
    button = display.create_pen(38, 46, 78)
    marked = display.create_pen(190, 70, 50)
    idle = display.create_pen(22, 24, 36)
    white = display.create_pen(240, 240, 245)
    grey = display.create_pen(120, 122, 134)
    display.set_pen(background)
    display.clear()
    display.set_pen(white)
    draw_text(display, view["title"], 4, 6, LABEL_SCALE)
    for cell in view["cells"]:
        display.set_pen(marked if cell["marked"] else button if cell["action"] else idle)
        display.rectangle(cell["x"], cell["y"], cell["width"], cell["height"])
        display.set_pen(white if cell["action"] or cell["marked"] or cell["info"] else grey)
        width, height = text_size(cell["label"], LABEL_SCALE)
        note = cell["note"]
        top = cell["y"] + (cell["height"] - height) // 2 - (5 if note else 0)
        draw_text(display, cell["label"], cell["x"] + (cell["width"] - width) // 2, top, LABEL_SCALE)
        if note:
            width, _ = text_size(note, NOTE_SCALE)
            draw_text(display, note, cell["x"] + (cell["width"] - width) // 2, top + height + 3, NOTE_SCALE)
    presto.update()


async def wait_release(touch):
    while True:
        touch.poll()
        if not touch.state:
            return
        await asyncio.sleep(0.02)


async def run_menu(app):
    """Show the menu until it is closed or left alone; settings go through app.change."""
    touch = app.presto.touch
    await wait_release(touch)
    menu = menu_open(app.state["settings"])

    def info():
        status = app.status()
        return {"address": status["ip"] or "нет Wi-Fi", "freeBytes": status["storage"]["free"]}

    def redraw():
        draw_menu(app.presto, menu_view(menu, app.state["catalog"], app.state["settings"], info()))

    redraw()
    last_touch = ticks_ms()
    while menu is not None:
        touch.poll()
        if touch.state:
            x, y = touch.x, touch.y
            await wait_release(touch)
            menu, settings = menu_tap(menu, x, y, app.state["catalog"], app.state["settings"], info())
            if settings is not None:
                app.change({"op": "setSettings", "settings": settings})
            if menu is not None:
                redraw()
            last_touch = ticks_ms()
        elif ticks_diff(ticks_ms(), last_touch) >= MENU_TIMEOUT_MS:
            return
        await asyncio.sleep(0.03)
