# LAYER 2 (calculations): pure Catalog operations. Every function returns a new catalog.

from .l1_primitives import clamp, normalize_name, normalize_tag, normalize_tags
from .model import (
    DEFAULT_SPEED, KIND_SCENE, SLIDE_MAX_SECONDS, SLIDE_MIN_SECONDS, SPEED_PERCENTS, collection,
)

ERROR_MAX_LENGTH = 200


def find_item(catalog, media_id):
    for item in catalog["items"]:
        if item["mediaId"] == media_id:
            return item
    return None


def _with_items(catalog, items):
    return {"formatVersion": catalog["formatVersion"], "items": items,
            "collections": catalog["collections"]}


def _with_collections(catalog, collections):
    return {"formatVersion": catalog["formatVersion"], "items": catalog["items"],
            "collections": collections}


def add_item(catalog, item):
    if find_item(catalog, item["mediaId"]) is not None:
        raise ValueError("duplicate media id")
    clean = dict(item)
    clean["name"] = normalize_name(item["name"])
    clean["tags"] = normalize_tags(item["tags"])
    return _with_items(catalog, catalog["items"] + [clean])


def remove_item(catalog, media_id):
    if find_item(catalog, media_id) is None:
        raise KeyError(media_id)
    catalog = _with_items(catalog, [i for i in catalog["items"] if i["mediaId"] != media_id])
    return _with_collections(catalog, [
        dict(c, mediaIds=[m for m in c["mediaIds"] if m != media_id]) for c in catalog["collections"]])


def _update(catalog, media_id, key, value):
    if find_item(catalog, media_id) is None:
        raise KeyError(media_id)
    items = []
    for item in catalog["items"]:
        if item["mediaId"] == media_id:
            item = dict(item)
            item[key] = value
        items.append(item)
    return _with_items(catalog, items)


def rename_item(catalog, media_id, name):
    return _update(catalog, media_id, "name", normalize_name(name))


def set_tags(catalog, media_id, tags):
    return _update(catalog, media_id, "tags", normalize_tags(tags))


def add_tag_to_items(catalog, media_ids, tag):
    """Add one Tag to each item that exists; its other Tags stay."""
    for media_id in media_ids:
        item = find_item(catalog, media_id)
        if item is not None:
            catalog = set_tags(catalog, media_id, item["tags"] + [tag])
    return catalog


def rename_tag(catalog, tag, new_tag):
    """Rename a Tag on every item; items that already have the new name end up with it once."""
    clean = normalize_tag(new_tag)
    return _replace_tag(catalog, tag, [clean])


def remove_tag(catalog, tag):
    """Remove a Tag from every item; the items stay."""
    return _replace_tag(catalog, tag, [])


def _replace_tag(catalog, tag, replacement):
    if not any(tag in item["tags"] for item in catalog["items"]):
        raise KeyError(tag)
    items = []
    for item in catalog["items"]:
        if tag in item["tags"]:
            item = dict(item, tags=normalize_tags([t for t in item["tags"] if t != tag] + replacement))
        items.append(item)
    return _with_items(catalog, items)


def remove_items(catalog, media_ids):
    """Remove every listed item that exists."""
    for media_id in media_ids:
        if find_item(catalog, media_id) is not None:
            catalog = remove_item(catalog, media_id)
    return catalog


def set_flag(catalog, media_id, flagged, error):
    """Flag a Scene (it leaves the Playlist) or clear its flag; pictures cannot be flagged."""
    item = find_item(catalog, media_id)
    if item is None:
        raise KeyError(media_id)
    if item["kind"] != KIND_SCENE:
        raise ValueError("only a scene can be flagged")
    catalog = _update(catalog, media_id, "flagged", flagged)
    return _update(catalog, media_id, "error", error[:ERROR_MAX_LENGTH] if error else None)


def item_speed(item):
    """The item's SceneSpeed; older entries and unknown values play at the default."""
    speed = item.get("speedPercent", DEFAULT_SPEED)
    return speed if speed in SPEED_PERCENTS else DEFAULT_SPEED


def set_speed(catalog, media_id, percent):
    item = find_item(catalog, media_id)
    if item is None:
        raise KeyError(media_id)
    if item["kind"] != KIND_SCENE:
        raise ValueError("only a scene has a speed")
    if percent not in SPEED_PERCENTS:
        raise ValueError("unknown speed")
    return _update(catalog, media_id, "speedPercent", percent)


