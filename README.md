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
([format](docs/bin-format.md)). Options: `--grid 16|32|40|60|64|80|120|240`, `--colors 2..256` or `--palette pico-8`,
`--fit crop|fit`, `--background #RRGGBB`, `--dither`, `--preview-scale N`, `--inbox`, `--outbox`.
Exit codes: 0 ok, 1 some file failed, 2 bad options.

Design: `specs/001-presto-pixelizer/` (spec, plan with layer graph), vocabulary
`knowledge/domain.okf.json`, principles `.specify/memory/constitution.md`.

## Presto Wi-Fi Gallery (feature 002)

The Presto serves a web page where you upload pictures and GIFs (converted in the browser),
tag them and choose what to show: everything, only pictures, only GIFs, or by tags.
Setup: [docs/device-setup.md](docs/device-setup.md). Try it locally without hardware:
`.venv/bin/python device/sim/run_sim.py 8080` → http://localhost:8080.
Browser and desktop share one quantization algorithm ([docs/pixelize-algorithm.md](docs/pixelize-algorithm.md)),
checked byte-for-byte by golden vectors (`tests/golden/`). Tests: `.venv/bin/pytest` and `node --test web/test/`.
