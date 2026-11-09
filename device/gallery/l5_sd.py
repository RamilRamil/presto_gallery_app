# LAYER 5 (actions): the microSD card and moving an existing gallery onto it.

import os

SD_MOUNT = "/sd"
SD_BAUD = 12000000
DATA_TOKEN = 0xFE
DATA_POLLS = 30000
COPY_CHUNK = 4096


def open_card():
    """The card as a block device. Two corrections to the firmware's sdcard driver, both checked on
    the board: it sends commands without the stop bit, which this card never leaves idle for, and it
    sleeps while waiting for each 512-byte block, which made a full frame take 733 ms instead of 70."""
    import machine
    import sdcard

    class Card(sdcard.SDCard):
        def cmd(self, index, arg, crc, *rest, **options):
            return super().cmd(index, arg, crc | 1, *rest, **options)

        def readinto(self, buffer):
            self.cs(0)
            token = bytearray(1)
            for _ in range(DATA_POLLS):
                self.spi.readinto(token, 0xFF)
                if token[0] == DATA_TOKEN:
                    break
            else:
                self.cs(1)
                raise OSError("timeout waiting for data")
            self.spi.readinto(buffer, 0xFF)
            self.spi.readinto(bytearray(2), 0xFF)  # checksum, unused in SPI mode
            self.cs(1)
            self.spi.write(b"\xff")

    spi = machine.SPI(0, sck=machine.Pin(34, machine.Pin.OUT), mosi=machine.Pin(35, machine.Pin.OUT),
                      miso=machine.Pin(36, machine.Pin.OUT))
    return Card(spi, machine.Pin(39), baudrate=SD_BAUD)


def mount_sd():
    """Mount microSD at /sd; False when there is no card, no driver, or it runs in the simulator."""
    try:
        os.mount(os.VfsFat(open_card()), SD_MOUNT)
        return True
    except Exception as error:
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


def needs_move(source_base, target_base):
    return exists(source_base + "/catalog.json") and not exists(target_base + "/catalog.json")


def _copy_file(source, target, buffer):
    view = memoryview(buffer)
    with open(source, "rb") as reader, open(target, "wb") as writer:
        while True:
            count = reader.readinto(buffer)
            if not count:
                return
            writer.write(view[:count])


def _files_to_move(source_base):
    names = []
    for folder in ("media", "scenes"):
        for name in os.listdir(source_base + "/" + folder):
            if not name.endswith(".tmp"):
                names.append(folder + "/" + name)
    if exists(source_base + "/settings.json"):
        names.append("settings.json")
    return names + ["catalog.json"]  # last: a copy cut short has no catalog and starts over


def move_gallery(source_base, target_base, progress):
    """Copy the gallery; the originals stay. progress(done, total) is called before each file."""
    make_dirs(target_base + "/media")
    make_dirs(target_base + "/scenes")
    names = _files_to_move(source_base)
    buffer = bytearray(COPY_CHUNK)
    for done, name in enumerate(names):
        progress(done, len(names))
        _copy_file(source_base + "/" + name, target_base + "/" + name, buffer)
