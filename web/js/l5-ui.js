// LAYER 5 (actions): DOM, files, canvas, timers. Talks to layers 3/4 and the HttpApi client.

import {
  addToQueue, binByteSize, changeSetup, checkLimits, checkSceneSize, cropWindow, defaultCropView,
  entrySetup, fromRelativeView, gifFirstFrame, gifSize, gridLimits, hasOwnSetup, makeSettings, nextPending,
  panCropView, parseTags, pixelizeFile, queueSummary, referenceEntry, removeFromQueue, resetEntry,
  retryFailed, setQueueEntry, toRelativeView, toggleTag, zoomCropView,
} from './l3-pipeline.js';
import { decodePrestoBin, encodePrestoBin, renderPixelArt } from './l4-encoders.js';
import { api, setPassword } from './l5-api.js';

const $ = (selector) => document.querySelector(selector);
const MAX_DECODE_SIDE = 2048;
const CONVERT_DELAY_MS = 60;
const SETTLE_DELAY_MS = 250;
const PREVIEW_SIDE = 256;
const WHEEL_SPEED = 0.002;
const MODE_NAMES = {
  all: 'всё', images: 'картинки', animations: 'гифки', scenes: 'сцены', collection: 'коллекция', tags: 'по тегам',
};
const STATE_NAMES = { waiting: 'ждёт', uploading: 'загружается', done: 'готово', failed: 'ошибка' };

const ui = {
  file: null, fileBytes: null, fileImage: null, art: null, artProblem: false, locked: false,
  source: null, sourceCanvas: null, view: null, pointers: new Map(),
  queue: [], shared: null, activeId: null, uploading: false, cancelRequested: false, passwordSet: true,
  editing: null,
  collections: [], selected: new Set(), visibleIds: [],
  convertTimer: null, previewPlayer: null, items: [], tags: [], settings: null, thumbs: new Map(),
};

// --- canvas playback ---------------------------------------------------------------------

/** The canvas holds one pixel per cell; CSS scales it up without smoothing. */
function drawArt(canvas, art, frameIndex) {
  if (canvas.width !== art.width) {
    canvas.width = art.width;
    canvas.height = art.height;
  }
  const image = renderPixelArt(art, frameIndex, 1);
  canvas.getContext('2d').putImageData(new ImageData(image.data, image.width, image.height), 0, 0);
}

function drawScenePlaceholder(canvas) {
  const context = canvas.getContext('2d');
  context.fillStyle = '#20202c';
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = '#ececf2';
  context.font = '18px sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('сцена', canvas.width / 2, canvas.height / 2);
}

function playArt(canvas, art) {
  let frame = 0;
  let timer = null;
  const tick = () => {
    drawArt(canvas, art, frame);
    if (art.frames.length > 1) {
      timer = setTimeout(tick, Math.max(20, art.frames[frame].durationMs));
      frame = (frame + 1) % art.frames.length;
    }
  };
  tick();
  return { stop: () => clearTimeout(timer) };
}

// --- reading files -----------------------------------------------------------------------

async function decodeImageFile(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DECODE_SIDE / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  return { width, height, data: context.getImageData(0, 0, width, height).data };
}

function isGif(file, bytes) {
  return file.type === 'image/gif' || (bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46);
}

// --- add & convert -----------------------------------------------------------------------

const SETUP_READERS = {
  gridSize: (form) => Number(form.gridSize.value),
  colorCount: (form) => Number(form.colorCount.value),
  paletteName: (form) => form.paletteName.value,
  fitMode: (form) => form.fitMode.value,
  dither: (form) => form.dither.checked,
  backgroundColor: (form) => form.backgroundColor.value,
  tags: (form) => form.tags.value,
  collection: (form) => form.collection.value,
};

function formSetup() {
  const form = $('#settings-form');
  return Object.fromEntries(Object.entries(SETUP_READERS).map(([name, read]) => [name, read(form)]));
}

const formSettings = () => makeSettings(formSetup());

function renderPaletteFields() {
  $('#colors-field').hidden = $('#settings-form').paletteName.value !== 'adaptive';
}

function showSetupInForm(setup) {
  const form = $('#settings-form');
  form.gridSize.value = setup.gridSize;
  form.colorCount.value = setup.colorCount;
  form.paletteName.value = setup.paletteName;
  form.fitMode.value = setup.fitMode;
  form.dither.checked = setup.dither;
  form.backgroundColor.value = setup.backgroundColor;
  form.tags.value = setup.tags;
  form.collection.value = setup.collection;
  renderPaletteFields();
  renderGridHint();
  renderUploadTags();
}

/** Record values set for the open file; on the reference file they reach the others too. */
function changeActive(values) {
  ({ queue: ui.queue, shared: ui.shared } = changeSetup(
    { queue: ui.queue, shared: ui.shared }, ui.activeId, values,
  ));
}

