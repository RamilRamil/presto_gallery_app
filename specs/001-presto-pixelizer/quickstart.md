# Quickstart
```bash
uv venv .venv && uv pip install -e '.[dev]'
cp ~/Pictures/cat.jpg inbox/
.venv/bin/python -m presto_pic_loader --grid 32 --colors 16
.venv/bin/pytest
```
