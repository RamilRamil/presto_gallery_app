// LAYER 3 (calculations): pixelize pipeline. Port of src/presto_pic_loader/l3_pipeline.py.
// PixelArt = {width, height, palette: [RgbColor], frames: [{indices: Uint8Array, durationMs}]}.

import {
  GRID_SIZES, PICO8_PALETTE, cropWindow, parseHexColor, screenOffset,
} from './l1-primitives.js';
import {
  boxDownscale, cropRgb, cropRgbWindow, decodeGif, fitRgb, fitRgbWindow, flattenRgba, quantizeFrames,
  rgbPixels,
} from './l2-image-ops.js';

export {
  MAX_CROP_ZOOM, cropWindow, defaultCropView, fromRelativeView, panCropView, toRelativeView, zoomCropView,
} from './l1-primitives.js';

export const PRESET_PALETTES = { 'pico-8': PICO8_PALETTE };
export const ADAPTIVE = 'adaptive';
export const MAX_FRAMES = 256;
export const MAX_BIN_BYTES = 1024 * 1024;
export const MAX_SCENE_BYTES = 256 * 1024;
export const RECOGNIZABLE_GRID = 120;
const LARGEST_BIN_HEAD = 16 + 3 * 256;
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

function toSquare(image, settings, view) {
  if (settings.fitMode !== 'crop') {
    return view
      ? fitRgbWindow(image, cropWindow(view, image.width, image.height, true), settings.backgroundColor)
      : fitRgb(image, settings.backgroundColor);
  }
  return view ? cropRgbWindow(image, cropWindow(view, image.width, image.height)) : cropRgb(image);
}

/** Stage A + B: RGB images (any size) -> PixelArt. `view` is the CropView, null for the default. */
export function pixelize(images, durationsMs, settings, view = null) {
  const grids = images.map((image) => rgbPixels(boxDownscale(toSquare(image, settings, view),
    settings.gridSize)));
  return pixelizeGrid(grids, durationsMs, settings);
}

export function frameDuration(delayMs) {
  return delayMs > 0 ? Math.max(MIN_FRAME_MS, delayMs) : DEFAULT_FRAME_MS;
}

/** First frame of a GIF as an RgbaImage, for showing the picture while choosing a CropView. */
export function gifFirstFrame(bytes) {
  return decodeGif(bytes).frames[0].image;
}

/** Picture size written in a GIF's header. */
export function gifSize(bytes) {
  return { width: bytes[6] | (bytes[7] << 8), height: bytes[8] | (bytes[9] << 8) };
}

