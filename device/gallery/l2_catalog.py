# LAYER 2 (calculations): pure Catalog operations. Every function returns a new catalog.

from .l1_primitives import normalize_name, normalize_tags
from .model import KIND_SCENE, collection

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
