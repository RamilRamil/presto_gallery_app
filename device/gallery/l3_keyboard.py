# LAYER 3 (calculations): the OnScreenKeyboard as data, drawn with the same cells as the menu.

from .l3_menu_cells import BAR_TOP, CHARS_IN_TITLE, LIST_TOP, ROW_HEIGHT, ROW_STEP, action_at, cell

COLUMNS = 6
KEY_SIZE = 40
PAGES = (
    ("а-ц", "абвгдеёжзийклмнопрстуфхц"),
    ("ч-я", "чшщъыьэюя0123456789-_.,!"),
    ("a-x", "abcdefghijklmnopqrstuvwx"),
    ("y-z", "yz0123456789-_.,!"),
)


def keyboard_open(prompt, text, limit, purpose):
    return {"prompt": prompt, "text": text, "limit": limit, "purpose": purpose, "page": 0, "message": None}


def keyboard_view(keyboard):
    """{title, cells}, like a menu screen."""
    text = keyboard["text"]
    title = keyboard["message"] or (text[-(CHARS_IN_TITLE - 1):] + "_" if text else keyboard["prompt"])
    page = keyboard["page"]
    cells = [cell(i % COLUMNS * KEY_SIZE, LIST_TOP + i // COLUMNS * ROW_STEP, KEY_SIZE, KEY_SIZE, char, ("key", char))
             for i, char in enumerate(PAGES[page][1])]
    next_page = (page + 1) % len(PAGES)
    cells += [
        cell(2, BAR_TOP, 56, ROW_HEIGHT, PAGES[next_page][0], ("page", next_page)),
        cell(62, BAR_TOP, 56, ROW_HEIGHT, "___", ("key", " ")),
        cell(122, BAR_TOP, 56, ROW_HEIGHT, "<", ("erase", None)) if text
        else cell(122, BAR_TOP, 56, ROW_HEIGHT, "Отм", ("cancel", None)),
        cell(182, BAR_TOP, 56, ROW_HEIGHT, "ОК", ("done", None)),
    ]
    return {"title": title, "cells": cells}


def keyboard_tap(keyboard, x, y):
    """(keyboard, "done" | "cancel" | None)."""
    action = action_at(keyboard_view(keyboard)["cells"], x, y)
    if action is None:
        return keyboard, None
    kind, value = action
    if kind in ("done", "cancel"):
        return keyboard, kind
    keyboard = dict(keyboard, message=None)
    if kind == "page":
        return dict(keyboard, page=value), None
    if kind == "erase":
        return dict(keyboard, text=keyboard["text"][:-1]), None
    if len(keyboard["text"]) >= keyboard["limit"]:
        return keyboard, None
    return dict(keyboard, text=keyboard["text"] + value), None
