# PRESTO_PIC_LOADER

Turns any PNG/JPEG/WebP into pixel art for the Pimoroni Presto (240×240).

```bash
uv venv .venv && uv pip install -p .venv -e '.[dev]'
cp ~/Pictures/cat.jpg inbox/
.venv/bin/python -m presto_pic_loader            # defaults: --grid 32 --colors 16 --fit crop
.venv/bin/python -m presto_pic_loader --grid 64 --palette pico-8 --fit fit --dither
.venv/bin/pytest
```

Results go to `outbox/`: `<name>.preview.png` (8 px per cell) and `<name>.bin`
([format](docs/bin-format.md)). Options: `--grid 16|32|64`, `--colors 2..256` or `--palette pico-8`,
`--fit crop|fit`, `--background #RRGGBB`, `--dither`, `--preview-scale N`, `--inbox`, `--outbox`.
Exit codes: 0 ok, 1 some file failed, 2 bad options.

Design: `specs/001-presto-pixelizer/` (spec, plan with layer graph), vocabulary
`knowledge/domain.okf.json`, principles `.specify/memory/constitution.md`.