function convert() {
  if (!ui.file || !ui.source) return;
  const info = $('#preview-info');
  ui.previewPlayer?.stop();
  try {
    const settings = formSettings();
    ui.art = ui.fileImage
      ? pixelizeFile('image', ui.fileImage, settings, ui.view)
      : pixelizeFile('gif', ui.fileBytes, settings, ui.view);
    ui.previewPlayer = playArt($('#preview'), ui.art);
    const problem = checkLimits(ui.art);
    const frames = ui.art.frames.length;
    info.textContent = problem || `${ui.art.width}×${ui.art.height}, ${frames > 1 ? frames + ' кадров, ' : ''}`
      + `${ui.art.palette.length} цветов, ${(binByteSize(ui.art) / 1024).toFixed(1)} КБ`;
    ui.artProblem = Boolean(problem);
  } catch (error) {
    ui.art = null;
    ui.artProblem = true;
    info.textContent = `Ошибка: ${error.message}`;
  }
  renderQueue();
}

function scheduleConvert(delay = CONVERT_DELAY_MS) {
  clearTimeout(ui.convertTimer);
  ui.convertTimer = setTimeout(convert, delay);
}

// --- choosing the part of the picture (CropView) --------------------------------------------

const isFit = () => $('#settings-form').fitMode.value === 'fit';

function setSource(image) {
  ui.source = image;
  ui.view = defaultCropView(image.width, image.height);
  const canvas = document.createElement('canvas');
  canvas.width = image.width;
  canvas.height = image.height;
  const pixels = new Uint8ClampedArray(image.data.buffer, image.data.byteOffset, image.data.length);
  canvas.getContext('2d').putImageData(new ImageData(pixels, image.width, image.height), 0, 0);
  ui.sourceCanvas = canvas;
}

function renderCropControls() {
  const adjustable = Boolean(ui.source);
  $('#crop-controls').hidden = !adjustable;
  $('#preview').classList.toggle('croppable', adjustable);
  if (adjustable) $('#crop-zoom').value = ui.view.zoom;
}

/** Follows the gesture cheaply; the exact pixels come from convert() when it ends. */
function drawFastPreview() {
  ui.previewPlayer?.stop();
  const canvas = $('#preview');
  if (canvas.width !== PREVIEW_SIDE) {
    canvas.width = PREVIEW_SIDE;
    canvas.height = PREVIEW_SIDE;
  }
  const { width, height } = ui.source;
  const { x, y, side } = cropWindow(ui.view, width, height, isFit());
  const scale = PREVIEW_SIDE / side;
  const context = canvas.getContext('2d');
  context.fillStyle = $('#settings-form').backgroundColor.value;
  context.fillRect(0, 0, PREVIEW_SIDE, PREVIEW_SIDE);
  context.drawImage(ui.sourceCanvas, -x * scale, -y * scale, width * scale, height * scale);
}

function applyView(view) {
  ui.view = view;
  changeActive({ view: toRelativeView(view, ui.source.width, ui.source.height) });
  $('#upload').disabled = true;  // the current ui.art no longer matches the view
  renderCropControls();
  drawFastPreview();
}

/** Source pixels under a point of the preview, and source pixels per CSS pixel. */
function previewToSource(clientX, clientY) {
  const rect = $('#preview').getBoundingClientRect();
  const { x, y, side } = cropWindow(ui.view, ui.source.width, ui.source.height, isFit());
  const perPixel = side / rect.width;
  return { x: x + (clientX - rect.left) * perPixel, y: y + (clientY - rect.top) * perPixel, perPixel };
}

function zoomAt(factor, clientX, clientY) {
  const anchor = previewToSource(clientX, clientY);
  applyView(zoomCropView(ui.view, factor, anchor.x, anchor.y, ui.source.width, ui.source.height, isFit()));
}

function onPreviewPointerDown(event) {
  if (!ui.source) return;
  event.currentTarget.setPointerCapture(event.pointerId);
  ui.pointers.set(event.pointerId, [event.clientX, event.clientY]);
}

function onPreviewPointerMove(event) {
  if (!ui.pointers.has(event.pointerId)) return;
  const [a, b] = [...ui.pointers.values()];
  ui.pointers.set(event.pointerId, [event.clientX, event.clientY]);
  const [nextA, nextB] = [...ui.pointers.values()];
  const dx = b ? (nextA[0] + nextB[0] - a[0] - b[0]) / 2 : nextA[0] - a[0];
  const dy = b ? (nextA[1] + nextB[1] - a[1] - b[1]) / 2 : nextA[1] - a[1];
  const { perPixel } = previewToSource(event.clientX, event.clientY);
  applyView(panCropView(ui.view, -dx * perPixel, -dy * perPixel, ui.source.width, ui.source.height, isFit()));
  if (b) {
    const factor = Math.hypot(nextA[0] - nextB[0], nextA[1] - nextB[1]) / Math.hypot(a[0] - b[0], a[1] - b[1]);
    if (Number.isFinite(factor) && factor > 0) {
      zoomAt(factor, (nextA[0] + nextB[0]) / 2, (nextA[1] + nextB[1]) / 2);
    }
  }
}

function onPreviewPointerEnd(event) {
  if (ui.pointers.delete(event.pointerId) && ui.pointers.size === 0) scheduleConvert();
}

function onPreviewWheel(event) {
  if (!ui.source) return;
  event.preventDefault();
  zoomAt(Math.exp(-event.deltaY * WHEEL_SPEED), event.clientX, event.clientY);
  scheduleConvert(SETTLE_DELAY_MS);
}

