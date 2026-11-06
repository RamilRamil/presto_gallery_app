import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  boxDownscale, cropRgb, decodeGif, ditherFloydSteinberg, fitRgb, flattenRgba, mapNearest,
  medianCut, orderPaletteByUsage, quantizeFrames, rgbPixels,
} from '../js/l2-image-ops.js';
import { PICO8_PALETTE } from '../js/l1-primitives.js';

const RED = [255, 0, 0];
const BLACK = [0, 0, 0];
const WHITE = [255, 255, 255];
const GOLDEN = new URL('../../tests/golden/', import.meta.url);

function rgb(width, height, fn) {
  const data = new Uint8Array(width * height * 3);
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) data.set(fn(x, y), (y * width + x) * 3);
  return { width, height, data };
}

test('flattenRgba composites onto background', () => {
  const image = { width: 2, height: 1, data: new Uint8ClampedArray([0, 0, 0, 0, 0, 0, 255, 255]) };
  assert.deepEqual([...flattenRgba(image, RED).data], [255, 0, 0, 0, 0, 255]);
});

test('cropRgb and fitRgb', () => {
  const image = rgb(6, 2, (x) => [x, 0, 0]);
  assert.deepEqual(rgbPixels(cropRgb(image)).map((p) => p[0]), [2, 3, 2, 3]);
  const fitted = fitRgb(rgb(2, 1, () => WHITE), RED);
  assert.deepEqual(rgbPixels(fitted), [WHITE, WHITE, RED, RED]);
});

test('boxDownscale averages and upscales', () => {
  const image = rgb(4, 4, (x) => (x < 2 ? [200, 200, 200] : BLACK));
  assert.deepEqual(rgbPixels(boxDownscale(image, 2)), [[200, 200, 200], BLACK, [200, 200, 200], BLACK]);
  assert.equal(boxDownscale(rgb(3, 3, () => RED), 16).data.length, 16 * 16 * 3);
});

test('medianCut matches documented examples', () => {
  assert.deepEqual(medianCut([RED, BLACK, RED], 16), [BLACK, RED]);
  const pixels = [...Array(3).fill(BLACK), [10, 0, 0], [200, 0, 0], [200, 0, 0]];
  assert.deepEqual(medianCut(pixels, 2), [BLACK, [137, 0, 0]]);
});

test('mapNearest and ditherFloydSteinberg', () => {
  assert.deepEqual([...mapNearest([[250, 5, 70], [3, 3, 3]], PICO8_PALETTE)], [8, 0]);
  const gray = Array(4).fill([128, 128, 128]);
  assert.deepEqual([...ditherFloydSteinberg(gray, 2, [BLACK, WHITE])], [1, 0, 0, 1]);
});

test('orderPaletteByUsage and quantizeFrames', () => {
  const ordered = orderPaletteByUsage([RED, BLACK, WHITE], [new Uint8Array([1, 1, 0]), new Uint8Array([1])]);
  assert.deepEqual(ordered.palette, [BLACK, RED]);
  assert.deepEqual(ordered.frames.map((f) => [...f]), [[0, 0, 1], [0]]);
  const result = quantizeFrames([Array(4).fill(RED), Array(4).fill(BLACK)], 2, 16, null, false);
  assert.deepEqual(result.palette, [BLACK, RED]);
});

for (const name of ['anim-small', 'anim-interlaced']) {
  test(`decodeGif reproduces Pillow-made ${name}.gif`, () => {
    const bytes = new Uint8Array(readFileSync(new URL(`gif/${name}.gif`, GOLDEN)));
    const expected = JSON.parse(readFileSync(new URL(`gif/${name}.json`, GOLDEN), 'utf8'));
    const gif = decodeGif(bytes);
    assert.equal(gif.width, expected.width);
    assert.equal(gif.frames.length, expected.frames.length);
    gif.frames.forEach((frame, i) => {
      const flat = flattenRgba(frame.image, BLACK);
      assert.equal(Buffer.from(flat.data).toString('hex'), expected.frames[i].pixels, `frame ${i}`);
      assert.equal(frame.delayMs, expected.frames[i].delayMs);
    });
  });
}

test('decodeGif rejects non-GIF', () => {
  assert.throws(() => decodeGif(new Uint8Array([1, 2, 3, 4, 5, 6, 7])), /not a GIF/);
});
