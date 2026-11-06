# DATA: plain dicts with camelCase keys (same names as knowledge/domain.okf.json and the HttpApi).

SHOW_MODES = ("all", "images", "animations", "tags")
CATALOG_FORMAT_VERSION = 1


def media_item(media_id, name, tags, frame_count, grid_size, byte_size, created_at):
    return {
        "mediaId": media_id, "name": name, "tags": list(tags), "frameCount": frame_count,
        "gridSize": grid_size, "byteSize": byte_size, "createdAt": created_at,
    }


def empty_catalog():
    return {"formatVersion": CATALOG_FORMAT_VERSION, "items": []}


def default_settings():
    return {"showMode": "all", "selectedTags": [], "slideSeconds": 10, "shuffle": False}


def device_state(catalog, settings, playlist, index):
    # Everything the player needs; replaced as a whole, never mutated.
    return {"catalog": catalog, "settings": settings, "playlist": playlist, "index": index}