function onZoomSlider(event) {
  const rect = $('#preview').getBoundingClientRect();
  zoomAt(Number(event.target.value) / ui.view.zoom, rect.left + rect.width / 2, rect.top + rect.height / 2);
  scheduleConvert(SETTLE_DELAY_MS);
}

function resetCrop() {
  applyView(defaultCropView(ui.source.width, ui.source.height));
  scheduleConvert();
}

function renderGridHint() {
  const limits = gridLimits(Number($('#settings-form').gridSize.value));
  $('#grid-hint').textContent = `${limits.fillsScreen ? 'Весь экран' : `Рамка ${limits.marginPx} px`}`
    + ` · кадр ${(limits.frameBytes / 1024).toFixed(1)} КБ · GIF до ${limits.maxFrames} кадров`;
  $('#grid-warning').hidden = !limits.recognizable;
}

// --- UploadQueue --------------------------------------------------------------------------

const activeEntry = () => ui.queue.find((entry) => entry.id === ui.activeId) || null;

function renderUploadControls() {
  const { total, pending, failed } = queueSummary(ui.queue);
  const toSend = pending + failed;
  const active = activeEntry();
  const blocked = total === 1 && active && active.kind === 'media' && (!ui.art || ui.artProblem);
  const button = $('#upload');
  button.disabled = ui.uploading || toSend === 0 || blocked;
  button.textContent = total > 1 ? `Загрузить все (${toSend})` : 'Загрузить на Presto';
  $('#upload-cancel').hidden = !ui.uploading;
  $('#queue-clear').hidden = ui.uploading || total === 0;
  $('#name-field').hidden = total > 1;
  $('#scene-note').hidden = !ui.queue.some((entry) => entry.kind === 'scene');
  $('#scene-off').hidden = ui.passwordSet || !ui.queue.some((entry) => entry.kind === 'scene');
  renderSetupNote();
}

function renderSetupNote() {
  const active = activeEntry();
  const note = $('#setup-note');
  note.hidden = !active || ui.queue.length < 2;
  if (note.hidden) return;
  const own = hasOwnSetup(active);
  $('#setup-reset').hidden = !own;
  $('#setup-text').textContent = own
    ? 'У этого файла есть свои значения. Остальное он берёт у первого файла.'
    : referenceEntry(ui.queue).id === active.id
      ? 'Что настроишь здесь, применится к остальным файлам. Значения, заданные у них вручную, останутся.'
      : 'Настройки как у первого файла. Что изменишь здесь, останется только у этого файла.';
}

function resetActiveSetup() {
  ui.queue = resetEntry(ui.queue, ui.activeId);
  activate(ui.activeId);
}

/** "образец · ждёт": what the row follows, then its upload state. */
function queueRowState(entry) {
  const role = ui.queue.length < 2 ? ''
    : hasOwnSetup(entry) ? 'своё · '
      : referenceEntry(ui.queue).id === entry.id ? 'образец · ' : '';
  return `${role}${STATE_NAMES[entry.state]}${entry.error ? `: ${entry.error}` : ''}`;
}

function renderQueue() {
  const list = $('#queue');
  list.hidden = ui.queue.length < 2;
  list.replaceChildren(...ui.queue.map((entry) => {
    const row = document.createElement('li');
    row.className = `queue-row ${entry.state}${entry.id === ui.activeId ? ' active' : ''}`;
    const open = Object.assign(document.createElement('button'), {
      type: 'button', className: 'queue-name', textContent: entry.name,
    });
    open.addEventListener('click', () => activate(entry.id));
    const state = Object.assign(document.createElement('span'), {
      className: 'muted',
      textContent: queueRowState(entry),
    });
    const remove = Object.assign(document.createElement('button'), {
      type: 'button', textContent: '×', disabled: ui.uploading,
    });
    remove.setAttribute('aria-label', `Убрать ${entry.name}`);
    remove.addEventListener('click', () => removeEntry(entry.id));
    row.append(open, state, remove);
    return row;
  }));
  renderUploadControls();
}

function clearPreview() {
  ui.file = null;
  ui.art = null;
  ui.artProblem = false;
  ui.fileBytes = null;
  ui.fileImage = null;
  ui.source = null;
  ui.sourceCanvas = null;
  ui.view = null;
  ui.previewPlayer?.stop();
  const canvas = $('#preview');
  canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  renderCropControls();
}

