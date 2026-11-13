# Plan

- Work item: works/current/20260604_2223_decompose-feedback-image-attachments
- Created at: 20260604_2223
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.DECOMP
- Slice: decompose phase

## Goal

Break phase P2 into concrete, dependency-ordered middle slices that let end users attach images to
feedback (jpg/jpeg/png/gif/webp), link them to the async-captured feedback record, surface them in
P1's operator-review and end-user-read responses, and serve them through authenticated downloads —
then record those slices in `works/backlog.md` between `P2.DECOMP` and `P2.REVIEW`. No production
code in this slice; only analysis and backlog/deferred edits.

## Scope

- In scope: analyze the async capture/persist/read patterns, lock the storage + async-link design,
  design the middle slices, write them into `works/backlog.md`, set P2 `in_progress`, mark
  `P2.DECOMP` done, and park the orphan-sweeper follow-up in `works/deferred.md` (`D3`).
- Out of scope: implementing any middle slice; touching `src/`, `alembic/`, `tests/`, `docs/`,
  `docker-compose.yml`, or `pyproject.toml`; non-image attachments, thumbnails/virus-scanning/image
  processing, CDN, multi-tenant, S3 backend (deferred behind the storage abstraction).

## Context

Grounded in the current codebase (read during this slice):

- **Async capture path is the defining constraint.** `POST /api/feedback` (`src/vocky/api.py`)
  validates via `src/vocky/capture.py`, builds `CreateFeedbackEvent`, and calls
  `get_capture_queue().enqueue_feedback(payload)` returning `202` with a queue `request_id` (not the
  feedback row id). A Redis JSON queue (`src/vocky/capture_queue.py`, `serialize_job` /
  `_serialize_payload` — an explicit field allowlist) carries the job; the worker
  (`src/vocky/worker.py`, `CaptureWorker._process_job`) pops it and calls
  `feedback_service.create_feedback_event(job.payload)`, **discarding the returned record**, with
  3 retries then dead-letter. The feedback row UUID is generated app-side (`default=uuid4`) and only
  known after persist. Binaries cannot ride the JSON queue.
- **Adopted protocol: upload-first.** The client uploads each image synchronously to a new endpoint
  that writes bytes to storage and inserts an UNLINKED `feedback_attachments` row, returning an
  `attachment_id`. The capture payload then carries `attachment_ids` (UUID strings) through the
  existing queue; the worker links them to the new feedback row after `create_feedback_event`
  succeeds, in the same transaction. This is the only shape that keeps capture async and the queue
  binary-free; the phase note endorses it.
- **Persistence pattern to mirror.** `feedback_comments` (`src/vocky/persistence/models.py`,
  `FeedbackCommentModel`): UUID PK; `feedback_id` UUID FK→`feedback_events.id` `ON DELETE CASCADE`;
  tz-aware `created_at` default `CURRENT_TIMESTAMP`; indexes on `feedback_id` and `(feedback_id,
  created_at)`. Migration `alembic/versions/20260604_2116_add_feedback_comments.py` is the current
  single head. The attachments table mirrors this but `feedback_id` is NULLABLE (upload-before-link).
- **Domain/service/repo layering.** `src/vocky/feedback/{types,repository,service,__init__}.py`:
  slotted `kw_only` dataclasses, repo methods on `FeedbackRepository(session)`, service wrappers on
  `FeedbackService(session_maker)` with `FeedbackPersistenceError`/`FeedbackReadError`, DI via
  `get_feedback_service()`. Batched `list_comments_for_feedback_ids` avoids N+1 — the attachments
  read mirrors it.
- **P1 read surfaces to extend.** Admin detail `GET /admin/api/feedback/{feedback_id}`
  (`src/vocky/admin_api.py`) builds `serialize_record(record)` then injects a `comments` array; the
  end-user read `GET /api/feedback` (`src/vocky/api.py`) requires non-blank `user_id` +
  `source_product` (`require_scope_value`), builds `FeedbackQueryFilters(...)`, and
  `serialize_user_feedback_record` injects `comments`. `serialize_comment` is shared from
  `src/vocky/tools/query_feedback_common.py`. Attachments mirror this exactly.
