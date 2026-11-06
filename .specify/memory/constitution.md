<!--
Sync Impact Report
- Version: template → 1.0.0 (first ratification)
- Principles: I Stratified Design, II Single Domain Vocabulary (OKF), III Tested Pure Layers,
  IV Extensible Documented Binary Format, V Simplicity & Locality
- Added sections: Architecture Constraints, Development Workflow, Governance
- Templates: plan-template.md ✅ (Constitution Check gate is filled per-plan from this file);
  spec-template.md ✅ no change; tasks-template.md ✅ no change
- Deferred TODOs: none
-->

# PRESTO_PIC_LOADER Constitution

## Core Principles

### I. Stratified Design (NON-NEGOTIABLE)

Following Eric Normand's "Grokking Simplicity":

- Code is classified as **data**, **calculations** (pure functions) or **actions** (I/O, time, state).
- Five layers, bottom to top:
  1. color and size primitives;
  2. image operations;
  3. pipeline `pixelize(image, settings) -> PixelArt`;
  4. encoders `PixelArt -> preview PNG / .bin` (the format abstraction barrier);
  5. actions: files, inbox/outbox, CLI.
- A function MUST call only functions of its own layer or lower, and MUST NOT skip layers
  (layer 5 talks to 3 and 4, never directly to 1–2 internals).
- Input/output (filesystem, argv, stdout) MUST happen only in layer 5. Layers 1–4 MUST be pure:
  they work on in-memory values only. Bytes go in and out of layer 4 as `bytes`.
- Every plan MUST contain a layered call graph and confirm it has no upward arrows.

Rationale: pure lower layers are trivially testable, and the format barrier lets us change
output formats or add animation without touching the pipeline.

### II. Single Domain Vocabulary (Open Knowledge Format)

- `knowledge/domain.okf.json` is the single dictionary of domain entities (SourceImage, Grid,
  Palette, PixelArt, PrestoBinFormat, Layer, ...) and their relations.
- `@id` values MUST be lowercase-with-dashes; properties MUST be camelCase; every entity MUST
  have `name` and `description`; every relation MUST point at an existing `@id`.
- Terms in spec.md, plan.md, docs and code identifiers MUST match this dictionary
  (e.g. `PixelArt` class ↔ `pixel-art` entity). A new term goes into the dictionary first.

### III. Tested Pure Layers

- Every public function in layers 1–4 MUST have pytest tests.
- Layer 5 is checked by an integration run: a real image in `inbox/` becomes a preview PNG and
  a `.bin` in `outbox/`; the `.bin` MUST round-trip through a reference decoder in the tests.

### IV. Extensible, Documented Binary Format

- The `.bin` format MUST carry a magic number and a version, and MUST already model a list of
  frames (MVP writes one frame), so GIF animation can be added without changing the pipeline.
- The format MUST be documented byte by byte in `docs/bin-format.md`, with enough detail to
  write a MicroPython player for Presto. Any format change bumps the format version.

### V. Simplicity & Locality

- Python 3 + Pillow (+ pytest for development) only; no other runtime dependencies.
- All files the project creates MUST stay inside the project folder.
- YAGNI: features beyond the MVP spec are not built, only enabled by structure.

## Architecture Constraints

- Target: Pimoroni Presto, 240×240 screen; grid sizes 16/32/64 (32 → 7 px cells).
- Settings are immutable data objects; the pipeline is a composition of calculations.

## Development Workflow

- Spec Kit flow: constitution → specify → plan → tasks → implement.
- spec.md and plan.md are reviewed by the user before any code is written.

## Governance

This constitution overrides other practices. Amendments are made via `/speckit-constitution`,
with a semantic version bump (MAJOR: principle removed/redefined; MINOR: principle added;
PATCH: wording). Every plan's Constitution Check MUST verify Principles I–V.

**Version**: 1.0.0 | **Ratified**: 2026-11-06 | **Last Amended**: 2026-11-06
