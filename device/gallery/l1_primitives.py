# LAYER 1 (calculations): small pure helpers.

PRESTO_SCREEN_SIZE = 480
UI_SIZE = 240            # the DeviceMenu and Gestures are laid out in these units
UI_SCALE = PRESTO_SCREEN_SIZE // UI_SIZE
TAG_MAX_LENGTH = 24
NAME_MAX_LENGTH = 64
_FORBIDDEN = ",/\\\"<>"


def clamp(value, low, high):
    return max(low, min(high, value))


def normalize_tag(text):
    """Trim, collapse spaces, lowercase; raise ValueError if empty/too long/forbidden chars.
    Note: MicroPython lowercases ASCII only; the WebUi sends already-lowercased tags."""
    label = " ".join(str(text).split()).lower()
    if not 1 <= len(label) <= TAG_MAX_LENGTH:
        raise ValueError("tag must be 1..%d characters" % TAG_MAX_LENGTH)
    for char in label:
        if char in _FORBIDDEN or ord(char) < 32:
            raise ValueError("tag contains a forbidden character")
    return label


def normalize_tags(tags):
    return sorted(set(normalize_tag(t) for t in tags))


def normalize_name(text):
    name = " ".join(str(text).split())
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        raise ValueError("name must be 1..%d characters" % NAME_MAX_LENGTH)
    return name


def lcg_next(state):
    return (state * 1103515245 + 12345) & 0x7FFFFFFF


def new_media_id(seed, taken):
    """8 hex chars derived from seed, avoiding ids in `taken`."""
    state = seed & 0x7FFFFFFF
    while True:
        state = lcg_next(state)
        media_id = "%08x" % (((state << 1) ^ lcg_next(state)) & 0xFFFFFFFF)
        if media_id not in taken:
            return media_id


def cell_size(grid_size, screen_size=PRESTO_SCREEN_SIZE):
    return screen_size // grid_size


def screen_offset(grid_size, screen_size=PRESTO_SCREEN_SIZE):
    return (screen_size - grid_size * cell_size(grid_size, screen_size)) // 2
