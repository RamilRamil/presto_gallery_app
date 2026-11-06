# LAYER 5 (actions): Wi-Fi, storage, HTTP routes, display, touch, asyncio loops.
# All hardware and file access of the DeviceApp lives here; logic is in l3/l4.

import gc
import os
import time

import asyncio
from microdot import Microdot, Request, Response, send_file

from .l3_playlist import (
    allocate_media_id, apply_command, slide_plan, tag_counts, validate_settings,
)
from .l4_codecs import (
    HEADER_SIZE, MAX_UPLOAD_BYTES, catalog_from_json, catalog_to_json, frame_offset,
    parse_bin_header, read_frame_duration, read_palette, settings_from_json, settings_to_json,
    validate_upload,
)
from .model import device_state, media_item

VERSION = "002-presto-wifi-gallery"
CHUNK = 4096
SPACE_MARGIN = 64 * 1024
LONG_PRESS_MS = 1000
INFO_MS = 5000

DEFAULT_CONFIG = {
    "webRoot": "/web",
    "storageBase": None,      # None: microSD (/sd/gallery) if it mounts, else /gallery
    "port": 80,
    "hostname": "presto",
}


def ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.monotonic() * 1000)


def ticks_diff(a, b):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(a, b)
    return a - b


# --- storage ------------------------------------------------------------------------------

def mount_sd():
    """Mount microSD at /sd. Pins follow Pimoroni's Presto examples (verify on hardware)."""
    try:
        import machine
        import sdcard
        spi = machine.SPI(0, sck=machine.Pin(34, machine.Pin.OUT),
                          mosi=machine.Pin(35, machine.Pin.OUT),
                          miso=machine.Pin(36, machine.Pin.OUT))
        os.mount(sdcard.SDCard(spi, machine.Pin(39)), "/sd")
        return True
    except Exception as error:  # no card, no driver or running in the simulator
        print("microSD not mounted:", error)
        return False


def make_dirs(path):
    current = "/" if path.startswith("/") else ""
    for part in path.strip("/").split("/"):
        current = current + part + "/"
        try:
            os.mkdir(current.rstrip("/"))
        except OSError:
            pass


def exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def read_text(path):
    with open(path) as f:
        return f.read()


def save_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    try:
        os.remove(path)  # FAT cannot rename over an existing file
    except OSError:
        pass
    os.rename(tmp, path)


def load_text(path):
    """Read path, falling back to path.tmp left by an interrupted save_atomic."""
    for candidate in (path, path + ".tmp"):
        if exists(candidate):
            try:
                return read_text(candidate)
            except OSError:
                pass
    return ""


def storage_info(base, kind):
    try:
        stat = os.statvfs(base)
        return {"kind": kind, "free": stat[1] * stat[4], "total": stat[1] * stat[2]}
    except (OSError, AttributeError):
        return {"kind": kind, "free": 0, "total": 0}


# --- Wi-Fi --------------------------------------------------------------------------------

def connect_wifi(hostname, timeout_ms=20000):
    """Join Wi-Fi from secrets.py; returns IP or None."""
    try:
        import network
        import secrets
    except ImportError:
        return None
    try:
        network.hostname(hostname)
    except Exception:
        pass
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        start = ticks_ms()
        while not wlan.isconnected() and ticks_diff(ticks_ms(), start) < timeout_ms:
            time.sleep_ms(200) if hasattr(time, "sleep_ms") else time.sleep(0.2)
    return wlan.ifconfig()[0] if wlan.isconnected() else None


# --- display ------------------------------------------------------------------------------

def draw_frame(display, pens, frame, size, cell, offset):
    """One rectangle per run of equal indices in a row."""
    for y in range(size):
        row = y * size
        x = 0
        while x < size:
            index = frame[row + x]
            end = x + 1
            while end < size and frame[row + end] == index:
                end += 1
            display.set_pen(pens[index])
            display.rectangle(offset + x * cell, offset + y * cell, (end - x) * cell, cell)
            x = end


def draw_message(presto, lines):
    display = presto.display
    display.set_pen(display.create_pen(8, 10, 20))
    display.clear()
    display.set_pen(display.create_pen(235, 235, 245))
    for i, line in enumerate(lines):
        display.text(line, 10, 20 + i * 28, 220, 2)
    presto.update()


# --- application --------------------------------------------------------------------------

