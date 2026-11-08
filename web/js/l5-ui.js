// LAYER 5 (actions): DOM, files, canvas, timers. Talks to layers 3/4 and the HttpApi client.

import {
  binByteSize, checkLimits, checkSceneSize, cropWindow, defaultCropView, gifFirstFrame, gridLimits,
  makeSettings, nameFromFile, panCropView, parseTags, pixelizeFile, zoomCropView,
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
  all: 'всё', images: 'картинки', animations: 'гифки', scenes: 'сцены', tags: 'по тегам',
};

const ui = {
  file: null, fileBytes: null, fileImage: null, art: null, sceneFile: null, locked: false,
  source: null, sourceCanvas: null, view: null, pointers: new Map(),
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

function formSettings() {
  const form = $('#settings-form');
  const paletteName = form.paletteName.value;
  $('#colors-field').hidden = paletteName !== 'adaptive';
  return makeSettings({
    gridSize: Number(form.gridSize.value),
    colorCount: Number(form.colorCount.value),
    paletteName,
    fitMode: form.fitMode.value,
    dither: form.dither.checked,
    backgroundColor: form.backgroundColor.value,
  });
}

function convert() {
  if (!ui.file) return;
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
    $('#upload').disabled = Boolean(problem);
  } catch (error) {
    ui.art = null;
    info.textContent = `Ошибка: ${error.message}`;
    $('#upload').disabled = true;
  }
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

async function onFile(file) {
  if (!file) return;
  ui.file = file;
  $('#drop-text').textContent = file.name;
  $('#settings-form').name.value = nameFromFile(file.name);
  $('#preview-info').textContent = 'Обрабатываю…';
  $('#upload-msg').textContent = '';
  try {
    ui.fileBytes = new Uint8Array(await file.arrayBuffer());
    ui.fileImage = isGif(file, ui.fileBytes) ? null : await decodeImageFile(file);
    setSource(ui.fileImage || gifFirstFrame(ui.fileBytes));
    renderCropControls();
    convert();
  } catch (error) {
    ui.file = null;
    ui.source = null;
    ui.view = null;
    renderCropControls();
    $('#preview-info').textContent = `Не получилось прочитать файл: ${error.message}`;
    $('#upload').disabled = true;
  }
}

async function upload() {
  if (!ui.art) return;
  const form = $('#settings-form');
  const message = $('#upload-msg');
  $('#upload').disabled = true;
  message.textContent = 'Загружаю…';
  try {
    const item = await api.upload(encodePrestoBin(ui.art), form.name.value.trim() || nameFromFile(ui.file.name),
      parseTags(form.tags.value));
    message.textContent = `Готово: «${item.name}» уже на экране`;
    await refreshAll();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  } finally {
    $('#upload').disabled = !ui.art;
  }
}

async function uploadScene() {
  const form = $('#scene-form');
  const message = $('#scene-msg');
  if (!ui.sceneFile) {
    message.textContent = 'Выбери файл сцены';
    return;
  }
  $('#scene-upload').disabled = true;
  message.textContent = 'Загружаю…';
  try {
    const bytes = new Uint8Array(await ui.sceneFile.arrayBuffer());
    const problem = checkSceneSize(bytes.length);
    if (problem) throw new Error(problem);
    const item = await api.uploadScene(bytes, form.name.value.trim() || nameFromFile(ui.sceneFile.name),
      parseTags(form.tags.value));
    message.textContent = `Готово: «${item.name}» уже на экране`;
    form.reset();
    ui.sceneFile = null;
    await refreshAll();
  } catch (error) {
    message.textContent = `Ошибка: ${error.message}`;
  } finally {
    $('#scene-upload').disabled = false;
  }
}

function renderTagSuggestions() {
  const box = $('#tag-suggest');
  box.replaceChildren(...ui.tags.map(({ label }) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'chip';
    chip.textContent = label;
    chip.addEventListener('click', () => {
      const field = $('#settings-form').tags;
      field.value = parseTags(`${field.value},${label}`).join(', ');
    });
    return chip;
  }));
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
  const matching = ui.items.filter((item) => !item.flagged
    && (value.showMode === 'images' ? item.frameCount === 1
      : value.showMode === 'animations' ? item.frameCount > 1
        : value.showMode === 'scenes' ? item.kind === 'scene'
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
  const items = ui.items.filter((item) => !filter || item.tags.includes(filter))
    .sort((a, b) => b.createdAt - a.createdAt);
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
    node.querySelector('[data-action=edit]').addEventListener('click', () => editItem(item));
    node.querySelector('[data-action=delete]').addEventListener('click', () => deleteItem(item));
    return node;
  }));
  const filterSelect = $('#lib-filter');
  filterSelect.replaceChildren(new Option('Все теги', ''),
    ...ui.tags.map(({ label, count }) => new Option(`${label} (${count})`, label)));
  filterSelect.value = ui.tags.some((t) => t.label === filter) ? filter : '';
}

