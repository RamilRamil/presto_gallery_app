"""Fake `presto` module for running the DeviceApp under CPython (simulator only).

The display keeps a 240x240 RGB framebuffer; update() writes it to SCREEN_PATH as PNG
(throttled), so the screen can be inspected while the simulator runs.
"""
import time

SCREEN_PATH = None
SIZE = 240


class _Display:
    def __init__(self):
        self.pen = (0, 0, 0)
        self.buffer = bytearray(SIZE * SIZE * 3)
        self.texts = []

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, pen):
        self.pen = pen

    def set_font(self, font):
        pass

    def get_bounds(self):
        return SIZE, SIZE

    def clear(self):
        self.buffer[:] = bytes(self.pen) * (SIZE * SIZE)
        self.texts = []

    def rectangle(self, x, y, w, h):
        row = bytes(self.pen) * max(0, min(w, SIZE - x))
        for yy in range(max(0, y), min(SIZE, y + h)):
            start = (yy * SIZE + x) * 3
            self.buffer[start:start + len(row)] = row

    def text(self, text, x, y, wordwrap=0, scale=1, *args, **kwargs):
        self.texts.append(text)
        self.rectangle(x, y + 4, min(len(text) * 6 * int(scale or 1), 220), 6)


class _Touch:
    state = False
    x = 0
    y = 0

    def poll(self):
        pass


class Presto:
    def __init__(self, *args, **kwargs):
        self.display = _Display()
        self.touch = _Touch()
        self.updates = 0
        self._last_save = 0.0

    def update(self):
        self.updates += 1
        now = time.monotonic()
        if SCREEN_PATH and now - self._last_save > 0.2:
            self._last_save = now
            from PIL import Image
            Image.frombytes("RGB", (SIZE, SIZE), bytes(self.display.buffer)).save(SCREEN_PATH)
