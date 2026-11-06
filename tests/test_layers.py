"""Stratified design guard: no upward imports, no skipping into L1/L2 from L5, no I/O below L5."""
import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parent.parent / "src" / "presto_pic_loader"
LEVEL = {"model": 0, "l1_primitives": 1, "l2_image_ops": 2, "l3_pipeline": 3,
         "l4_encoders": 4, "l5_actions": 5}
# Allowed imports per layer: same/lower, plus the documented exception (plan.md):
# L3/L4 may use L1 constants and tiny math directly; L5 only talks to L3/L4.
ALLOWED = {
    "model": set(),
    "l1_primitives": {"model"},
    "l2_image_ops": {"model", "l1_primitives"},
    "l3_pipeline": {"model", "l1_primitives", "l2_image_ops"},
    "l4_encoders": {"model", "l1_primitives"},
    "l5_actions": {"model", "l3_pipeline", "l4_encoders"},
}
IO_MODULES = {"os", "sys", "pathlib", "shutil", "glob", "subprocess", "argparse"}


def imports(module: str) -> tuple[set[str], set[str], bool]:
    tree = ast.parse((PACKAGE / f"{module}.py").read_text())
    internal, external, calls_open = set(), set(), False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            internal.add(node.module)
        elif isinstance(node, ast.ImportFrom):
            external.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            external.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            calls_open = True
    return internal, external, calls_open


@pytest.mark.parametrize("module", LEVEL)
def test_imports_follow_layers(module):
    internal, _, _ = imports(module)
    assert internal <= ALLOWED[module], f"{module} imports {internal - ALLOWED[module]}"


@pytest.mark.parametrize("module", [m for m, level in LEVEL.items() if level < 5])
def test_pure_layers_do_no_io(module):
    _, external, calls_open = imports(module)
    assert not external & IO_MODULES and not calls_open
