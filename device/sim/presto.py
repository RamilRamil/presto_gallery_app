"""Fake `presto` module for running the DeviceApp under CPython (simulator only).

The display keeps a 240x240 RGB framebuffer (480x480 with full_res=True); update() writes it to SCREEN_PATH as PNG
(throttled), so the screen can be inspected while the simulator runs.
"""
import time

SCREEN_PATH = None


class _Display:
    def __init__(self, size):
        self.size = size
        self.pen = (0, 0, 0)
        self.buffer = bytearray(size * size * 3)
        self.texts = []

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, pen):
        self.pen = pen

    def set_font(self, font):
        pass

    def get_bounds(self):
        return self.size, self.size

    def clear(self):
        self.buffer[:] = bytes(self.pen) * (self.size * self.size)
        self.texts = []

    def rectangle(self, x, y, w, h):
        size = self.size
        row = bytes(self.pen) * max(0, min(w, size - x))
        for yy in range(max(0, y), min(size, y + h)):
            start = (yy * size + x) * 3
            self.buffer[start:start + len(row)] = row

    def text(self, text, x, y, wordwrap=0, scale=1, *args, **kwargs):
        self.texts.append(text)
        scale = int(scale or 1)
        self.rectangle(x, y + 2 * scale, min(len(text) * 6 * scale, self.size - x), 3 * scale)


class _Touch:
    state = False
    x = 0
    y = 0

    def poll(self):
        pass


class Presto:
    def __init__(self, *args, full_res=False, **kwargs):
        self.display = _Display(480 if full_res else 240)
        self.touch = _Touch()
        self.updates = 0
        self.backlight = 1.0
        self._last_save = 0.0

    def set_backlight(self, value):
        self.backlight = value

    NUM_LEDS = 7

    def auto_ambient_leds(self, enable):
        self.ambient = enable  # the simulator has no LEDs

    def set_led_rgb(self, i, r, g, b):
        pass

    def update(self):
        self.updates += 1
        now = time.monotonic()
        if SCREEN_PATH and now - self._last_save > 0.2:
            self._last_save = now
            from PIL import Image
            size = self.display.size
            Image.frombytes("RGB", (size, size), bytes(self.display.buffer)).save(SCREEN_PATH)
