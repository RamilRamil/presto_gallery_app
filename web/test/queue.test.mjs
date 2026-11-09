import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  addToQueue, changeSetup, entrySetup, fileKind, fromRelativeView, gifSize, hasOwnSetup, MAX_QUEUE_FILES,
  nextPending, parseTags, queueSummary, referenceEntry, removeFromQueue, resetEntry, retryFailed,
  setQueueEntry, toggleTag, toRelativeView,
} from '../js/l3-pipeline.js';

const file = (name) => ({ name });

test('fileKind', () => {
  assert.equal(fileKind('scene_storm.PY'), 'scene');
  assert.equal(fileKind('cat.jpg'), 'media');
});

test('addToQueue names files, keeps duplicates, drops finished rows', () => {
  let queue = addToQueue([], [file('a b.jpg'), file('a b.jpg'), file('s.py')]);
  assert.deepEqual(queue.map((e) => [e.name, e.kind, e.state, hasOwnSetup(e)]), [
    ['a b', 'media', 'waiting', false], ['a b', 'media', 'waiting', false], ['s', 'scene', 'waiting', false],
  ]);
  assert.equal(new Set(queue.map((e) => e.id)).size, 3);
  queue = setQueueEntry(queue, queue[0].id, { state: 'done' });
  queue = addToQueue(queue, [file('c.png')]);
  assert.deepEqual(queue.map((e) => e.name), ['a b', 's', 'c']);
  assert.equal(new Set(queue.map((e) => e.id)).size, 3);
});

test('addToQueue stops at the limit', () => {
  const many = Array.from({ length: MAX_QUEUE_FILES + 5 }, (_, i) => file(`${i}.png`));
  assert.equal(addToQueue([], many).length, MAX_QUEUE_FILES);
});

test('nextPending, retry, remove and summary', () => {
  let queue = addToQueue([], [file('a.png'), file('b.png'), file('c.png')]);
  const [a, b, c] = queue;
  assert.equal(nextPending(queue).id, a.id);
  queue = setQueueEntry(queue, a.id, { state: 'done' });
  queue = setQueueEntry(queue, b.id, { state: 'failed', error: 'no space' });
  assert.equal(nextPending(queue).id, c.id);
  assert.deepEqual(queueSummary(queue), { total: 3, done: 1, failed: 1, pending: 1 });
  queue = retryFailed(removeFromQueue(queue, c.id));
  assert.deepEqual(queue.map((e) => [e.state, e.error]), [['done', null], ['waiting', null]]);
  assert.equal(nextPending(setQueueEntry(queue, b.id, { state: 'done' })), null);
});

const shared = { gridSize: 60, fitMode: 'crop', view: null, tags: '', paletteName: 'adaptive' };
const batch = (...names) => ({ queue: addToQueue([], names.map(file)), shared });
const used = (state, index) => entrySetup(state.queue[index], state.shared);

test('the reference is the first picture or GIF', () => {
  assert.equal(referenceEntry(batch('s.py', 'a.png', 'b.png').queue).name, 'a');
  assert.equal(referenceEntry(batch('s.py', 't.py').queue).name, 's');
  assert.equal(referenceEntry([]), null);
});

test('a change on the reference reaches every file following it', () => {
  const start = batch('a.png', 'b.png', 'c.png');
  const state = changeSetup(start, start.queue[0].id, { gridSize: 120, tags: 'коты' });
  assert.deepEqual([0, 1, 2].map((i) => [used(state, i).gridSize, used(state, i).tags]),
    [[120, 'коты'], [120, 'коты'], [120, 'коты']]);
  assert.equal(state.queue.some(hasOwnSetup), false);
});

test('a change on another file stays on it, value by value', () => {
  const start = batch('a.png', 'b.png', 'c.png');
  const [a, b] = start.queue;
  let state = changeSetup(start, b.id, { gridSize: 240 });
  state = changeSetup(state, a.id, { gridSize: 32, paletteName: 'pico-8' });
  assert.deepEqual([used(state, 0).gridSize, used(state, 1).gridSize, used(state, 2).gridSize], [32, 240, 32]);
  assert.equal(used(state, 1).paletteName, 'pico-8');
  assert.deepEqual([hasOwnSetup(state.queue[1]), hasOwnSetup(state.queue[2])], [true, false]);
});

