// LAYER 2 (calculations): image operations on in-memory pixel buffers.
// RgbImage = {width, height, data: Uint8Array of R,G,B}; RgbaImage = same with 4 channels.
// Stage B functions follow docs/pixelize-algorithm.md exactly (shared with Python).

import {
  centerSquareBox, colorKey, compareColors, fitInside, nearestColorIndex,
} from './l1-primitives.js';

// --- Stage A: prepare (tolerance allowed) -------------------------------------------------

/** Composite RGBA onto an opaque background color. */
export function flattenRgba(image, background) {
  const { width, height, data } = image;
  const out = new Uint8Array(width * height * 3);
  for (let i = 0, j = 0; i < data.length; i += 4, j += 3) {
    const a = data[i + 3];
    for (let ch = 0; ch < 3; ch++) {
      out[j + ch] = Math.round((data[i + ch] * a + background[ch] * (255 - a)) / 255);
    }
  }
  return { width, height, data: out };
}

function copyRegion(src, left, top, width, height, dest, destX, destY) {
  for (let y = 0; y < height; y++) {
    const from = ((top + y) * src.width + left) * 3;
    const to = ((destY + y) * dest.width + destX) * 3;
    dest.data.set(src.data.subarray(from, from + width * 3), to);
  }
}

export function cropRgbWindow(image, { x, y, side }) {
  const out = { width: side, height: side, data: new Uint8Array(side * side * 3) };
  copyRegion(image, x, y, side, side, out, 0, 0);
  return out;
}

export function cropRgb(image) {
  const [left, top, right] = centerSquareBox(image.width, image.height);
  return cropRgbWindow(image, { x: left, y: top, side: right - left });
}

/** The square {x, y, side}, which may extend past the picture, filled with `background` there. */
export function fitRgbWindow(image, { x, y, side }, background) {
  const out = { width: side, height: side, data: new Uint8Array(side * side * 3) };
  for (let i = 0; i < out.data.length; i += 3) out.data.set(background, i);
  const left = Math.max(x, 0);
  const top = Math.max(y, 0);
  const right = Math.min(x + side, image.width);
  const bottom = Math.min(y + side, image.height);
  if (right > left && bottom > top) copyRegion(image, left, top, right - left, bottom - top, out, left - x, top - y);
  return out;
}

export function fitRgb(image, background) {
  const { side, offset } = fitInside(image.width, image.height);
  const out = { width: side, height: side, data: new Uint8Array(side * side * 3) };
  for (let i = 0; i < out.data.length; i += 3) out.data.set(background, i);
  copyRegion(image, 0, 0, image.width, image.height, out, offset[0], offset[1]);
  return out;
}

/** Area-average a square image down (or nearest-sample up) to size x size. */
export function boxDownscale(image, size) {
  const out = { width: size, height: size, data: new Uint8Array(size * size * 3) };
  const span = (i, total) => {
    const start = Math.floor((i * total) / size);
    return [start, Math.max(start + 1, Math.floor(((i + 1) * total) / size))];
  };
  for (let gy = 0; gy < size; gy++) {
    const [y0, y1] = span(gy, image.height);
    for (let gx = 0; gx < size; gx++) {
      const [x0, x1] = span(gx, image.width);
      const sum = [0, 0, 0];
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const p = (y * image.width + x) * 3;
          sum[0] += image.data[p];
          sum[1] += image.data[p + 1];
          sum[2] += image.data[p + 2];
        }
      }
      const count = (y1 - y0) * (x1 - x0);
      const o = (gy * size + gx) * 3;
      for (let ch = 0; ch < 3; ch++) out.data[o + ch] = Math.round(sum[ch] / count);
    }
  }
  return out;
}

/** RgbImage -> row-major array of [r, g, b]. */
export function rgbPixels(image) {
  const pixels = [];
  for (let i = 0; i < image.data.length; i += 3) {
    pixels.push([image.data[i], image.data[i + 1], image.data[i + 2]]);
  }
  return pixels;
}

