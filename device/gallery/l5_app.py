# LAYER 5 (actions): Wi-Fi, storage, HTTP routes, display, touch, asyncio loops.
# All hardware and file access of the DeviceApp lives here; logic is in l3/l4.

import gc
import os
import time
from array import array

import asyncio
from microdot import Microdot, Request, Response, send_file
import pixel

from .l3_gesture import TAP, gesture_command, is_long_press, press_end, press_move, press_start
from .l3_playlist import (
    allocate_collection_id, allocate_media_id, apply_command, collection_by_id, item_by_id, item_speed,
    quiet_change, show_settings, slide_limit_ms, slide_plan, tag_counts, validate_settings,
)
from .l3_screen import SCREEN_SIZE, picture_margin, to_screen, to_ui
from .l4_codecs import (
    HEADER_SIZE, MAX_SCENE_BYTES, MAX_UPLOAD_BYTES, bearer_token, catalog_from_json,
    catalog_to_json, frame_offset, parse_bin_header, password_matches, read_frame_duration,
    read_palette, settings_from_json, settings_to_json, validate_scene_source, validate_upload,
)
from .l5_clock import ticks_diff, ticks_ms
from .l5_menu import run_menu
from .l5_scene import check_syntax, clear_running, make_stop, mark_running, run_scene
from .l5_sd import exists, make_dirs, mount_sd, move_gallery, needs_move
from .model import KIND_SCENE, device_state, media_item, scene_item

VERSION = "003-fullscreen-scenes"
CHUNK = 4096
SPACE_MARGIN = 64 * 1024
AUTH_RETRY_MS = 1000
NOT_RESPONDING = "not responding: restarted before its first stop() call"
FLASH_BASE = "/gallery"
SD_BASE = "/sd/gallery"

DEFAULT_CONFIG = {
    "webRoot": "/web",
    "storageBase": None,      # None: microSD (/sd/gallery) if it mounts, else /gallery
    "port": 80,
    "hostname": "presto",
    "password": None,         # None: WEB_PASSWORD from secrets.py
}


# --- storage ------------------------------------------------------------------------------

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


def choose_storage(presto):
    """(base, kind): the card when it works, first copying a gallery that lives on flash."""
    if not mount_sd():
        return FLASH_BASE, "flash"
    if needs_move(FLASH_BASE, SD_BASE):
        try:
            move_gallery(FLASH_BASE, SD_BASE, lambda done, total: draw_message(
                presto, ["moving files to microSD", "%d / %d" % (done, total)]))
        except OSError as error:  # the catalog is copied last, so the next start tries again
            print("gallery not moved:", error)
            return FLASH_BASE, "flash"
    return SD_BASE, "microSD"


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


def load_password():
    try:
        import secrets
    except ImportError:
        return ""
    return getattr(secrets, "WEB_PASSWORD", "") or ""


# --- display ------------------------------------------------------------------------------

def make_blitter(display):
    """(framebuffer, blit_frame, layout), or None when rectangles have to be used."""
    try:
        from .l5_blit import blit_frame, layout
        return memoryview(display), blit_frame, layout
    except (ImportError, TypeError):
        return None


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
    s = to_screen(1)
    for i, line in enumerate(lines):
        display.text(line, 10 * s, (20 + i * 28) * s, 220 * s, 2 * s)
    presto.update()


# --- application --------------------------------------------------------------------------

