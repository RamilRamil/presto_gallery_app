# Tasks: Presto Pixelizer (MVP)

**Input**: plan.md, spec.md, data-model.md, contracts/, research.md
**Tests**: required by constitution III (pytest for layers 1–4 + integration run).

## Phase 1: Setup
- [x] T001 Create pyproject.toml (package presto_pic_loader in src/, deps Pillow, extra dev: pytest) and .gitignore
- [x] T002 Create project-local venv and install: `uv venv .venv && uv pip install -e '.[dev]'`
- [x] T003 [P] Create inbox/ and outbox/ with .gitkeep

## Phase 2: Foundational (blocks all stories)
- [x] T004 Data types RgbColor, Size, FitMode, PixelizeSettings, SourceImage, Frame, PixelArt in src/presto_pic_loader/model.py
- [x] T005 Layer 1 primitives (clamp_channel, color_distance, cell_size, screen_offset, center_square_box, fit_inside, parse_hex_color, PICO8_PALETTE) in src/presto_pic_loader/l1_primitives.py
- [x] T006 [P] Tests for layer 1 in tests/test_l1_primitives.py
- [x] T007 [P] Layer guard test (no upward imports, no I/O modules in l1–l4) in tests/test_layers.py
- [x] T008 [P] OKF dictionary rules + code-term match test in tests/test_okf_dictionary.py

## Phase 3: US1 — convert with defaults (P1) 🎯 MVP
Independent test: one real JPEG in inbox → 32×32 ≤16-color .bin + preview in outbox.
- [x] T009 [US1] Layer 2: to_rgb, crop_to_square, fit_to_square, downscale_to_grid, quantize_adaptive in src/presto_pic_loader/l2_image_ops.py
- [x] T010 [P] [US1] Tests for layer 2 in tests/test_l2_image_ops.py
- [x] T011 [US1] Layer 3: make_settings, load_source_image, pixelize in src/presto_pic_loader/l3_pipeline.py
- [x] T012 [P] [US1] Tests for layer 3 in tests/test_l3_pipeline.py
- [x] T013 [US1] Layer 4: encode_preview_png, encode_presto_bin, decode_presto_bin in src/presto_pic_loader/l4_encoders.py
- [x] T014 [P] [US1] Tests for layer 4 incl. byte offsets and round-trip in tests/test_l4_encoders.py
- [x] T015 [US1] Layer 5: main, parse_args, list_inbox, output_names, process_file in src/presto_pic_loader/l5_actions.py and __main__.py
- [x] T016 [US1] Integration test inbox→outbox on a real image in tests/test_integration_inbox_outbox.py

## Phase 4: US2 — tune the look (P2)
- [x] T017 [US2] quantize_to_palette (dither on/off) in src/presto_pic_loader/l2_image_ops.py + tests
- [x] T018 [US2] CLI options --grid/--colors/--palette/--fit/--background/--dither/--preview-scale with validation (exit 2) in src/presto_pic_loader/l5_actions.py + integration tests

## Phase 5: US3 — format for Presto player (P3)
- [x] T019 [US3] Byte-level format document in docs/bin-format.md (header table, palette, frames, MicroPython reading sketch)

## Phase 6: Polish
- [x] T020 README.md with usage; run full pytest; real run inbox→outbox and inspect preview

## Dependencies
T001→T002→T004→T005→(US1: T009→T011→T013→T015→T016)→US2→US3 docs (US3 can run in parallel after T013).
Parallel: test files [P] alongside their layer once the layer exists.

## Strategy
MVP = Phases 1–3; then US2 options; then US3 document.
