# LAYER 5 (action): copy palette indices straight into the display buffer. MicroPython only;
# l5_app falls back to rectangles when this cannot be imported.

import micropython

from .l3_screen import SCREEN_SIZE as SCREEN


def layout(size, cell, offset):
    # Viper functions take at most four arguments, so the geometry travels as one integer.
    return size | (cell << 9) | (offset << 17)


@micropython.viper
def blit_frame(target, frame, pens, packed: int):
    """Writes size*size cells; pens must hold 256 entries so that any index is in bounds."""
    screen = int(SCREEN)
    size = packed & 0x1FF
    cell = (packed >> 9) & 0xFF
    offset = packed >> 17
    dst = ptr16(target)
    src = ptr8(frame)
    pal = ptr16(pens)
    y = 0
    while y < size:
        row = y * size
        top = offset + y * cell
        cy = 0
        while cy < cell:
            base = (top + cy) * screen + offset
            x = 0
            while x < size:
                value = pal[src[row + x]]
                left = base + x * cell
                cx = 0
                while cx < cell:
                    dst[left + cx] = value
                    cx += 1
                x += 1
            cy += 1
        y += 1
