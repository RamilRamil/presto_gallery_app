# Data Model (mirrors knowledge/domain.okf.json)

- **MediaItem**: mediaId (8 hex), name (1..64), tags (sorted unique Tag labels), frameCount ≥1, gridSize, byteSize, createdAt.
- **Tag**: label — trimmed, lowercased, collapsed spaces, 1..24 chars of letters/digits/`-`/`_`/space.
- **Catalog**: `{formatVersion: 1, items: [MediaItem…]}` in `catalog.json`.
- **DeviceSettings**: `{showMode: all|images|animations|tags, selectedTags: [], slideSeconds: 3..600, shuffle: bool}` in `settings.json`.
- **Playlist**: list of mediaId; rebuilt on every Catalog/DeviceSettings change; shuffle uses a per-round seed.
- **Command** (D3 input): `upload(item)`, `rename(id,name)`, `set_tags(id,tags)`, `remove(id)`, `set_settings(settings)`.
