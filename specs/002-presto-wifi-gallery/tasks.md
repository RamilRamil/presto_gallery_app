# Tasks: Presto Wi-Fi Gallery

**Input**: plan.md, spec.md, data-model.md, contracts/http-api.md, research.md
**Tests**: required (constitution III, VI).

## Phase 1: Setup
- [x] T001 Vendor microdot (MIT) into device/lib/microdot.py with device/lib/LICENSE-microdot
- [x] T002 [P] Create device/secrets.example.py, update .gitignore (secrets.py, .sim-storage/)

## Phase 2: Foundational — shared algorithm (blocks US1/US2)
- [x] T003 Write docs/pixelize-algorithm.md (median cut, nearest, integer Floyd–Steinberg, palette ordering)
- [x] T004 Rewrite quantization in src/presto_pic_loader/l2_image_ops.py (median_cut, map_nearest, dither_floyd_steinberg, order_palette_by_usage) + tests
- [x] T005 Add pixelize_grid(frames, settings) to src/presto_pic_loader/l3_pipeline.py; pixelize uses it; tests
- [x] T006 Golden generator src/presto_pic_loader/golden.py (L5) writing tests/golden/*.json; pytest checks files are current
- [x] T007 [P] Web L1 web/js/l1-primitives.js + web/test/l1.test.mjs
- [x] T008 Web L2 web/js/l2-image-ops.js (cropRgba, fitRgba, boxDownscale, medianCut, mapNearest, ditherFloydSteinberg) + tests
- [x] T009 Web L4 web/js/l4-encoders.js (encodePrestoBin, decodePrestoBin, renderPixelArt) + tests
- [x] T010 Web L3 web/js/l3-pipeline.js (makeSettings, pixelizeGrid, pixelize, checkLimits) + golden test web/test/golden.test.mjs
- [x] T011 [P] Web layer-import guard web/test/layers.test.mjs; device guard tests/test_device_layers.py

## Phase 3: US1 upload a picture (P1) 🎯
- [x] T012 [US1] Device data + L1 (device/gallery/model.py, l1_primitives.py) + tests/test_device_l1.py
- [x] T013 [US1] Device L2 catalog ops device/gallery/l2_catalog.py + tests
- [x] T014 [US1] Device L3 playlist + apply_command device/gallery/l3_playlist.py + tests
- [x] T015 [US1] Device L4 codecs device/gallery/l4_codecs.py + tests
- [x] T016 [US1] Device L5 app device/gallery/l5_app.py, device/main.py (wifi, storage, routes, play/touch loops)
- [x] T017 [US1] Simulator device/sim/ (fake presto/network) to run DeviceApp under CPython
- [x] T018 [US1] Web L5 web/index.html, web/style.css, web/js/l5-api.js, web/js/l5-ui.js (upload with live preview)

## Phase 4: US2 GIFs (P1)
- [x] T019 [US2] decodeGif in web/js/l2-image-ops.js + pixelizeFile in l3 + tests with Pillow-made GIF fixture

## Phase 5: US3/US4 tags, modes, library (P2)
- [x] T020 [US3] Settings panel + tag editing in web/js/l5-ui.js; /api/settings, /api/tags routes
- [x] T021 [US4] Library list with animated thumbnails, rename, delete, show now, storage info

## Phase 6: US5 touch (P3)
- [x] T022 [US5] touch_loop in device/gallery/l5_app.py (next/prev/long press info)

## Phase 7: Polish
- [x] T023 docs/device-setup.md; docs/bin-format.md flags bit0; README update
- [x] T024 End-to-end: simulator + browser upload of picture and GIF, tags, modes; full pytest + node --test
