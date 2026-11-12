"""OnScreenKeyboard: pure logic, no hardware."""
from gallery import l1_font, l3_keyboard as k


def tap(keyboard, label):
    for cell in k.keyboard_view(keyboard)["cells"]:
        if cell["label"] == label:
            return k.keyboard_tap(keyboard, cell["x"] + 1, cell["y"] + 1)
    raise AssertionError("no key " + label)


def typed(keyboard, *labels):
    for label in labels:
        keyboard, _ = tap(keyboard, label)
    return keyboard


def fresh(text="", limit=10):
    return k.keyboard_open("Имя", text, limit, "newCollection")


def test_keys_are_large_enough_and_inside_the_screen():
    for page in range(len(k.PAGES)):
        for cell in k.keyboard_view(dict(fresh(), page=page))["cells"]:
            assert cell["height"] >= 40 and cell["width"] >= 40
            assert cell["x"] + cell["width"] <= 240 and cell["y"] + cell["height"] <= 240


def test_every_letter_and_digit_can_be_reached_and_drawn():
    keys = "".join(page[1] for page in k.PAGES)
    for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz0123456789":
        assert char in keys
    unknown = l1_font.glyph_rows("☃")
    assert all(l1_font.glyph_rows(c) != unknown for c in keys)
    assert all(len(page[1]) <= 24 for page in k.PAGES)


def test_typing_erasing_and_space():
    keyboard = typed(fresh(), "к", "о", "т")
    assert keyboard["text"] == "кот"
    keyboard = typed(keyboard, "___", "<")
    assert keyboard["text"] == "кот"
    assert k.keyboard_view(keyboard)["title"] == "кот_"


def test_pages_cycle():
    keyboard = fresh()
    seen = []
    for _ in k.PAGES:
        seen.append(keyboard["page"])
        keyboard, _ = tap(keyboard, k.PAGES[(keyboard["page"] + 1) % len(k.PAGES)][0])
    assert seen == [0, 1, 2, 3] and keyboard["page"] == 0


def test_limit_is_respected():
    assert typed(fresh("абв", limit=3), "г")["text"] == "абв"


def test_cancel_is_offered_only_on_empty_text():
    assert tap(fresh(), "Отм")[1] == "cancel"
    labels = [c["label"] for c in k.keyboard_view(fresh("а"))["cells"]]
    assert "Отм" not in labels and "<" in labels


def test_done_and_outside_touch():
    keyboard = fresh("а")
    assert tap(keyboard, "ОК")[1] == "done"
    assert k.keyboard_tap(keyboard, 1, 1) == (keyboard, None)


def test_message_shows_until_the_next_key_and_long_text_keeps_its_end():
    keyboard = dict(fresh("кот"), message="Имя не подходит")
    assert k.keyboard_view(keyboard)["title"] == "Имя не подходит"
    assert typed(keyboard, "а")["message"] is None
    long = fresh("а" * 30, limit=64)
    title = k.keyboard_view(dict(long, text="б" + "а" * 30))["title"]
    assert len(title) == 19 and title.endswith("а_")
