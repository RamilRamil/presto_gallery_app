// LAYER 4 (calculations): PixelArt <-> PrestoBinFormat v1 bytes, and RGBA rendering.
// The format abstraction barrier; byte layout in docs/bin-format.md.

import { cellSize } from './l1-primitives.js';

export const MAGIC = [0x50, 0x50, 0x58, 0x41]; // "PPXA"
export const FORMAT_VERSION = 1;
export const HEADER_SIZE = 16;
export const FLAG_LOOP = 0x01;

export function encodePrestoBin(art) {
  const frameSize = art.width * art.height;
  const size = HEADER_SIZE + 3 * art.palette.length + art.frames.length * (2 + frameSize);
  const out = new Uint8Array(size);
  const view = new DataView(out.buffer);
  out.set(MAGIC, 0);
  out[4] = FORMAT_VERSION;
  out[5] = art.frames.length > 1 ? FLAG_LOOP : 0;
  view.setUint16(6, art.width, true);
  view.setUint16(8, art.height, true);
  view.setUint16(10, art.palette.length, true);
  view.setUint16(12, art.frames.length, true);
  out[14] = cellSize(art.width);
  out[15] = 0;
  let pos = HEADER_SIZE;
  for (const color of art.palette) {
    out.set(color, pos);
    pos += 3;
  }
  for (const frame of art.frames) {
    view.setUint16(pos, frame.durationMs, true);
    out.set(frame.indices, pos + 2);
    pos += 2 + frameSize;
  }
  return out;
}

/** Reference decoder; throws Error on malformed data. */
export function decodePrestoBin(bytes) {
  if (bytes.length < HEADER_SIZE) throw new Error('file too short');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (!MAGIC.every((b, i) => bytes[i] === b) || bytes[4] !== FORMAT_VERSION) {
    throw new Error('not a PrestoBinFormat v1 file');
  }
  const width = view.getUint16(6, true);
  const height = view.getUint16(8, true);
  const paletteSize = view.getUint16(10, true);
  const frameCount = view.getUint16(12, true);
  let pos = HEADER_SIZE;
  const palette = [];
  for (let i = 0; i < paletteSize; i++, pos += 3) palette.push([bytes[pos], bytes[pos + 1], bytes[pos + 2]]);
  const frames = [];
  for (let i = 0; i < frameCount; i++) {
    if (pos + 2 + width * height > bytes.length) throw new Error('file length does not match header');
    const durationMs = view.getUint16(pos, true);
    frames.push({ indices: bytes.slice(pos + 2, pos + 2 + width * height), durationMs });
    pos += 2 + width * height;
  }
  if (pos !== bytes.length) throw new Error('file length does not match header');
  return { width, height, palette, frames };
}

/** PixelArt frame -> RgbaImage with `scale` pixels per cell (for <canvas> putImageData). */
export function renderPixelArt(art, frameIndex = 0, scale = 1) {
  const width = art.width * scale;
  const height = art.height * scale;
  const data = new Uint8ClampedArray(width * height * 4);
  const { indices } = art.frames[frameIndex];
  for (let y = 0; y < height; y++) {
    const row = Math.floor(y / scale) * art.width;
    for (let x = 0; x < width; x++) {
      const color = art.palette[indices[row + Math.floor(x / scale)]];
      const o = (y * width + x) * 4;
      data[o] = color[0];
      data[o + 1] = color[1];
      data[o + 2] = color[2];
      data[o + 3] = 255;
    }
  }
  return { width, height, data };
}
