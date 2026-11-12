# LAYER 5 (actions): draws the DeviceMenu and reads the touch screen for it.

import asyncio

from .l3_menu import glyph_rows, menu_open, menu_rejected, menu_tap, menu_timeout_ms, menu_view, text_size
from .l3_playlist import allocate_collection_id
from .l3_screen import to_screen, to_ui
from .l5_clock import ticks_diff, ticks_ms

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


def draw_menu(presto, view, scale=to_screen(1)):
    """The view is laid out in UI units; every length is multiplied by scale on the screen."""
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
    draw_text(display, view["title"], 4 * scale, 6 * scale, LABEL_SCALE * scale)
    for cell in view["cells"]:
        display.set_pen(marked if cell["marked"] else button if cell["action"] else idle)
        display.rectangle((cell["x"] + 1) * scale, cell["y"] * scale, (cell["width"] - 2) * scale,
                          cell["height"] * scale)
        display.set_pen(white if cell["action"] or cell["marked"] or cell["info"] else grey)
        width, height = text_size(cell["label"], LABEL_SCALE)
        note = cell["note"]
        top = cell["y"] + (cell["height"] - height) // 2 - (5 if note else 0)
        draw_text(display, cell["label"], (cell["x"] + (cell["width"] - width) // 2) * scale, top * scale,
                  LABEL_SCALE * scale)
        if note:
            width, _ = text_size(note, NOTE_SCALE)
            draw_text(display, note, (cell["x"] + (cell["width"] - width) // 2) * scale,
                      (top + height + 3) * scale, NOTE_SCALE * scale)
    presto.update()


async def wait_release(touch):
    while True:
        touch.poll()
        if not touch.state:
            return
        await asyncio.sleep(0.02)


def apply_menu_command(app, command, closing):
    """A new Collection gets its id here; choosing what to show from the menu ends the Pause."""
    if command["op"] == "createCollection":
        command = dict(command, collectionId=allocate_collection_id(app.state["catalog"], ticks_ms()))
    app.change(command)
    if closing and command["op"] == "setSettings":
        app.paused = False


async def run_menu(app):
    """Show the menu until it is closed or left alone; settings go through app.change."""
    touch = app.presto.touch
    await wait_release(touch)
    playlist, index = app.state["playlist"], app.state["index"]
    menu = menu_open(app.state["settings"], playlist[index] if playlist else None)

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
            x, y = to_ui(touch.x), to_ui(touch.y)
            await wait_release(touch)
            following, command = menu_tap(menu, x, y, app.state["catalog"], app.state["settings"], info())
            if command is not None:
                try:
                    apply_menu_command(app, command, following is None)
                except (ValueError, KeyError, OSError) as error:
                    print("menu change refused:", error)
                    following = menu_rejected(menu)
            menu = following
            if menu is not None:
                redraw()
            last_touch = ticks_ms()
        elif ticks_diff(ticks_ms(), last_touch) >= menu_timeout_ms(menu):
            return
        await asyncio.sleep(0.03)
