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
3. In your router's settings you can reserve this IP for the Presto (a DHCP reservation), so
   the address never changes.
4. Gestures on the screen:

   | Gesture | Action |
   |---|---|
   | Swipe left / right | next / previous |
   | Tap | pause / continue |
   | Hold still for 1 s | menu |
   | Swipe up / down | brighter / darker |

5. In the menu you choose what to show. "Ещё" leads to the Tags and Collections of the current
   picture, to managing Collections and Tags with an on-screen keyboard, and to "Настройки"
   (slide time, shuffle, the address and free storage). In the mode "Сцены" the slide time does not
   apply: a Scene plays until you swipe, and "Настройки" says "сцены: по свайпу".
6. A Collection can have its own slide time and order. In "Ещё" → "Изменить коллекции" → the
   Collection → "Показ": "Своё время" on/off, "−"/"+" for the time, "Порядок" (как везде, по кругу,
   вперемешку) and "Сцены" for the speed of its Scenes. Own values apply only while that Collection
   is shown; "Настройки" marks the general value with "у коллекции свои" when it is overridden.
   The browser shows and edits the same values with the "Показ" button of the Collection.
7. The 7 LEDs on the back light the wall with the colours of the nearby screen edges, for pictures,
   GIFs, Scenes and the menu alike. "Настройки" → "Подсветка: вкл / выкл" (or "Подсветка сзади" in
   the browser settings) turns them off for everything; off means dark, and the choice survives a
   restart. It does not depend on the screen brightness.

The gallery runs the screen in full-resolution mode, 480×480. Pictures of every grid size fill it;
grid 480 is one screen pixel per cell. The menu keeps its layout and is drawn twice as large.

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

Open http://localhost:8080. Data goes to `.sim-storage/gallery`, the emulated screen (480×480) to
`.sim-storage/screen.png`. A second argument sets a password, which Scene upload needs. In the
simulator the web server pauses while a Scene runs; the real device keeps serving.

## Tests

```bash
.venv/bin/pytest            # desktop tool + device logic + golden vectors + layer guards
node --test web/test/       # browser logic, golden vectors, GIF decoder, layer guard
python -m presto_pic_loader.golden   # regenerate golden vectors after changing the algorithm
```
