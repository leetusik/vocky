# Result

- Work item: works/current/20260604_2223_decompose-feedback-image-attachments
- Created at: 20260604_2223
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.DECOMP
- Slice: decompose phase
- Review status: pending
- Reviewer:
- Next action: Implement P2.S1 (attachment storage seam + configuration) on the next `do the next slice`.

## Outcome

Decomposed phase P2 into five dependency-ordered middle slices and recorded them in
`works/backlog.md` between `P2.DECOMP` and `P2.REVIEW`:

- **P2.S1 — attachment storage seam and configuration** (foundation; no DB, no HTTP): new
  `src/vocky/storage/` (`AttachmentStorage` interface + `LocalFilesystemAttachmentStorage` with
  path-traversal guard and atomic write + `get_attachment_storage()` DI), four `VOCKY_ATTACHMENTS_*`
  config vars, `tests/test_storage.py`, `docs/architecture.md`. S3 deferred behind the interface.
- **P2.S2 — feedback_attachments persistence** (depends on S1 ordering): new
  `feedback_attachments` table/model (NULLABLE `feedback_id` for upload-before-link, ON DELETE
  CASCADE, `claimed_user_id`/`claimed_source_product`) + Alembic migration off `20260604_2116`,
  `CreateFeedbackAttachment`/`FeedbackAttachmentRecord` types, repository (create / get / guarded
  `link_attachments_to_feedback` / batched `list_attachments_for_feedback_ids` / list /
  `list_storage_keys_for_feedback`) + service incl. `create_feedback_event_with_attachments`,
  `tests/test_feedback_attachments.py`, `docs/architecture.md`.
- **P2.S3 — synchronous attachment upload endpoint** (depends on S1, S2): new
  `src/vocky/attachments_api.py` `POST /api/feedback/attachments` (scoped, streamed byte cap,
  magic-byte sniff, write-then-row + cleanup), `app.py` wiring, `python-multipart` dep,
  `tests/test_attachments_api.py`, `docs/api.md`.
- **P2.S4 — async-link attachments through capture path** (depends on S2, S3): `attachment_ids` on
  `CreateFeedbackEvent` + capture normalization + queue serialize/deserialize (back-compat) + worker
  scope-verified linking, queue/worker tests, `docs/api.md` + `docs/architecture.md`.
- **P2.S5 — attachment exposure in reads and scoped downloads** (depends on S2, S3, S4, S1):
  `serialize_attachment` + `attachments` arrays in the admin detail and end-user read, operator +
  end-user download endpoints with P1 scoping (404 on cross-scope), delete-files-on-feedback-delete,
  `docker-compose` shared volume, `tests/test_admin_api.py` + `tests/test_user_feedback_api.py`,
  `docs/product.md` + `docs/api.md` + `docs/architecture.md`.

Each slice note names exact files, expected behavior, error codes, and edge cases so implementation
has no ambiguity. Phase P2 set to `in_progress`; `P2.DECOMP` marked `done`; work item linked.

Key design decisions captured for the implementation slices:

- **Upload-first async-link**: the client uploads each image synchronously to get an
  `attachment_id`; the capture payload carries `attachment_ids` (UUID strings) through the existing
  Redis queue; the worker links them to the feedback row after persist, in the same transaction.
  Binaries never enter the queue.
- **Identity binding at upload** (confirmed with the user): the attachment row stores
  `claimed_user_id`/`claimed_source_product`; the worker links only if they match the feedback's
  scope via a guarded `UPDATE ... WHERE feedback_id IS NULL AND claimed_* = ...`. This blocks a
  misrouting integration from attaching one user's image to another user's feedback and is the
  must-have for "an end user sees only their own attachments". End-user downloads are additionally
  authorized off the linked feedback row (404, not 403, on mismatch).
- **Delete files on feedback-delete** (confirmed with the user): Admin delete gathers `storage_key`s
  before the cascade and removes the files; the scheduled orphan-upload sweeper is deferred (`D3`)
  with the schema kept sweep-ready.
- **Local filesystem only** behind an `AttachmentStorage` abstraction (S3 deferred); **magic-byte
  MIME sniffing** (not the declared header); UUID-only storage keys; streamed size cap; per-feedback
  count cap enforced at link time.
- A batched `list_attachments_for_feedback_ids` (S2) keeps the S5 list read free of N+1, mirroring
  P1's `list_comments_for_feedback_ids`.

## Deviations from plan

None. This slice produced only analysis and backlog/deferred edits, as planned.

## Validation run

- Re-read `works/backlog.md`: P2 is `in_progress`; slice order is `P2.DECOMP` (done) → `P2.S1` →
  `P2.S2` → `P2.S3` → `P2.S4` → `P2.S5` → `P2.REVIEW` (all middle/review slices `todo`); work item
  linked on the phase and on `P2.DECOMP`.
- `works/deferred.md`: `D3` (orphan-upload sweeper) present with source `P2.DECOMP`.
- No `src/`, `alembic/`, `tests/`, `docs/`, `docker-compose.yml`, or `pyproject.toml` files were
  modified by this slice (decompose-only).

## Files changed

- `works/backlog.md` — set P2 `in_progress`, linked work item, marked `P2.DECOMP` done, inserted
  `P2.S1`–`P2.S5`.
- `works/deferred.md` — added `D3` (orphan-upload sweeper).
- `works/current/20260604_2223_decompose-feedback-image-attachments/plan.md`, `result.md` — this
  work item.

## Docs updated

- None (decompose-only slice). Doc updates are scheduled inside the middle slices:
  `architecture.md` (S1, S2, S4, S5), `api.md` (S3, S4, S5), `product.md` (S5).

## Roadmap updates

- Phase P2 now has its full middle-slice plan and is `in_progress`. P2 remains the current phase for
  `do the next slice` / `do the whole phase`; the next slice is `P2.S1`.

## Retrospective

- The hard part of P2 is the async-capture decoupling: the feedback UUID exists only after the
  worker persists, so attachments must be uploaded first and linked later. Grounding the
  decomposition in the real queue serializer (an explicit field allowlist) and the worker's
  discard-the-record persist call made the two load-bearing risks concrete and assignable — the
  silent `attachment_ids` drop (S4) and cross-user link integrity (S2 columns + S4 check + S5
  download authz). Everything else reuses P1's store/serialize/scoping/auth plumbing; the only
  genuinely new subsystem is the storage seam (S1), which is why it earns its own slice.
