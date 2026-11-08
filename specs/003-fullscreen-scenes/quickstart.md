# Quickstart: Full-Screen Pictures and Scenes

1. Add `WEB_PASSWORD = "…"` to `device/secrets.py`, then copy the app to the Presto as in
   `docs/device-setup.md`, now including `device/pixel.py`.
2. Open the device address and enter the password.
3. Upload a photo at Grid 60: no black frame.
4. Upload a GIF at Grid 240: timing matches the original.
5. Upload `scene_storm.py`: it fills the screen and the slideshow moves on after the slide time.
6. While it runs, open the library in the WebUi and press "show now" on another item.
7. Upload a Scene that loops forever without calling `stop`, power-cycle, and check it is flagged.
8. Run the automated checks:

```bash
.venv/bin/pytest
node --test web/test/
```