class GalleryApp:
    def __init__(self, presto, config):
        self.presto = presto
        self.config = config
        self.ip = None
        self.broken = set()
        self.wake = asyncio.Event()
        self.menu_requested = False
        self.menu_active = False
        self.paused = False
        self.redraw = None        # draws the current picture again; None during a Scene
        self.blitter = make_blitter(presto.display)
        password = config["password"]
        self.password = load_password() if password is None else password
        self.auth_slot = ticks_ms()
        pixel.bind(presto)
        base = config["storageBase"]
        kind = "custom"
        if base is None:
            base, kind = choose_storage(presto)
        self.base, self.storage_kind = base, kind
        make_dirs(base + "/media")
        make_dirs(base + "/scenes")
        catalog = catalog_from_json(load_text(self.path("catalog.json")))
        try:
            settings = validate_settings(settings_from_json(load_text(self.path("settings.json"))))
        except ValueError:
            settings = validate_settings({})
        self.state = apply_command(device_state(catalog, settings, [], 0),
                                   {"op": "setSettings", "settings": settings}, ticks_ms())
        self.apply_brightness()
        self.apply_leds()
        self.recover_stuck_scene()

    def path(self, name):
        return self.base + "/" + name

    def media_path(self, media_id):
        return self.base + "/media/" + media_id + ".bin"

    def scene_path(self, media_id):
        return self.base + "/scenes/" + media_id + ".py"

    def recover_stuck_scene(self):
        """A marker left from the last run means that Scene never reached its first stop()."""
        marker = self.path("scene.running")
        media_id = load_text(marker).strip()
        clear_running(marker)
        if media_id and item_by_id(self.state["catalog"], media_id) is not None:
            self.change({"op": "flag", "mediaId": media_id, "error": NOT_RESPONDING})

    def apply_brightness(self):
        self.presto.set_backlight(self.state["settings"]["brightness"] / 100)

    def apply_leds(self):
        """AmbientLeds: the firmware colours the LEDs from the screen edges on every update()."""
        presto = self.presto
        if not hasattr(presto, "auto_ambient_leds"):
            return
        on = self.state["settings"]["ambientLeds"]
        presto.auto_ambient_leds(on)
        if not on:  # turning auto off leaves the last colours lit
            for i in range(getattr(presto, "NUM_LEDS", 7)):
                presto.set_led_rgb(i, 0, 0, 0)

    def change(self, command):
        """Apply a command, persist what changed, wake the player (not for Brightness or AmbientLeds:
        nothing to redraw)."""
        old, new_state = self.state, apply_command(self.state, command, ticks_ms())
        if new_state["catalog"] is not old["catalog"]:
            save_atomic(self.path("catalog.json"), catalog_to_json(new_state["catalog"]))
        if new_state["settings"] is not old["settings"]:
            save_atomic(self.path("settings.json"), settings_to_json(new_state["settings"]))
        self.state = new_state
        if new_state["settings"]["brightness"] != old["settings"]["brightness"]:
            self.apply_brightness()
        if new_state["settings"]["ambientLeds"] != old["settings"]["ambientLeds"]:
            self.apply_leds()
        quiet = command["op"] in ("setBrightness", "setSettings") and new_state["playlist"] is old["playlist"] \
            and quiet_change(old["settings"], new_state["settings"])
        if not quiet:
            self.wake.set()
        return new_state

    def status(self):
        playlist, index = self.state["playlist"], self.state["index"]
        return {
            "ip": self.ip, "version": VERSION, "passwordSet": bool(self.password),
            "storage": storage_info(self.base, self.storage_kind),
            "current": {"mediaId": playlist[index] if playlist else None, "index": index,
                        "playlistLength": len(playlist)},
            "brokenIds": sorted(self.broken),
        }

    # -- playback --

    async def sleep_or_wake(self, ms):
        """True when woken by a change before `ms` passed."""
        if ms <= 0:
            await asyncio.sleep(0)  # slow frames must still let the server run
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
            draw = self.frame_drawer(pens, header)
            count, size = header["frameCount"], header["frameSize"]
            durations = []
            for i in range(count):
                f.seek(frame_offset(header, i))
                durations.append(read_frame_duration(f.read(2)))
            plan = slide_plan(durations, slide_seconds)
            frames = None
            if count > 1:
                # A 480 frame takes most of a short GIF delay to read from the card, so read them once.
                gc.collect()
                try:
                    frames = memoryview(bytearray(count * size))
                except MemoryError:
                    print("GIF frames read per frame: not enough memory")
            if frames is not None:
                for i in range(count):
                    f.seek(frame_offset(header, i) + 2)
                    f.readinto(frames[i * size:(i + 1) * size])
            frame = bytearray(size) if frames is None else frames[0:size]

            def show():
                draw(frame)
                if self.paused:
                    self.draw_pause_mark()
                self.presto.update()

            self.redraw = show
            display.set_pen(display.create_pen(0, 0, 0))
            display.clear()
            for _ in range(plan["loops"]):
                for i in range(count):
                    started = ticks_ms()
                    if frames is None:
                        f.seek(frame_offset(header, i) + 2)
                        f.readinto(frame)
                    else:
                        frame = frames[i * size:(i + 1) * size]
                    show()
                    wait = max(20, durations[i]) - ticks_diff(ticks_ms(), started) if count > 1 else 0
                    if await self.sleep_or_wake(wait):
                        return True
            return await self.sleep_or_wake(plan["holdMs"])

    def draw_pause_mark(self):
        display = self.presto.display
        display.set_pen(display.create_pen(0, 0, 0))
        s = to_screen(1)
        display.rectangle(208 * s, 8 * s, 24 * s, 24 * s)
        display.set_pen(display.create_pen(240, 240, 245))
        display.rectangle(213 * s, 13 * s, 5 * s, 14 * s)
        display.rectangle(222 * s, 13 * s, 5 * s, 14 * s)

    def frame_drawer(self, pens, header):
        """Function drawing one frame of this item, by the fastest available method."""
        size, cell = header["width"], header["cellSize"]
        offset = picture_margin(size)
        if self.blitter is None:
            display = self.presto.display
            return lambda frame: draw_frame(display, pens, frame, size, cell, offset)
        target, blit_frame, layout = self.blitter
        palette = array("H", pens + [0] * (256 - len(pens)))
        packed = layout(size, cell, offset)
        return lambda frame: blit_frame(target, frame, palette, packed)

    async def play_scene(self, media_id, playlist, slide_seconds):
        """Run one Scene for its slide time; True if interrupted or flagged."""
        display = self.presto.display
        display.set_pen(display.create_pen(0, 0, 0))
        display.clear()
        marker = self.path("scene.running")
        mark_running(marker, media_id)
        limit = slide_limit_ms(playlist, slide_seconds, self.state["settings"]["showMode"])
        stop = make_stop(self.wake, limit,
                         lambda: clear_running(marker), lambda: self.paused)
        speed = item_speed(item_by_id(self.state["catalog"], media_id))
        error = run_scene(self.scene_path(media_id), stop, speed)
        clear_running(marker)
        if error:
            print("scene failed", media_id, error)
            self.change({"op": "flag", "mediaId": media_id, "error": error})
            return True
        return await self.sleep_or_wake(0)

    async def open_menu(self):
        self.menu_active = True
        try:
            await run_menu(self)
        finally:
            self.menu_active = False

    async def play_loop(self):
        while True:
            self.wake.clear()
            if self.menu_requested:
                self.menu_requested = False
                await self.open_menu()
                continue
            state = self.state
            playlist = state["playlist"]
            if not playlist:
                draw_message(self.presto, ["nothing to show", "mode: " + state["settings"]["showMode"],
                                           "http://" + (self.ip or "no wifi")])
                await self.sleep_or_wake(60000)
                continue
            media_id = playlist[state["index"]]
            seconds = show_settings(state["catalog"], state["settings"])["slideSeconds"]
            try:
                if item_by_id(state["catalog"], media_id)["kind"] == KIND_SCENE:
                    interrupted = await self.play_scene(media_id, playlist, seconds)
                else:
                    interrupted = await self.play_item(media_id, seconds)
                self.broken.discard(media_id)
            except (OSError, ValueError) as error:
                print("cannot play", media_id, error)
                self.broken.add(media_id)
                interrupted = await self.sleep_or_wake(500)
            self.redraw = None
            gc.collect()
            current = self.state  # may differ from `state` by a Brightness change only
            if not interrupted and not self.paused and current["playlist"] is playlist \
                    and current["index"] == state["index"]:
                self.state = apply_command(current, {"op": "next"}, ticks_ms())

    def toggle_pause(self):
        self.paused = not self.paused
        if self.redraw is not None:
            self.redraw()

    def on_gesture(self, gesture):
        if gesture == TAP:
            self.toggle_pause()
            return
        command = gesture_command(gesture, self.state["settings"])
        if command is not None:
            self.change(command)

    async def touch_loop(self):
        touch = self.presto.touch
        press = None
        pressed_at = 0
        while True:
            touch.poll()
            if self.menu_active or self.menu_requested:
                press = None  # the menu reads the touch screen itself
            elif touch.state:
                if press is None:
                    press = press_start(to_ui(touch.x), to_ui(touch.y))
                    pressed_at = ticks_ms()
                else:
                    press = press_move(press, to_ui(touch.x), to_ui(touch.y),
                                       ticks_diff(ticks_ms(), pressed_at))
                if is_long_press(press):
                    self.menu_requested = True
                    self.wake.set()
            elif press is not None:
                self.on_gesture(press_end(press))
                press = None
            await asyncio.sleep_ms(50) if hasattr(asyncio, "sleep_ms") else await asyncio.sleep(0.05)

    async def wifi_loop(self):
        while True:
            await asyncio.sleep(30)
            self.ip = connect_wifi(self.config["hostname"], 10000)  # also after a lost link


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

    def tags_from(args):
        return [t for t in (args.get("tags", "") or "").split(",") if t.strip()]

    def upload_command(item, args):
        command = {"op": "upload", "item": item, "show": args.get("show") != "0"}
        if args.get("collection"):
            command["collectionId"] = args.get("collection")
        return command

    def remove_files(media_id):
        for path in (app.media_path(media_id), app.scene_path(media_id)):
            try:
                os.remove(path)
            except OSError:
                pass
        app.broken.discard(media_id)

    @server.before_request
    async def check_password(request):
        if not request.path.startswith("/api/") or not app.password:
            return None
        presented = bearer_token(request.headers.get("Authorization"))
        if password_matches(app.password, presented):
            return None
        now = ticks_ms()  # every failure takes its own one-second slot
        wait = max(0, ticks_diff(app.auth_slot, now))
        app.auth_slot = now + wait + AUTH_RETRY_MS
        if wait:
            await asyncio.sleep(wait / 1000)
        return error_response(401, "password required")

    @server.get("/")
    async def index(request):
        return send_file(web_root + "/index.html", max_age=0)

    @server.get("/web/<path:path>")
    async def static(request, path):
        target = web_root + "/" + path
        if ".." in path or "%" in path or not exists(target):
            return error_response(404, "not found")
        return send_file(target, max_age=0)

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
        item = media_item(media_id, args.get("name", "untitled") or "untitled", tags_from(args),
                          header["frameCount"], header["width"], length, int(time.time()))
        state, error = run_command(upload_command(item, args))
        if error:
            os.remove(app.media_path(media_id))
            return error
        return item_by_id(state["catalog"], media_id), 201

    @server.post("/api/scenes")
    async def upload_scene(request):
        if not app.password:
            return error_response(403, "set WEB_PASSWORD on the device to upload scenes")
        length = request.content_length or 0
        if length > MAX_SCENE_BYTES:
            return error_response(400, "scene larger than 256 KB")
        info = storage_info(app.base, app.storage_kind)
        if info["total"] and length + SPACE_MARGIN > info["free"]:
            return error_response(507, "not enough storage")
        data = b""
        while len(data) < length:
            chunk = await request.stream.read(min(CHUNK, length - len(data)))
            if not chunk:
                return error_response(400, "upload interrupted")
            data += chunk
        try:
            text = validate_scene_source(data)
            check_syntax(text)
        except ValueError as error:
            return error_response(400, str(error))
        except SyntaxError as error:
            return error_response(400, "syntax error: " + str(error))
        media_id = allocate_media_id(app.state["catalog"], ticks_ms() ^ length)
        path = app.scene_path(media_id)
        save_atomic(path, text)
        args = request.args
        item = scene_item(media_id, args.get("name", "scene") or "scene", tags_from(args),
                          length, int(time.time()))
        state, error = run_command(upload_command(item, args))
        if error:
            os.remove(path)
            return error
        return item_by_id(state["catalog"], media_id), 201

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
        edit = {"op": "editItem", "mediaId": media_id}
        for key, field in (("name", "name"), ("tags", "tags"), ("collections", "collectionIds"),
                           ("speedPercent", "speedPercent")):
            if key in body:
                edit[field] = body[key]
        if len(edit) > 2:  # one command: a bad value changes nothing, and flash is written once
            state, error = run_command(edit)
            if error:
                return error
        if body.get("flagged") is False:
            state, error = run_command({"op": "unflag", "mediaId": media_id})
            if error:
                return error
        if state is None:
            return error_response(400, "nothing to change")
        return item_by_id(state["catalog"], media_id)

    @server.delete("/api/media/<media_id>")
    async def delete_media(request, media_id):
        _, error = run_command({"op": "remove", "mediaId": media_id})
        if error:
            return error
        remove_files(media_id)
        return "", 204

    @server.post("/api/media/bulk")
    async def bulk_media(request):
        body = request.json or {}
        action = body.get("action")
        media_ids = body.get("mediaIds", [])
        if action == "delete":
            command = {"op": "removeItems", "mediaIds": media_ids}
        elif action == "addTag":
            command = {"op": "addTag", "mediaIds": media_ids, "tag": body.get("tag", "")}
        elif action == "addToCollection":
            command = {"op": "addToCollection", "mediaIds": media_ids,
                       "collectionId": body.get("collectionId", "")}
        else:
            return error_response(400, "unknown action")
        _, error = run_command(command)
        if error:
            return error
        if action == "delete":
            for media_id in media_ids:
                remove_files(media_id)
        return {"count": len(media_ids)}

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

    @server.get("/api/collections")
    async def list_collections(request):
        return app.state["catalog"]["collections"]

    @server.post("/api/collections")
    async def create_collection(request):
        collection_id = allocate_collection_id(app.state["catalog"], ticks_ms())
        name = (request.json or {}).get("name", "")
        state, error = run_command({"op": "createCollection", "collectionId": collection_id, "name": name})
        return error or (collection_by_id(state["catalog"], collection_id), 201)

    @server.patch("/api/collections/<collection_id>")
    async def patch_collection(request, collection_id):
        body = request.json or {}
        show = dict((k, body[k]) for k in ("slideSeconds", "shuffle") if k in body)
        if show:  # CollectionShowSettings; null clears a value
            command = dict(show, op="setCollectionShow", collectionId=collection_id)
        elif "speedPercent" in body:
            command = {"op": "setCollectionSpeed", "collectionId": collection_id, "speedPercent": body["speedPercent"]}
        else:
            command = {"op": "renameCollection", "collectionId": collection_id, "name": body.get("name", "")}
        state, error = run_command(command)
        return error or collection_by_id(state["catalog"], collection_id)

    @server.delete("/api/collections/<collection_id>")
    async def delete_collection(request, collection_id):
        _, error = run_command({"op": "deleteCollection", "collectionId": collection_id})
        return error or ("", 204)

    @server.post("/api/collections/<collection_id>/items")
    async def add_collection_items(request, collection_id):
        state, error = run_command({"op": "addToCollection", "collectionId": collection_id,
                                    "mediaIds": (request.json or {}).get("mediaIds", [])})
        return error or collection_by_id(state["catalog"], collection_id)

    @server.delete("/api/collections/<collection_id>/items/<media_id>")
    async def remove_collection_item(request, collection_id, media_id):
        _, error = run_command({"op": "removeFromCollection", "collectionId": collection_id,
                                "mediaId": media_id})
        return error or ("", 204)

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
    asyncio.run(main_async(Presto(ambient_light=False, full_res=SCREEN_SIZE == 480), merged))
