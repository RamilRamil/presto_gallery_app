"""The Scene helpers cover the whole screen and run existing Scene code unchanged."""
import asyncio

import pixel
from gallery import l5_scene


class FakeDisplay:
    def __init__(self):
        self.pen = None
        self.covered = set()

    def create_pen(self, r, g, b):
        return (r, g, b)

    def set_pen(self, pen):
        self.pen = pen

    def rectangle(self, x, y, w, h):
        self.covered.update((xx, yy) for xx in range(x, x + w) for yy in range(y, y + h))


class FakePresto:
    def __init__(self):
        self.display = FakeDisplay()


def test_block_fills_the_whole_screen():
    presto = FakePresto()
    pixel.bind(presto)
    for y in range(pixel.GRID):
        for x in range(pixel.GRID):
            pixel.pix(x, y, pixel.make_pen(1, 2, 3))
    assert len(presto.display.covered) == 480 * 480


def run_source(tmp_path, source, stop):
    path = tmp_path / "scene.py"
    path.write_text(source)
    return l5_scene.run_scene(str(path), stop)


def test_run_scene_passes_stop_and_skips_main_block(tmp_path):
    calls = []
    source = (
        "def run(stop):\n"
        "    while not stop():\n"
        "        pass\n"
        "if __name__ == '__main__':\n"
        "    raise RuntimeError('main block ran')\n"
    )
    assert run_source(tmp_path, source, lambda: calls.append(1) or len(calls) >= 3) is None
    assert len(calls) == 3


def test_run_scene_reports_errors(tmp_path):
    assert "ValueError: boom" in run_source(
        tmp_path, "def run(stop):\n    raise ValueError('boom')\n", lambda: True)
    assert "SystemExit" in run_source(
        tmp_path, "import sys\ndef run(stop):\n    sys.exit(1)\n", lambda: True)
    assert "NameError" in run_source(tmp_path, "nope\n", lambda: True)


def test_make_stop_clears_marker_once_and_honours_limit(tmp_path):
    async def body():
        marker = tmp_path / "scene.running"
        l5_scene.mark_running(str(marker), "abc")
        assert marker.read_text() == "abc"
        cleared = []

        def clear():
            cleared.append(1)
            l5_scene.clear_running(str(marker))

        wake = asyncio.Event()
        stop = l5_scene.make_stop(wake, None, clear)
        assert stop() is False and stop() is False
        assert cleared == [1] and not marker.exists()
        wake.set()
        assert stop() is True
        assert l5_scene.make_stop(asyncio.Event(), 0, lambda: None)() is True

    asyncio.run(body())
