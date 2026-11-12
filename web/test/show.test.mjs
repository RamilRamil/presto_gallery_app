// CollectionShowSettings in the WebUi: what the row and the settings form say, and what the dialog sends.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { collectionShow, collectionShowSummary, ownShowNote, showForm, showPatch } from '../js/l3-show.js';

const plain = { collectionId: 'c', name: 'Фото', mediaIds: [] };

test('a Collection without own values has no summary and no note', () => {
  assert.deepEqual(collectionShow(plain), { slideSeconds: null, shuffle: null });
  assert.equal(collectionShowSummary(plain), '');
  assert.equal(ownShowNote(plain), '');
});

test('summary and note name the own values', () => {
  const own = { ...plain, slideSeconds: 60, shuffle: true };
  assert.equal(collectionShowSummary(own), '60 с · вперемешку');
  assert.equal(collectionShowSummary({ ...plain, shuffle: false }), 'по кругу');
  assert.equal(ownShowNote(own), 'У этой коллекции свои настройки: 60 с, вперемешку');
});

test('damaged stored values count as none, out of range is clamped as on the device', () => {
  assert.deepEqual(collectionShow({ ...plain, slideSeconds: '60', shuffle: 'yes' }), { slideSeconds: null, shuffle: null });
  assert.equal(collectionShow({ ...plain, slideSeconds: 9999 }).slideSeconds, 600);
  assert.equal(collectionShow({ ...plain, slideSeconds: 1 }).slideSeconds, 3);
});

test('the dialog starts from the stored values', () => {
  assert.deepEqual(showForm(plain), { seconds: '', order: 'general' });
  assert.deepEqual(showForm({ ...plain, slideSeconds: 30, shuffle: false }), { seconds: '30', order: 'loop' });
  assert.deepEqual(showForm({ ...plain, shuffle: true }), { seconds: '', order: 'shuffle' });
});

test('the dialog sends values, and null for "как в настройках"', () => {
  assert.deepEqual(showPatch({ seconds: '', order: 'general' }), { slideSeconds: null, shuffle: null });
  assert.deepEqual(showPatch({ seconds: ' 45 ', order: 'shuffle' }), { slideSeconds: 45, shuffle: true });
  assert.deepEqual(showPatch({ seconds: '2', order: 'loop' }), { slideSeconds: 3, shuffle: false });
  assert.deepEqual(showPatch({ seconds: '10.6', order: 'loop' }).slideSeconds, 11);
  assert.deepEqual(showPatch({ seconds: 'abc', order: 'general' }).slideSeconds, null);
});

test('a round trip through the dialog keeps the values', () => {
  for (const own of [plain, { ...plain, slideSeconds: 120 }, { ...plain, slideSeconds: 5, shuffle: true }]) {
    const sent = showPatch(showForm(own));
    assert.deepEqual(collectionShow({ ...plain, ...sent }), collectionShow(own));
  }
});
