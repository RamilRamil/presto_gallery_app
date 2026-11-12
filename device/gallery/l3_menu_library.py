# LAYER 3 (calculations): DeviceMenu screens for the current item, Collections and Tags.

from .l1_font import fit_text
from .l1_primitives import NAME_MAX_LENGTH, TAG_MAX_LENGTH
from .l2_catalog import (
    all_tags, collection_scenes, collection_show, common_speed, find_collection, find_item, item_speed,
)
from .l3_keyboard import keyboard_open, keyboard_tap, keyboard_view
from .l3_menu_cells import (
    CHARS_IN_TITLE, LIST_TOP, ROW_HEIGHT, ROW_STEP, ROWS_PER_PAGE, back_bar, cell, named, page_bar, paged, row_cell,
    slide_cells, step_slide,
)
from .l3_scene import speed_label
from .model import KIND_SCENE, SPEED_PERCENTS

REJECTED = "Имя не подходит"
BACK_TO = {
    "collections": "main", "tags": "main", "more": "main", "settings": "more", "item": "more",
    "manageCollections": "more", "manageTags": "more", "itemTags": "item", "itemCollections": "item",
    "itemSpeed": "item", "collectionCard": "manageCollections", "collectionItems": "collectionCard",
    "collectionShow": "collectionCard", "collectionSpeed": "collectionShow", "confirmCollection": "collectionCard", "tagCard": "manageTags",
    "confirmTag": "tagCard",
}
ITEM_SCREENS = ("item", "itemTags", "itemCollections", "itemSpeed")
COLLECTION_SCREENS = ("collectionCard", "collectionItems", "collectionShow", "collectionSpeed", "confirmCollection")
TAG_SCREENS = ("tagCard", "confirmTag")
LIBRARY_SCREENS = ITEM_SCREENS + COLLECTION_SCREENS + TAG_SCREENS + ("manageCollections", "manageTags")
ASK = {
    "itemTag": ("Новый тег", TAG_MAX_LENGTH),
    "itemCollection": ("Новая коллекция", NAME_MAX_LENGTH),
    "newCollection": ("Новая коллекция", NAME_MAX_LENGTH),
    "renameCollection": ("Новое имя", NAME_MAX_LENGTH),
    "renameTag": ("Новое имя", TAG_MAX_LENGTH),
}
ORDER_LABELS = ((None, "как везде"), (False, "по кругу"), (True, "вперемешку"))


def _has_tag(catalog, label):
    return any(tag["label"] == label for tag in all_tags(catalog))


def library_settled(menu, catalog):
    """The menu to use when what its screen shows was deleted in the meantime."""
    screen = menu["screen"]
    fallback = None
    if screen in ITEM_SCREENS and find_item(catalog, menu["mediaId"]) is None:
        fallback = "more"
    elif screen in COLLECTION_SCREENS and find_collection(catalog, menu["target"]) is None:
        fallback = "manageCollections"
    elif screen in TAG_SCREENS and not _has_tag(catalog, menu["target"]):
        fallback = "manageTags"
    return menu if fallback is None else dict(menu, screen=fallback, page=0, keyboard=None)


def _list_view(title, rows, menu, extra=None):
    """Paged rows of (label, action, marked), and one fixed row under them when `extra` is given."""
    per_page = ROWS_PER_PAGE - (1 if extra else 0)
    shown, page, pages = paged(rows, menu["page"], per_page)
    cells = [row_cell(i, *row) for i, row in enumerate(shown)]
    if extra:
        cells.append(row_cell(per_page, *extra))
    return {"title": fit_text(title, CHARS_IN_TITLE), "cells": cells + page_bar(page, pages)}


def _fixed_view(title, rows):
    cells = [row_cell(i, *row) for i, row in enumerate(rows)]
    return {"title": fit_text(title, CHARS_IN_TITLE), "cells": cells + back_bar()}


def _collections_of(catalog, media_id):
    return [c["collectionId"] for c in catalog["collections"] if media_id in c["mediaIds"]]


def _more_view(menu, catalog):
    return _fixed_view("Ещё", [
        ("Эта картинка", ("open", "item") if find_item(catalog, menu["mediaId"]) else None, False),
        ("Изменить коллекции", ("open", "manageCollections"), False),
        ("Изменить теги", ("open", "manageTags"), False),
        ("Настройки", ("open", "settings"), False),
    ])


def _item_view(menu, catalog):
    item = find_item(catalog, menu["mediaId"])
    rows = [
        ("Теги (%d)" % len(item["tags"]), ("open", "itemTags"), False),
        ("Коллекции (%d)" % len(_collections_of(catalog, item["mediaId"])), ("open", "itemCollections"), False),
    ]
    if item["kind"] == KIND_SCENE:
        rows.append(("Скорость: " + speed_label(item_speed(item)), ("open", "itemSpeed"), False))
    return _fixed_view(item["name"], rows)