/** Show one queue file in the preview; only this file is decoded and kept in memory. */
async function activate(id) {
  const entry = ui.queue.find((candidate) => candidate.id === id);
  if (!entry) return;
  ui.activeId = id;
  clearPreview();
  ui.file = entry.file;
  $('#drop-text').textContent = ui.queue.length > 1 ? `Файлов: ${ui.queue.length}` : entry.file.name;
  $('#settings-form').name.value = entry.name;
  $('#upload-msg').textContent = '';
  showSetupInForm(entrySetup(entry, ui.shared));
  renderQueue();
  if (entry.kind === 'scene') {
    $('#preview-info').textContent = `Сцена «${entry.name}» загрузится как есть`;
    renderUploadControls();
    return;
  }
  $('#preview-info').textContent = 'Обрабатываю…';
  try {
    const bytes = new Uint8Array(await entry.file.arrayBuffer());
    const image = isGif(entry.file, bytes) ? null : await decodeImageFile(entry.file);
    if (ui.activeId !== id) return;  // the user has already opened another file
    ui.fileBytes = bytes;
    ui.fileImage = image;
    setSource(image || gifFirstFrame(bytes));
    const { view, fitMode } = entrySetup(activeEntry(), ui.shared);
    if (view) ui.view = fromRelativeView(view, ui.source.width, ui.source.height, fitMode === 'fit');
    renderCropControls();
    convert();
  } catch (error) {
    if (ui.activeId !== id) return;
    clearPreview();
    ui.artProblem = true;
    $('#preview-info').textContent = `Не получилось прочитать файл: ${error.message}`;
    renderUploadControls();
  }
}

function addFiles(files) {
  if (!files.length || ui.uploading) return;
  const before = new Set(ui.queue.map((entry) => entry.id));
  if (ui.queue.every((entry) => entry.state === 'done')) ui.shared = { ...ui.shared, view: null };  // a new batch
  ui.queue = addToQueue(ui.queue, files);
  renderQueue();
  const fresh = ui.queue.find((entry) => !before.has(entry.id));
  if (!activeEntry() || (fresh && before.size === 0)) activate((fresh || ui.queue[0]).id);
  else if (activeEntry().state === 'done' && fresh) activate(fresh.id);
}

function removeEntry(id) {
  ui.queue = removeFromQueue(ui.queue, id);
  if (ui.activeId === id) {
    ui.activeId = null;
    clearPreview();
    $('#preview-info').textContent = 'Нет файла';
    if (ui.queue.length) activate(ui.queue[0].id);
  }
  renderQueue();
}

function clearQueue() {
  ui.queue = [];
  ui.shared = { ...ui.shared, view: null };
  ui.activeId = null;
  clearPreview();
  $('#preview-info').textContent = 'Нет файла';
  $('#drop-text').textContent = 'Выбери картинки, GIF или сцены .py (или перетащи сюда)';
  $('#file').value = '';
  $('#upload-msg').textContent = '';
  renderQueue();
}

async function artFor(entry, setup) {
  if (entry.id === ui.activeId && ui.art) return ui.art;
  const settings = makeSettings(setup);
  const viewFor = ({ width, height }) => (setup.view
    ? fromRelativeView(setup.view, width, height, setup.fitMode === 'fit')
    : null);
  const bytes = new Uint8Array(await entry.file.arrayBuffer());
  if (isGif(entry.file, bytes)) return pixelizeFile('gif', bytes, settings, viewFor(gifSize(bytes)));
  const image = await decodeImageFile(entry.file);
  return pixelizeFile('image', image, settings, viewFor(image));
}

async function sendEntry(entry, show) {
  const setup = entrySetup(entry, ui.shared);
  const tags = parseTags(setup.tags);
  const options = { show, collection: setup.collection };
  if (entry.kind === 'scene') {
    const bytes = new Uint8Array(await entry.file.arrayBuffer());
    const problem = checkSceneSize(bytes.length);
    if (problem) throw new Error(problem);
    return api.uploadScene(bytes, entry.name, tags, options);
  }
  const art = await artFor(entry, setup);
  const problem = checkLimits(art);
  if (problem) throw new Error(problem);
  return api.upload(encodePrestoBin(art), entry.name, tags, options);
}

async function uploadQueue() {
  const form = $('#settings-form');
  const message = $('#upload-msg');
  const single = ui.queue.length === 1;
  if (single) ui.queue = setQueueEntry(ui.queue, ui.queue[0].id, { name: form.name.value.trim() || ui.queue[0].name });
  ui.queue = retryFailed(ui.queue);
  ui.uploading = true;
  ui.cancelRequested = false;
  const total = queueSummary(ui.queue).pending;
  let sent = 0;
  try {
    for (let entry = nextPending(ui.queue); entry && !ui.cancelRequested; entry = nextPending(ui.queue)) {
      ui.queue = setQueueEntry(ui.queue, entry.id, { state: 'uploading' });
      renderQueue();
      message.textContent = `${sent + 1} из ${total}…`;
      try {
        await sendEntry(entry, single);
        ui.queue = setQueueEntry(ui.queue, entry.id, { state: 'done' });
        sent += 1;
      } catch (error) {
        ui.queue = setQueueEntry(ui.queue, entry.id, { state: 'failed', error: error.message });
        if (error.status === 401) {
          lock();
          return;
        }
      }
    }
    const { failed, pending } = queueSummary(ui.queue);
    message.textContent = single && !failed
      ? 'Готово: уже на экране'
      : `Загружено ${sent} из ${total}${failed ? `, ошибок ${failed}` : ''}${pending ? ', остановлено' : ''}`;
    await refreshAll();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  } finally {
    ui.uploading = false;
    renderQueue();
  }
}

// --- labels -------------------------------------------------------------------------------

