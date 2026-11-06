# Research: Presto Wi-Fi Gallery

- **Where conversion runs**: browser. Device has no Pillow and little RAM; router/PC server rejected by user.
- **HTTP server on device**: vendored `microdot` (MIT, asyncio). Alternative: hand-written socket server (more code, more bugs).
- **Storage**: microSD via SPI + `sdcard` driver, fallback internal flash. TO VERIFY on hardware: pins, driver presence.
- **Identical results**: own median cut + Floyd–Steinberg in both languages, golden vectors. Pillow quantize rejected (not reproducible in JS).
- **GIF decoding**: own decoder (no deps, deterministic, works in Safari). WebCodecs `ImageDecoder` rejected (Safari support/varying output).
- **Animation palette**: one median cut over all frames. Per-frame palettes rejected (format has one palette).
- **Playback timing**: `asyncio.sleep_ms(durationMs)` minus draw time; durations < 20 ms clamped to 20 ms.
- **Atomic writes**: write `.tmp` then `os.rename` (supported on FAT and littlefs).
- **Auth**: none (trusted LAN, spec assumption).