/** kind 'gif': input is GIF bytes; kind 'image': input is an RgbaImage. */
export function pixelizeFile(kind, input, settings, view = null) {
  const background = settings.backgroundColor;
  if (kind === 'gif') {
    const gif = decodeGif(input);
    if (gif.frames.length > MAX_FRAMES) {
      throw new Error(`GIF has ${gif.frames.length} frames, the limit is ${MAX_FRAMES}`);
    }
    const images = gif.frames.map((frame) => flattenRgba(frame.image, background));
    const durations = gif.frames.length > 1 ? gif.frames.map((f) => frameDuration(f.delayMs)) : [0];
    return pixelize(images, durations, settings, view);
  }
  return pixelize([flattenRgba(input, background)], [0], settings, view);
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

/** What a Grid means for the user: size of one frame, GIF limit, screen coverage. */
export function gridLimits(gridSize) {
  const frameBytes = gridSize * gridSize;
  const marginPx = screenOffset(gridSize);
  return {
    frameBytes,
    maxFrames: Math.min(MAX_FRAMES, Math.floor((MAX_BIN_BYTES - LARGEST_BIN_HEAD) / (2 + frameBytes))),
    fillsScreen: marginPx === 0,
    marginPx,
    recognizable: gridSize >= RECOGNIZABLE_GRID,
  };
}

/** null when a Scene file of this size can be uploaded, otherwise a message. */
export function checkSceneSize(byteLength) {
  if (byteLength === 0) return 'Файл пустой';
  if (byteLength > MAX_SCENE_BYTES) return 'Файл больше 256 КБ';
  return null;
}

// --- UploadQueue: {id, file, name, kind, state, error, own} ----------------------------------
// Setup = {gridSize, colorCount, paletteName, fitMode, dither, backgroundColor, view, tags, collection}.
// `shared` is what the reference file sets; `own` holds only the values set on one file.

export const MAX_QUEUE_FILES = 100;

export function fileKind(fileName) {
  return /\.py$/i.test(String(fileName)) ? 'scene' : 'media';
}

/** Append files after dropping finished rows; ids stay unique within the queue. */
export function addToQueue(queue, files) {
  const kept = queue.filter((entry) => entry.state !== 'done');
  let nextId = queue.reduce((largest, entry) => Math.max(largest, entry.id), 0) + 1;
  const added = [...files].slice(0, Math.max(0, MAX_QUEUE_FILES - kept.length)).map((file) => ({
    id: nextId++, file, name: nameFromFile(file.name), kind: fileKind(file.name),
    state: 'waiting', error: null, own: {},
  }));
  return [...kept, ...added];
}

export function setQueueEntry(queue, id, changes) {
  return queue.map((entry) => (entry.id === id ? { ...entry, ...changes } : entry));
}

export function removeFromQueue(queue, id) {
  return queue.filter((entry) => entry.id !== id);
}

export function retryFailed(queue) {
  return queue.map((entry) => (entry.state === 'failed' ? { ...entry, state: 'waiting', error: null } : entry));
}

export function nextPending(queue) {
  return queue.find((entry) => entry.state === 'waiting') || null;
}

export function queueSummary(queue) {
  const count = (state) => queue.filter((entry) => entry.state === state).length;
  return { total: queue.length, done: count('done'), failed: count('failed'), pending: count('waiting') };
}

/** The file whose changes apply to the others: the first picture or GIF, else the first file. */
export function referenceEntry(queue) {
  return queue.find((entry) => entry.kind === 'media') || queue[0] || null;
}

export function entrySetup(entry, shared) {
  return { ...shared, ...entry.own };
}

export function hasOwnSetup(entry) {
  return Object.keys(entry.own).length > 0;
}

function withoutKeys(values, keys) {
  return Object.fromEntries(Object.entries(values).filter(([key]) => !keys.includes(key)));
}

/** Own values equal to the shared ones are dropped, so the file keeps following the reference. */
function changeOwn(entry, changes, shared) {
  const own = { ...entry.own, ...changes };
  return { ...entry, own: Object.fromEntries(Object.entries(own).filter(([key, value]) => value !== shared[key])) };
}

/** Apply values set on file `id`: on the reference they go to everyone who follows it.
 *  Changing fit resets the view, because zoom 1 means a different square in each mode. */
export function changeSetup({ queue, shared }, id, values) {
  const changes = 'fitMode' in values ? { ...values, view: null } : values;
  const reference = referenceEntry(queue);
  if (reference && reference.id !== id) {
    return { shared, queue: queue.map((entry) => (entry.id === id ? changeOwn(entry, changes, shared) : entry)) };
  }
  const keys = Object.keys(changes);
  return {
    shared: { ...shared, ...changes },
    queue: queue.map((entry) => {
      if (reference && entry.id === reference.id) return { ...entry, own: withoutKeys(entry.own, keys) };
      return 'fitMode' in values && !('fitMode' in entry.own)
        ? { ...entry, own: withoutKeys(entry.own, ['view']) }
        : entry;
    }),
  };
}

/** Forget the values set on this file. */
export function resetEntry(queue, id) {
  return setQueueEntry(queue, id, { own: {} });
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

/** Tag field text with `label` added, or removed if it is already there. */
export function toggleTag(text, label) {
  const tags = parseTags(text);
  return (tags.includes(label) ? tags.filter((tag) => tag !== label) : parseTags(`${text},${label}`)).join(', ');
}

/** Default MediaItem name from a file name: "cat photo.jpg" -> "cat photo". */
export function nameFromFile(fileName) {
  return (String(fileName).replace(/\.[^.]+$/, '').trim() || 'untitled').slice(0, 64);
}