- **Auth + wiring.** `src/vocky/auth.py` guards `/api/*` (`APIBearerAuthMiddleware`,
  `VOCKY_API_AUTH_TOKEN`) and `/admin/api/*` (`AdminBearerAuthMiddleware`, `VOCKY_ADMIN_AUTH_TOKEN`)
  by path prefix; new routes under those prefixes are auto-guarded. `src/vocky/app.py` `create_app()`
  splices per-module `routes = [...]` lists. `src/vocky/config.py` is pydantic `BaseSettings` with a
  cached `get_settings()`. **No storage/blob abstraction exists yet** — P2 introduces the first.
- **Tests.** `tests/conftest.py` provides `configured_database` (per-test TRUNCATE) + httpx
  `ASGITransport` apps; `uv run pytest`. Multipart idiom: `client.post(url, files={"file":
  ("photo.png", io.BytesIO(content), "image/png")}, headers=...)`.

### Locked design decisions (from analysis + two confirmed product choices)

- **Storage**: local filesystem only behind an `AttachmentStorage` abstraction; S3 deferred behind
  the same interface.
- **Identity binding at upload (user choice)**: the upload endpoint requires `user_id` +
  `source_product`; the attachment row stores `claimed_user_id` + `claimed_source_product`; the
  worker links only if they match the feedback's `user_id`/`source_product`. The link is a guarded
  `UPDATE ... WHERE id IN (...) AND feedback_id IS NULL AND claimed_user_id = :uid AND
  claimed_source_product = :sp`; non-matching/already-linked/bogus ids are skipped and logged, never
  dead-lettered (a missing screenshot must not fail real feedback). The `feedback_id IS NULL` guard
  makes linking idempotent and blocks cross-feedback theft.
- **Download authorization**: end-user download authorized off the LINKED feedback row's
  `(user_id, source_product)` matching the caller's required `user_id` + `source_product`;
  operator/admin download sees all (admin token only). Cross-scope/missing → 404 (not 403) to avoid
  existence leaks; row-without-file → 404 + log.
- **Validation**: allowed types via magic-byte sniffing (derive `content_type` from the sniff, not
  the declared header; reject SVG); per-request byte cap enforced by streaming (413); per-feedback
  count cap enforced authoritatively at link time (quick reject at capture-accept too).
- **Storage keys** from a server UUID only (never the client filename); filename stored as a column
  for display/`Content-Disposition`, sanitized; local backend writes temp + atomic `os.replace`.
- **Delete files on feedback-delete (user choice)**: Admin delete gathers `storage_key`s before the
  cascade and deletes the files; the scheduled orphan-upload sweeper is deferred (`D3`), with the
  schema kept sweep-ready (`created_at` + index).
- **Docs** folded per slice (mirroring P1); `python-multipart` added as an explicit direct dep for
  the upload endpoint.

## Milestones

1. Confirm the slice breakdown and dependency order (S1 storage seam → S2 persistence → S3 upload →
   S4 async-link → S5 reads+downloads), each naming exact files, behavior, error codes, and edge
   cases.
2. Insert `P2.S1`–`P2.S5` into `works/backlog.md` between `P2.DECOMP` and `P2.REVIEW`; set P2
   `Status: in_progress`; set P2 work items to this folder; mark `P2.DECOMP` `[x]` / done with a
   summary note.
3. Add `D3` (orphan-upload sweeper) to `works/deferred.md`.
4. Fill `result.md` and stop (do not start `P2.S1`).

### Planned middle slices (recorded into the backlog by this slice)

