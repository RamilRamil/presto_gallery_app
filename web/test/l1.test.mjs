import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  PICO8_PALETTE, cellSize, centerSquareBox, clampChannel, colorDistance, fitInside,
  nearestColorIndex, parseHexColor, screenOffset, toHexColor,
} from '../js/l1-primitives.js';

test('clampChannel', () => {
  assert.deepEqual([-5, 0, 128, 255, 300].map(clampChannel), [0, 0, 128, 255, 255]);
});

test('colorDistance and nearestColorIndex (ties -> lowest index)', () => {
  assert.equal(colorDistance([0, 0, 0], [1, 2, 3]), 14);
  const palette = [[0, 0, 0], [255, 255, 255], [0, 0, 0]];
  assert.equal(nearestColorIndex([10, 10, 10], palette), 0);
  assert.equal(nearestColorIndex([200, 220, 240], palette), 1);
});

test('parseHexColor / toHexColor', () => {
  assert.deepEqual(parseHexColor('#FF8000'), [255, 128, 0]);
  assert.equal(toHexColor([255, 128, 0]), '#ff8000');
  for (const bad of ['#fff', 'zzzzzz', '']) assert.throws(() => parseHexColor(bad));
});

test('cellSize and screenOffset', () => {
  assert.deepEqual([16, 32, 64, 60, 240].map((g) => [cellSize(g), screenOffset(g)]),
    [[15, 0], [7, 8], [3, 24], [4, 0], [1, 0]]);
});

test('centerSquareBox and fitInside', () => {
  assert.deepEqual(centerSquareBox(100, 60), [20, 0, 80, 60]);
  assert.deepEqual(fitInside(100, 60), { side: 100, offset: [0, 20] });
});

test('PICO-8 palette', () => {
  assert.equal(PICO8_PALETTE.length, 16);
  assert.deepEqual(PICO8_PALETTE[8], [0xff, 0x00, 0x4d]);
});
