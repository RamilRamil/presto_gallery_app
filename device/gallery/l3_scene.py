# LAYER 3 (calculations): where a Scene's grid cells land on the screen.


def scene_rect(x, y, width, height, grid, screen):
    """Cell rectangle -> (left, top, width, height) in pixels, covering the screen with no gaps.
    When grid does not divide screen, neighbouring cells differ by at most 1 px."""
    left = x * screen // grid
    top = y * screen // grid
    return left, top, (x + width) * screen // grid - left, (y + height) * screen // grid - top