class GalleryApp:
    def __init__(self, presto, config):
        self.presto = presto
        self.config = config
        self.ip = None
        self.broken = set()
        self.wake = asyncio.Event()
        self.info_requested = False
        base = config["storageBase"]
        kind = "custom"
        if base is None:
            kind = "microSD" if mount_sd() else "flash"
            base = "/sd/gallery" if kind == "microSD" else "/gallery"
        self.base, self.storage_kind = base, kind
        make_dirs(base + "/media")
        catalog = catalog_from_json(load_text(self.path("catalog.json")))
        try:
            settings = validate_settings(settings_from_json(load_text(self.path("settings.json"))))
        except ValueError:
            settings = validate_settings({})
        self.state = apply_command(device_state(catalog, settings, [], 0),
                                   {"op": "setSettings", "settings": settings}, ticks_ms())

    def path(self, name):
        return self.base + "/" + name

    def media_path(self, media_id):
        return self.base + "/media/" + media_id + ".bin"

    def change(self, command):
        """Apply a command, persist what changed, wake the player."""
        new_state = apply_command(self.state, command, ticks_ms())
        if new_state["catalog"] is not self.state["catalog"]:
            save_atomic(self.path("catalog.json"), catalog_to_json(new_state["catalog"]))
        if new_state["settings"] is not self.state["settings"]:
            save_atomic(self.path("settings.json"), settings_to_json(new_state["settings"]))
        self.state = new_state
        self.wake.set()
        return new_state

    def status(self):
        playlist, index = self.state["playlist"], self.state["index"]
        return {
            "ip": self.ip, "version": VERSION,
            "storage": storage_info(self.base, self.storage_kind),
            "current": {"mediaId": playlist[index] if playlist else None, "index": index,
                        "playlistLength": len(playlist)},
            "brokenIds": sorted(self.broken),
        }

    # -- playback --

    async def sleep_or_wake(self, ms):
        """True when woken by a change before `ms` passed."""
        if ms <= 0:
            return self.wake.is_set()
        try:
            await asyncio.wait_for(self.wake.wait(), ms / 1000)
            return True
        except asyncio.TimeoutError:
            return False

    async def play_item(self, media_id, slide_seconds):
        """Draw one MediaItem for its slide time; True if interrupted by a change."""
        display = self.presto.display
        with open(self.media_path(media_id), "rb") as f:
            head = f.read(HEADER_SIZE + 3 * 256)
            header = parse_bin_header(head)
            pens = [display.create_pen(r, g, b) for r, g, b in read_palette(head, header)]
            durations = []
            for i in range(header["frameCount"]):
                f.seek(frame_offset(header, i))
                durations.append(read_frame_duration(f.read(2)))
            plan = slide_plan(durations, slide_seconds)
            size, cell = header["width"], header["cellSize"]
            offset = (240 - size * cell) // 2
            display.set_pen(display.create_pen(0, 0, 0))
            display.clear()
            for _ in range(plan["loops"]):
                for i in range(header["frameCount"]):
                    started = ticks_ms()
                    f.seek(frame_offset(header, i) + 2)
                    draw_frame(display, pens, f.read(header["frameSize"]), size, cell, offset)
                    self.presto.update()
                    wait = max(20, durations[i]) - ticks_diff(ticks_ms(), started) \
                        if header["frameCount"] > 1 else 0
                    if await self.sleep_or_wake(wait):
                        return True
            return await self.sleep_or_wake(plan["holdMs"])

    async def show_info(self):
        settings = self.state["settings"]
        mode = settings["showMode"]
        if mode == "tags":
            mode += ": " + ", ".join(settings["selectedTags"])
        draw_message(self.presto, ["http://" + (self.ip or "no wifi"),
                                   "http://%s.local" % self.config["hostname"], "mode: " + mode])
        await self.sleep_or_wake(INFO_MS)

    async def play_loop(self):
        while True:
            self.wake.clear()
            if self.info_requested:
                self.info_requested = False
                await self.show_info()
                continue
            state = self.state
            playlist = state["playlist"]
            if not playlist:
                draw_message(self.presto, ["nothing to show", "mode: " + state["settings"]["showMode"],
                                           "http://" + (self.ip or "no wifi")])
                await self.sleep_or_wake(60000)
                continue
            media_id = playlist[state["index"]]
            try:
                interrupted = await self.play_item(media_id, state["settings"]["slideSeconds"])
                self.broken.discard(media_id)
            except (OSError, ValueError) as error:
                print("cannot play", media_id, error)
                self.broken.add(media_id)
                interrupted = await self.sleep_or_wake(500)
            gc.collect()
            if not interrupted and self.state is state:
                self.state = apply_command(state, {"op": "next"}, ticks_ms())

    async def touch_loop(self):
        touch = self.presto.touch
        pressed_at = None
        x = 0
        while True:
            touch.poll()
            if touch.state:
                if pressed_at is None:
                    pressed_at = ticks_ms()
                x = touch.x
            elif pressed_at is not None:
                held = ticks_diff(ticks_ms(), pressed_at)
                pressed_at = None
                if held >= LONG_PRESS_MS:
                    self.info_requested = True
                    self.wake.set()
                else:
                    self.change({"op": "next" if x >= 120 else "prev"})
            await asyncio.sleep_ms(50) if hasattr(asyncio, "sleep_ms") else await asyncio.sleep(0.05)

    async def wifi_loop(self):
        while True:
            await asyncio.sleep(30)
            if self.ip is None:
                self.ip = connect_wifi(self.config["hostname"], 10000)


# --- HTTP ---------------------------------------------------------------------------------

def error_response(status, message):
    return {"error": message}, status


