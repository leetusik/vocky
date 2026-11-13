# Plan

- Work item: works/current/20260604_2309_attachment-upload-endpoint
- Created at: 20260604_2309
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S3
- Slice: synchronous attachment upload endpoint

## Goal

Add `POST /api/feedback/attachments`: a synchronous, scoped multipart image upload that validates and
stores the bytes and inserts an unlinked `feedback_attachments` row, returning an `attachment_id` the
client later references in a capture call.

## Scope

- In scope: new `src/vocky/attachments_api.py` (handler + `routes`), wiring into `app.py`,
  `python-multipart` dependency, `tests/test_attachments_api.py`, `docs/api.md`.
- Out of scope: linking through capture (S4), reads/downloads (S5).

## Context / validated mechanics

- `max_part_size` does NOT bound file-part size in Starlette 0.52.1 (verified). Enforce the byte cap
  with a `Content-Length` pre-check + `UploadFile.size` + a chunked running total → 413.
- `UploadFile.content_type` is client-controlled; derive the stored type from magic-byte sniffing
  (JPEG `FF D8 FF`; PNG `89 50 4E 47 0D 0A 1A 0A`; GIF `GIF87a`/`GIF89a`; WebP `RIFF`+`WEBP@8`).
- Catch `MultiPartException` (from `starlette.formparsers`) → 400 to keep the `{"detail": ...}` shape.
- Reuse `require_scope_value` from `api.py`; auto-guarded by `APIBearerAuthMiddleware` on `/api/`.
- Write-then-row: `storage.save` then `create_unlinked_attachment`; delete the file if the row fails.

## Milestones

1. `sniff_image_content_type` + `_clean_filename` helpers.
2. `upload_attachment` handler (scope → CL pre-check → form parse → size/sniff/empty → write → row →
   201), `routes`.
3. Splice `*attachment_routes` into `app.py`; `uv add python-multipart`.
4. `tests/test_attachments_api.py` (tmp-dir storage fixture).
5. `docs/api.md` upload contract.

## Validation

- `uv run pytest tests/test_attachments_api.py -q` green; full `uv run pytest` green.

## Risks / open questions

- Byte cap correctness (above) is the main risk; tested via the size guard with a small configured
  max.
- Storage isolation in tests: monkeypatch `vocky.attachments_api.get_attachment_storage` to a
  `tmp_path` backend.

## Docs to update

- `docs/api.md` — Feedback Attachment Upload REST API contract.
