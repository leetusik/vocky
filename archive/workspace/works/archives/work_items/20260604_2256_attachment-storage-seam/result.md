# Result

- Work item: works/current/20260604_2256_attachment-storage-seam
- Created at: 20260604_2256
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S1
- Slice: attachment storage seam and configuration
- Review status: pending
- Reviewer:
- Next action: Implement P2.S2 (feedback_attachments persistence).

## Outcome

Introduced Vocky's first file-storage subsystem behind an `AttachmentStorage` seam:

- `src/vocky/storage/base.py` — `AttachmentStorage` ABC (`save`/`load`/`delete`), `StorageError`,
  `StorageObjectNotFoundError`.
- `src/vocky/storage/local.py` — `LocalFilesystemAttachmentStorage(root_dir)`: rejects absolute /
  traversal keys (`resolve()` + `is_relative_to`), creates intermediate dirs, writes via sibling
  temp file + atomic `os.replace`, maps missing→`StorageObjectNotFoundError` and other `OSError`→
  `StorageError`, creates the root on init.
- `src/vocky/storage/__init__.py` — exports + `get_attachment_storage()` returning a backend built
  from cached settings (mirrors `get_feedback_service()`).
- `src/vocky/config.py` — `VOCKY_ATTACHMENTS_DIR` (`./attachments`), `VOCKY_ATTACHMENTS_MAX_BYTES`
  (5 MiB), `VOCKY_ATTACHMENTS_MAX_COUNT` (10), `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES` (CSV) + the
  `attachments_allowed_mime_type_values` property.
- `.env.example` documents the four vars.

No DB and no HTTP in this slice, as scoped.

## Deviations from plan

None. `get_attachment_storage()` returns a fresh backend per call (not a cached singleton) to match
the `get_feedback_service()` precedent and keep later upload/download tests free of stale-singleton
state.

## Validation run

- `uv run pytest tests/test_storage.py -q` → 9 passed (round-trip incl. non-UTF-8 bytes, NotFound,
  relative + absolute traversal rejection, intermediate-dir creation, atomic overwrite with no temp
  leak, delete + delete-missing, root created on init).
- `uv run pytest -q` → 131 passed (122 prior + 9 new; no regressions).

## Files changed

- `src/vocky/storage/base.py` (new)
- `src/vocky/storage/local.py` (new)
- `src/vocky/storage/__init__.py` (new)
- `src/vocky/config.py` (four `VOCKY_ATTACHMENTS_*` settings + parsed property)
- `.env.example` (four vars documented)
- `tests/test_storage.py` (new, 9 tests)

## Docs updated

- `docs/architecture.md` — added the four config vars to the Configuration Surface and a new **File
  Storage Subsystem** section (seam, local backend, S3 deferred behind the same interface).

## Roadmap updates

- `P2.S1` done. Next slice `P2.S2` (feedback_attachments persistence). Phase P2 stays `in_progress`.

## Retrospective

- The seam is intentionally a dumb byte store: size/count/type limits live in config and are
  enforced at the HTTP/capture layers (S3/S4), not in the backend, so the S3 object-store backend
  can drop in unchanged. Keys are server UUIDs in later slices, but the backend still rejects unsafe
  keys defensively.
