// Stratified design guard for web/js: imports go only to the same or lower layers,
// layer 5 talks only to layers 3/4 (and other layer-5 modules), no DOM/network below layer 5.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';

const DIR = new URL('../js/', import.meta.url);
const level = (file) => Number(file.match(/^l(\d)-/)[1]);
const ALLOWED = { 1: [], 2: [1], 3: [1, 2], 4: [1], 5: [3, 4, 5] };
const ACTIONS = /\b(document|window|fetch|localStorage|XMLHttpRequest|navigator)\b/;

for (const file of readdirSync(DIR).filter((f) => f.endsWith('.js'))) {
  test(`layers: ${file}`, () => {
    const source = readFileSync(new URL(file, DIR), 'utf8');
    const own = level(file);
    for (const [, target] of source.matchAll(/from '\.\/(l\d-[\w-]+\.js)'/g)) {
      assert.ok(ALLOWED[own].includes(level(target)), `${file} imports ${target}`);
    }
    if (own < 5) assert.doesNotMatch(source.replace(/\/\/.*$/gm, ''), ACTIONS);
  });
}
