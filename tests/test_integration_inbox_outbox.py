"""Actions layer: real files, temp inbox/outbox."""
import io

from PIL import Image

from presto_pic_loader.l4_encoders import decode_presto_bin
from presto_pic_loader.l5_actions import main


def make_photo(path, size=(1920, 1080)):
    image = Image.new("RGB", size)
    w, h = size
    image.putdata([((x * 255) // w, (y * 255) // h, 128) for y in range(h) for x in range(w)])
    image.save(path)


def run(tmp_path, *options):
    return main(["--inbox", str(tmp_path / "inbox"), "--outbox", str(tmp_path / "outbox"),
                 *options])


def test_defaults_inbox_to_outbox(tmp_path, capsys):
    (tmp_path / "inbox").mkdir()
    make_photo(tmp_path / "inbox" / "cat.jpg")
    assert run(tmp_path) == 0
    art = decode_presto_bin((tmp_path / "outbox" / "cat.bin").read_bytes())
    assert (art.width, art.height) == (32, 32) and len(art.palette) <= 16
    preview = Image.open(tmp_path / "outbox" / "cat.preview.png")
    assert preview.size == (256, 256)
    assert "cat.jpg -> cat.bin" in capsys.readouterr().out


def test_bad_files_and_name_clash(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    make_photo(inbox / "a.png", (50, 40))
    make_photo(inbox / "a.webp", (40, 50))
    (inbox / "notes.txt").write_text("hi")
    (inbox / "broken.png").write_bytes(b"not a png")
    assert run(tmp_path, "--palette", "pico-8", "--fit", "fit", "--dither", "--grid", "64") == 1
    out = sorted(p.name for p in (tmp_path / "outbox").iterdir())
    assert out == ["a.bin", "a.preview.png", "a_webp.bin", "a_webp.preview.png"]
    assert "broken.png" in capsys.readouterr().err


def test_invalid_options_write_nothing(tmp_path):
    (tmp_path / "inbox").mkdir()
    make_photo(tmp_path / "inbox" / "x.png", (10, 10))
    assert run(tmp_path, "--grid", "20") == 2
    assert not (tmp_path / "outbox").exists()


def test_empty_inbox(tmp_path, capsys):
    (tmp_path / "inbox").mkdir()
    assert run(tmp_path) == 0
    assert "no images" in capsys.readouterr().out


def test_output_is_byte_identical(tmp_path):
    (tmp_path / "inbox").mkdir()
    make_photo(tmp_path / "inbox" / "p.png", (300, 200))
    run(tmp_path, "--dither")
    first = (tmp_path / "outbox" / "p.bin").read_bytes()
    run(tmp_path, "--dither")
    assert (tmp_path / "outbox" / "p.bin").read_bytes() == first
