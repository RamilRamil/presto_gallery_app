# Pixelize algorithm (shared by desktop Python and browser JS)

Two stages. Terms: `knowledge/domain.okf.json`.

## Stage A — prepare (platform-dependent)

Decode SourceImage → RGB (alpha flattened onto `backgroundColor`), square it (FitMode `crop`:
centered square; `fit`: pad to square with `backgroundColor`), area-average down to
`gridSize × gridSize`. Desktop uses Pillow (`BOX`); browser uses its image decoder + `boxDownscale`.
Small differences (±a few levels per channel) are allowed here.

## Stage B — quantize (exact, must be byte-identical everywhere)

Input: one or more frames of `gridSize²` RGB pixels (0..255 integers). Output: Palette + indices.
Verified by golden vectors in `tests/golden/`.

### 1. Palette
- Preset (`pico-8`): fixed, canonical order. Skip to step 2.
- Adaptive, `colorCount = n`, **median cut** over the pixels of *all* frames:
  1. Histogram: unique colors with pixel counts.
  2. If unique colors ≤ n: candidate palette = unique colors. Otherwise start with one box holding
     all unique colors and repeat until there are n boxes:
     - Splittable boxes have ≥ 2 unique colors; none → stop.
     - Pick the box with the largest channel range (max − min over its colors, the widest of R, G, B);
       ties → larger total pixel count → lower box index.
     - Its split channel is the widest one (ties in order R, G, B). Sort its colors by
       (that channel, R, G, B) ascending.
     - Split after the first position `k` where `2 · cumulativeCount ≥ totalCount`; if `k` is the
       last position use `k − 1`. Lower part replaces the box in place, upper part is appended.
     - Candidate color of a box = per-channel weighted mean, rounded: `(sum + total // 2) // total`.
  3. Remove duplicate candidates, keeping the first.

### 2. Mapping
- `nearest(c)` = index with smallest squared RGB distance; ties → lowest index.
- No dithering: each pixel → `nearest(pixel)`.
- Dithering (Floyd–Steinberg, integer): per frame keep an integer error buffer per channel,
  scan rows top→bottom, pixels left→right. For each pixel `v = clamp(pixel + error, 0, 255)`,
  `i = nearest(v)`, `e = v − palette[i]` per channel, then add to neighbours
  `(e·7) >> 4` right, `(e·3) >> 4` down-left, `(e·5) >> 4` down, `(e·1) >> 4` down-right
  (`>>` = arithmetic shift, floors negatives), skipping neighbours outside the frame.

### 3. Palette order (adaptive only)
Count how many pixels (all frames) use each entry; drop unused entries; sort by count descending,
then (R, G, B) ascending; remap indices. Preset palettes keep their order and unused entries.
