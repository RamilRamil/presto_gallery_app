"""LAYER 5 (actions): command line, inbox/outbox scanning, file I/O, printing."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .l3_pipeline import ADAPTIVE, PRESET_PALETTES, load_source_image, make_settings, pixelize
from .l4_encoders import encode_presto_bin, encode_preview_png
from .model import PixelizeSettings

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="presto_pic_loader",
                                     description="Convert inbox/ images into Presto pixel art.")
    parser.add_argument("--inbox", type=Path, default=Path("inbox"))
    parser.add_argument("--outbox", type=Path, default=Path("outbox"))
    parser.add_argument("--grid", type=int, default=32, help="16, 32, 40, 60, 64, 80, 120 or 240")
    colors = parser.add_mutually_exclusive_group()
    colors.add_argument("--colors", type=int, default=16, help="adaptive palette size 2..256")
    colors.add_argument("--palette", choices=sorted(PRESET_PALETTES), default=None)
    parser.add_argument("--fit", choices=["crop", "fit"], default="crop")
    parser.add_argument("--background", default="#000000", help="padding/transparency color")
    parser.add_argument("--dither", action="store_true")
    parser.add_argument("--preview-scale", type=int, default=8)
    return parser.parse_args(argv)


def list_inbox(inbox: Path) -> list[Path]:
    if not inbox.is_dir():
        return []
    return sorted(p for p in inbox.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def output_names(paths: list[Path]) -> dict[Path, str]:
    """Output stem per input; a repeated stem gets its extension appended."""
    seen: set[str] = set()
    names = {}
    for path in paths:
        name = path.stem if path.stem not in seen else f"{path.stem}_{path.suffix[1:].lower()}"
        seen.add(path.stem)
        names[path] = name
    return names


def process_file(path: Path, out_name: str, outbox: Path, settings: PixelizeSettings,
                 preview_scale: int) -> str:
    source = load_source_image(path.name, path.read_bytes(), settings)
    art = pixelize(source, settings)
    (outbox / f"{out_name}.preview.png").write_bytes(encode_preview_png(art, preview_scale))
    (outbox / f"{out_name}.bin").write_bytes(encode_presto_bin(art))
    return f"{path.name} -> {out_name}.bin ({art.width}x{art.height}, {len(art.palette)} colors)"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        settings = make_settings(args.grid, args.colors, args.palette or ADAPTIVE,
                                 args.fit, args.dither, args.background)
        if not 1 <= args.preview_scale <= 64:
            raise ValueError("preview scale must be 1..64")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    paths = list_inbox(args.inbox)
    if not paths:
        print(f"no images in {args.inbox}/")
        return 0
    args.outbox.mkdir(parents=True, exist_ok=True)
    failed = 0
    for path, out_name in output_names(paths).items():
        try:
            print(process_file(path, out_name, args.outbox, settings, args.preview_scale))
        except Exception as error:  # one bad file must not stop the batch
            failed += 1
            print(f"error: {path.name}: {error}", file=sys.stderr)
    return 1 if failed else 0