function makeLabel(text, on, onClick) {
  const chip = Object.assign(document.createElement('button'), {
    type: 'button', className: `chip${on ? ' on' : ''}`, textContent: text,
  });
  chip.setAttribute('aria-pressed', String(on));
  chip.addEventListener('click', () => onClick(chip));
  return chip;
}

/** Labels of the existing Tags, drawn from the text field: a click adds or removes that Tag. */
function renderTagLabels(box, field, onChange) {
  const chosen = parseTags(field.value);
  box.replaceChildren(...ui.tags.map(({ label }) => makeLabel(label, chosen.includes(label), () => {
    field.value = toggleTag(field.value, label);
    onChange();
  })));
}

function renderUploadTags() {
  renderTagLabels($('#tag-suggest'), $('#settings-form').tags, onUploadTagsChanged);
}

function onUploadTagsChanged() {
  changeActive({ tags: $('#settings-form').tags.value });
  renderUploadTags();
  renderQueue();
}

function renderTagSuggestions() {
  renderUploadTags();
  $('#tag-list').replaceChildren(...ui.tags.map(({ label }) => new Option(label)));
}

// --- show mode ---------------------------------------------------------------------------

function renderModeForm() {
  const form = $('#mode-form');
  const settings = ui.settings;
  form.showMode.value = settings.showMode;
  form.slideSeconds.value = settings.slideSeconds;
  form.shuffle.checked = settings.shuffle;
  const selected = new Set(settings.selectedTags);
  const box = $('#mode-tags');
  box.hidden = settings.showMode !== 'tags';
  const collectionSelect = $('#mode-collection');
  collectionSelect.hidden = settings.showMode !== 'collection';
  collectionSelect.replaceChildren(...ui.collections.map((c) => new Option(`${c.name} (${c.mediaIds.length})`, c.collectionId)));
  if (settings.selectedCollection) collectionSelect.value = settings.selectedCollection;
  box.replaceChildren(...(ui.tags.length ? ui.tags.map(({ label, count }) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip' + (selected.has(label) ? ' on' : '');
    chip.textContent = `${label} · ${count}`;
    chip.dataset.tag = label;
    chip.addEventListener('click', () => chip.classList.toggle('on'));
    return chip;
  }) : [Object.assign(document.createElement('span'), { className: 'muted', textContent: 'Тегов пока нет' })]));
}

function modeFormValue() {
  const form = $('#mode-form');
  return {
    showMode: form.showMode.value || 'all',
    selectedTags: [...$('#mode-tags').querySelectorAll('.chip.on')].map((c) => c.dataset.tag),
    selectedCollection: $('#mode-collection').value || null,
    slideSeconds: Math.round(Number(form.slideSeconds.value) || 10),
    shuffle: form.shuffle.checked,
  };
}

async function saveMode() {
  const message = $('#mode-msg');
  const value = modeFormValue();
  if (value.showMode === 'tags' && value.selectedTags.length === 0) {
    message.textContent = 'Выбери хотя бы один тег';
    return;
  }
  if (value.showMode === 'collection' && !value.selectedCollection) {
    message.textContent = 'Сначала создай коллекцию';
    return;
  }
  const chosen = ui.collections.find((c) => c.collectionId === value.selectedCollection);
  const matching = ui.items.filter((item) => !item.flagged
    && (value.showMode === 'images' ? item.frameCount === 1
      : value.showMode === 'animations' ? item.frameCount > 1
        : value.showMode === 'scenes' ? item.kind === 'scene'
          : value.showMode === 'collection' ? chosen.mediaIds.includes(item.mediaId)
            : value.showMode === 'tags' ? item.tags.some((t) => value.selectedTags.includes(t)) : true));
  try {
    ui.settings = await api.putSettings(value);
    renderModeForm();
    message.textContent = matching.length
      ? `Сохранено: ${MODE_NAMES[value.showMode]}, ${matching.length} шт.`
      : 'Сохранено, но под этот режим ничего не подходит';
    refreshStatus();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  }
}

// --- library -----------------------------------------------------------------------------

async function thumbnail(item) {
  if (!ui.thumbs.has(item.mediaId)) {
    ui.thumbs.set(item.mediaId, api.mediaFile(item.mediaId).then(decodePrestoBin));
  }
  return ui.thumbs.get(item.mediaId);
}

let libraryPlayers = [];

