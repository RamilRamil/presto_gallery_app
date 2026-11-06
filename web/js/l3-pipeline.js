// LAYER 3 (calculations): pixelize pipeline. Port of src/presto_pic_loader/l3_pipeline.py.
// PixelArt = {width, height, palette: [RgbColor], frames: [{indices: Uint8Array, durationMs}]}.

import { GRID_SIZES, PICO8_PALETTE, parseHexColor } from './l1-primitives.js';
import {
  boxDownscale, cropRgb, decodeGif, fitRgb, flattenRgba, quantizeFrames, rgbPixels,
} from './l2-image-ops.js';

export const PRESET_PALETTES = { 'pico-8': PICO8_PALETTE };
export const ADAPTIVE = 'adaptive';
export const MAX_FRAMES = 256;
export const MAX_BIN_BYTES = 1024 * 1024;
export const MIN_FRAME_MS = 20;
export const DEFAULT_FRAME_MS = 100;

/** Validate raw option values; throws Error with a user-facing message. */
export function makeSettings({
  gridSize = 32, colorCount = 16, paletteName = ADAPTIVE, fitMode = 'crop',
  dither = false, backgroundColor = '#000000',
} = {}) {
  if (!GRID_SIZES.includes(gridSize)) {
    throw new Error(`grid size must be one of ${GRID_SIZES.join(', ')}, got ${gridSize}`);
  }
  if (paletteName !== ADAPTIVE && !(paletteName in PRESET_PALETTES)) {
    throw new Error(`unknown palette ${JSON.stringify(paletteName)}`);
  }
  const presetPalette = PRESET_PALETTES[paletteName] || null;
  if (!presetPalette && !(Number.isInteger(colorCount) && colorCount >= 2 && colorCount <= 256)) {
    throw new Error(`color count must be 2..256, got ${colorCount}`);
  }
  if (fitMode !== 'crop' && fitMode !== 'fit') {
    throw new Error(`fit mode must be 'crop' or 'fit', got ${JSON.stringify(fitMode)}`);
  }
  return Object.freeze({
    gridSize,
    colorCount: presetPalette ? presetPalette.length : colorCount,
    paletteName,
    presetPalette,
    fitMode,
    dither: Boolean(dither),
    backgroundColor: parseHexColor(backgroundColor),
  });
}

/** Stage B: grid-sized pixel frames -> PixelArt (exact, shared with Python). */
export function pixelizeGrid(frames, durationsMs, settings) {
  const size = settings.gridSize;
  const result = quantizeFrames(frames, size, settings.colorCount, settings.presetPalette,
    settings.dither);
  return {
    width: size,
    height: size,
    palette: result.palette,
    frames: result.frames.map((indices, i) => ({ indices, durationMs: durationsMs[i] })),
  };
}

/** Stage A + B: RGB images (any size) -> PixelArt. */
export function pixelize(images, durationsMs, settings) {
  const grids = images.map((image) => {
    const square = settings.fitMode === 'crop' ? cropRgb(image) : fitRgb(image, settings.backgroundColor);
    return rgbPixels(boxDownscale(square, settings.gridSize));
  });
  return pixelizeGrid(grids, durationsMs, settings);
}

export function frameDuration(delayMs) {
  return delayMs > 0 ? Math.max(MIN_FRAME_MS, delayMs) : DEFAULT_FRAME_MS;
}

/** kind 'gif': input is GIF bytes; kind 'image': input is an RgbaImage. */
export function pixelizeFile(kind, input, settings) {
  const background = settings.backgroundColor;
  if (kind === 'gif') {
    const gif = decodeGif(input);
    if (gif.frames.length > MAX_FRAMES) {
      throw new Error(`GIF has ${gif.frames.length} frames, the limit is ${MAX_FRAMES}`);
    }
    const images = gif.frames.map((frame) => flattenRgba(frame.image, background));
    const durations = gif.frames.length > 1 ? gif.frames.map((f) => frameDuration(f.delayMs)) : [0];
    return pixelize(images, durations, settings);
  }
  return pixelize([flattenRgba(input, background)], [0], settings);
}

export function binByteSize(art) {
  return 16 + 3 * art.palette.length + art.frames.length * (2 + art.width * art.height);
}

/** null when the PixelArt can be uploaded, otherwise a message. */
export function checkLimits(art) {
  if (art.frames.length > MAX_FRAMES) return `too many frames: ${art.frames.length} > ${MAX_FRAMES}`;
  const size = binByteSize(art);
  if (size > MAX_BIN_BYTES) return `file too large: ${size} bytes > ${MAX_BIN_BYTES}`;
  return null;
}

export const TAG_MAX_LENGTH = 24;

/** "Коты,  Winter sky , коты" -> ["winter sky", "коты"]: trimmed, lowercased, unique, sorted. */
export function parseTags(text) {
  const tags = String(text).split(',')
    .map((t) => t.trim().replace(/\s+/g, ' ').toLowerCase())
    .filter((t) => t.length > 0)
    .map((t) => t.slice(0, TAG_MAX_LENGTH).replace(/[/\\"<>]/g, ''));
  return [...new Set(tags)].sort();
}

/** Default MediaItem name from a file name: "cat photo.jpg" -> "cat photo". */
export function nameFromFile(fileName) {
  return (String(fileName).replace(/\.[^.]+$/, '').trim() || 'untitled').slice(0, 64);
}
