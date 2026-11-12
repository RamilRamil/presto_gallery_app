# LAYER 5 (actions): running a Scene inside the playback task (docs/scene-format.md).
# A Scene is trusted code: it can read everything on the device.

import gc
import os
import time

import asyncio

from .l3_scene import paced_ms
from .l5_clock import ticks_diff, ticks_ms
from .model import DEFAULT_SPEED

try:
    from asyncio import core as _core  # MicroPython only
except ImportError:
    _core = None

SIMULATOR_LIMIT_MS = 5000
PUMP_PASSES = 8
PAUSE_SLICE_MS = 100
MS_PER_UNIT = (("sleep", 1000), ("sleep_ms", 1), ("sleep_us", 0.001))


async def _noop():
    await asyncio.sleep_ms(0)


def pump():
    """Run a few passes of the asyncio loop from synchronous code, so the server and touch keep
    working while a Scene holds the playback task. Uses asyncio internals (see plan.md).
    One HTTP request takes several passes, and a Scene may call stop() only a few times a second."""
    if _core is None:
        return
    saved = _core.cur_task
    try:
        for _ in range(PUMP_PASSES):
            _core.run_until_complete(_core.create_task(_noop()))
    finally:
        _core.cur_task = saved


def mark_running(path, media_id):
    with open(path, "w") as f:
        f.write(media_id)


def clear_running(path):
    try:
        os.remove(path)
    except OSError:
        pass


def make_stop(wake, limit_ms, on_first_call, held=lambda: False):
    """The Scene's stop(): serves the loop, then says whether the Scene must return.
    While `held()` is true the time limit does not apply (Pause)."""
    start = ticks_ms()
    pending = [on_first_call]
    if _core is None and limit_ms is None:
        limit_ms = SIMULATOR_LIMIT_MS  # nothing else can run here, so never go on forever

    def stop():
        if pending:
            pending.pop()()
        pump()
        if wake.is_set():
            return True
        return limit_ms is not None and not held() and ticks_diff(ticks_ms(), start) >= limit_ms

    return stop


def check_syntax(text):
    """Compile without running; raises SyntaxError."""
    compile(text, "scene", "exec")


class _PacedTime:
    """Stands in for the time module inside a Scene."""


def _paced_sleep(percent, stop, ms_per_unit):
    """A sleep divided by the speed. A long pause keeps serving touches and the server."""

    def sleep(amount):
        left = paced_ms(amount * ms_per_unit, percent)
        while left > PAUSE_SLICE_MS:
            time.sleep(PAUSE_SLICE_MS / 1000)
            left -= PAUSE_SLICE_MS
            if stop():
                return
        time.sleep(left / 1000)

    return sleep


def pace_scene(namespace, percent, stop):
    """Replace what the loaded Scene took from `time`, under any name, by paced versions."""
    if percent == DEFAULT_SPEED:
        return
    paced = {}  # original sleep function -> its paced version
    substitute = _PacedTime()
    for name in dir(time):
        if not name.startswith("__"):
            setattr(substitute, name, getattr(time, name))
    for name, ms_per_unit in MS_PER_UNIT:
        original = getattr(time, name, None)
        if original is not None:
            replacement = _paced_sleep(percent, stop, ms_per_unit)
            setattr(substitute, name, replacement)
            paced[id(original)] = replacement
    for key, value in list(namespace.items()):
        if value is time:
            namespace[key] = substitute
        elif id(value) in paced:
            namespace[key] = paced[id(value)]


def run_scene(path, stop, speed_percent=DEFAULT_SPEED):
    """Run the Scene file to its end; returns None or the error text."""
    with open(path) as f:
        source = f.read()
    namespace = {"__name__": "scene"}
    try:
        exec(compile(source, "scene", "exec"), namespace)
        pace_scene(namespace, speed_percent, stop)
        namespace["run"](stop)
    except (Exception, SystemExit) as error:
        return "%s: %s" % (type(error).__name__, error)
    finally:
        del source
        namespace.clear()
        gc.collect()
    return None
