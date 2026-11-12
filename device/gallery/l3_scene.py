# LAYER 3 (calculations): where a Scene's grid cells land on the screen, and its pace.


def paced_ms(ms, percent):
    """Length of a pause of `ms` at this SceneSpeed."""
    return ms * 100 / percent


def speed_label(percent):
    """Menu text of a SceneSpeed, in characters the device font has."""
    if percent % 100 == 0:
        return "%dx" % (percent // 100)
    return ("%.2f" % (percent / 100)).rstrip("0") + "x"


def scene_rect(x, y, width, height, grid, screen):
    """Cell rectangle -> (left, top, width, height) in pixels, covering the screen with no gaps.
    When grid does not divide screen, neighbouring cells differ by at most 1 px."""
    left = x * screen // grid
    top = y * screen // grid
    return left, top, (x + width) * screen // grid - left, (y + height) * screen // grid - top
