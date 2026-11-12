# LAYER 3 (calculations): the pieces every DeviceMenu screen is built from.

from .l1_font import fit_text

SCREEN = 240
LIST_TOP = 28
ROW_STEP = 42
ROW_HEIGHT = 40
BAR_TOP = 198
ROWS_PER_PAGE = 4
CHARS_PER_ROW = 18
CHARS_IN_TITLE = 19
SLIDE_STEPS = (3, 5, 10, 15, 30, 60, 120, 300, 600)


def cell(x, y, width, height, label, action=None, marked=False, note=None, info=False):
    """`info` is a line to read, not a button; it stays bright although it cannot be pressed."""
    return {"x": x, "y": y, "width": width, "height": height, "label": label, "action": action,
            "marked": marked, "note": note, "info": info}


def row_cell(index, label, action=None, marked=False):
    return cell(2, LIST_TOP + index * ROW_STEP, 236, ROW_HEIGHT, label, action, marked)


def named(name, suffix):
    return fit_text(name, CHARS_PER_ROW - len(suffix)) + suffix


def page_bar(page, pages):
    return [
        cell(2, BAR_TOP, 56, ROW_HEIGHT, "<", ("page", page - 1) if page > 0 else None),
        cell(62, BAR_TOP, 116, ROW_HEIGHT, "Назад", ("back", None)),
        cell(182, BAR_TOP, 56, ROW_HEIGHT, ">", ("page", page + 1) if page < pages - 1 else None),
    ]


def back_bar():
    return [cell(62, BAR_TOP, 116, ROW_HEIGHT, "Назад", ("back", None))]


def paged(rows, page, per_page):
    pages = max(1, (len(rows) + per_page - 1) // per_page)
    page = min(page, pages - 1)
    return rows[page * per_page: (page + 1) * per_page], page, pages


def action_at(cells, x, y):
    """The action of the pressable cell under the point, or None."""
    for entry in cells:
        if entry["action"] and entry["x"] <= x < entry["x"] + entry["width"] \
                and entry["y"] <= y < entry["y"] + entry["height"]:
            return entry["action"]
    return None


def step_slide(seconds, direction):
    """The next slide time up (direction 1) or down (-1) in SLIDE_STEPS; a time between steps moves to one."""
    if direction > 0:
        for step in SLIDE_STEPS:
            if step > seconds:
                return step
        return SLIDE_STEPS[-1]
    for step in reversed(SLIDE_STEPS):
        if step < seconds:
            return step
    return SLIDE_STEPS[0]


def slide_cells(top, seconds, action, note=None):
    """"-", "Слайд N с", "+" in one row; `action` is None for a row that cannot be changed."""
    return [
        cell(2, top, 50, ROW_HEIGHT, "-", (action, -1) if action and seconds > SLIDE_STEPS[0] else None),
        cell(56, top, 128, ROW_HEIGHT, "Слайд %d с" % seconds, note=note, info=True),
        cell(188, top, 50, ROW_HEIGHT, "+", (action, 1) if action and seconds < SLIDE_STEPS[-1] else None),
    ]