function renderLibrary(brokenIds = []) {
  libraryPlayers.forEach((p) => p.stop());
  libraryPlayers = [];
  const filter = $('#lib-filter').value;
  const collection = ui.collections.find((c) => c.collectionId === $('#lib-collection').value);
  const items = ui.items.filter((item) => (!filter || item.tags.includes(filter))
    && (!collection || collection.mediaIds.includes(item.mediaId)))
    .sort((a, b) => b.createdAt - a.createdAt);
  ui.visibleIds = items.map((item) => item.mediaId);
  $('#lib-count').textContent = `· ${ui.items.length}`;
  const template = $('#item-template');
  $('#items').replaceChildren(...items.map((item) => {
    const node = template.content.firstElementChild.cloneNode(true);
    const isScene = item.kind === 'scene';
    node.classList.toggle('broken', item.flagged || brokenIds.includes(item.mediaId));
    node.querySelector('.name').textContent = item.name;
    const size = `${(item.byteSize / 1024).toFixed(1)} КБ`;
    node.querySelector('.kind').textContent = isScene
      ? `сцена · ${size}${item.flagged ? ` · отключена: ${item.error}` : ''}`
      : `${item.gridSize}×${item.gridSize} · `
        + `${item.frameCount > 1 ? `гифка, ${item.frameCount} кадров` : 'картинка'} · ${size}`;
    node.querySelector('.tags').replaceChildren(...item.tags.map((t) =>
      Object.assign(document.createElement('span'), { className: 'chip', textContent: t })));
    const canvas = node.querySelector('canvas');
    if (isScene) {
      drawScenePlaceholder(canvas);
    } else {
      thumbnail(item).then((art) => libraryPlayers.push(playArt(canvas, art))).catch(() => {
        node.classList.add('broken');
      });
    }
    const showButton = node.querySelector('[data-action=show]');
    showButton.disabled = item.flagged;
    showButton.addEventListener('click', () => api.showMedia(item.mediaId).then(refreshStatus));
    const enableButton = node.querySelector('[data-action=enable]');
    enableButton.hidden = !item.flagged;
    enableButton.addEventListener('click', () => enableScene(item));
    const pick = node.querySelector('.pick');
    pick.dataset.id = item.mediaId;
    pick.checked = ui.selected.has(item.mediaId);
    pick.setAttribute('aria-label', `Выбрать ${item.name}`);
    pick.addEventListener('change', () => {
      if (pick.checked) ui.selected.add(item.mediaId);
      else ui.selected.delete(item.mediaId);
      renderBulk();
    });
    const uncollect = node.querySelector('[data-action=uncollect]');
    uncollect.hidden = !collection;
    uncollect.addEventListener('click', () => removeFromShownCollection(collection, item));
    node.querySelector('[data-action=edit]').addEventListener('click', () => editItem(item));
    node.querySelector('[data-action=delete]').addEventListener('click', () => deleteItem(item));
    return node;
  }));
  const filterSelect = $('#lib-filter');
  filterSelect.replaceChildren(new Option('Все теги', ''),
    ...ui.tags.map(({ label, count }) => new Option(`${label} (${count})`, label)));
  filterSelect.value = ui.tags.some((t) => t.label === filter) ? filter : '';
  renderBulk();
}

function renderBulk() {
  const count = ui.selected.size;
  $('#bulk-count').textContent = `Выбрано: ${count}`;
  ['#bulk-clear', '#bulk-delete', '#bulk-tag-add', '#bulk-collection-add'].forEach((id) => {
    $(id).disabled = count === 0;
  });
  $('#bulk-collection-add').disabled = count === 0 || ui.collections.length === 0;
}

function setVisibleSelection(selected) {
  ui.visibleIds.forEach((id) => (selected ? ui.selected.add(id) : ui.selected.delete(id)));
  document.querySelectorAll('#items .pick').forEach((box) => { box.checked = selected; });
  renderBulk();
}

function clearSelection() {
  ui.selected.clear();
  document.querySelectorAll('#items .pick').forEach((box) => { box.checked = false; });
  renderBulk();
}

async function runBulk(changes, done) {
  const message = $('#bulk-msg');
  const mediaIds = [...ui.selected];
  try {
    await api.bulk({ ...changes, mediaIds });
    message.textContent = done(mediaIds.length);
    await refreshAll();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  }
}

async function bulkDelete() {
  const count = ui.selected.size;
  if (!confirm(`Удалить выбранные файлы: ${count} шт.? Вернуть их будет нельзя.`)) return;
  const ids = [...ui.selected];
  await runBulk({ action: 'delete' }, (n) => `Удалено: ${n}`);
  ids.forEach((id) => ui.thumbs.delete(id));
}

async function bulkAddTag() {
  const [tag] = parseTags($('#bulk-tag').value);
  if (!tag) {
    $('#bulk-msg').textContent = 'Напиши тег';
    return;
  }
  await runBulk({ action: 'addTag', tag }, (n) => `Тег «${tag}» добавлен: ${n}`);
  $('#bulk-tag').value = '';
}

async function bulkAddToCollection() {
  const collectionId = $('#bulk-collection').value;
  const collection = ui.collections.find((c) => c.collectionId === collectionId);
  if (!collection) return;
  await runBulk({ action: 'addToCollection', collectionId }, (n) => `Добавлено в «${collection.name}»: ${n}`);
}

async function removeFromShownCollection(collection, item) {
  try {
    await api.removeFromCollection(collection.collectionId, item.mediaId);
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
  }
}

// --- collections ---------------------------------------------------------------------------

function fillCollectionSelect(select, firstLabel) {
  const value = select.value;
  select.replaceChildren(...(firstLabel === null ? [] : [new Option(firstLabel, '')]),
    ...ui.collections.map((c) => new Option(`${c.name} (${c.mediaIds.length})`, c.collectionId)));
  if ([...select.options].some((option) => option.value === value)) select.value = value;
}

