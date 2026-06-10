# Result

- Work item: works/current/20260604_2320_attachment-reads-and-downloads
- Created at: 20260604_2320
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S5
- Slice: attachment exposure in reads and scoped downloads
- Review status: pending
- Reviewer:
- Next action: P2.REVIEW is intentionally skipped per the user's request ("skip review slice I'll
  handle it later"). Phase P2 stays `in_progress`; work items remain under `works/current/`.

## Outcome

Surfaced attachments in both P1 reads, added scoped downloads, and wired delete-on-delete:

- `src/vocky/tools/query_feedback_common.py`: `serialize_attachment(record, *, url)` shared by both
  surfaces (`{id, content_type, byte_size, filename, created_at, url}`).
- `src/vocky/feedback/repository.py`: `get_user_attachment` (joins attachment→feedback, filters on
  the linked feedback's `user_id`+`source_product`) and `get_admin_attachment` (feedback linkage
  only).
- `src/vocky/feedback/service.py`: `list_feedback_with_comments_and_attachments` (one session,
  batched comments + attachments); `get_user_attachment` / `get_admin_attachment` wrappers;
  `delete_feedback_event` now returns `(deleted, storage_keys)`, gathering keys before the cascade.
- `src/vocky/admin_api.py`: detail payload gains an `attachments` array; operator download
  `GET /admin/api/feedback/{id}/attachments/{id}` (sees all linked attachments; 404 otherwise;
  `nosniff`); `delete_admin_feedback` best-effort deletes the files after the DB commit.
- `src/vocky/api.py`: end-user read threads attachments into `serialize_user_feedback_record`; end-user
  download `GET /api/feedback/{id}/attachments/{id}` requires `user_id`+`source_product`, authorized
  off the linked feedback row (404 on any mismatch), with `Content-Disposition: attachment`,
  `X-Content-Type-Options: nosniff`, `Cache-Control: private, no-store` and an RFC 5987-safe filename.
- `docker-compose.yml`: named `attachments-data` volume mounted at `/var/lib/vocky/attachments` on
  both `app` and `worker`; `VOCKY_ATTACHMENTS_DIR` (and tunables on app) set.

## Deviations from plan

- Changed `delete_feedback_event` to return `(deleted, storage_keys)` (race-free single-transaction
  key gather) instead of adding a parallel method; updated the two existing cascade-test assertions
  in `test_feedback_comments.py` and `test_feedback_attachments.py`.
- Download `url` is the surface-specific relative path the caller builds (admin vs `/api`), passed
  into `serialize_attachment`, because the two download routes live under different prefixes.

## Validation run

- `uv run pytest tests/test_admin_api.py tests/test_user_feedback_api.py -q` → 28 passed (admin
  detail includes attachments; operator download bytes; operator download wrong-feedback → 404;
  delete removes files; end-user read surfaces only the caller's own attachments; end-user download
  own → bytes; other user → 404; other product → 404; missing scope → 400; bearer required → 401).
- `uv run pytest -q` → 170 passed (160 prior + 10 new; no regressions).
- `uv run alembic heads` → single head `20260604_2305`; `alembic history` linear.
- Migration round-trip on the test DB: `downgrade -1` (2305→2116) then `upgrade head` (2116→2305)
  ran clean, ending at head.

## Files changed

- `src/vocky/tools/query_feedback_common.py`, `src/vocky/feedback/repository.py`,
  `src/vocky/feedback/service.py`, `src/vocky/admin_api.py`, `src/vocky/api.py`
- `docker-compose.yml`
- `tests/test_admin_api.py`, `tests/test_user_feedback_api.py`, `tests/test_feedback_comments.py`,
  `tests/test_feedback_attachments.py`

## Docs updated

- `docs/product.md` — image attachments introduced (end users see only their own; operators see all
  for the feedback they review); Public REST surface role updated with upload/download endpoints.
- `docs/api.md` — operator + end-user download contracts; `attachments` arrays in the Admin detail and
  End-User read shapes; Admin Attachment shape; delete-removes-files note; flipped the P2 forward-compat
  note to implemented.
- `docs/architecture.md` — Feedback Attachment Store gains a reads/downloads/delete-on-delete +
  shared-volume paragraph.

## Roadmap updates

- `P2.S1`–`P2.S5` are all `done`. `P2.REVIEW` is intentionally NOT run (user deferred it). Phase P2
  stays `in_progress`; no work items archived (phase-level archival is gated on review passing).

## Retrospective

- The end-user download authorization is the security crux: authorizing off the linked feedback row
  (not the attachment's claimed scope) means an unlinked or cross-scope attachment is never
  downloadable, and the uniform 404 avoids existence leaks. Gathering storage keys before the cascade
  in the same transaction keeps delete-on-delete race-free; making file deletion best-effort keeps an
  already-committed delete from failing on a missing/locked file.