- **P2.S1 — Attachment storage seam + configuration** (no DB, no HTTP). New `src/vocky/storage/`
  (`base.py` `AttachmentStorage` interface `save`/`load`/`delete` + `StorageError` /
  `StorageObjectNotFoundError`; `local.py` `LocalFilesystemAttachmentStorage` with path-traversal
  guard + temp-write/atomic `os.replace`; `__init__.py` `get_attachment_storage()` DI). Config
  (`src/vocky/config.py`) `VOCKY_ATTACHMENTS_DIR`, `VOCKY_ATTACHMENTS_MAX_BYTES` (5 MiB),
  `VOCKY_ATTACHMENTS_MAX_COUNT` (10), `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES` (CSV) + parsed property;
  `.env.example`. Tests `tests/test_storage.py` (round-trip incl. binary, NotFound, traversal
  rejection, dir creation, atomic replace). Docs: `architecture.md` (File Storage Subsystem; S3
  deferred behind seam). No DB, no HTTP. Depends on: none.
- **P2.S2 — `feedback_attachments` persistence** (table + migration + domain + repo/service).
  `FeedbackAttachmentModel` in `models.py` (id UUID PK; `feedback_id` UUID **nullable** FK→
  `feedback_events.id` ON DELETE CASCADE; `storage_key`/`content_type`/`claimed_user_id`/
  `claimed_source_product` Text NN; `byte_size` Integer NN; `filename` Text nullable; tz-aware
  `created_at`; indexes `ix_feedback_attachments_feedback_id`,
  `ix_feedback_attachments_feedback_id_created_at`, and a `created_at` sweep index). Migration
  `alembic/versions/{stamp}_add_feedback_attachments.py` (`down_revision = "20260604_2116"`,
  mirroring the comments migration). Export in `persistence/__init__.py`; extend `conftest.py`
  TRUNCATE with `feedback_attachments`. Types `CreateFeedbackAttachment` / `FeedbackAttachmentRecord`
  in `feedback/types.py` (export via `__init__.py`). Repo (+ `_to_attachment_record`):
  `create_feedback_attachment`, `get_feedback_attachment`, `link_attachments_to_feedback(feedback_id,
  ids, *, user_id, source_product)` (guarded UPDATE, returns count), `list_attachments_for_feedback_
  ids` (batched), `list_feedback_attachments`, `list_storage_keys_for_feedback`. Service: wrappers +
  `create_feedback_event_with_attachments(payload)` (create event + link in one txn) reusing existing
  errors. Tests `tests/test_feedback_attachments.py` (create unlinked; get/unknown→None; link
  guarded/idempotent; scope-mismatch skipped; cross-feedback theft blocked; atomic create+link
  rollback; batched list; FK cascade). Docs: `architecture.md` (Attachment Store; nullable-FK +
  cascade rationale; `claimed_*`). Depends on: none at SQL level; ordered after S1.
- **P2.S3 — Synchronous attachment upload endpoint.** New `src/vocky/attachments_api.py`:
  `POST /api/feedback/attachments` (auto-guarded by `APIBearerAuthMiddleware`); require non-blank
  `user_id` + `source_product` (query params, reuse `require_scope_value`); parse multipart `file`,
  stream with byte cap → 413, magic-byte sniff allowed types → 415, empty → 400; `storage_key` from
  `uuid4`; write bytes via seam (write-then-row; delete file on row failure); create row with
  `claimed_*`; `201 {attachment_id, content_type, byte_size, filename}`; `StorageError` → 503;
  `routes = [...]`. Splice `*attachment_routes` in `app.py`; `uv add python-multipart`. Tests
  `tests/test_attachments_api.py` (valid PNG→201 + row + retrievable bytes; spoofed/SVG→415;
  oversize→413; no file→400; missing scope→400; auth→401). Docs: `api.md` (upload contract). Depends
  on: S1, S2.
- **P2.S4 — Async-link through the capture path** (payload + queue + worker). Add `attachment_ids:
  tuple[UUID, ...] = ()` to `CreateFeedbackEvent`. `capture.py`: add `attachment_ids` to the REST
  input + `_normalize_capture_payload` (parse UUID, dedupe, reject non-UUID, cap ≤
  `attachments_max_count` → `CaptureFeedbackValidationError`); MCP input stays attachment-free.
  `capture_queue.py`: add to `_serialize_payload` (`[str(u) …]`) and `_deserialize_payload`
  (`tuple(UUID(x) for x in raw.get("attachment_ids", []))` — back-compat default). `worker.py`
  `_process_job`: non-empty `attachment_ids` → `create_feedback_event_with_attachments(job.payload)`,
  else unchanged; retry/dead-letter untouched. Tests: capture validation (too many→400,
  non-UUID→400); queue round-trip preserves ids + only strings (no bytes); old job without key
  deserializes; worker links on persist; empty ids = today's behavior (regression). Docs: `api.md`
  (`attachment_ids` in capture input), `architecture.md` (upload-first async-link; binaries never in
  Redis). Depends on: S2 (link + create-and-link), S3 (real ids).