def all_tags(catalog):
    """[{label, count}] sorted by label."""
    counts = {}
    for item in catalog["items"]:
        for tag in item["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"label": t, "count": counts[t]} for t in sorted(counts)]


def find_collection(catalog, collection_id):
    for entry in catalog["collections"]:
        if entry["collectionId"] == collection_id:
            return entry
    return None


def _require_unique_name(catalog, name, own_id):
    for entry in catalog["collections"]:
        if entry["name"].lower() == name.lower() and entry["collectionId"] != own_id:
            raise ValueError("a collection with this name already exists")


def add_collection(catalog, collection_id, name):
    clean = normalize_name(name)
    _require_unique_name(catalog, clean, collection_id)
    return _with_collections(catalog, catalog["collections"] + [collection(collection_id, clean)])


def _replace_collection(catalog, collection_id, changes):
    if find_collection(catalog, collection_id) is None:
        raise KeyError(collection_id)
    return _with_collections(catalog, [
        dict(c, **changes) if c["collectionId"] == collection_id else c
        for c in catalog["collections"]])


def rename_collection(catalog, collection_id, name):
    clean = normalize_name(name)
    _require_unique_name(catalog, clean, collection_id)
    return _replace_collection(catalog, collection_id, {"name": clean})


def remove_collection(catalog, collection_id):
    if find_collection(catalog, collection_id) is None:
        raise KeyError(collection_id)
    return _with_collections(catalog, [
        c for c in catalog["collections"] if c["collectionId"] != collection_id])


def add_to_collection(catalog, collection_id, media_ids):
    """Append items that exist and are not in the Collection yet, keeping their order."""
    entry = find_collection(catalog, collection_id)
    if entry is None:
        raise KeyError(collection_id)
    merged = list(entry["mediaIds"])
    for media_id in media_ids:
        if media_id not in merged and find_item(catalog, media_id) is not None:
            merged.append(media_id)
    return _replace_collection(catalog, collection_id, {"mediaIds": merged})


def collection_scenes(catalog, collection_id):
    entry = find_collection(catalog, collection_id)
    if entry is None:
        raise KeyError(collection_id)
    members = set(entry["mediaIds"])
    return [i for i in catalog["items"] if i["mediaId"] in members and i["kind"] == KIND_SCENE]


def common_speed(scenes):
    """The SceneSpeed these Scenes share, or None when they differ or there are none."""
    speeds = set(item_speed(scene) for scene in scenes)
    return speeds.pop() if len(speeds) == 1 else None


def set_collection_speed(catalog, collection_id, percent):
    """Give every Scene of the Collection this SceneSpeed; other items stay as they are."""
    if percent not in SPEED_PERCENTS:
        raise ValueError("unknown speed")
    ids = set(scene["mediaId"] for scene in collection_scenes(catalog, collection_id))
    if not ids:
        raise ValueError("this collection has no scenes")
    return _with_items(catalog, [dict(i, speedPercent=percent) if i["mediaId"] in ids else i
                                 for i in catalog["items"]])


SHOW_KEYS = ("slideSeconds", "shuffle")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def collection_show(entry):
    """CollectionShowSettings: {slideSeconds, shuffle}, None where the Collection has no own value.
    A damaged stored value counts as none, so the Collection still plays."""
    seconds = entry.get("slideSeconds")
    shuffle = entry.get("shuffle")
    return {
        "slideSeconds": clamp(seconds, SLIDE_MIN_SECONDS, SLIDE_MAX_SECONDS) if _is_int(seconds) else None,
        "shuffle": shuffle if isinstance(shuffle, bool) else None,
    }


def set_collection_show(catalog, collection_id, changes):
    """Set (a value) or clear (None) own slide time and order; keys not in `changes` stay."""
    entry = find_collection(catalog, collection_id)
    if entry is None:
        raise KeyError(collection_id)
    updated = dict(entry)
    for key in changes:
        if key not in SHOW_KEYS:
            raise ValueError("unknown show setting " + key)
        value = changes[key]
        if value is None:
            updated.pop(key, None)
        elif key == "slideSeconds":
            if not _is_int(value):
                raise ValueError("slideSeconds must be an integer")
            updated[key] = clamp(value, SLIDE_MIN_SECONDS, SLIDE_MAX_SECONDS)
        else:
            if not isinstance(value, bool):
                raise ValueError("shuffle must be true or false")
            updated[key] = value
    return _with_collections(catalog, [
        updated if c["collectionId"] == collection_id else c for c in catalog["collections"]])


def remove_from_collection(catalog, collection_id, media_id):
    entry = find_collection(catalog, collection_id)
    if entry is None:
        raise KeyError(collection_id)
    return _replace_collection(catalog, collection_id,
                               {"mediaIds": [m for m in entry["mediaIds"] if m != media_id]})


def set_item_collections(catalog, media_id, collection_ids):
    """The item ends up in exactly these Collections: kept in place where it stays, last where new."""
    if find_item(catalog, media_id) is None:
        raise KeyError(media_id)
    if not isinstance(collection_ids, list):
        raise ValueError("collections must be a list of ids")
    for collection_id in collection_ids:
        if find_collection(catalog, collection_id) is None:
            raise KeyError(collection_id)
    updated = []
    for entry in catalog["collections"]:
        wanted = entry["collectionId"] in collection_ids
        if wanted and media_id not in entry["mediaIds"]:
            entry = dict(entry, mediaIds=entry["mediaIds"] + [media_id])
        elif not wanted and media_id in entry["mediaIds"]:
            entry = dict(entry, mediaIds=[m for m in entry["mediaIds"] if m != media_id])
        updated.append(entry)
    return _with_collections(catalog, updated)


def filter_by_mode(catalog, show_mode, selected_tags, selected_collection=None):
    items = [i for i in catalog["items"] if not i["flagged"]]
    if show_mode == "images":
        return [i for i in items if i["frameCount"] == 1]
    if show_mode == "animations":
        return [i for i in items if i["frameCount"] > 1]
    if show_mode == "scenes":
        return [i for i in items if i["kind"] == KIND_SCENE]
    if show_mode == "collection":
        entry = find_collection(catalog, selected_collection)
        if entry is None:
            return []
        by_id = dict((i["mediaId"], i) for i in items)
        return [by_id[m] for m in entry["mediaIds"] if m in by_id]
    if show_mode == "tags":
        wanted = set(selected_tags)
        return [i for i in items if wanted.intersection(i["tags"])]
    return list(items)
