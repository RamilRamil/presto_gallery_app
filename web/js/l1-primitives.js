// LAYER 1 (calculations): color and size primitives. Port of src/presto_pic_loader/l1_primitives.py.
// RgbColor is a [red, green, blue] array of 0..255 integers.

export const PRESTO_SCREEN_SIZE = 240;
export const GRID_SIZES = [16, 32, 40, 60, 64, 80, 120, 240];

export const PICO8_PALETTE = Object.freeze([
  '000000', '1D2B53', '7E2553', '008751', 'AB5236', '5F574F', 'C2C3C7', 'FFF1E8',
  'FF004D', 'FFA300', 'FFEC27', '00E436', '29ADFF', '83769C', 'FF77A8', 'FFCCAA',
].map((hex) => Object.freeze([0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16)))));

export function clampChannel(value) {
  return Math.max(0, Math.min(255, Math.trunc(value)));
}

export function colorDistance(a, b) {
  const dr = a[0] - b[0];
  const dg = a[1] - b[1];
  const db = a[2] - b[2];
  return dr * dr + dg * dg + db * db;
}

/** Index of the closest palette entry; ties go to the lowest index. */
export function nearestColorIndex(color, palette) {
  let best = 0;
  let bestDistance = Infinity;
  for (let i = 0; i < palette.length; i++) {
    const d = colorDistance(color, palette[i]);
    if (d < bestDistance) {
      best = i;
      bestDistance = d;
    }
  }
  return best;
}

export function colorKey(color) {
  return (color[0] << 16) | (color[1] << 8) | color[2];
}

/** Compare colors by (R, G, B) ascending. */
export function compareColors(a, b) {
  return a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
}

export function parseHexColor(text) {
  const digits = String(text).trim().replace(/^#/, '');
  if (!/^[0-9a-fA-F]{6}$/.test(digits)) {
    throw new Error(`color must look like #RRGGBB, got ${JSON.stringify(text)}`);
  }
  return [0, 2, 4].map((i) => parseInt(digits.slice(i, i + 2), 16));
}

export function toHexColor(color) {
  return '#' + color.map((c) => c.toString(16).padStart(2, '0')).join('');
}

export function cellSize(gridSize, screenSize = PRESTO_SCREEN_SIZE) {
  return Math.floor(screenSize / gridSize);
}

export function screenOffset(gridSize, screenSize = PRESTO_SCREEN_SIZE) {
  return Math.floor((screenSize - gridSize * cellSize(gridSize, screenSize)) / 2);
}

/** [left, top, right, bottom] of the largest centered square. */
export function centerSquareBox(width, height) {
  const side = Math.min(width, height);
  const left = Math.floor((width - side) / 2);
  const top = Math.floor((height - side) / 2);
  return [left, top, left + side, top + side];
}

/** Side of the square containing width x height, and the offset that centers it. */
export function fitInside(width, height) {
  const side = Math.max(width, height);
  return { side, offset: [Math.floor((side - width) / 2), Math.floor((side - height) / 2)] };
}

export const MAX_CROP_ZOOM = 8;

/** CropView = {centerX, centerY, zoom}: the chosen square of a width x height picture. */
export function defaultCropView(width, height) {
  return { centerX: width / 2, centerY: height / 2, zoom: 1 };
}

/** Side of the view's square in source pixels; `fit` lets it take in the whole picture. */
export function cropSide(view, width, height, fit = false) {
  return (fit ? Math.max(width, height) : Math.min(width, height)) / view.zoom;
}

const between = (value, low, high) => Math.min(Math.max(value, low), high);

/** A picture smaller than the square moves inside it; a larger one keeps covering it. */
function clampCenter(center, size, half) {
  return between(center, Math.min(half, size - half), Math.max(half, size - half));
}

export function clampCropView(view, width, height, fit = false) {
  const zoom = between(view.zoom, 1, MAX_CROP_ZOOM);
  const half = cropSide({ zoom }, width, height, fit) / 2;
  return {
    centerX: clampCenter(view.centerX, width, half),
    centerY: clampCenter(view.centerY, height, half),
    zoom,
  };
}

export function panCropView(view, dx, dy, width, height, fit = false) {
  return clampCropView({ ...view, centerX: view.centerX + dx, centerY: view.centerY + dy },
    width, height, fit);
}

/** Multiply the zoom, keeping the picture point (anchorX, anchorY) where it is on the preview. */
export function zoomCropView(view, factor, anchorX, anchorY, width, height, fit = false) {
  const zoom = between(view.zoom * factor, 1, MAX_CROP_ZOOM);
  const scale = view.zoom / zoom;
  return clampCropView({
    centerX: anchorX + (view.centerX - anchorX) * scale,
    centerY: anchorY + (view.centerY - anchorY) * scale,
    zoom,
  }, width, height, fit);
}

/** The view as a whole-pixel square {x, y, side}. Default views equal the center crop and fit.
 *  With `fit` the square may extend past the picture, so x and y may be negative. */
export function cropWindow(view, width, height, fit = false) {
  const side = Math.max(1, Math.round(cropSide(view, width, height, fit)));
  if (fit) {
    return { x: Math.ceil(view.centerX - side / 2), y: Math.ceil(view.centerY - side / 2), side };
  }
  return {
    x: between(Math.floor(view.centerX - side / 2), 0, width - side),
    y: between(Math.floor(view.centerY - side / 2), 0, height - side),
    side,
  };
}
