# LAYER 3 (calculations): Playlist, playback timing and the single entry for state changes.

from .l1_primitives import clamp, lcg_next, new_media_id, normalize_tags
from .l2_catalog import (
    add_collection, add_item, add_tag_to_items, add_to_collection, all_tags, filter_by_mode,
    find_collection, find_item, remove_collection, remove_from_collection, remove_item, remove_items,
    rename_collection, rename_item, set_flag, set_item_collections, set_tags,
)
from .model import SHOW_MODES, device_state

SLIDE_MIN_SECONDS = 3
SLIDE_MAX_SECONDS = 600


def allocate_media_id(catalog, seed):
    return new_media_id(seed, set(i["mediaId"] for i in catalog["items"]))


def tag_counts(catalog):
    return all_tags(catalog)


def item_by_id(catalog, media_id):
    return find_item(catalog, media_id)


def collection_by_id(catalog, collection_id):
    return find_collection(catalog, collection_id)


def allocate_collection_id(catalog, seed):
    return new_media_id(seed, set(c["collectionId"] for c in catalog["collections"]))



def validate_settings(raw):
    mode = raw.get("showMode", "all")
    if mode not in SHOW_MODES:
        raise ValueError("showMode must be one of " + ", ".join(SHOW_MODES))
    seconds = raw.get("slideSeconds", 10)
    if not isinstance(seconds, int) or isinstance(seconds, bool):
        raise ValueError("slideSeconds must be an integer")
    selected_collection = raw.get("selectedCollection")
    if selected_collection is not None and not isinstance(selected_collection, str):
        raise ValueError("selectedCollection must be a collection id")
    return {
        "showMode": mode,
        "selectedTags": normalize_tags(raw.get("selectedTags", [])),
        "selectedCollection": selected_collection,
        "slideSeconds": clamp(seconds, SLIDE_MIN_SECONDS, SLIDE_MAX_SECONDS),
        "shuffle": bool(raw.get("shuffle", False)),
    }


def shuffled(values, seed):
    """Fisher-Yates with our LCG, so it is identical on MicroPython and CPython."""
    out = list(values)
    state = seed & 0x7FFFFFFF
    for i in range(len(out) - 1, 0, -1):
        state = lcg_next(state)
        j = state % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out


def build_playlist(catalog, settings, seed):
    ids = [i["mediaId"] for i in
           filter_by_mode(catalog, settings["showMode"], settings["selectedTags"],
                          settings["selectedCollection"])]
    return shuffled(ids, seed) if settings["shuffle"] else ids


def next_index(playlist, index):
    return 0 if not playlist else (index + 1) % len(playlist)


def prev_index(playlist, index):
    return 0 if not playlist else (index - 1) % len(playlist)


def reposition(old_playlist, old_index, new_playlist):
    """Keep showing the same item if it is still in the new Playlist."""
    if old_playlist and 0 <= old_index < len(old_playlist):
        current = old_playlist[old_index]
        if current in new_playlist:
            return new_playlist.index(current)
    return 0


def slide_plan(frame_durations_ms, slide_seconds):
    """How many times to play the frames: stills hold slide time, animations loop >= once."""
    slide_ms = slide_seconds * 1000
    if len(frame_durations_ms) <= 1:
        return {"loops": 1, "holdMs": slide_ms}
    loop_ms = max(1, sum(frame_durations_ms))
    return {"loops": max(1, -(-slide_ms // loop_ms)), "holdMs": 0}


def slide_limit_ms(playlist, slide_seconds):
    """How long a Scene may run; None when it is the only item, so it never restarts."""
    return None if len(playlist) == 1 else slide_seconds * 1000


def _known_collection(catalog, settings):
    """A show mode pointing at a Collection that is gone falls back to everything."""
    if settings["showMode"] == "collection" \
            and find_collection(catalog, settings["selectedCollection"]) is None:
        return dict(settings, showMode="all", selectedCollection=None)
    return settings


def apply_command(state, command, seed):
    """Pure entry for every change; returns the new device state.
    command["op"]: upload(item) | rename(mediaId, name) | setTags(mediaId, tags) | remove(mediaId)
                   | setSettings(settings) | show(mediaId) | flag(mediaId, error) | unflag(mediaId)
                   | createCollection(collectionId, name) | renameCollection(collectionId, name)
                   | deleteCollection(collectionId) | addToCollection(collectionId, mediaIds)
                   | removeFromCollection(collectionId, mediaId) | removeItems(mediaIds)
                   | addTag(mediaIds, tag) | editItem(mediaId, name?, tags?, collectionIds?)
                   | next | prev
    upload also takes show (False: keep showing the current item) and collectionId."""
    catalog, settings = state["catalog"], state["settings"]
    playlist, index = state["playlist"], state["index"]
    op = command["op"]
    if op in ("next", "prev"):
        step = next_index if op == "next" else prev_index
        return device_state(catalog, settings, playlist, step(playlist, index))
    target = None
    if op == "upload":
        catalog = add_item(catalog, command["item"])
        if "collectionId" in command:
            catalog = add_to_collection(catalog, command["collectionId"], [command["item"]["mediaId"]])
        if command.get("show", True):
            target = command["item"]["mediaId"]
    elif op == "rename":
        catalog = rename_item(catalog, command["mediaId"], command["name"])
    elif op == "setTags":
        catalog = set_tags(catalog, command["mediaId"], command["tags"])
    elif op == "editItem":
        media_id = command["mediaId"]
        if "name" in command:
            catalog = rename_item(catalog, media_id, command["name"])
        if "tags" in command:
            catalog = set_tags(catalog, media_id, command["tags"])
        if "collectionIds" in command:
            catalog = set_item_collections(catalog, media_id, command["collectionIds"])
    elif op == "remove":
        catalog = remove_item(catalog, command["mediaId"])
    elif op == "setSettings":
        settings = _known_collection(catalog, validate_settings(command["settings"]))
    elif op == "show":
        item = find_item(catalog, command["mediaId"])
        if item is None:
            raise KeyError(command["mediaId"])
        if item["flagged"]:
            raise ValueError("scene is flagged, enable it first")
        target = command["mediaId"]
    elif op == "flag":
        catalog = set_flag(catalog, command["mediaId"], True, command["error"])
    elif op == "unflag":
        catalog = set_flag(catalog, command["mediaId"], False, None)
    elif op == "removeItems":
        catalog = remove_items(catalog, command["mediaIds"])
    elif op == "addTag":
        catalog = add_tag_to_items(catalog, command["mediaIds"], command["tag"])
    elif op == "createCollection":
        catalog = add_collection(catalog, command["collectionId"], command["name"])
    elif op == "renameCollection":
        catalog = rename_collection(catalog, command["collectionId"], command["name"])
    elif op == "deleteCollection":
        catalog = remove_collection(catalog, command["collectionId"])
        settings = _known_collection(catalog, settings)
    elif op == "addToCollection":
        catalog = add_to_collection(catalog, command["collectionId"], command["mediaIds"])
    elif op == "removeFromCollection":
        catalog = remove_from_collection(catalog, command["collectionId"], command["mediaId"])
    else:
        raise ValueError("unknown command " + op)
    new_playlist = build_playlist(catalog, settings, seed)
    if op == "flag":
        new_index = index % len(new_playlist) if new_playlist else 0  # the next item moved here
    else:
        new_index = reposition(playlist, index, new_playlist)
    if target is not None:
        if target not in new_playlist:
            new_playlist = new_playlist + [target]  # show now even outside the ShowMode
        new_index = new_playlist.index(target)
    return device_state(catalog, settings, new_playlist, new_index)