// --- Stage B: exact quantization -----------------------------------------------------------

function channelRange(colors) {
  let best = [-1, 0];
  for (let ch = 0; ch < 3; ch++) {
    let min = 255;
    let max = 0;
    for (const c of colors) {
      if (c[ch] < min) min = c[ch];
      if (c[ch] > max) max = c[ch];
    }
    if (max - min > best[0]) best = [max - min, ch];
  }
  return best;
}

function boxTotal(box, counts) {
  let total = 0;
  for (const c of box) total += counts.get(colorKey(c));
  return total;
}

function boxMean(box, counts) {
  const total = boxTotal(box, counts);
  return [0, 1, 2].map((ch) => {
    let sum = 0;
    for (const c of box) sum += c[ch] * counts.get(colorKey(c));
    return Math.floor((sum + Math.floor(total / 2)) / total);
  });
}

export function medianCut(pixels, colorCount) {
  const counts = new Map();
  const unique = [];
  for (const p of pixels) {
    const key = colorKey(p);
    if (!counts.has(key)) {
      counts.set(key, 0);
      unique.push(p);
    }
    counts.set(key, counts.get(key) + 1);
  }
  unique.sort(compareColors);
  if (unique.length <= colorCount) return unique.map((c) => [...c]);
  const boxes = [unique];
  while (boxes.length < colorCount) {
    let bestIndex = -1;
    let bestRange = -1;
    let bestTotal = -1;
    boxes.forEach((box, index) => {
      if (box.length < 2) return;
      const range = channelRange(box)[0];
      const total = boxTotal(box, counts);
      if (range > bestRange || (range === bestRange && total > bestTotal)) {
        bestIndex = index;
        bestRange = range;
        bestTotal = total;
      }
    });
    if (bestIndex < 0) break;
    const channel = channelRange(boxes[bestIndex])[1];
    const box = [...boxes[bestIndex]].sort((a, b) => a[channel] - b[channel] || compareColors(a, b));
    let cumulative = 0;
    let k = 0;
    for (; k < box.length; k++) {
      cumulative += counts.get(colorKey(box[k]));
      if (2 * cumulative >= bestTotal) break;
    }
    if (k === box.length - 1) k -= 1;
    boxes[bestIndex] = box.slice(0, k + 1);
    boxes.push(box.slice(k + 1));
  }
  const palette = [];
  const seen = new Set();
  for (const box of boxes) {
    const mean = boxMean(box, counts);
    if (!seen.has(colorKey(mean))) {
      seen.add(colorKey(mean));
      palette.push(mean);
    }
  }
  return palette;
}

export function mapNearest(pixels, palette) {
  const cache = new Map();
  const out = new Uint8Array(pixels.length);
  pixels.forEach((color, i) => {
    const key = colorKey(color);
    if (!cache.has(key)) cache.set(key, nearestColorIndex(color, palette));
    out[i] = cache.get(key);
  });
  return out;
}

const FS_WEIGHTS = [[1, 0, 7], [-1, 1, 3], [0, 1, 5], [1, 1, 1]];

export function ditherFloydSteinberg(pixels, width, palette) {
  const height = pixels.length / width;
  const error = new Int32Array(pixels.length * 3);
  const out = new Uint8Array(pixels.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pos = y * width + x;
      const value = [0, 1, 2].map((ch) =>
        Math.max(0, Math.min(255, pixels[pos][ch] + error[pos * 3 + ch])));
      const index = nearestColorIndex(value, palette);
      out[pos] = index;
      const diff = [0, 1, 2].map((ch) => value[ch] - palette[index][ch]);
      for (const [dx, dy, weight] of FS_WEIGHTS) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx >= 0 && nx < width && ny < height) {
          const target = (ny * width + nx) * 3;
          for (let ch = 0; ch < 3; ch++) error[target + ch] += (diff[ch] * weight) >> 4;
        }
      }
    }
  }
  return out;
}

