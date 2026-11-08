# LAYER 5 (actions): running a Scene inside the playback task (docs/scene-format.md).
# A Scene is trusted code: it can read everything on the device.

import gc
import os

import asyncio

from .l5_clock import ticks_diff, ticks_ms

try:
    from asyncio import core as _core  # MicroPython only
except ImportError:
    _core = None

SIMULATOR_LIMIT_MS = 5000
PUMP_PASSES = 8


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


def make_stop(wake, limit_ms, on_first_call):
    """The Scene's stop(): serves the loop, then says whether the Scene must return."""
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
        return limit_ms is not None and ticks_diff(ticks_ms(), start) >= limit_ms

    return stop


def check_syntax(text):
    """Compile without running; raises SyntaxError."""
    compile(text, "scene", "exec")


def run_scene(path, stop):
    """Run the Scene file to its end; returns None or the error text."""
    with open(path) as f:
        source = f.read()
    namespace = {"__name__": "scene"}
    try:
        exec(compile(source, "scene", "exec"), namespace)
        namespace["run"](stop)
    except (Exception, SystemExit) as error:
        return "%s: %s" % (type(error).__name__, error)
    finally:
        del source
        namespace.clear()
        gc.collect()
    return None
