// Constitution VI: browser Stage B must reproduce the Python reference byte for byte.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { makeSettings, pixelizeGrid } from '../js/l3-pipeline.js';
import { encodePrestoBin } from '../js/l4-encoders.js';

const DIR = new URL('../../tests/golden/', import.meta.url);

function pixels(hex) {
  const bytes = Buffer.from(hex, 'hex');
  const out = [];
  for (let i = 0; i < bytes.length; i += 3) out.push([bytes[i], bytes[i + 1], bytes[i + 2]]);
  return out;
}

const files = readdirSync(DIR).filter((f) => f.endsWith('.json'));

test('golden vectors exist', () => assert.ok(files.length >= 8));

for (const file of files) {
  test(`golden ${file}`, () => {
    const vector = JSON.parse(readFileSync(new URL(file, DIR), 'utf8'));
    const art = pixelizeGrid(vector.frames.map((f) => pixels(f.pixels)),
      vector.frames.map((f) => f.durationMs), makeSettings(vector.settings));
    assert.equal(Buffer.from(encodePrestoBin(art)).toString('hex'), vector.expectedBin);
  });
}
