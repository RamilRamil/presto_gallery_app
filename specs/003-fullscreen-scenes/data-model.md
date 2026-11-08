# Data Model: Full-Screen Pictures and Scenes

## MediaItem (changed)

| Field | Type | Rule |
|---|---|---|
| kind | `"picture"` \| `"scene"` | missing in old catalogs → `"picture"` |
| flagged | bool | Scenes only; a flagged Scene is left out of the Playlist; default false |
| error | string \| null | last Scene error, at most 200 chars |
| frameCount, gridSize | int | Scene: `frameCount` 0, `gridSize` 0 |
| others | | unchanged from 002 |

Files: picture `media/<id>.bin`; Scene `scenes/<id>.py`.

## ShowMode (changed)

`all` (all kinds) · `images` (pictures, frameCount = 1) · `animations` (pictures, frameCount > 1) ·
`scenes` (Scenes) · `tags` (any kind having a selected Tag). Flagged Scenes are always excluded.

## Grid (changed)

16, 32, 40, 60, 64, 80, 120, 240. Cell size is `240 // grid`.

## AccessPassword (new)

`WEB_PASSWORD` in `secrets.py`. An empty or missing value means no password is set.

## Scene contract (new)

- Text file, at most 64 KB, valid MicroPython, with a top-level `def run(stop):`.
- `stop()` must be called often; it returns `True` when the Scene must return.
- Helpers from `pixel`: `presto`, `display`, `GRID` (32), `make_pen(r, g, b)`,
  `block(x, y, w, h, pen)`, `pix(x, y, pen)`.

## State transitions of a Scene

`ok` → (error raised) → `flagged, error set` · `ok` → (restart before the first `stop` call) →
`flagged, error "not responding"` · `flagged` → (PATCH `flagged: false`) → `ok`.

## CropView (new, WebUi only)

| Field | Type | Rule |
|---|---|---|
| centerX, centerY | number | source pixels; see the crop and fit limits in spec FR-022 |
| zoom | number | 1 to 8; the square's side is `min(width, height) / zoom` for crop, `max(width, height) / zoom` for fit |