/** Drop unused entries, sort by usage desc then RGB asc, remap every frame. */
export function orderPaletteByUsage(palette, frames) {
  const usage = new Array(palette.length).fill(0);
  for (const frame of frames) for (const i of frame) usage[i] += 1;
  const order = palette.map((_, i) => i).filter((i) => usage[i] > 0)
    .sort((a, b) => usage[b] - usage[a] || compareColors(palette[a], palette[b]));
  const remap = new Uint8Array(256);
  order.forEach((old, index) => { remap[old] = index; });
  return {
    palette: order.map((i) => palette[i]),
    frames: frames.map((frame) => frame.map((i) => remap[i])),
  };
}

/** Stage B for one or more frames sharing one Palette. */
export function quantizeFrames(frames, width, colorCount, preset, dither) {
  const palette = preset ? preset.map((c) => [...c]) : medianCut(frames.flat(), colorCount);
  const indices = frames.map((frame) => (dither
    ? ditherFloydSteinberg(frame, width, palette)
    : mapNearest(frame, palette)));
  if (preset) return { palette, frames: indices };
  return orderPaletteByUsage(palette, indices);
}

// --- GIF decoding (GIF87a/89a, LZW, interlace, transparency, disposal 0-3) ----------------

function readSubBlocks(bytes, pos) {
  const chunks = [];
  let length = 0;
  while (bytes[pos] !== 0) {
    const size = bytes[pos];
    chunks.push(bytes.subarray(pos + 1, pos + 1 + size));
    length += size;
    pos += size + 1;
  }
  const data = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    data.set(chunk, offset);
    offset += chunk.length;
  }
  return { data, next: pos + 1 };
}

function readColorTable(bytes, pos, size) {
  const table = [];
  for (let i = 0; i < size; i++) table.push(bytes.subarray(pos + 3 * i, pos + 3 * i + 3));
  return table;
}

export function lzwDecode(data, minCodeSize, pixelCount) {
  const clear = 1 << minCodeSize;
  const end = clear + 1;
  const prefix = new Int32Array(4096);
  const suffix = new Uint8Array(4096);
  const first = new Uint8Array(4096);
  const stack = new Uint8Array(4097);
  const out = new Uint8Array(pixelCount);
  for (let i = 0; i < clear; i++) {
    prefix[i] = -1;
    suffix[i] = i;
    first[i] = i;
  }
  let codeSize = minCodeSize + 1;
  let next = end + 1;
  let previous = -1;
  let bitBuffer = 0;
  let bitCount = 0;
  let outPos = 0;
  for (let bytePos = 0; bytePos < data.length && outPos < pixelCount;) {
    while (bitCount < codeSize && bytePos < data.length) {
      bitBuffer |= data[bytePos++] << bitCount;
      bitCount += 8;
    }
    if (bitCount < codeSize) break;
    const code = bitBuffer & ((1 << codeSize) - 1);
    bitBuffer >>>= codeSize;
    bitCount -= codeSize;
    if (code === clear) {
      codeSize = minCodeSize + 1;
      next = end + 1;
      previous = -1;
      continue;
    }
    if (code === end) break;
    let current = code;
    let top = 0;
    if (previous === -1) {
      out[outPos++] = suffix[code];
      previous = code;
      continue;
    }
    if (code >= next) { // KwKwK case
      stack[top++] = first[previous];
      current = previous;
    }
    while (current >= clear) {
      stack[top++] = suffix[current];
      current = prefix[current];
    }
    stack[top++] = suffix[current];
    if (next < 4096) {
      prefix[next] = previous;
      suffix[next] = suffix[current];
      first[next] = first[previous];
      next += 1;
      if (next === 1 << codeSize && codeSize < 12) codeSize += 1;
    }
    while (top > 0 && outPos < pixelCount) out[outPos++] = stack[--top];
    previous = code;
  }
  return out;
}

