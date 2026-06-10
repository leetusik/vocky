# Plan

- Work item: works/current/20260604_2320_attachment-reads-and-downloads
- Created at: 20260604_2320
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S5
- Slice: attachment exposure in reads and scoped downloads

## Goal

Surface linked attachments in P1's operator-review and end-user-read responses, add scoped operator
and end-user download endpoints, and delete attachment files when their feedback is deleted.

## Scope

- In scope: `serialize_attachment`; `attachments` arrays in admin detail + end-user read; operator
  download (`/admin/api/feedback/{id}/attachments/{id}`) and end-user download
  (`/api/feedback/{id}/attachments/{id}`); delete-files-on-delete; `docker-compose` volume; tests in
  `test_admin_api.py` + `test_user_feedback_api.py`; `docs/product.md` + `docs/api.md` +
  `docs/architecture.md`.
- Out of scope: orphan-upload sweeper (`D3`), S3 backend, thumbnails.

## Context / validated mechanics

- Download bytes via plain `Response(content=data, media_type=...)` (bytes already in memory; sets
  Content-Length). End-user adds `Content-Disposition: attachment`, `X-Content-Type-Options:
  nosniff`, `Cache-Control: private, no-store`.
- End-user download authorized off the LINKED feedback row's `(user_id, source_product)` via a
  join (`get_user_attachment`); operator download verifies feedback linkage only (`get_admin_attachment`).
  Any miss → 404 (no existence leak).
- Delete: gather `storage_key`s before the cascade in one transaction (`delete_feedback_event` now
  returns `(deleted, storage_keys)`), then best-effort file delete after commit.
- Batch attachments with comments in one session for the list read.

## Milestones

1. `serialize_attachment(record, *, url)` in `query_feedback_common.py`.
2. Repo `get_user_attachment` / `get_admin_attachment`; service read wrappers,
   `list_feedback_with_comments_and_attachments`, delete-returns-keys.
3. `admin_api.py`: detail `attachments`, operator download route, delete file cleanup.
4. `api.py`: read threads attachments, end-user download route + safe Content-Disposition.
5. `docker-compose.yml`: `attachments-data` volume on app + worker.
6. Tests (admin + user) and docs.

## Validation

- Targeted `uv run pytest tests/test_admin_api.py tests/test_user_feedback_api.py -q` green; full
  `uv run pytest` green; alembic single head; migration downgrade/upgrade round-trip clean.

## Risks / open questions

- `delete_feedback_event` signature change ripples to two cascade tests — update their assertions.
- Cross-user/product download isolation — explicit 404 tests for other user, other product, missing
  scope, and auth.

## Docs to update

- `docs/product.md` (attachments introduced), `docs/api.md` (operator + end-user download contracts,
  `attachments` arrays, flip P2 forward-compat note), `docs/architecture.md` (batched reads, downloads
  reuse P1 scoping, delete-on-delete, shared volume).
