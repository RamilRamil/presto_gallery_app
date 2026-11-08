"""Stratified design guard for device/gallery (and MicroPython compatibility basics)."""
import ast
from pathlib import Path

import pytest

GALLERY = Path(__file__).resolve().parents[2] / "device" / "gallery"
ALLOWED = {
    "model": set(),
    "l1_primitives": set(),
    "l2_catalog": {"model", "l1_primitives"},
    "l3_playlist": {"model", "l1_primitives", "l2_catalog"},
    "l3_scene": set(),
    "l4_codecs": {"model", "l1_primitives"},
    "l5_clock": set(),
    "l5_blit": set(),
    "l5_scene": {"l5_clock"},
    "l5_app": {"model", "l3_playlist", "l4_codecs", "l5_clock", "l5_scene", "l5_blit"},
}
IO_MODULES = {"os", "sys", "time", "network", "machine", "presto", "socket", "asyncio",
              "microdot", "random", "sdcard", "uos"}
NOT_ON_MICROPYTHON = {"dataclasses", "typing", "__future__", "enum", "pathlib"}


def parse(module):
    tree = ast.parse((GALLERY / f"{module}.py").read_text())
    internal, external = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            internal.add(node.module)
        elif isinstance(node, ast.ImportFrom):
            external.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            external.update(a.name.split(".")[0] for a in node.names)
    return internal, external, tree


@pytest.mark.parametrize("module", ALLOWED)
def test_imports_follow_layers(module):
    internal, external, _ = parse(module)
    assert internal <= ALLOWED[module], internal - ALLOWED[module]
    assert not external & NOT_ON_MICROPYTHON


@pytest.mark.parametrize("module", [m for m in ALLOWED if not m.startswith("l5_")])
def test_pure_layers_do_no_io(module):
    _, external, tree = parse(module)
    assert not external & IO_MODULES
    calls = {getattr(n.func, "id", None) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "open" not in calls and "print" not in calls


def test_pixel_module_calls_only_layer_3():
    tree = ast.parse((GALLERY.parent / "pixel.py").read_text())
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports == {"gallery.l3_scene"}