test('setting a value back to the shared one follows the reference again', () => {
  const start = batch('a.png', 'b.png');
  const b = start.queue[1];
  const state = changeSetup(changeSetup(start, b.id, { gridSize: 240 }), b.id, { gridSize: 60 });
  assert.equal(hasOwnSetup(state.queue[1]), false);
});

test('resetEntry drops the own values', () => {
  const start = batch('a.png', 'b.png');
  const b = start.queue[1];
  const state = changeSetup(start, b.id, { gridSize: 240 });
  assert.equal(used({ ...state, queue: resetEntry(state.queue, b.id) }, 1).gridSize, 60);
});

test('files added later follow the reference', () => {
  const start = batch('a.png');
  const state = changeSetup(start, start.queue[0].id, { gridSize: 120 });
  const later = { ...state, queue: addToQueue(state.queue, [file('b.png')]) };
  assert.equal(used(later, 1).gridSize, 120);
});

test('the setup survives removing the reference', () => {
  const start = batch('a.png', 'b.png');
  const state = changeSetup(start, start.queue[0].id, { gridSize: 120 });
  const rest = { ...state, queue: removeFromQueue(state.queue, start.queue[0].id) };
  assert.equal(referenceEntry(rest.queue).name, 'b');
  assert.equal(used(rest, 0).gridSize, 120);
});

test('with an empty queue a change is remembered as shared', () => {
  const state = changeSetup({ queue: [], shared }, null, { gridSize: 32 });
  assert.equal(state.shared.gridSize, 32);
});

test('changing fit resets the view of those following that fit', () => {
  const view = { x: 0.2, y: 0.5, zoom: 2 };
  const start = batch('a.png', 'b.png', 'c.png');
  const [a, b, c] = start.queue;
  let state = changeSetup(start, a.id, { view });
  state = changeSetup(state, b.id, { view: { x: 0.9, y: 0.5, zoom: 3 } });
  state = changeSetup(state, c.id, { fitMode: 'fit', view: { x: 0.1, y: 0.1, zoom: 4 } });
  state = changeSetup(state, c.id, { view: { x: 0.1, y: 0.1, zoom: 4 } });
  state = changeSetup(state, a.id, { fitMode: 'fit' });
  assert.equal(used(state, 0).view, null);
  assert.equal(used(state, 1).view, null);
  assert.deepEqual(used(state, 2).view, { x: 0.1, y: 0.1, zoom: 4 });
});

test('a fit change on another file gives it the default view', () => {
  const start = batch('a.png', 'b.png');
  const [a, b] = start.queue;
  const state = changeSetup(changeSetup(start, a.id, { view: { x: 0.2, y: 0.5, zoom: 2 } }), b.id, { fitMode: 'fit' });
  assert.equal(used(state, 1).view, null);
  assert.deepEqual(used(state, 0).view, { x: 0.2, y: 0.5, zoom: 2 });
});

test('a relative view lands at the same place on a picture of another size', () => {
  const relative = toRelativeView({ centerX: 100, centerY: 50, zoom: 2 }, 400, 200);
  assert.deepEqual(relative, { x: 0.25, y: 0.25, zoom: 2 });
  assert.deepEqual(fromRelativeView(relative, 800, 400), { centerX: 200, centerY: 100, zoom: 2 });
});

test('a relative view is kept inside a picture of other proportions', () => {
  const view = fromRelativeView({ x: 0, y: 0.5, zoom: 2 }, 100, 400);
  assert.deepEqual(view, { centerX: 25, centerY: 200, zoom: 2 });
});

test('gifSize reads the header', () => {
  assert.deepEqual(gifSize(Uint8Array.from([71, 73, 70, 56, 57, 97, 44, 1, 200, 0])), { width: 300, height: 200 });
});

test('toggleTag adds, then removes', () => {
  const added = toggleTag('коты', 'зима');
  assert.equal(added, 'зима, коты');
  assert.equal(toggleTag(added, 'зима'), 'коты');
  assert.equal(toggleTag('зима', 'зима'), '');
});

test('toggleTag keeps tags typed by hand', () => {
  assert.deepEqual(parseTags(toggleTag('новый, Коты', 'зима')), ['зима', 'коты', 'новый']);
});