function deinterlaceRows(height) {
  const rows = [];
  for (const [start, step] of [[0, 8], [4, 8], [2, 4], [1, 2]]) {
    for (let y = start; y < height; y += step) rows.push(y);
  }
  return rows;
}

/** GIF bytes -> {width, height, frames: [{image: RgbaImage, delayMs}]} (full composited frames). */
export function decodeGif(bytes) {
  const signature = String.fromCharCode(...bytes.subarray(0, 6));
  if (signature !== 'GIF87a' && signature !== 'GIF89a') throw new Error('not a GIF file');
  const width = bytes[6] | (bytes[7] << 8);
  const height = bytes[8] | (bytes[9] << 8);
  const packed = bytes[10];
  let pos = 13;
  let globalTable = null;
  if (packed & 0x80) {
    const size = 1 << ((packed & 7) + 1);
    globalTable = readColorTable(bytes, pos, size);
    pos += 3 * size;
  }
  const canvas = new Uint8ClampedArray(width * height * 4);
  const frames = [];
  let control = { disposal: 0, delayMs: 0, transparent: -1 };
  let pendingDisposal = null;
  while (pos < bytes.length) {
    const block = bytes[pos++];
    if (block === 0x3b) break;
    if (block === 0x21) {
      const label = bytes[pos++];
      if (label === 0xf9) {
        const flags = bytes[pos + 1];
        control = {
          disposal: (flags >> 2) & 7,
          delayMs: (bytes[pos + 2] | (bytes[pos + 3] << 8)) * 10,
          transparent: flags & 1 ? bytes[pos + 4] : -1,
        };
      }
      pos = readSubBlocks(bytes, pos).next;
      continue;
    }
    if (block !== 0x2c) throw new Error(`bad GIF block 0x${block.toString(16)}`);
    const left = bytes[pos] | (bytes[pos + 1] << 8);
    const top = bytes[pos + 2] | (bytes[pos + 3] << 8);
    const w = bytes[pos + 4] | (bytes[pos + 5] << 8);
    const h = bytes[pos + 6] | (bytes[pos + 7] << 8);
    const flags = bytes[pos + 8];
    pos += 9;
    let table = globalTable;
    if (flags & 0x80) {
      const size = 1 << ((flags & 7) + 1);
      table = readColorTable(bytes, pos, size);
      pos += 3 * size;
    }
    if (!table) throw new Error('GIF frame without color table');
    const minCodeSize = bytes[pos++];
    const { data, next } = readSubBlocks(bytes, pos);
    pos = next;
    if (pendingDisposal) pendingDisposal();
    pendingDisposal = null;
    if (control.disposal === 3) {
      const saved = canvas.slice();
      pendingDisposal = () => canvas.set(saved);
    }
    const indices = lzwDecode(data, minCodeSize, w * h);
    const rows = flags & 0x40 ? deinterlaceRows(h) : null;
    for (let row = 0; row < h; row++) {
      const y = top + (rows ? rows[row] : row);
      if (y >= height) continue;
      for (let x = 0; x < w; x++) {
        const index = indices[row * w + x];
        if (index === control.transparent || left + x >= width) continue;
        const color = table[index] || [0, 0, 0];
        const o = (y * width + left + x) * 4;
        canvas[o] = color[0];
        canvas[o + 1] = color[1];
        canvas[o + 2] = color[2];
        canvas[o + 3] = 255;
      }
    }
    frames.push({ image: { width, height, data: canvas.slice() }, delayMs: control.delayMs });
    if (control.disposal === 2) {
      pendingDisposal = () => {
        for (let y = top; y < Math.min(height, top + h); y++) {
          canvas.fill(0, (y * width + left) * 4, (y * width + Math.min(width, left + w)) * 4);
        }
      };
    }
    control = { disposal: 0, delayMs: 0, transparent: -1 };
  }
  if (!frames.length) throw new Error('GIF has no frames');
  return { width, height, frames };
}