def _speed_view(title, current, kind):
    """Five buttons in two columns, so they all fit on one screen."""
    cells = []
    for i, percent in enumerate(SPEED_PERCENTS):
        cells.append(cell(2 + (i % 2) * 120, LIST_TOP + (i // 2) * ROW_STEP, 116, ROW_HEIGHT,
                          speed_label(percent), (kind, percent), percent == current))
    return {"title": title, "cells": cells + back_bar()}


def _item_tags_view(menu, catalog):
    item = find_item(catalog, menu["mediaId"])
    labels = sorted(set([t["label"] for t in all_tags(catalog)] + menu["known"]))  # a Tag just unset stays
    rows = [(fit_text(label, 18), ("itemTag", label), label in item["tags"]) for label in labels]
    return _list_view("Теги картинки", rows, menu, ("+ Новый тег", ("ask", "itemTag"), False))


def _item_collections_view(menu, catalog):
    joined = _collections_of(catalog, menu["mediaId"])
    rows = [(fit_text(c["name"], 18), ("itemCollection", c["collectionId"]), c["collectionId"] in joined)
            for c in catalog["collections"]]
    return _list_view("Коллекции картинки", rows, menu, ("+ Новая коллекция", ("ask", "itemCollection"), False))


def _manage_collections_view(menu, catalog):
    rows = [(named(c["name"], " (%d)" % len(c["mediaIds"])), ("target", ("collectionCard", c["collectionId"])), False)
            for c in catalog["collections"]]
    return _list_view("Коллекции", rows, menu, ("+ Новая коллекция", ("ask", "newCollection"), False))


def _collection_card_view(menu, catalog):
    collection = find_collection(catalog, menu["target"])
    amount = len(collection["mediaIds"])
    rows = [
        ("Переименовать", ("ask", "renameCollection"), False),
        ("Картинки (%d)" % amount, ("open", "collectionItems") if amount else None, False),
    ]
    rows.append(("Показ", ("open", "collectionShow"), False))
    rows.append(("Удалить", ("open", "confirmCollection"), False))
    return _fixed_view(collection["name"], rows)


def _next_order(shuffle):
    """как везде -> по кругу -> вперемешку -> как везде."""
    values = [value for value, _ in ORDER_LABELS]
    return values[(values.index(shuffle) + 1) % len(values)]


def _collection_show_view(menu, catalog, settings):
    """CollectionShowSettings of the Collection; without own time the general one is shown, unchangeable."""
    own = collection_show(find_collection(catalog, menu["target"]))
    has_time = own["slideSeconds"] is not None
    seconds = own["slideSeconds"] if has_time else settings["slideSeconds"]
    order = dict(ORDER_LABELS)[own["shuffle"]]
    cells = [row_cell(0, "Своё время: " + ("вкл" if has_time else "выкл"), ("ownSlide", None), has_time)]
    cells += slide_cells(LIST_TOP + ROW_STEP, seconds, "ownSlideStep" if has_time else None,
                         None if has_time else "как везде")
    cells.append(row_cell(2, "Порядок: " + order, ("ownOrder", None), own["shuffle"] is not None))
    scenes = collection_scenes(catalog, menu["target"])
    if scenes:
        speed = common_speed(scenes)
        cells.append(row_cell(3, "Сцены: " + (speed_label(speed) if speed else "разная"),
                              ("open", "collectionSpeed")))
    return {"title": fit_text(_show_title(catalog, menu), CHARS_IN_TITLE), "cells": cells + back_bar()}


def _show_title(catalog, menu):
    return "Показ: " + find_collection(catalog, menu["target"])["name"]


def _collection_items_view(menu, catalog):
    rows = []
    for media_id in find_collection(catalog, menu["target"])["mediaIds"]:
        item = find_item(catalog, media_id)
        if item is not None:
            rows.append((fit_text(item["name"], 18), ("dropItem", media_id), False))
    return _list_view("Убрать из коллекции", rows, menu)


def _manage_tags_view(menu, catalog):
    rows = [(named(t["label"], " (%d)" % t["count"]), ("target", ("tagCard", t["label"])), False)
            for t in all_tags(catalog)]
    return _list_view("Теги", rows, menu)


def _tag_card_view(menu):
    return _fixed_view(menu["target"], [
        ("Переименовать", ("ask", "renameTag"), False),
        ("Удалить", ("open", "confirmTag"), False),
    ])


def _confirm_view(name, action):
    return _fixed_view("Удалить?", [
        (fit_text(name, 18), None, False),
        ("Да, удалить", (action, None), False),
    ])


def library_view(menu, catalog, settings):
    """{title, cells} of a library screen, or of the open keyboard."""
    if menu["keyboard"]:
        return keyboard_view(menu["keyboard"])
    screen = menu["screen"]
    if screen == "more":
        return _more_view(menu, catalog)
    if screen == "item":
        return _item_view(menu, catalog)
    if screen == "itemTags":
        return _item_tags_view(menu, catalog)
    if screen == "itemCollections":
        return _item_collections_view(menu, catalog)
    if screen == "itemSpeed":
        return _speed_view("Скорость", item_speed(find_item(catalog, menu["mediaId"])), "itemSpeed")
    if screen == "collectionShow":
        return _collection_show_view(menu, catalog, settings)
    if screen == "collectionSpeed":
        return _speed_view("Скорость сцен", common_speed(collection_scenes(catalog, menu["target"])), "collectionSpeed")
    if screen == "manageCollections":
        return _manage_collections_view(menu, catalog)
    if screen == "collectionCard":
        return _collection_card_view(menu, catalog)
    if screen == "collectionItems":
        return _collection_items_view(menu, catalog)
    if screen == "confirmCollection":
        return _confirm_view(find_collection(catalog, menu["target"])["name"], "deleteCollection")
    if screen == "manageTags":
        return _manage_tags_view(menu, catalog)
    if screen == "tagCard":
        return _tag_card_view(menu)
    return _confirm_view(menu["target"], "deleteTag")


def _toggled(values, value):
    rest = [v for v in values if v != value]
    return rest if len(rest) != len(values) else values + [value]


def _ask(menu, purpose, catalog):
    prompt, limit = ASK[purpose]
    text = ""
    if purpose == "renameCollection":
        text = find_collection(catalog, menu["target"])["name"]
    elif purpose == "renameTag":
        text = menu["target"]
    return dict(menu, keyboard=keyboard_open(prompt, text, limit, purpose))


def _without_tag(menu, tag):
    return [t for t in menu["tags"] if t != tag]


def _finish_keyboard(menu, catalog):
    purpose, text = menu["keyboard"]["purpose"], menu["keyboard"]["text"]
    closed = dict(menu, keyboard=None)
    media_id, target = menu["mediaId"], menu["target"]
    if purpose == "itemTag":
        return closed, {"op": "editItem", "mediaId": media_id, "tags": find_item(catalog, media_id)["tags"] + [text]}
    if purpose == "itemCollection":
        return closed, {"op": "createCollection", "name": text, "mediaIds": [media_id]}
    if purpose == "newCollection":
        return closed, {"op": "createCollection", "name": text}
    if purpose == "renameCollection":
        return closed, {"op": "renameCollection", "collectionId": target, "name": text}
    return dict(closed, screen="manageTags", page=0, tags=_without_tag(menu, target)), \
        {"op": "renameTag", "tag": target, "newTag": text}


def library_keyboard_tap(menu, x, y, catalog):
    """(next menu, command or None) for a touch on the open keyboard."""
    keyboard, outcome = keyboard_tap(menu["keyboard"], x, y)
    if outcome == "cancel":
        return dict(menu, keyboard=None), None
    if outcome == "done":
        return _finish_keyboard(menu, catalog)
    return (menu if keyboard is menu["keyboard"] else dict(menu, keyboard=keyboard)), None


def library_action(menu, kind, value, catalog, settings):
    """(next menu, command or None) for a pressed library cell."""
    media_id, target = menu["mediaId"], menu["target"]
    if kind == "target":
        return dict(menu, screen=value[0], target=value[1], page=0), None
    if kind == "ask":
        return _ask(menu, value, catalog), None
    if kind == "itemTag":
        command = {"op": "editItem", "mediaId": media_id, "tags": _toggled(find_item(catalog, media_id)["tags"], value)}
        return dict(menu, known=menu["known"] + [value]), command
    if kind == "itemCollection":
        ids = _toggled(_collections_of(catalog, media_id), value)
        return menu, {"op": "editItem", "mediaId": media_id, "collectionIds": ids}
    if kind == "itemSpeed":
        return menu, {"op": "editItem", "mediaId": media_id, "speedPercent": value}
    if kind == "collectionSpeed":
        return menu, {"op": "setCollectionSpeed", "collectionId": target, "speedPercent": value}
    if kind in ("ownSlide", "ownSlideStep", "ownOrder"):
        return menu, _show_command(kind, value, target, collection_show(find_collection(catalog, target)), settings)
    if kind == "dropItem":
        return menu, {"op": "removeFromCollection", "collectionId": target, "mediaId": value}
    if kind == "deleteCollection":
        return dict(menu, screen="manageCollections", page=0), {"op": "deleteCollection", "collectionId": target}
    if kind == "deleteTag":
        return dict(menu, screen="manageTags", page=0, tags=_without_tag(menu, target)), \
            {"op": "removeTag", "tag": target}
    raise ValueError("unknown menu action " + kind)


def _show_command(kind, value, collection_id, own, settings):
    command = {"op": "setCollectionShow", "collectionId": collection_id}
    if kind == "ownSlide":  # turning own time on starts it at the general time
        command["slideSeconds"] = None if own["slideSeconds"] is not None else settings["slideSeconds"]
    elif kind == "ownSlideStep":
        command["slideSeconds"] = step_slide(own["slideSeconds"], value)
    else:
        command["shuffle"] = _next_order(own["shuffle"])
    return command


def menu_rejected(menu):
    """The menu to show after its command was refused; `menu` is the one before the touch."""
    if menu["keyboard"]:
        return dict(menu, keyboard=dict(menu["keyboard"], message=REJECTED))
    return dict(menu, screen="more", page=0)