function renderCollections() {
  fillCollectionSelect($('#lib-collection'), 'Все коллекции');
  fillCollectionSelect($('#settings-form').collection, 'Без коллекции');
  fillCollectionSelect($('#bulk-collection'), null);
  const list = $('#collections-list');
  list.replaceChildren(...ui.collections.map((collection) => {
    const row = document.createElement('li');
    row.className = 'collection-row';
    const name = Object.assign(document.createElement('span'), {
      textContent: `${collection.name} · ${collection.mediaIds.length}`,
    });
    const rename = Object.assign(document.createElement('button'), { type: 'button', textContent: 'Переименовать' });
    rename.addEventListener('click', () => renameCollection(collection));
    const remove = Object.assign(document.createElement('button'), {
      type: 'button', textContent: 'Удалить', className: 'danger',
    });
    remove.addEventListener('click', () => deleteCollection(collection));
    row.append(name, rename, remove);
    return row;
  }));
  $('#collections-empty').hidden = ui.collections.length > 0;
}

async function createCollection() {
  const field = $('#collection-name');
  const name = field.value.trim();
  const message = $('#collection-msg');
  if (!name) {
    message.textContent = 'Напиши название';
    return;
  }
  try {
    await api.createCollection(name);
    field.value = '';
    message.textContent = '';
    await refreshAll();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  }
}

async function renameCollection(collection) {
  const name = prompt('Название коллекции', collection.name);
  if (name === null || !name.trim()) return;
  try {
    await api.renameCollection(collection.collectionId, name.trim());
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
  }
}

async function deleteCollection(collection) {
  if (!confirm(`Удалить коллекцию «${collection.name}»? Сами файлы останутся.`)) return;
  try {
    await api.deleteCollection(collection.collectionId);
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
  }
}

function renderEditTags() {
  renderTagLabels($('#edit-tag-labels'), $('#edit-form').tags, renderEditTags);
}

function renderEditCollections(item) {
  const box = $('#edit-collections');
  box.replaceChildren(...(ui.collections.length ? ui.collections.map((collection) => {
    const member = collection.mediaIds.includes(item.mediaId);
    const chip = makeLabel(collection.name, member, (self) => {
      self.setAttribute('aria-pressed', String(self.classList.toggle('on')));
    });
    chip.dataset.id = collection.collectionId;
    return chip;
  }) : [Object.assign(document.createElement('span'), { className: 'muted', textContent: 'Коллекций пока нет' })]));
}

function editItem(item) {
  const form = $('#edit-form');
  ui.editing = item;
  form.name.value = item.name;
  form.tags.value = item.tags.join(', ');
  $('#edit-msg').textContent = '';
  renderEditTags();
  renderEditCollections(item);
  $('#edit-dialog').showModal();
}

async function saveEdit() {
  const form = $('#edit-form');
  const item = ui.editing;
  const save = $('#edit-save');
  save.disabled = true;
  try {
    await api.patchMedia(item.mediaId, {
      name: form.name.value.trim() || item.name,
      tags: parseTags(form.tags.value),
      collections: [...$('#edit-collections').querySelectorAll('.chip.on')].map((chip) => chip.dataset.id),
    });
    $('#edit-dialog').close();
    await refreshAll();
  } catch (error) {
    if (error.status === 401) lock();
    else $('#edit-msg').textContent = `Ошибка: ${error.message}`;
  } finally {
    save.disabled = false;
  }
}

async function enableScene(item) {
  try {
    await api.patchMedia(item.mediaId, { flagged: false });
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
  }
}

async function deleteItem(item) {
  if (!confirm(`Удалить «${item.name}»?`)) return;
  try {
    await api.removeMedia(item.mediaId);
    ui.thumbs.delete(item.mediaId);
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
  }
}

// --- status ------------------------------------------------------------------------------

function lock() {
  ui.locked = true;
  setPassword(null);
  $('#edit-dialog').close();
  libraryPlayers.forEach((p) => p.stop());
  libraryPlayers = [];
  ui.thumbs.clear();
  ui.items = [];
  ui.tags = [];
  $('#items').replaceChildren();
  $('#app').hidden = true;
  $('#login').hidden = false;
  $('#logout').hidden = true;
  $('#status').textContent = 'Нужен пароль';
}

async function login() {
  const form = $('#login-form');
  const message = $('#login-msg');
  const value = form.password.value;
  if (!/^[\x20-\x7e]+$/.test(value)) {
    message.textContent = 'В пароле могут быть только латиница, цифры и знаки';
    return;
  }
  setPassword(value);
  message.textContent = 'Проверяю…';
  try {
    await api.status();
  } catch (error) {
    setPassword(null);
    message.textContent = error.status === 401 ? 'Неверный пароль' : `Ошибка: ${error.message}`;
    return;
  }
  form.reset();
  message.textContent = '';
  ui.locked = false;
  $('#login').hidden = true;
  $('#app').hidden = false;
  await refreshAll();
}

function renderProtection(passwordSet) {
  $('#no-password').hidden = passwordSet;
  $('#logout').hidden = !passwordSet;
  ui.passwordSet = passwordSet;
  renderUploadControls();
}

