# Presto Wi-Fi Gallery: device setup

## What goes on the Presto

Copy to the root of the Presto's filesystem (e.g. with the MicroPico extension in VS Code,
"Upload file/folder", or `mpremote cp -r`):

```
/main.py            ← device/main.py
/pixel.py           ← device/pixel.py (drawing helpers for Scenes)
/gallery/           ← device/gallery/ (all .py files)
/lib/microdot/      ← device/lib/microdot/ (__init__.py, microdot.py)
/web/               ← web/index.html, web/style.css, web/js/*.js  (not web/test, not package.json)
/secrets.py         ← copy of device/secrets.example.py with your Wi-Fi and WEB_PASSWORD
```

`WEB_PASSWORD` protects everything under `/api`: viewing, changing and uploading. Use Latin letters,
digits and punctuation. Without it the gallery is open to the whole network and Scene upload is off.
The password travels over plain HTTP inside your network. See [scene-format.md](scene-format.md).

This replaces the old `main.py` menu of code-drawn scenes. Keep a copy of the old project if you
still want those scenes.

Example with `mpremote` (run from the project folder, Presto connected by USB):

```bash
mpremote mkdir :gallery :lib :lib/microdot :web :web/js
mpremote cp device/main.py device/pixel.py : + cp device/gallery/*.py :gallery/ + cp device/lib/microdot/*.py :lib/microdot/
mpremote cp web/index.html web/style.css :web/ + cp web/js/*.js :web/js/
mpremote cp device/secrets.py :secrets.py
```

## First start

1. Reset the Presto. It shows "connecting to Wi-Fi", then its address, e.g. `http://192.168.1.57`
   and `http://presto.local`, and which storage it uses (`microSD` or `flash`).
2. Open the address on a phone or computer in the same network.
3. In the Keenetic web interface (Home network → device list → Presto) you can make the IP
   permanent ("Permanent IP address"), so the address never changes.
4. Tap right/left = next/previous. A long press (1 s) opens the menu: choose what to show, change
   the slide time and shuffle; the address and free storage are under "Настройки".

## microSD

The card must be FAT32 and inserted before power-on. Other files on it are left alone. The app mounts
it at `/sd` (SCK 34, MOSI 35, MISO 36, CS 39) with corrections to the firmware's `sdcard` driver, see
`gallery/l5_sd.py`. If the screen says `storage: flash` with a card inserted, the card did not mount;
everything still works on flash with less space.

Media lives in `/sd/gallery` (or `/gallery`): `media/<id>.bin`, `scenes/`, `catalog.json`,
`settings.json`. On the first start with a card, a gallery on flash is copied to it and the screen
shows the progress. The copy on flash stays, and is what you see if the card is later removed.

## Try it without the Presto (simulator)

```bash
.venv/bin/python device/sim/run_sim.py 8080
```

Open http://localhost:8080. Data goes to `.sim-storage/gallery`, the emulated screen to
`.sim-storage/screen.png`. A second argument sets a password, which Scene upload needs. In the
simulator the web server pauses while a Scene runs; the real device keeps serving.

## Tests

```bash
.venv/bin/pytest            # desktop tool + device logic + golden vectors + layer guards
node --test web/test/       # browser logic, golden vectors, GIF decoder, layer guard
python -m presto_pic_loader.golden   # regenerate golden vectors after changing the algorithm
```
