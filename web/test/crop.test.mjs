import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  centerSquareBox, clampCropView, cropWindow, defaultCropView, MAX_CROP_ZOOM, panCropView,
  zoomCropView,
} from '../js/l1-primitives.js';
import { cropRgb, cropRgbWindow, fitRgb, fitRgbWindow, rgbPixels } from '../js/l2-image-ops.js';
import { makeSettings, pixelize } from '../js/l3-pipeline.js';

test('default view equals the center crop for even and odd sizes', () => {
  for (const [width, height] of [[100, 50], [51, 100], [33, 33], [101, 40]]) {
    const { x, y, side } = cropWindow(defaultCropView(width, height), width, height);
    assert.deepEqual([x, y, x + side, y + side], centerSquareBox(width, height));
  }
});

test('the view never leaves the picture', () => {
  const start = defaultCropView(200, 100);
  assert.equal(panCropView(start, -500, 0, 200, 100).centerX, 50);
  assert.equal(panCropView(start, 500, 500, 200, 100).centerX, 150);
  assert.equal(panCropView(start, 0, 500, 200, 100).centerY, 50);
  const zoomed = zoomCropView(start, 4, 100, 50, 200, 100);
  const corner = panCropView(zoomed, 1000, 1000, 200, 100);
  assert.deepEqual(cropWindow(corner, 200, 100), { x: 175, y: 75, side: 25 });
});

test('zoom limits and clamping', () => {
  const start = defaultCropView(200, 100);
  assert.equal(zoomCropView(start, 100, 100, 50, 200, 100).zoom, MAX_CROP_ZOOM);
  assert.equal(zoomCropView(start, 0.1, 100, 50, 200, 100).zoom, 1);
  assert.equal(clampCropView({ centerX: 0, centerY: 0, zoom: 0 }, 200, 100).zoom, 1);
});

test('zoom keeps the anchor point in place', () => {
  const view = zoomCropView({ centerX: 100, centerY: 100, zoom: 1 }, 2, 50, 100, 200, 200);
  assert.deepEqual(view, { centerX: 75, centerY: 100, zoom: 2 });
  const { x, side } = cropWindow(view, 200, 200);
  assert.equal(x, 25);
  assert.equal(((50 - x) / side), 0.25); // the same fraction as (50 - 0) / 200 before zooming
});

function image(width, height) {
  const data = new Uint8Array(width * height * 3);
  for (let i = 0; i < width * height; i += 1) data[i * 3] = i;
  return { width, height, data };
}

test('cropRgbWindow copies exactly the window, and cropRgb is its default', () => {
  const source = image(4, 2);
  assert.deepEqual(rgbPixels(cropRgbWindow(source, { x: 2, y: 0, side: 2 })).map((p) => p[0]), [2, 3, 6, 7]);
  assert.deepEqual(cropRgb(source), cropRgbWindow(source, { x: 1, y: 0, side: 2 }));
});

test('pixelize uses the view, and the default view changes nothing', () => {
  const picture = { width: 16, height: 8, data: new Uint8Array(16 * 8 * 3) };
  for (let i = 0; i < 16 * 8; i += 1) {
    picture.data.set((i % 16) < 8 ? [255, 0, 0] : [0, 0, 255], i * 3);
  }
  const settings = makeSettings({ gridSize: 16, colorCount: 4 });
  assert.deepEqual(pixelize([picture], [0], settings, defaultCropView(16, 8)),
    pixelize([picture], [0], settings));
  const leftOnly = pixelize([picture], [0], settings, { centerX: 4, centerY: 4, zoom: 1 });
  assert.deepEqual(leftOnly.palette, [[255, 0, 0]]);
});

test('fit: default view equals the existing fit for even and odd sizes', () => {
  const background = [9, 8, 7];
  for (const [width, height] of [[6, 3], [5, 2], [3, 7], [4, 4]]) {
    const picture = image(width, height);
    const window = cropWindow(defaultCropView(width, height), width, height, true);
    assert.deepEqual(fitRgbWindow(picture, window, background), fitRgb(picture, background));
  }
});

test('fit: the picture moves within its margins, not past them', () => {
  const start = defaultCropView(200, 100);
  assert.deepEqual(panCropView(start, 0, 500, 200, 100, true), { centerX: 100, centerY: 100, zoom: 1 });
  assert.deepEqual(panCropView(start, 500, -500, 200, 100, true), { centerX: 100, centerY: 0, zoom: 1 });
  assert.deepEqual(cropWindow({ centerX: 100, centerY: 0, zoom: 1 }, 200, 100, true), { x: 0, y: -100, side: 200 });
});

test('fit: zoom enlarges inside the square, then it pans like a crop', () => {
  const zoomed = zoomCropView(defaultCropView(200, 100), 2, 100, 50, 200, 100, true);
  assert.deepEqual(cropWindow(zoomed, 200, 100, true), { x: 50, y: 0, side: 100 });
  const edge = panCropView(zoomed, 1000, 1000, 200, 100, true);
  assert.deepEqual(cropWindow(edge, 200, 100, true), { x: 100, y: 0, side: 100 });
  assert.equal(zoomCropView(zoomed, 100, 100, 50, 200, 100, true).zoom, MAX_CROP_ZOOM);
});

test('fitRgbWindow fills only what the picture does not cover', () => {
  const picture = { width: 2, height: 1, data: Uint8Array.from([1, 1, 1, 2, 2, 2]) };
  const placed = fitRgbWindow(picture, { x: 0, y: -1, side: 2 }, [9, 9, 9]);
  assert.deepEqual(rgbPixels(placed).map((p) => p[0]), [9, 9, 1, 2]);
  const inside = fitRgbWindow(picture, { x: 1, y: 0, side: 1 }, [9, 9, 9]);
  assert.deepEqual(rgbPixels(inside).map((p) => p[0]), [2]);
  const outside = fitRgbWindow(picture, { x: 5, y: 5, side: 1 }, [9, 9, 9]);
  assert.deepEqual(rgbPixels(outside).map((p) => p[0]), [9]);
});

test('pixelize uses the view in fit mode', () => {
  const picture = { width: 16, height: 8, data: new Uint8Array(16 * 8 * 3) };
  for (let i = 0; i < 16 * 8; i += 1) picture.data.set([255, 0, 0], i * 3);
  const settings = makeSettings({ gridSize: 16, colorCount: 4, fitMode: 'fit', backgroundColor: '#0000ff' });
  const atDefault = pixelize([picture], [0], settings, defaultCropView(16, 8));
  assert.deepEqual(atDefault, pixelize([picture], [0], settings));
  const zoomed = pixelize([picture], [0], settings, { centerX: 8, centerY: 4, zoom: 2 });
  assert.deepEqual(zoomed.palette, [[255, 0, 0]]);
});
