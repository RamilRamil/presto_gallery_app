# LAYER 3 (calculations): the DeviceMenu as data. A menu is plain data; menu_view turns it into a
# title and cells, menu_tap turns a touch into the next menu and an optional apply_command command.

from .l1_font import GLYPH_HEIGHT, GLYPH_WIDTH, fit_text, glyph_rows  # glyph_rows: used by layer 5
from .l2_catalog import all_tags, filter_by_mode
from .l3_menu_cells import (
    CHARS_PER_ROW, LIST_TOP, ROW_HEIGHT, ROW_STEP, ROWS_PER_PAGE, action_at, back_bar, cell, named,
    page_bar, paged, slide_cells, step_slide,
)
from .l3_playlist import show_settings
from .l3_menu_library import (
    BACK_TO, LIBRARY_SCREENS, library_action, library_keyboard_tap, library_settled, library_view, menu_rejected,
)

MENU_TIMEOUT_MS = 20000
LIBRARY_TIMEOUT_MS = 60000
MODES = (("all", "Всё"), ("images", "Картинки"), ("animations", "Гифки"), ("scenes", "Сцены"))


def menu_open(settings, media_id=None):
    """`media_id` is the item on the screen, the one "Эта картинка" changes."""
    return {"screen": "main", "page": 0, "tags": list(settings["selectedTags"]), "mediaId": media_id,
            "target": None, "known": [], "keyboard": None}


def menu_timeout_ms(menu):
    return LIBRARY_TIMEOUT_MS if menu["keyboard"] or menu["screen"] in LIBRARY_SCREENS else MENU_TIMEOUT_MS


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
    entries.append(("Ещё", ("open", "more"), False, None))
    entries.append(("Закрыть", ("close", None), False, None))
    cells = [cell(2 + (i % 2) * 120, LIST_TOP + (i // 2) * 52, 116, 48, label, action, marked, text)
             for i, (label, action, marked, text) in enumerate(entries)]
    return {"title": "Что показывать", "cells": cells}


def _collections_view(menu, catalog, settings):
    shown, page, pages = paged(catalog["collections"], menu["page"], ROWS_PER_PAGE)
    selected = settings["selectedCollection"] if settings["showMode"] == "collection" else None
    cells = []
    for i, collection in enumerate(shown):
        amount = len(filter_by_mode(catalog, "collection", [], collection["collectionId"]))
        suffix = " (%d)" % amount if amount else " пусто"
        action = ("collection", collection["collectionId"]) if amount else None
        cells.append(cell(2, LIST_TOP + i * ROW_STEP, 236, ROW_HEIGHT,
                          named(collection["name"], suffix), action,
                          collection["collectionId"] == selected))
    return {"title": "Коллекции", "cells": cells + page_bar(page, pages)}


def _tags_view(menu, catalog):
    per_page = ROWS_PER_PAGE - 1
    shown, page, pages = paged(all_tags(catalog), menu["page"], per_page)
    cells = []
    for i, tag in enumerate(shown):
        cells.append(cell(2, LIST_TOP + i * ROW_STEP, 236, ROW_HEIGHT,
                          named(tag["label"], " (%d)" % tag["count"]),
                          ("toggleTag", tag["label"]), tag["label"] in menu["tags"]))
    count = len(menu["tags"])
    cells.append(cell(2, LIST_TOP + per_page * ROW_STEP, 236, ROW_HEIGHT, "Показать (%d)" % count,
                      ("showTags", None) if count else None))
    return {"title": "Теги", "cells": cells + page_bar(page, pages)}


OWN_NOTE = "у коллекции свои"
SCENES_NOTE = "сцены: по свайпу"


def _settings_view(catalog, settings, info):
    """The general settings; a note says when the Collection on show overrides one of them, or that
    the ShowMode "scenes" ignores the slide time."""
    shown = show_settings(catalog, settings)

    def note(key):
        return OWN_NOTE if shown[key] != settings[key] else None

    slide_note = SCENES_NOTE if settings["showMode"] == "scenes" else note("slideSeconds")
    cells = slide_cells(LIST_TOP, settings["slideSeconds"], "slide", slide_note) + [
        cell(2, LIST_TOP + ROW_STEP, 236, ROW_HEIGHT,
             "Перемешать: " + ("вкл" if settings["shuffle"] else "выкл"), ("shuffle", None), note=note("shuffle")),
        cell(2, LIST_TOP + 2 * ROW_STEP, 236, ROW_HEIGHT,
             "Подсветка: " + ("вкл" if settings["ambientLeds"] else "выкл"), ("ambientLeds", None)),
        cell(2, LIST_TOP + 3 * ROW_STEP, 236, ROW_HEIGHT, fit_text(info["address"], CHARS_PER_ROW),
             note="свободно %.1f МБ" % (info["freeBytes"] / 1048576), info=True),
    ]
    return {"title": "Настройки", "cells": cells + back_bar()}


def menu_view(menu, catalog, settings, info):
    """{title, cells}; a cell without an action is shown but cannot be pressed."""
    menu = library_settled(menu, catalog)
    screen = menu["screen"]
    if menu["keyboard"]:
        return library_view(menu, catalog, settings)
    if screen == "main":
        return _main_view(catalog, settings)
    if screen == "collections":
        return _collections_view(menu, catalog, settings)
    if screen == "tags":
        return _tags_view(menu, catalog)
    if screen == "settings":
        return _settings_view(catalog, settings, info)
    return library_view(menu, catalog, settings)


def _set_settings(settings):
    return {"op": "setSettings", "settings": settings}


def _apply_action(menu, kind, value, catalog, settings):
    if kind == "close":
        return None, None
    if kind == "back":
        return dict(menu, screen=BACK_TO[menu["screen"]], page=0), None
    if kind == "open":
        return dict(menu, screen=value, page=0), None
    if kind == "page":
        return dict(menu, page=value), None
    if kind == "mode":
        return None, _set_settings(dict(settings, showMode=value))
    if kind == "collection":
        return None, _set_settings(dict(settings, showMode="collection", selectedCollection=value))
    if kind == "toggleTag":
        tags = [t for t in menu["tags"] if t != value]
        if len(tags) == len(menu["tags"]):
            tags.append(value)
        return dict(menu, tags=tags), None
    if kind == "showTags":
        return None, _set_settings(dict(settings, showMode="tags", selectedTags=list(menu["tags"])))
    if kind == "slide":
        return menu, _set_settings(dict(settings, slideSeconds=step_slide(settings["slideSeconds"], value)))
    if kind == "shuffle":
        return menu, _set_settings(dict(settings, shuffle=not settings["shuffle"]))
    if kind == "ambientLeds":
        return menu, _set_settings(dict(settings, ambientLeds=not settings["ambientLeds"]))
    return library_action(menu, kind, value, catalog, settings)


def menu_tap(menu, x, y, catalog, settings, info):
    """Returns (next menu or None when closed, command for apply_command or None)."""
    menu = library_settled(menu, catalog)
    if menu["keyboard"]:
        return library_keyboard_tap(menu, x, y, catalog)
    action = action_at(menu_view(menu, catalog, settings, info)["cells"], x, y)
    if action is None:
        return menu, None
    return _apply_action(menu, action[0], action[1], catalog, settings)


def text_size(text, scale):
    """Width and height in pixels of text drawn with the 5x7 font."""
    return len(text) * (GLYPH_WIDTH + 1) * scale - scale if text else 0, GLYPH_HEIGHT * scale
