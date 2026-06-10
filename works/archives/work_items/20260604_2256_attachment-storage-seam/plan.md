# Plan

- Work item: works/current/20260604_2256_attachment-storage-seam
- Created at: 20260604_2256
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S1
- Slice: attachment storage seam and configuration

## Goal

Introduce Vocky's first file-storage subsystem behind an `AttachmentStorage` abstraction, with a
local-filesystem implementation and configuration, so later slices (S3 upload, S5 download/delete)
have a stable seam to write/read/delete attachment bytes. No DB and no HTTP in this slice.

## Scope

- In scope: new `src/vocky/storage/` package (`base.py` interface + errors, `local.py`
  filesystem backend, `__init__.py` `get_attachment_storage()` DI), four `VOCKY_ATTACHMENTS_*`
  config vars + a parsed allowed-types property in `src/vocky/config.py`, `.env.example` docs,
  `tests/test_storage.py`, and the `docs/architecture.md` File Storage Subsystem section.
- Out of scope: DB models, HTTP endpoints, capture/worker changes, S3 backend (deferred behind the
  same interface).

## Context

- DI pattern to mirror: `get_engine()`/`get_session_maker()` in `src/vocky/db.py` use a module-level
  lazy singleton; `get_feedback_service()` reads `get_settings()`. `get_attachment_storage()` mirrors
  this (lazy singleton built from `get_settings()`).
- Config pattern: `src/vocky/config.py` is pydantic `BaseSettings` with `Field(alias="VOCKY_...")`,
  `@property` accessors, and `parse_csv_setting` for CSV→tuple; `get_settings()` is `@lru_cache`.

## Milestones

1. `src/vocky/storage/base.py`: `AttachmentStorage` ABC (`save`/`load`/`delete`), `StorageError`,
   `StorageObjectNotFoundError`.
2. `src/vocky/storage/local.py`: `LocalFilesystemAttachmentStorage(root_dir)` with path-traversal
   guard, temp-write + atomic `os.replace`, NotFound on missing, `OSError`→`StorageError`.
3. `src/vocky/storage/__init__.py`: exports + `get_attachment_storage()` lazy singleton.
4. `src/vocky/config.py`: `VOCKY_ATTACHMENTS_DIR`, `VOCKY_ATTACHMENTS_MAX_BYTES` (5 MiB),
   `VOCKY_ATTACHMENTS_MAX_COUNT` (10), `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES` (CSV) + parsed property.
5. `.env.example` documents the four vars.
6. `tests/test_storage.py` covers round-trip (binary), NotFound, traversal rejection, dir creation,
   atomic overwrite.
7. `docs/architecture.md` File Storage Subsystem section.

## Validation

- `uv run pytest tests/test_storage.py -q` green; full `uv run pytest` still green (no regressions).
- `python -c "from vocky.storage import get_attachment_storage"` imports cleanly.

## Risks / open questions

- Path traversal: keys are server-side UUIDs in later slices, but the backend must still reject
  `../`/absolute keys defensively (`resolve()` + `is_relative_to`).
- Atomicity: temp-write + `os.replace` within the same root so the replace is atomic on POSIX.

## Docs to update

- `docs/architecture.md` — File Storage Subsystem (local FS behind the seam; S3 deferred); the four
  config vars. (`.env.example` is config, not `docs/`.)
