# Scene format

A Scene is a MicroPython text file, at most 64 KB, uploaded through the web interface. It draws an
animation in code and plays as one slide of the gallery.

**A Scene is trusted code.** There is no sandbox: it can read everything on the device, including
the Wi-Fi password and all media, and it can use the network. Upload only your own files or files
you have read. Scene upload is refused until `WEB_PASSWORD` is set on the device.

## Contract

```python
import time
from pixel import presto, GRID, make_pen, block, pix

RED = make_pen(255, 0, 0)


def run(stop):
    x = 0
    while not stop():
        block(0, 0, GRID, GRID, make_pen(0, 0, 0))
        pix(x % GRID, GRID // 2, RED)
        presto.update()
        x += 1
        time.sleep(0.05)
```

- The file must have a top-level `def run(stop):`.
- Call `stop()` often, at least a few times a second. It returns `True` when the Scene must return.
- While `stop()` is not being called, the web interface, touch and slide changes wait.
- Code under `if __name__ == "__main__":` does not run.

## The `pixel` helpers

| Name | Meaning |
|---|---|
| `GRID` | 32 cells per side |
| `make_pen(r, g, b)` | create a pen |
| `block(x, y, w, h, pen)` | fill a rectangle of cells |
| `pix(x, y, pen)` | fill one cell |
| `presto`, `display` | the shared device objects; call `presto.update()` after drawing |

The 32 cells are stretched over the whole 240×240 screen, so a cell is 7 or 8 px wide. Drawing
directly on `display` uses screen pixels and is not stretched. Do not create another `Presto`.

## Timing and errors

A Scene runs for the slide time, or until the next change from the web interface or a tap. The only
item in the Playlist keeps running. A Scene that raises an error is flagged, skipped, and shows its
error in the library; "Включить" gives it another try.

A Scene that hangs before its first `stop()` call blocks the device until you switch it off and on.
It is then flagged and skipped. A Scene that hangs later is not detected: after switching the device
on, delete it in the web interface before the slideshow reaches it again.
