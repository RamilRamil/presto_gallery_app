# LAYER 3 (calculations): the DeviceMenu as data. A menu is {screen, page, tags}; menu_view turns it
# into a title and cells, menu_tap turns a touch into the next menu and optional new settings.

from .l1_font import GLYPH_HEIGHT, GLYPH_WIDTH, fit_text, glyph_rows  # glyph_rows: used by layer 5
from .l2_catalog import all_tags, filter_by_mode

SCREEN = 240
LIST_TOP = 28
ROW_STEP = 42
ROW_HEIGHT = 40
BAR_TOP = 198
ROWS_PER_PAGE = 4
CHARS_PER_ROW = 18
SLIDE_STEPS = (3, 5, 10, 15, 30, 60, 120, 300, 600)
MODES = (("all", "Всё"), ("images", "Картинки"), ("animations", "Гифки"), ("scenes", "Сцены"))


def menu_open(settings):
    return {"screen": "main", "page": 0, "tags": list(settings["selectedTags"])}


def _cell(x, y, width, height, label, action=None, marked=False, note=None, info=False):
    """`info` is a line to read, not a button; it stays bright although it cannot be pressed."""
    return {"x": x, "y": y, "width": width, "height": height, "label": label, "action": action,
            "marked": marked, "note": note, "info": info}


def _named(name, suffix):
    return fit_text(name, CHARS_PER_ROW - len(suffix)) + suffix


def _bar(page, pages):
    return [
        _cell(2, BAR_TOP, 56, ROW_HEIGHT, "<", ("page", -1) if page > 0 else None),
        _cell(62, BAR_TOP, 116, ROW_HEIGHT, "Назад", ("back", None)),
        _cell(182, BAR_TOP, 56, ROW_HEIGHT, ">", ("page", 1) if page < pages - 1 else None),
    ]


def _paged(rows, page, per_page):
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = min(page, pages - 1)
    return rows[page * per_page: (page + 1) * per_page], page, pages


