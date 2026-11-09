// LAYER 5 (actions): HttpApi client (contracts/http-api.md).

const PASSWORD_KEY = 'presto-password';

function readStoredPassword() {
  try { return sessionStorage.getItem(PASSWORD_KEY); } catch { return null; }
}

let password = readStoredPassword();

/** Remember the password for this browser tab; null forgets it. */
export function setPassword(value) {
  password = value;
  try {
    if (value === null) sessionStorage.removeItem(PASSWORD_KEY);
    else sessionStorage.setItem(PASSWORD_KEY, value);
  } catch { /* storage blocked: kept in memory only */ }
}

async function request(method, path, body, headers = {}) {
  const auth = password === null ? {} : { Authorization: `Bearer ${password}` };
  const response = await fetch(path, { method, body, headers: { ...headers, ...auth } });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { message = (await response.json()).error || message; } catch { /* not JSON */ }
    throw Object.assign(new Error(message), { status: response.status });
  }
  if (response.status === 204) return null;
  const type = response.headers.get('Content-Type') || '';
  if (type.includes('json')) return response.json();
  return new Uint8Array(await response.arrayBuffer());
}

const json = (value) => [JSON.stringify(value), { 'Content-Type': 'application/json' }];

/** options: {show: false} keeps the current slide, {collection: id} also adds the item there. */
function query(name, tags, { show = true, collection = '' } = {}) {
  return `?name=${encodeURIComponent(name)}&tags=${encodeURIComponent(tags.join(','))}`
    + `${show ? '' : '&show=0'}${collection ? `&collection=${encodeURIComponent(collection)}` : ''}`;
}

export const api = {
  status: () => request('GET', '/api/status'),
  listMedia: () => request('GET', '/api/media'),
  mediaFile: (id) => request('GET', `/api/media/${id}/file`),
  upload: (bytes, name, tags, options) => request('POST', `/api/media${query(name, tags, options)}`,
    bytes, { 'Content-Type': 'application/octet-stream' }),
  uploadScene: (bytes, name, tags, options) => request('POST', `/api/scenes${query(name, tags, options)}`,
    bytes, { 'Content-Type': 'text/plain' }),
  patchMedia: (id, changes) => request('PATCH', `/api/media/${id}`, ...json(changes)),
  removeMedia: (id) => request('DELETE', `/api/media/${id}`),
  bulk: (changes) => request('POST', '/api/media/bulk', ...json(changes)),
  listCollections: () => request('GET', '/api/collections'),
  createCollection: (name) => request('POST', '/api/collections', ...json({ name })),
  renameCollection: (id, name) => request('PATCH', `/api/collections/${id}`, ...json({ name })),
  deleteCollection: (id) => request('DELETE', `/api/collections/${id}`),
  removeFromCollection: (id, mediaId) => request('DELETE', `/api/collections/${id}/items/${mediaId}`),
  showMedia: (id) => request('POST', `/api/media/${id}/show`),
  next: () => request('POST', '/api/next'),
  prev: () => request('POST', '/api/prev'),
  getSettings: () => request('GET', '/api/settings'),
  putSettings: (settings) => request('PUT', '/api/settings', ...json(settings)),
  tags: () => request('GET', '/api/tags'),
};
