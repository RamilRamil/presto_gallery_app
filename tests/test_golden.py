import json
from pathlib import Path

from presto_pic_loader.golden import GOLDEN_DIR, build_all
from presto_pic_loader.l4_encoders import decode_presto_bin


def test_golden_files_are_current():
    for vector in build_all():
        path = GOLDEN_DIR / f"{vector['name']}.json"
        assert json.loads(path.read_text()) == vector, \
            f"{path.name} outdated: run python -m presto_pic_loader.golden"


def test_golden_bins_decode():
    for path in Path(GOLDEN_DIR).glob("*.json"):
        vector = json.loads(path.read_text())
        art = decode_presto_bin(bytes.fromhex(vector["expectedBin"]))
        assert len(art.frames) == len(vector["frames"])
