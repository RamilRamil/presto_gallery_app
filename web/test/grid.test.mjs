import { test } from 'node:test';
import assert from 'node:assert/strict';
import { GRID_SIZES, screenOffset } from '../js/l1-primitives.js';
import { checkSceneSize, gridLimits, makeSettings, MAX_SCENE_BYTES } from '../js/l3-pipeline.js';

test('every grid is accepted and full-screen grids have no margin', () => {
  for (const gridSize of GRID_SIZES) assert.equal(makeSettings({ gridSize }).gridSize, gridSize);
  assert.deepEqual([16, 40, 60, 80, 120, 240].map((g) => screenOffset(g)), [0, 0, 0, 0, 0, 0]);
  assert.throws(() => makeSettings({ gridSize: 100 }));
});

test('gridLimits', () => {
  assert.deepEqual(gridLimits(60), {
    frameBytes: 3600, maxFrames: 256, fillsScreen: true, marginPx: 0, recognizable: false,
  });
  assert.deepEqual(gridLimits(64), {
    frameBytes: 4096, maxFrames: 255, fillsScreen: false, marginPx: 24, recognizable: false,
  });
  const full = gridLimits(240);
  assert.equal(full.maxFrames, 18);
  assert.ok(full.fillsScreen && full.recognizable);
  assert.ok(gridLimits(120).recognizable);
});

test('checkSceneSize', () => {
  assert.equal(checkSceneSize(MAX_SCENE_BYTES), null);
  assert.match(checkSceneSize(MAX_SCENE_BYTES + 1), /64/);
  assert.match(checkSceneSize(0), /пуст/);
});
