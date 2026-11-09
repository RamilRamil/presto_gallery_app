from gallery import l5_sd


def make_gallery(base):
    (base / "media").mkdir(parents=True)
    (base / "scenes").mkdir()
    (base / "media" / "a.bin").write_bytes(bytes(range(256)) * 40)
    (base / "media" / "b.bin.tmp").write_bytes(b"partial")
    (base / "scenes" / "s.py").write_text("def run(stop): pass")
    (base / "settings.json").write_text("{}")
    (base / "catalog.json").write_text('{"items": []}')


def test_needs_move(tmp_path):
    flash, card = tmp_path / "flash", tmp_path / "card"
    assert not l5_sd.needs_move(str(flash), str(card))
    make_gallery(flash)
    assert l5_sd.needs_move(str(flash), str(card))
    card.mkdir()
    (card / "catalog.json").write_text("{}")
    assert not l5_sd.needs_move(str(flash), str(card))


def test_move_copies_everything_and_keeps_originals(tmp_path):
    flash, card = tmp_path / "flash", tmp_path / "card"
    make_gallery(flash)
    calls = []
    l5_sd.move_gallery(str(flash), str(card), lambda done, total: calls.append((done, total)))
    assert (card / "media" / "a.bin").read_bytes() == (flash / "media" / "a.bin").read_bytes()
    assert (card / "scenes" / "s.py").exists() and (card / "settings.json").exists()
    assert (card / "catalog.json").exists() and (flash / "catalog.json").exists()
    assert not (card / "media" / "b.bin.tmp").exists()
    assert calls == [(n, 4) for n in range(4)]


def test_catalog_is_copied_last_so_a_cut_copy_starts_over(tmp_path):
    flash, card = tmp_path / "flash", tmp_path / "card"
    make_gallery(flash)
    seen = []

    def stop_before_last(done, total):
        seen.append(done)
        if done == total - 1:
            raise OSError("card removed")

    try:
        l5_sd.move_gallery(str(flash), str(card), stop_before_last)
    except OSError:
        pass
    assert len(seen) == 4
    assert l5_sd.needs_move(str(flash), str(card))


def test_other_files_on_the_card_stay(tmp_path):
    flash, card = tmp_path / "flash", tmp_path / "card" / "gallery"
    make_gallery(flash)
    card.parent.mkdir()
    (card.parent / "photo.jpg").write_bytes(b"mine")
    l5_sd.move_gallery(str(flash), str(card), lambda done, total: None)
    assert (card.parent / "photo.jpg").read_bytes() == b"mine"
