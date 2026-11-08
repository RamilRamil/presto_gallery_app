# Research: Full-Screen Pictures and Scenes

Measured on the user's Presto (MicroPython 1.26, build 2025-08-18) on 2026-11-08.

## Drawing speed

`rect` is the 002 method, `blit` is a viper copy into `memoryview(display)`. Times in ms per frame.
"mixed" has runs of 1–3 equal cells; "noise" has every cell different.

| Grid | rect mixed | rect noise | blit |
|---|---|---|---|
| 60 | 46 | 72 | 17 |
| 80 | 76 | 125 | 19 |
| 120 | 167 | 278 | 22 |
| 240 | 655 | 1091 | 33 |

`presto.update()` took 2–15 ms. The buffer is 115 200 bytes, and a pen value matches the two bytes
stored for a pixel.

**Decision**: blit, with rectangles as a fallback. **Rejected**: rectangles, as Grid 240 GIFs would
run near 1 fps.

## Keeping the server alive during a blocking Scene

A 2 s blocking loop calling a nested `run_until_complete` of a no-op task every 20 ms let a separate
asyncio task run 97 times in 97 pumps, and the loop kept working afterwards.

**Decision**: pump from `stop()`. **Rejected**: running Scenes on the second core, as the Presto
firmware drives the display from it; running the server only between slides, which breaks FR-014.

## Existing Scenes

All four scenes in the old project (`scene_dutch`, `scene_storm`, `scene_storm2`, `scene_watch`) use
`run(stop)` and `from pixel import presto, GRID, make_pen, block[, pix]`. None creates its own
`Presto`. The largest is 13 090 bytes, so a 64 KB limit is comfortable.

## Password

**Decision**: one Bearer password per request, kept in `sessionStorage`. **Rejected**: login sessions
with tokens, which add state and no real protection over plain HTTP; HTTPS, for which the device has
no practical certificate.

## Grids

240 divides evenly by 40, 60, 80, 120 and 240. 16 also fills the screen. 32 and 64 stay for existing
files and keep their 8 px and 24 px margins.
