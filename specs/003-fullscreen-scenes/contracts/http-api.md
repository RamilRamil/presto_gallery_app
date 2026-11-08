# HttpApi changes (extends 002)

## Authentication

When `WEB_PASSWORD` is set, every `/api/*` request needs `Authorization: Bearer <password>`.
Otherwise the answer is `401 {"error": "password required"}`, with no other data. Failed attempts are
processed at most once per second. `/` and `/web/*` need no password.

## New and changed endpoints

| Method | Path | Body → Response |
|---|---|---|
| POST | `/api/scenes?name=…&tags=a,b` | Scene source, ≤ 64 KB → `201 MediaItem` · `400 {"error": "…"}` invalid · `403` no password configured · `507` no space |
| GET | `/api/status` | adds `passwordSet: bool` |
| GET | `/api/media` | items add `kind`, `flagged`, `error` |
| GET | `/api/media/{id}/file` | picture only; Scene → `404` |
| PATCH | `/api/media/{id}` | adds `flagged: false` to re-enable a Scene |
| DELETE | `/api/media/{id}` | removes the `.bin` or the Scene file |
| GET/PUT | `/api/settings` | `showMode` accepts `scenes` |
| any | a path decoding to contain `..` | `404`, never `500` |
