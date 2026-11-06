import json
import re
from pathlib import Path

from presto_pic_loader import model

ROOT = Path(__file__).parent.parent
OKF = json.loads((ROOT / "knowledge" / "domain.okf.json").read_text())
IDS = {e["@id"] for e in OKF["entities"]}


def test_entities_follow_okf_rules():
    for entity in OKF["entities"]:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", entity["@id"])
        assert entity["name"] and entity["description"]
        for prop in entity["properties"]:
            assert re.fullmatch(r"[a-z][A-Za-z0-9]*", prop), prop


def test_relations_point_to_existing_ids():
    for relation in OKF["relations"]:
        assert relation["source"] in IDS and relation["target"] in IDS, relation


def test_code_types_are_in_dictionary():
    names = {e["name"] for e in OKF["entities"]}
    for type_name in ("RgbColor", "Size", "FitMode", "PixelizeSettings", "SourceImage",
                      "Frame", "PixelArt"):
        assert hasattr(model, type_name) and type_name in names


def test_settings_fields_match_dictionary_properties():
    def snake(name):
        return re.sub(r"([A-Z])", r"_\1", name).lower()
    props = next(e for e in OKF["entities"] if e["@id"] == "pixelize-settings")["properties"]
    fields = set(model.PixelizeSettings.__dataclass_fields__)
    assert {snake(p) for p in props} <= fields
