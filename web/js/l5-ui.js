// LAYER 5 (actions): DOM, files, canvas, timers. Talks to layers 3/4 and the HttpApi client.

import {
  binByteSize, checkLimits, makeSettings, nameFromFile, parseTags, pixelizeFile,
} from './l3-pipeline.js';
import { decodePrestoBin, encodePrestoBin, renderPixelArt } from './l4-encoders.js';
import { api } from './l5-api.js';

const $ = (selector) => document.querySelector(selector);
const MAX_DECODE_SIDE = 1024;
const MODE_NAMES = { all: 'всё', images: 'картинки', animations: 'гифки', tags: 'по тегам' };

const ui = {
  file: null, fileBytes: null, fileImage: null, art: null,
  previewPlayer: null, items: [], tags: [], settings: null, thumbs: new Map(),
};

// --- canvas playback ---------------------------------------------------------------------

function drawArt(canvas, art, frameIndex) {
  const scale = Math.max(1, Math.floor(canvas.width / art.width));
  const image = renderPixelArt(art, frameIndex, scale);
  canvas.getContext('2d').putImageData(new ImageData(image.data, image.width, image.height), 0, 0);
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
      ? pixelizeFile('image', ui.fileImage, settings)
      : pixelizeFile('gif', ui.fileBytes, settings);
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
    convert();
  } catch (error) {
    ui.file = null;
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
  const matching = ui.items.filter((item) => (value.showMode === 'images' ? item.frameCount === 1
    : value.showMode === 'animations' ? item.frameCount > 1
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
    node.classList.toggle('broken', brokenIds.includes(item.mediaId));
    node.querySelector('.name').textContent = item.name;
    node.querySelector('.kind').textContent = `${item.gridSize}×${item.gridSize} · `
      + (item.frameCount > 1 ? `гифка, ${item.frameCount} кадров` : 'картинка')
      + ` · ${(item.byteSize / 1024).toFixed(1)} КБ`;
    node.querySelector('.tags').replaceChildren(...item.tags.map((t) =>
      Object.assign(document.createElement('span'), { className: 'chip', textContent: t })));
    const canvas = node.querySelector('canvas');
    thumbnail(item).then((art) => libraryPlayers.push(playArt(canvas, art))).catch(() => {
      node.classList.add('broken');
    });
    node.querySelector('[data-action=show]').addEventListener('click', () =>
      api.showMedia(item.mediaId).then(refreshStatus));
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

async function refreshStatus() {
  try {
    const status = await api.status();
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
  } catch {
    $('#status').textContent = 'Presto недоступен';
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
    if (!['name', 'tags'].includes(e.target.name)) convert();
  });
  $('#settings-form').addEventListener('submit', (e) => e.preventDefault());
  $('#upload').addEventListener('click', upload);
  $('#mode-form').addEventListener('change', (e) => {
    if (e.target.name === 'showMode') $('#mode-tags').hidden = e.target.value !== 'tags';
  });
  $('#save-mode').addEventListener('click', saveMode);
  $('#lib-filter').addEventListener('change', () => refreshStatus().then((s) => renderLibrary(s ? s.brokenIds : [])));
  $('#next').addEventListener('click', () => api.next().then(refreshStatus));
  $('#prev').addEventListener('click', () => api.prev().then(refreshStatus));
  formSettings();
  refreshAll().catch((error) => { $('#status').textContent = `Ошибка: ${error.message}`; });
  setInterval(refreshStatus, 5000);
}

init();