async function refreshStatus() {
  if (ui.locked) return null;
  try {
    const status = await api.status();
    renderProtection(status.passwordSet);
    const current = ui.items.find((i) => i.mediaId === status.current.mediaId);
    const mode = ui.settings ? MODE_NAMES[ui.settings.showMode] : '';
    $('#status').textContent = current
      ? `Сейчас: ${current.name} · ${status.current.index + 1}/${status.current.playlistLength} · ${mode}`
      : `Нечего показывать · ${mode}`;
    const { kind, free, total } = status.storage;
    $('#storage').textContent = total
      ? `Хранилище: ${kind}, свободно ${(free / 1048576).toFixed(1)} из ${(total / 1048576).toFixed(1)} МБ`
      : `Хранилище: ${kind}`;
    return status;
  } catch (error) {
    if (error.status === 401) lock();
    else $('#status').textContent = 'Presto недоступен';
    return null;
  }
}

async function refreshAll() {
  [ui.items, ui.tags, ui.settings, ui.collections] = await Promise.all([
    api.listMedia(), api.tags(), api.getSettings(), api.listCollections(),
  ]);
  const known = new Set(ui.items.map((item) => item.mediaId));
  ui.selected = new Set([...ui.selected].filter((id) => known.has(id)));
  renderTagSuggestions();
  renderCollections();
  renderModeForm();
  const status = await refreshStatus();
  renderLibrary(status ? status.brokenIds : []);
}

// --- wiring ------------------------------------------------------------------------------

function init() {
  $('#file').addEventListener('change', (e) => { addFiles([...e.target.files]); e.target.value = ''; });
  const drop = $('#drop');
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('over');
    addFiles([...e.dataTransfer.files]);
  });
  $('#settings-form').addEventListener('change', (e) => {
    const { name } = e.target;
    if (!(name in SETUP_READERS) || name === 'tags') return;
    changeActive({ [name]: SETUP_READERS[name](e.currentTarget) });
    renderQueue();
    if (name === 'gridSize') renderGridHint();
    if (name === 'paletteName') renderPaletteFields();
    if (name === 'fitMode' && ui.source) {  // zoom 1 means a different square in each mode
      ui.view = defaultCropView(ui.source.width, ui.source.height);
      renderCropControls();
    }
    if (name !== 'collection') scheduleConvert();
  });
  $('#settings-form').tags.addEventListener('input', onUploadTagsChanged);
  $('#setup-reset').addEventListener('click', resetActiveSetup);
  $('#edit-form').addEventListener('submit', (e) => { e.preventDefault(); saveEdit(); });
  $('#edit-form').tags.addEventListener('input', renderEditTags);
  $('#edit-cancel').addEventListener('click', () => $('#edit-dialog').close());
  const preview = $('#preview');
  preview.addEventListener('pointerdown', onPreviewPointerDown);
  preview.addEventListener('pointermove', onPreviewPointerMove);
  preview.addEventListener('pointerup', onPreviewPointerEnd);
  preview.addEventListener('pointercancel', onPreviewPointerEnd);
  preview.addEventListener('wheel', onPreviewWheel, { passive: false });
  $('#crop-zoom').addEventListener('input', onZoomSlider);
  $('#crop-reset').addEventListener('click', resetCrop);
  $('#settings-form').addEventListener('submit', (e) => e.preventDefault());
  $('#upload').addEventListener('click', uploadQueue);
  $('#upload-cancel').addEventListener('click', () => { ui.cancelRequested = true; });
  $('#queue-clear').addEventListener('click', clearQueue);
  $('#collection-create').addEventListener('click', createCollection);
  $('#collection-form').addEventListener('submit', (e) => { e.preventDefault(); createCollection(); });
  $('#bulk-all').addEventListener('click', () => setVisibleSelection(true));
  $('#bulk-clear').addEventListener('click', clearSelection);
  $('#bulk-delete').addEventListener('click', bulkDelete);
  $('#bulk-tag-add').addEventListener('click', bulkAddTag);
  $('#bulk-collection-add').addEventListener('click', bulkAddToCollection);
  $('#lib-collection').addEventListener('change', () => refreshStatus().then((s) => renderLibrary(s ? s.brokenIds : [])));
  $('#login-form').addEventListener('submit', (e) => { e.preventDefault(); login(); });
  $('#logout').addEventListener('click', lock);
  $('#mode-form').addEventListener('change', (e) => {
    if (e.target.name === 'showMode') {
      $('#mode-tags').hidden = e.target.value !== 'tags';
      $('#mode-collection').hidden = e.target.value !== 'collection';
    }
  });
  $('#save-mode').addEventListener('click', saveMode);
  $('#lib-filter').addEventListener('change', () => refreshStatus().then((s) => renderLibrary(s ? s.brokenIds : [])));
  $('#next').addEventListener('click', () => api.next().then(refreshStatus));
  $('#prev').addEventListener('click', () => api.prev().then(refreshStatus));
  ui.shared = { ...formSetup(), view: null };
  renderPaletteFields();
  renderGridHint();
  // One request first: a locked gallery answers each failed request with a one-second delay.
  api.status().then(refreshAll).catch((error) => {
    if (error.status === 401) lock();
    else $('#status').textContent = `Ошибка: ${error.message}`;
  });
  setInterval(refreshStatus, 5000);
}

init();