async function editItem(item) {
  const name = prompt('Название', item.name);
  if (name === null) return;
  const tags = prompt('Теги через запятую', item.tags.join(', '));
  if (tags === null) return;
  try {
    await api.patchMedia(item.mediaId, { name: name.trim() || item.name, tags: parseTags(tags) });
    await refreshAll();
  } catch (error) {
    alert(`Ошибка: ${error.message}`);
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
  $('#scene-off').hidden = passwordSet;
  $('#scene-upload').disabled = !passwordSet;
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
  [ui.items, ui.tags, ui.settings] = await Promise.all([api.listMedia(), api.tags(), api.getSettings()]);
  renderTagSuggestions();
  renderModeForm();
  const status = await refreshStatus();
  renderLibrary(status ? status.brokenIds : []);
}

// --- wiring ------------------------------------------------------------------------------

function init() {
  $('#file').addEventListener('change', (e) => onFile(e.target.files[0]));
  const drop = $('#drop');
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('over');
    onFile(e.dataTransfer.files[0]);
  });
  $('#settings-form').addEventListener('change', (e) => {
    if (e.target.name === 'gridSize') renderGridHint();
    if (e.target.name === 'fitMode' && ui.source) {  // zoom 1 means a different square in each mode
      ui.view = defaultCropView(ui.source.width, ui.source.height);
      renderCropControls();
    }
    if (!['name', 'tags'].includes(e.target.name)) scheduleConvert();
  });
  const preview = $('#preview');
  preview.addEventListener('pointerdown', onPreviewPointerDown);
  preview.addEventListener('pointermove', onPreviewPointerMove);
  preview.addEventListener('pointerup', onPreviewPointerEnd);
  preview.addEventListener('pointercancel', onPreviewPointerEnd);
  preview.addEventListener('wheel', onPreviewWheel, { passive: false });
  $('#crop-zoom').addEventListener('input', onZoomSlider);
  $('#crop-reset').addEventListener('click', resetCrop);
  $('#settings-form').addEventListener('submit', (e) => e.preventDefault());
  $('#upload').addEventListener('click', upload);
  $('#scene-file').addEventListener('change', (e) => {
    ui.sceneFile = e.target.files[0] || null;
    if (ui.sceneFile) $('#scene-form').name.value = nameFromFile(ui.sceneFile.name);
  });
  $('#scene-form').addEventListener('submit', (e) => e.preventDefault());
  $('#scene-upload').addEventListener('click', uploadScene);
  $('#login-form').addEventListener('submit', (e) => { e.preventDefault(); login(); });
  $('#logout').addEventListener('click', lock);
  $('#mode-form').addEventListener('change', (e) => {
    if (e.target.name === 'showMode') $('#mode-tags').hidden = e.target.value !== 'tags';
  });
  $('#save-mode').addEventListener('click', saveMode);
  $('#lib-filter').addEventListener('change', () => refreshStatus().then((s) => renderLibrary(s ? s.brokenIds : [])));
  $('#next').addEventListener('click', () => api.next().then(refreshStatus));
  $('#prev').addEventListener('click', () => api.prev().then(refreshStatus));
  formSettings();
  renderGridHint();
  // One request first: a locked gallery answers each failed request with a one-second delay.
  api.status().then(refreshAll).catch((error) => {
    if (error.status === 401) lock();
    else $('#status').textContent = `Ошибка: ${error.message}`;
  });
  setInterval(refreshStatus, 5000);
}

init();