- **P2.S5 — Attachment exposure in reads + scoped downloads + delete-on-delete.**
  `query_feedback_common.py`: `serialize_attachment(record)` (id, content_type, byte_size, filename,
  created_at, relative download path) shared like `serialize_comment`. `admin_api.py`: inject
  `attachments` into the detail payload; operator download `GET /admin/api/feedback/{feedback_id}/
  attachments/{attachment_id}` (verify linked → 404 else; stream via seam; admin token); delete path
  gathers `storage_key`s before cascade then deletes files (best-effort, logged). `api.py`: thread
  attachments into `serialize_user_feedback_record` + `list_user_feedback` (batched); end-user
  download `GET /api/feedback/{feedback_id}/attachments/{attachment_id}` requiring `user_id` +
  `source_product`, authorized off the linked feedback row (404 on mismatch/missing), streaming with
  `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff`. `service.py`: batch
  attachments with comments for the list read; delete-with-file-cleanup path. `docker-compose.yml`:
  named `attachments-data` volume on **both** `app` and `worker` + worker env. Tests: admin detail
  includes attachments; operator download bytes; operator download wrong-feedback→404; end-user read
  surfaces only the caller's own attachments; end-user download own→bytes; another user's→404;
  missing scope→400; auth→401; delete removes files. Docs: `product.md` (attachments introduced),
  `api.md` (download contracts + read shapes; flip P2 forward-compat note), `architecture.md`
  (batched reads; downloads reuse P1 scoping; delete-on-delete). Depends on: S2, S3, S4, S1.

## Validation

- `works/backlog.md` parses; P2 now lists `P2.DECOMP` (done), `P2.S1`–`P2.S5` (todo), `P2.REVIEW`
  (todo) in order; P2 `Status: in_progress`; work item linked.
- Each middle slice names exact files, expected behavior, error codes, and edge cases (the CLAUDE.md
  concreteness bar).
- `D3` present in `works/deferred.md`.
- No `src/`, `alembic/`, `tests/`, `docs/`, `docker-compose.yml`, or `pyproject.toml` files changed
  by this slice (decompose-only).

## Risks / open questions

- **Async-link is the load-bearing novelty.** `attachment_ids` must be added to the queue
  serializer/deserializer AND the carrier type or they vanish silently between enqueue and worker;
  S4 owns this with an explicit round-trip test and a back-compat default for in-flight jobs.
- **Cross-user isolation under the upload/capture identity split.** Authorizing downloads off the
  linked feedback row is insufficient alone, because a misrouted `attachment_id` could link one
  user's image into another user's feedback; the confirmed identity-binding (claimed-scope columns +
  worker scope-verified link) closes this. Spread across S2 (columns), S4 (link check), S5 (download
  authz).
- **First file-storage subsystem.** FS/DB consistency (write-then-row + cleanup), MIME spoofing
  (magic-byte sniff), DoS (streamed byte cap), path traversal (UUID-only keys), and persistent
  shared volume (app + worker) are all genuinely new; each is assigned to a slice above.
- **Orphan never-linked uploads** accumulate; the sweeper is deferred (`D3`) with the schema kept
  sweep-ready. Deleting feedback deletes its files now (confirmed choice), so the only residue is
  never-linked uploads.

## Docs to update

- None in this slice. Doc updates happen inside the middle slices: `architecture.md` (S1, S2, S4,
  S5), `api.md` (S3, S4, S5), `product.md` (S5). `.env.example` (S1) and `docker-compose.yml` (S5)
  are config/runtime, not `docs/`.
