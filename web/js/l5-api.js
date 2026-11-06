// LAYER 5 (actions): HttpApi client (contracts/http-api.md).

async function request(method, path, body, headers = {}) {
  const response = await fetch(path, { method, body, headers });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try { message = (await response.json()).error || message; } catch { /* not JSON */ }
    throw new Error(message);
  }
  if (response.status === 204) return null;
  const type = response.headers.get('Content-Type') || '';
  if (type.includes('json')) return response.json();
  return new Uint8Array(await response.arrayBuffer());
}

const json = (value) => [JSON.stringify(value), { 'Content-Type': 'application/json' }];

export const api = {
  status: () => request('GET', '/api/status'),
  listMedia: () => request('GET', '/api/media'),
  mediaFile: (id) => request('GET', `/api/media/${id}/file`),
  upload: (bytes, name, tags) => request('POST',
    `/api/media?name=${encodeURIComponent(name)}&tags=${encodeURIComponent(tags.join(','))}`,
    bytes, { 'Content-Type': 'application/octet-stream' }),
  patchMedia: (id, changes) => request('PATCH', `/api/media/${id}`, ...json(changes)),
  removeMedia: (id) => request('DELETE', `/api/media/${id}`),
  showMedia: (id) => request('POST', `/api/media/${id}/show`),
  next: () => request('POST', '/api/next'),
  prev: () => request('POST', '/api/prev'),
  getSettings: () => request('GET', '/api/settings'),
  putSettings: (settings) => request('PUT', '/api/settings', ...json(settings)),
  tags: () => request('GET', '/api/tags'),
};
