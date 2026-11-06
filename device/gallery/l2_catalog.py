# LAYER 2 (calculations): pure Catalog operations. Every function returns a new catalog.

from .l1_primitives import normalize_name, normalize_tags


def find_item(catalog, media_id):
    for item in catalog["items"]:
        if item["mediaId"] == media_id:
            return item
    return None


def _with_items(catalog, items):
    return {"formatVersion": catalog["formatVersion"], "items": items}


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
    return _with_items(catalog, [i for i in catalog["items"] if i["mediaId"] != media_id])


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


def all_tags(catalog):
    """[{label, count}] sorted by label."""
    counts = {}
    for item in catalog["items"]:
        for tag in item["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return [{"label": t, "count": counts[t]} for t in sorted(counts)]


def filter_by_mode(catalog, show_mode, selected_tags):
    items = catalog["items"]
    if show_mode == "images":
        return [i for i in items if i["frameCount"] == 1]
    if show_mode == "animations":
        return [i for i in items if i["frameCount"] > 1]
    if show_mode == "tags":
        wanted = set(selected_tags)
        return [i for i in items if wanted.intersection(i["tags"])]
    return list(items)
