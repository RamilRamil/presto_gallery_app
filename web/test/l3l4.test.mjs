import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  binByteSize, checkLimits, frameDuration, makeSettings, nameFromFile, parseTags, pixelizeFile,
  pixelizeGrid,
} from '../js/l3-pipeline.js';
import { decodePrestoBin, encodePrestoBin, renderPixelArt } from '../js/l4-encoders.js';

const ART = {
  width: 2, height: 2, palette: [[1, 2, 3], [250, 251, 252]],
  frames: [{ indices: new Uint8Array([0, 1, 1, 0]), durationMs: 0 }],
};

test('makeSettings defaults and validation', () => {
  const s = makeSettings();
  assert.equal(s.gridSize, 32);
  assert.equal(s.colorCount, 16);
  assert.equal(makeSettings({ paletteName: 'pico-8' }).colorCount, 16);
  for (const bad of [{ gridSize: 20 }, { colorCount: 1 }, { paletteName: 'nes' }, { fitMode: 'x' },
    { backgroundColor: 'red' }]) {
    assert.throws(() => makeSettings(bad));
  }
});

test('encodePrestoBin byte layout', () => {
  const data = encodePrestoBin(ART);
  assert.deepEqual([...data.subarray(0, 16)], [0x50, 0x50, 0x58, 0x41, 1, 0, 2, 0, 2, 0, 2, 0, 1, 0, 120, 0]);
  assert.deepEqual([...data.subarray(16)], [1, 2, 3, 250, 251, 252, 0, 0, 0, 1, 1, 0]);
  assert.equal(binByteSize(ART), data.length);
});

test('round trip with frames sets loop flag', () => {
  const art = { ...ART, frames: [...ART.frames, { indices: new Uint8Array([1, 1, 0, 0]), durationMs: 120 }] };
  const data = encodePrestoBin(art);
  assert.equal(data[5], 1);
  const back = decodePrestoBin(data);
  assert.deepEqual(back.palette, art.palette);
  assert.deepEqual(back.frames.map((f) => [[...f.indices], f.durationMs]), [[[0, 1, 1, 0], 0], [[1, 1, 0, 0], 120]]);
  assert.throws(() => decodePrestoBin(data.subarray(0, data.length - 1)));
});

test('renderPixelArt scales cells', () => {
  const image = renderPixelArt(ART, 0, 2);
  assert.equal(image.width, 4);
  assert.deepEqual([...image.data.subarray(0, 4)], [1, 2, 3, 255]);
  assert.deepEqual([...image.data.subarray(8, 12)], [250, 251, 252, 255]);
});

test('pixelizeFile image: crop to grid', () => {
  const data = new Uint8ClampedArray(64 * 40 * 4).fill(255);
  const art = pixelizeFile('image', { width: 64, height: 40, data }, makeSettings({ gridSize: 16 }));
  assert.equal(art.width, 16);
  assert.deepEqual(art.palette, [[255, 255, 255]]);
});

test('frameDuration and checkLimits', () => {
  assert.deepEqual([0, 10, 100].map(frameDuration), [100, 20, 100]);
  assert.equal(checkLimits(ART), null);
  const big = { ...ART, frames: Array(300).fill(ART.frames[0]) };
  assert.match(checkLimits(big), /too many frames/);
});

test('pixelizeGrid keeps durations', () => {
  const art = pixelizeGrid([[[0, 0, 0]], [[9, 9, 9]]], [100, 50], makeSettings({ gridSize: 16 }));
  assert.deepEqual(art.frames.map((f) => f.durationMs), [100, 50]);
});

test('parseTags and nameFromFile', () => {
  assert.deepEqual(parseTags('Коты,  Winter   sky , коты,,'), ['winter sky', 'коты']);
  assert.deepEqual(parseTags('a/b'), ['ab']);
  assert.equal(nameFromFile('cat photo.jpg'), 'cat photo');
  assert.equal(nameFromFile('.gif'), 'untitled');
});
