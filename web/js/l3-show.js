// LAYER 3 (calculations): CollectionShowSettings in the WebUi - the same rules as device/gallery/l2_catalog.py.

export const SLIDE_MIN_SECONDS = 3;
export const SLIDE_MAX_SECONDS = 600;
export const ORDER_NAMES = { general: 'как в настройках', loop: 'по кругу', shuffle: 'вперемешку' };

const isWhole = (value) => Number.isInteger(value);
const clampSlide = (seconds) => Math.min(SLIDE_MAX_SECONDS, Math.max(SLIDE_MIN_SECONDS, seconds));

/** {slideSeconds, shuffle} of a Collection, null where it has no own value (or a damaged one). */
export function collectionShow(collection) {
  const { slideSeconds, shuffle } = collection || {};
  return {
    slideSeconds: isWhole(slideSeconds) ? clampSlide(slideSeconds) : null,
    shuffle: typeof shuffle === 'boolean' ? shuffle : null,
  };
}

function ownParts(collection) {
  const own = collectionShow(collection);
  const parts = [];
  if (own.slideSeconds !== null) parts.push(`${own.slideSeconds} с`);
  if (own.shuffle !== null) parts.push(own.shuffle ? ORDER_NAMES.shuffle : ORDER_NAMES.loop);
  return parts;
}

/** Short text for the Collection row, e.g. "60 с · вперемешку"; '' without own values. */
export function collectionShowSummary(collection) {
  return ownParts(collection).join(' · ');
}

/** Note under the general settings when the chosen Collection overrides them; '' otherwise. */
export function ownShowNote(collection) {
  const parts = ownParts(collection);
  return parts.length ? `У этой коллекции свои настройки: ${parts.join(', ')}` : '';
}

/** Values for the "Показ коллекции" dialog: seconds '' means "как в настройках". */
export function showForm(collection) {
  const own = collectionShow(collection);
  return {
    seconds: own.slideSeconds === null ? '' : String(own.slideSeconds),
    order: own.shuffle === null ? 'general' : own.shuffle ? 'shuffle' : 'loop',
  };
}

/** PATCH /api/collections/<id> body from the dialog; null clears a value. */
export function showPatch({ seconds, order }) {
  const text = String(seconds ?? '').trim();
  const number = Math.round(Number(text));
  return {
    slideSeconds: text === '' || !Number.isFinite(number) ? null : clampSlide(number),
    shuffle: order === 'shuffle' ? true : order === 'loop' ? false : null,
  };
}