def _main_view(catalog, settings):
    def count(mode):
        return len(filter_by_mode(catalog, mode, [], None))

    def note(amount):
        return str(amount) if amount else "пусто"

    current = settings["showMode"]
    entries = []
    for mode, label in MODES:
        amount = count(mode)
        entries.append((label, ("mode", mode) if amount else None, current == mode, note(amount)))
    amount = len(catalog["collections"])
    entries.append(("Коллекции", ("open", "collections") if amount else None,
                    current == "collection", note(amount)))
    amount = len(all_tags(catalog))
    entries.append(("Теги", ("open", "tags") if amount else None, current == "tags", note(amount)))
    entries.append(("Настройки", ("open", "settings"), False, None))
    entries.append(("Закрыть", ("close", None), False, None))
    cells = [_cell(2 + (i % 2) * 120, LIST_TOP + (i // 2) * 52, 116, 48, label, action, marked, text)
             for i, (label, action, marked, text) in enumerate(entries)]
    return {"title": "Что показывать", "cells": cells}


def _collections_view(menu, catalog, settings):
    shown, page, pages = _paged(catalog["collections"], menu["page"], ROWS_PER_PAGE)
    selected = settings["selectedCollection"] if settings["showMode"] == "collection" else None
    cells = []
    for i, collection in enumerate(shown):
        amount = len(filter_by_mode(catalog, "collection", [], collection["collectionId"]))
        suffix = " (%d)" % amount if amount else " пусто"
        action = ("collection", collection["collectionId"]) if amount else None
        cells.append(_cell(2, LIST_TOP + i * ROW_STEP, 236, ROW_HEIGHT,
                           _named(collection["name"], suffix), action,
                           collection["collectionId"] == selected))
    return {"title": "Коллекции", "cells": cells + _bar(page, pages)}


def _tags_view(menu, catalog):
    per_page = ROWS_PER_PAGE - 1
    shown, page, pages = _paged(all_tags(catalog), menu["page"], per_page)
    cells = []
    for i, tag in enumerate(shown):
        cells.append(_cell(2, LIST_TOP + i * ROW_STEP, 236, ROW_HEIGHT,
                           _named(tag["label"], " (%d)" % tag["count"]),
                           ("toggleTag", tag["label"]), tag["label"] in menu["tags"]))
    count = len(menu["tags"])
    cells.append(_cell(2, LIST_TOP + per_page * ROW_STEP, 236, ROW_HEIGHT, "Показать (%d)" % count,
                       ("showTags", None) if count else None))
    return {"title": "Теги", "cells": cells + _bar(page, pages)}


def _settings_view(settings, info):
    seconds = settings["slideSeconds"]
    cells = [
        _cell(2, LIST_TOP, 50, ROW_HEIGHT, "-", ("slide", -1) if seconds > SLIDE_STEPS[0] else None),
        _cell(56, LIST_TOP, 128, ROW_HEIGHT, "Слайд %d с" % seconds, info=True),
        _cell(188, LIST_TOP, 50, ROW_HEIGHT, "+", ("slide", 1) if seconds < SLIDE_STEPS[-1] else None),
        _cell(2, LIST_TOP + ROW_STEP, 236, ROW_HEIGHT,
              "Перемешать: " + ("вкл" if settings["shuffle"] else "выкл"), ("shuffle", None)),
        _cell(2, LIST_TOP + 2 * ROW_STEP, 236, ROW_HEIGHT, fit_text(info["address"], CHARS_PER_ROW),
              info=True),
        _cell(2, LIST_TOP + 3 * ROW_STEP, 236, ROW_HEIGHT,
              "Свободно %.1f МБ" % (info["freeBytes"] / 1048576), info=True),
    ]
    return {"title": "Настройки", "cells": cells + [_cell(62, BAR_TOP, 116, ROW_HEIGHT, "Назад", ("back", None))]}


def menu_view(menu, catalog, settings, info):
    """{title, cells}; a cell without an action is shown but cannot be pressed."""
    screen = menu["screen"]
    if screen == "main":
        return _main_view(catalog, settings)
    if screen == "collections":
        return _collections_view(menu, catalog, settings)
    if screen == "tags":
        return _tags_view(menu, catalog)
    return _settings_view(settings, info)


def _step_slide(seconds, direction):
    if direction > 0:
        for step in SLIDE_STEPS:
            if step > seconds:
                return step
        return SLIDE_STEPS[-1]
    for step in reversed(SLIDE_STEPS):
        if step < seconds:
            return step
    return SLIDE_STEPS[0]


def _apply_action(menu, kind, value, settings):
    if kind == "close":
        return None, None
    if kind == "back":
        return dict(menu, screen="main", page=0), None
    if kind == "open":
        return dict(menu, screen=value, page=0), None
    if kind == "page":
        return dict(menu, page=menu["page"] + value), None
    if kind == "mode":
        return None, dict(settings, showMode=value)
    if kind == "collection":
        return None, dict(settings, showMode="collection", selectedCollection=value)
    if kind == "toggleTag":
        tags = [t for t in menu["tags"] if t != value]
        if len(tags) == len(menu["tags"]):
            tags.append(value)
        return dict(menu, tags=tags), None
    if kind == "showTags":
        return None, dict(settings, showMode="tags", selectedTags=list(menu["tags"]))
    if kind == "slide":
        return menu, dict(settings, slideSeconds=_step_slide(settings["slideSeconds"], value))
    if kind == "shuffle":
        return menu, dict(settings, shuffle=not settings["shuffle"])
    raise ValueError("unknown menu action " + kind)


def menu_tap(menu, x, y, catalog, settings, info):
    """Returns (next menu or None when closed, new settings or None)."""
    for cell in menu_view(menu, catalog, settings, info)["cells"]:
        if cell["action"] and cell["x"] <= x < cell["x"] + cell["width"] \
                and cell["y"] <= y < cell["y"] + cell["height"]:
            return _apply_action(menu, cell["action"][0], cell["action"][1], settings)
    return menu, None


def text_size(text, scale):
    """Width and height in pixels of text drawn with the 5x7 font."""
    return len(text) * (GLYPH_WIDTH + 1) * scale - scale if text else 0, GLYPH_HEIGHT * scale
