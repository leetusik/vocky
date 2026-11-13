# Result

- Work item: works/current/20260604_2309_attachment-upload-endpoint
- Created at: 20260604_2309
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S3
- Slice: synchronous attachment upload endpoint
- Review status: pending
- Reviewer:
- Next action: Implement P2.S4 (async-link attachments through the capture path).

## Outcome

Added `POST /api/feedback/attachments` (`src/vocky/attachments_api.py`):

- Requires non-blank `user_id` + `source_product` query params (reuses `require_scope_value`).
- Byte cap enforced by a `Content-Length` pre-check (+ multipart slack) → 413, then `UploadFile.size`
  → 413, then a chunked running total → 413 (because `max_part_size` does not bound file parts in
  Starlette 0.52.1).
- `await request.form(max_files=1, max_fields=1)` with `MultiPartException` → 400; missing `file`
  part → 400; `form.close()` in `finally`.
- Empty body → 400. `sniff_image_content_type` derives the stored `content_type` from magic bytes
  (jpeg/png/gif/webp), intersected with `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES`; SVG/spoofed/unknown →
  415.
- `storage_key = uuid4`; write-then-row (`storage.save` → 503 on `StorageError`;
  `create_unlinked_attachment` → on `FeedbackPersistenceError`, best-effort `storage.delete` then
  503). `201 {attachment_id, content_type, byte_size, filename}`.
- Filename cleaned of control/newline characters and length-capped for safe storage.
- Spliced `*attachment_routes` into `app.py` (auto-guarded by `APIBearerAuthMiddleware`).
- Added `python-multipart>=0.0.26` as an explicit direct dependency.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_attachments_api.py -q` → 7 passed (valid PNG → 201 + unlinked row with
  claimed scope + bytes retrievable from storage; spoofed SVG → 415; oversize → 413; empty → 400;
  missing `file` part → 400; missing `user_id`/`source_product` → 400; bearer required when
  configured: no token → 401, valid → 201).
- `uv run pytest -q` → 150 passed (143 prior + 7 new; no regressions).

## Files changed

- `src/vocky/attachments_api.py` (new — handler, sniff/clean helpers, `routes`)
- `src/vocky/app.py` (import + splice `*attachment_routes`)
- `pyproject.toml` / `uv.lock` (`python-multipart>=0.0.26`)
- `tests/test_attachments_api.py` (new, 7 tests)

## Docs updated

- `docs/api.md` — added the **Feedback Attachment Upload REST API** contract (scoped multipart upload,
  magic-byte validation, size cap, error codes, upload-first/link-later note).

## Roadmap updates

- `P2.S3` done. Next slice `P2.S4` (async-link attachments through the capture path). Phase P2 stays
  `in_progress`.

## Retrospective

- The Starlette `max_part_size` gotcha (it does not cap file-part bytes) was the load-bearing detail;
  the layered `Content-Length` + `size` + running-total guard is what actually enforces the cap.
  Deriving `content_type` from magic bytes rather than the declared header is the other security
  hinge, blocking SVG and spoofed declarations.