def build_server(app):
    server = Microdot()
    Request.max_content_length = MAX_UPLOAD_BYTES + 4096
    web_root = app.config["webRoot"]

    def run_command(command):
        try:
            return app.change(command), None
        except KeyError:
            return None, error_response(404, "no such media")
        except ValueError as error:
            return None, error_response(400, str(error))

    @server.get("/")
    async def index(request):
        return send_file(web_root + "/index.html", max_age=0)

    @server.get("/web/<path:path>")
    async def static(request, path):
        if ".." in path:
            return error_response(404, "not found")
        return send_file(web_root + "/" + path, max_age=0)

    @server.get("/api/status")
    async def status(request):
        return app.status()

    @server.get("/api/media")
    async def list_media(request):
        return app.state["catalog"]["items"]

    @server.post("/api/media")
    async def upload(request):
        length = request.content_length or 0
        info = storage_info(app.base, app.storage_kind)
        if info["total"] and length + SPACE_MARGIN > info["free"]:
            return error_response(507, "not enough storage")
        stream = request.stream
        head = b""
        while len(head) < HEADER_SIZE and len(head) < length:
            chunk = await stream.read(min(CHUNK, length - len(head)))
            if not chunk:
                break
            head += chunk
        try:
            header = validate_upload(head, length)
        except ValueError as error:
            return error_response(400, str(error))
        media_id = allocate_media_id(app.state["catalog"], ticks_ms() ^ length)
        tmp = app.media_path(media_id) + ".tmp"
        received = len(head)
        try:
            with open(tmp, "wb") as f:
                f.write(head)
                while received < length:
                    chunk = await stream.read(min(CHUNK, length - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
            if received != length:
                raise OSError("upload interrupted")
            os.rename(tmp, app.media_path(media_id))
        except OSError as error:
            try:
                os.remove(tmp)
            except OSError:
                pass
            return error_response(400, str(error))
        args = request.args
        item = media_item(media_id, args.get("name", "untitled") or "untitled",
                          [t for t in (args.get("tags", "") or "").split(",") if t.strip()],
                          header["frameCount"], header["width"], length, int(time.time()))
        state, error = run_command({"op": "upload", "item": item})
        if error:
            os.remove(app.media_path(media_id))
            return error
        return next(i for i in state["catalog"]["items"] if i["mediaId"] == media_id), 201

    @server.get("/api/media/<media_id>/file")
    async def media_file(request, media_id):
        path = app.media_path(media_id)
        if "/" in media_id or not exists(path):
            return error_response(404, "no such media")
        return send_file(path, content_type="application/octet-stream", max_age=0)

    @server.patch("/api/media/<media_id>")
    async def patch_media(request, media_id):
        body = request.json or {}
        state = None
        if "name" in body:
            state, error = run_command({"op": "rename", "mediaId": media_id, "name": body["name"]})
            if error:
                return error
        if "tags" in body:
            state, error = run_command({"op": "setTags", "mediaId": media_id, "tags": body["tags"]})
            if error:
                return error
        if state is None:
            return error_response(400, "nothing to change")
        return next(i for i in state["catalog"]["items"] if i["mediaId"] == media_id)

    @server.delete("/api/media/<media_id>")
    async def delete_media(request, media_id):
        _, error = run_command({"op": "remove", "mediaId": media_id})
        if error:
            return error
        try:
            os.remove(app.media_path(media_id))
        except OSError:
            pass
        app.broken.discard(media_id)
        return "", 204

    @server.post("/api/media/<media_id>/show")
    async def show_media(request, media_id):
        _, error = run_command({"op": "show", "mediaId": media_id})
        return error or ("", 204)

    @server.post("/api/next")
    async def next_item(request):
        app.change({"op": "next"})
        return "", 204

    @server.post("/api/prev")
    async def prev_item(request):
        app.change({"op": "prev"})
        return "", 204

    @server.get("/api/settings")
    async def get_settings(request):
        return app.state["settings"]

    @server.put("/api/settings")
    async def put_settings(request):
        state, error = run_command({"op": "setSettings", "settings": request.json or {}})
        return error or state["settings"]

    @server.get("/api/tags")
    async def tags(request):
        return tag_counts(app.state["catalog"])

    return server


async def main_async(presto, config):
    draw_message(presto, ["starting...", "connecting to Wi-Fi"])
    app = GalleryApp(presto, config)
    app.ip = connect_wifi(config["hostname"])
    draw_message(presto, ["http://" + (app.ip or "no wifi"),
                          "http://%s.local" % config["hostname"],
                          "storage: " + app.storage_kind])
    await asyncio.sleep(4)
    server = build_server(app)
    await asyncio.gather(server.start_server(port=config["port"]), app.play_loop(),
                         app.touch_loop(), app.wifi_loop())


def run(config=None):
    from presto import Presto
    merged = dict(DEFAULT_CONFIG)
    merged.update(config or {})
    asyncio.run(main_async(Presto(ambient_light=False), merged))
