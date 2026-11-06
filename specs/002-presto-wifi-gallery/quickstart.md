# Quickstart
1. Flash Pimoroni Presto MicroPython firmware; insert microSD (optional).
2. Copy `device/` contents and `web/` to the Presto root (MicroPico "Upload project"); create `secrets.py` from `secrets.example.py`.
3. Reboot: the screen shows `http://<ip>` / `http://presto.local`. Open it in a browser, upload a picture.
4. Tests: `.venv/bin/pytest` and `node --test web/test/`.
