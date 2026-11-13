---
doc_id: architecture
version: v0002
created_at: 2026-07-15T16:28:07+09:00
source: P1.REVIEW
summary: Retire MCP track; REST-only two-track API (public REST + Admin REST)
previous: v0001_bootstrap
---

# Architecture

## Status

This architecture is intentionally lightweight. Vocky is still pre-MVP, and the current service accepts capture work through server-to-server REST using Redis-backed queueing plus a dedicated worker while exposing a scoped end-user REST read, separate Admin REST endpoints, and a same-origin self-hosted Admin Web UI with dashboard metrics, feedback review management, in-app operator documentation, and REST capture try-it over the same PostgreSQL feedback store. The earlier MCP/agent-decided capture and MCP read tools have been retired (recoverable through git history).

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `pyproject.toml`: Python project metadata and dependencies
- `src/vocky/`: service code, public REST and Admin REST/Web UI routing, persistence layer, and smoke script
- `alembic/` and `alembic.ini`: database migration environment
- `tests/`: validation, persistence, and REST/persistence coverage
- `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile`: local run, package verification, external smoke checks, and self-hosted development workflow
- `docs/`: stable reference documents
- `works/`: active backlog, deferred queue, active work items, archives, and templates
- `scripts/`: workflow helpers

## First MVP System Shape

The first MVP should be built from these parts:

- Server-to-server REST feedback capture for explicit human-triggered website or product feedback
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- A scoped end-user REST read that returns one user's own records plus operator comments
- Dedicated Admin REST endpoints for human operators, dashboard metrics, and review workflows
- A packaged same-origin Admin Web UI for self-hosted operators, including dashboard metrics, feedback review management, in-app operator docs, and an operator REST capture try-it flow backed by the existing capture endpoint rather than a separate browser-facing data API

## Runtime Shape

The current service uses these choices:

- Python application managed with `uv`
- Application package under `src/vocky`
- A Starlette ASGI host process for REST and health traffic
- A separate worker process for background capture persistence
- Redis-backed queueing between the app and worker
- Public REST capture route and scoped end-user read route under `/api/*`
- Starlette Admin REST routes under `/admin/api/*`
- Starlette Admin Web UI routes under `/admin` and packaged static assets under `/admin/assets/*`
- A plain `/healthz` endpoint on the same host app for smoke checks
- Optional bearer-token protection for public REST capture traffic when `VOCKY_API_AUTH_TOKEN` is set
- Optional bearer-token protection for Admin REST traffic when `VOCKY_ADMIN_AUTH_TOKEN` is set
- Docker builds install runtime dependencies and the local project into the image, while Compose app and worker commands use `uv run --no-sync` so container startup does not repeat dependency sync
- REST capture and Admin REST handlers share validation helpers, service, and persistence layers, and the worker reuses the same persistence path

Server-to-server product integrations should use `/api/feedback` for capture-only ingestion, especially explicit product/UI-triggered feedback from pages, widgets, controls, surveys, or other product surfaces. Human/operator tools should use `/admin/api/*`, while browser operators can load the packaged UI from `/admin`. The Admin Docs try-it flow may send same-origin browser requests to `POST /api/feedback` as an operator verification convenience, but it uses the existing capture-only contract and creates normal queued feedback on success.

## Two-Track API Shape

Vocky now has two public-facing tracks over the same feedback schema:

- Public REST track for server-to-server product integrations: `POST /api/feedback` capture plus `GET /api/feedback`, a scoped end-user read of one user's own feedback (required `user_id` + `source_product`) together with operator comments and cursor pagination. REST capture uses the shared capture field set for explicit human-triggered product/UI feedback, including surface feedback represented with `target_type="surface"` when applicable.
- Admin REST track for humans and dashboards: `/admin/api/feedback` list/detail, `/admin/api/feedback/metrics` dashboard metrics, `/admin/api/feedback/{feedback_id}/comments` operator comment add/list (with the feedback detail response carrying a `comments` array), plus patch/delete management endpoints.

The Admin Web UI is a same-origin browser surface layered over the Admin REST track for protected dashboard data, feedback review management, and packaged static docs assets for operator reference content. It can also render an internal REST capture try-it docs block that posts to same-origin `/api/feedback`, sends `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` only when the operator enters an API token, and stores that API token only in browser session storage. Both API tracks use the same PostgreSQL `feedback_events` table, feedback service, and repository. Public REST is capture plus a single scoped end-user read (`GET /api/feedback`); it does not expose broad review, query, summary, job-status, or management endpoints. The scoped read returns only the caller-identified user's own records, scoped by required `user_id` + `source_product`, together with operator comments; any optional filters are AND-combined with that mandatory scope so the read never returns cross-user data. REST does not add a separate wire shape; website and product context should be represented with `target_type`, `target_id`, `target_text`, nullable `channel`, `tags`, `source_metadata`, and `attributes`. `target_type` is the review discriminator for message, conversation, and surface feedback; it does not create a second feedback store or a new capture endpoint. Admin REST is the surface that can inspect and manage all feedback records, including likes, dislikes, comments, channel category, metadata, target context, messages, and used context. The browser workflow intentionally exposes a narrower edit surface than Admin REST: `feedback_value`, `comment`, `channel`, and `tags`.

## Configuration Surface

The runtime configuration surface is intentionally small:

- `DATABASE_URL`: PostgreSQL connection URL for the async SQLAlchemy engine and Alembic migrations
- `REDIS_URL`: Redis connection URL shared by the app enqueue path and the background worker
- `VOCKY_HOST`: application bind host
- `VOCKY_PORT`: application bind port
- `VOCKY_LOG_LEVEL`: application log level
- `VOCKY_API_AUTH_TOKEN`: optional bearer token required for `/api/*` traffic. Public deployments that expose REST capture should set it.
- `VOCKY_ADMIN_AUTH_TOKEN`: optional bearer token required for Admin REST traffic. Public deployments that expose `/admin/api` should set it.
- `VOCKY_ATTACHMENTS_DIR`: directory the local attachment storage backend reads and writes. In Docker this is a named volume mounted on both the app and worker.
- `VOCKY_ATTACHMENTS_MAX_BYTES`: maximum size in bytes of a single uploaded attachment. Default `5242880` (5 MiB).
- `VOCKY_ATTACHMENTS_MAX_COUNT`: maximum number of attachments that may be linked to one feedback event. Default `10`.
- `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES`: comma-separated allowed attachment MIME types, validated by magic-byte sniffing. Default `image/jpeg,image/png,image/gif,image/webp`.

The supported local operator workflow adds these host-side settings:

- `TEST_DATABASE_URL`: dedicated disposable PostgreSQL database used by `make test`. It must not point at the same database as `DATABASE_URL`.
- `VOCKY_PUBLISH_HOST`: host interface Docker Compose publishes the app port on. The default is `127.0.0.1` for local-only access.
- `POSTGRES_PUBLISH_HOST`: host interface Docker Compose publishes PostgreSQL on. The default is `127.0.0.1`.
- `REDIS_PUBLISH_HOST`: host interface Docker Compose publishes Redis on. The default is `127.0.0.1`.
- `VOCKY_BASE_URL`: optional override for host-side smoke checks when the public base URL differs from `http://127.0.0.1:${VOCKY_PORT}`.
- `VOCKY_EXTERNAL_BASE_URL`: optional external URL used for public custom-domain deployments through Cloudflare Tunnel or another HTTPS reverse proxy, for example `https://vocky.example.com`.

`VOCKY_HOST` remains the application bind address inside the process. The `*_PUBLISH_HOST` variables control which host interface Docker publishes to. `VOCKY_BASE_URL` remains the local verification target, while `VOCKY_EXTERNAL_BASE_URL` is reserved for public custom-domain operator docs and client examples.

The root `.env`, copied from `.env.example`, is the primary local configuration source for both Docker Compose and the Make-based host workflow. The Compose app service receives public REST and Admin auth settings from this file, including `VOCKY_API_AUTH_TOKEN` and `VOCKY_ADMIN_AUTH_TOKEN`. The supported self-hosted path remains Compose-first and includes Redis plus the worker process. `make bootstrap` should bring up the service dependencies, apply migrations, and wait for readiness. `make verify` should build and inspect a fresh wheel for packaged Admin UI assets, wait for readiness, verify the eventual write path with the REST smoke flow, and run the test suite. `make compose-down` should tear the stack back down.

The supported operator modes are:

- Internal self-hosting: Compose publishes on loopback by default and host-side checks use `VOCKY_BASE_URL`.
- Public custom-domain deploy: operators can publish the app through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to the public origin such as `https://vocky.example.com`, require `VOCKY_API_AUTH_TOKEN` before exposing `/api/*`, and require `VOCKY_ADMIN_AUTH_TOKEN` before exposing Admin REST. `make external-smoke` and `make external-verify` run the public checks against `VOCKY_EXTERNAL_BASE_URL`.

The `/admin` shell and `/admin/assets/*` static assets, including packaged operator docs, can load without server-side auth, but protected Admin data remains unavailable unless the browser supplies the configured Admin bearer token to `/admin/api/*`. The Admin Docs REST capture try flow uses the separate `VOCKY_API_AUTH_TOKEN` setting because `/api/*` and `/admin/api/*` have separate auth boundaries.

For Cloudflare Tunnel users, the recommended public shape is a hostname-to-service mapping from `vocky.example.com` to `http://127.0.0.1:8000`, with the local Vocky process still bound behind the tunnel and no inbound origin port requirement.

## MVP Boundaries

- Self-hosted and single-tenant
- Capture ingestion is limited to server-to-server REST in the MVP; browser-direct unauthenticated ingestion is outside scope
- No automatic classification or summarization in the MVP
- Admin Web UI includes a same-origin self-hosted operator shell, dashboard metrics, recent activity, feedback list/filter/detail inspection, review-field editing, guarded delete, in-app operator docs, and an operator-only REST capture try-it form
- Channel handling uses the built-in nullable MVP categories `web`, `mobile`, and `support`; custom category management and deployment-configured category lists are outside the MVP
- No separate Admin REST database or per-surface feedback store
- No managed-cloud or multi-tenant architecture in the MVP
- No public job-status API or dashboard in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, explicit feedback value, optional comment, nullable channel category, the exact reviewed target when available, surrounding conversation messages, used context, creation time, and optional caller-provided tags or attributes.
- `message` is the required human-readable feedback summary or display text. It is not an implicit target selector.
- `conversation_id` identifies the conversation or thread that the feedback belongs to.
- `session_id` is optional runtime, browser, or user-session scope that can correlate repeated interactions without replacing `conversation_id`.
- `user_id` is an optional caller-owned end-user or account-member identifier. It is stored as opaque identity context and does not replace `session_id`, product auth, or tenancy concepts.
- Trigger fields preserve why capture happened: `trigger_type` stores the normalized trigger category, `trigger_message` stores optional event copy or action text, and `trigger_metadata` stores structured trigger-specific context.
- `channel` is an optional nullable review category. New captures and Admin edits should only assign `web`, `mobile`, `support`, or `null`; blank input is normalized to `null`, and no channel is inferred by default.
- Target fields identify the exact reviewed item when known: `target_type` describes whether the target is a `message`, whole `conversation`, or product/UI `surface`; `null` means no exact target category was supplied; `target_id` stores the caller's stable identifier; `target_role` stores the reviewed message role when applicable; and `target_text` stores a snapshot of the exact reviewed text.
- `messages` stores surrounding conversation context supplied by the caller. `used_context` stores context that the agent used while producing the reviewed response.
- REST product or website feedback can omit conversation-specific fields and store page, widget, URL, account, or runtime context in `target_*`, `source_metadata`, and `attributes`.
- The storage layer only needs to support the retrieval and aggregate queries required by the scoped end-user read and Admin REST review surfaces; it does not need analytics-warehouse style modeling for the first MVP.

## Field Responsibilities

The capture schema backs public REST capture. The fields are organized by responsibility so callers can choose the right amount of context without creating transport-specific payload shapes or split storage. Admin REST reads the same stored shape and can manage only the fields that are review-oriented in the current MVP.

| Responsibility | Current fields | Role |
| --- | --- | --- |
| Display and action | `message`, `feedback_value`, `comment` | Human-readable record label plus explicit like, dislike, or comment details. |
| Source identity | `source.product` / `source_product`, `source.integration` / `source_integration` | Caller-provided product and integration identity for grouping and filtering. |
| Caller identity | `user_id` | Caller-owned opaque user or account-member identity associated with the feedback event. |
| Trigger context | `trigger_type`, `trigger_message`, `trigger_metadata` | Captures the action, copy, survey, rating, manual workflow, or other product event that caused feedback capture. |
| Review category | `channel`, `tags` | Operator-facing classification and exact filters. `channel` is constrained for new writes; `tags` remain caller-provided labels. |
| Exact target | `target_type`, `target_id`, `target_role`, `target_text` | Identifies the reviewed message, conversation, or product surface when known. `target_type` is the first-class review discriminator. |
| Conversation and session context | `conversation_id`, `session_id`, `messages` | Groups records with conversation/thread scope, runtime/session scope, and supplied surrounding messages. |
| Agent and process context | `used_context` | Preserves the documents, snippets, tool context, or other context the agent used while producing the reviewed response. |
| Metadata | `id`, `event_at`, `ingested_at`, `source_metadata`, `attributes` | Stores record identity, event and ingest time, source-specific context, and product-specific dimensions. |

## Capture Storage Model

The completed-feedback persistence layer uses PostgreSQL with SQLAlchemy async sessions and Alembic migrations.

The primary table is `feedback_events` with this hybrid shape:

- `id UUID` primary key
- `message TEXT` not null
- `source_product TEXT` not null
- `feedback_value INTEGER` null, where `1` represents like and `2` represents dislike for explicit action feedback
- `comment TEXT` null
- `channel TEXT` null, where new writes should contain only `web`, `mobile`, `support`, or `null`
- `source_integration TEXT` null
- `conversation_id TEXT` null
- `session_id TEXT` null
- `user_id TEXT` null
- `trigger_type TEXT` null, accepted values `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`
- `trigger_message TEXT` null
- `trigger_metadata JSONB` not null with default empty object
- `target_type TEXT` null, where expected capture values are `message`, `conversation`, and `surface`
- `target_id TEXT` null
- `target_role TEXT` null, where expected capture values are `user`, `assistant`, `system`, and `tool`
- `target_text TEXT` null
- `event_at TIMESTAMPTZ` null
- `ingested_at TIMESTAMPTZ` not null
- `tags TEXT[]` not null with default empty array
- `messages JSONB` not null with default empty array
- `used_context JSONB` not null with default empty array
- `source_metadata JSONB` not null with default empty object
- `attributes JSONB` not null with default empty object

Indexes for the intended P1 read model should cover:

- `ingested_at`
- `event_at`
- `source_product`
- `feedback_value`
- `channel`
- `conversation_id`
- `session_id`
- `user_id`
- `trigger_type`
- `target_type`
- GIN on `tags`

The schema keeps the most important review dimensions visible as first-class columns while leaving room for source-specific metadata in JSONB fields. `channel` remains nullable `TEXT` rather than a database enum so older arbitrary channel values can stay readable and exact-filterable without destructive migration; write validation prevents new arbitrary channel values on capture and Admin edits. `target_type` is the only target field promoted to a first-class review discriminator in P1; other target fields remain captured context and are not filters or editable review fields.

## Operator Comment Store

Operator-authored comments are a separate first-class store, not an overload of the user-supplied `comment` column on `feedback_events` (which remains the end user's own comment captured at feedback time). The store lets operators annotate a stored feedback event for review and for one-way operator-to-user visibility.

The secondary table is `feedback_comments`:

- `id UUID` primary key
- `feedback_id UUID` not null, foreign key to `feedback_events.id` with `ON DELETE CASCADE` (deleting a feedback event removes its comments)
- `author TEXT` null, an optional caller-supplied operator label; Vocky has no native operator accounts
- `body TEXT` not null, the comment text
- `created_at TIMESTAMPTZ` not null, defaulting to `CURRENT_TIMESTAMP`

Indexes cover `feedback_id` and the composite `(feedback_id, created_at)` so a single feedback event's comments and batched multi-event lookups both read efficiently. Comments are returned oldest-first ordered by `(created_at, id)`. The repository exposes a batched `list_comments_for_feedback_ids` so list-style reads (the end-user feedback read) fetch all comments for a page in one query instead of N+1 per-record lookups. This is the only genuinely new subsystem in P1; the comment store reuses the same SQLAlchemy async session, repository, and service layering as `feedback_events`, with the same `FeedbackPersistenceError` / `FeedbackReadError` wrapping.

The async capture path is layered as:

- REST route input normalization and error mapping
- Redis enqueue on the request path
- A dedicated worker process
- A transport-neutral feedback service
- A repository backed by SQLAlchemy async sessions
- PostgreSQL plus Alembic-managed schema

The read path reuses the same service and repository layers:

- REST route input normalization and error mapping for the scoped end-user read and Admin REST list/detail
- Transport-neutral read methods on the feedback service
- Repository queries against `feedback_events`
- A single scoped public REST read (`GET /api/feedback`) over the same service and repository, restricted to one user's own records by required `user_id` + `source_product` and returning operator comments via a batched `feedback_comments` fetch; no broad public REST query stack

The Admin dashboard metrics path uses the same read layers:

- Admin REST query normalization and JSON error mapping for `GET /admin/api/feedback/metrics`
- Required timezone-aware `start_ingested_at` and `end_ingested_at` query parameters normalized to UTC
- A transport-neutral feedback service metrics method backed by repository aggregates over `feedback_events`
- UTC day bucketing with zero-filled daily buckets for the requested inclusive-start/exclusive-end ingest-time window
- Aggregate counts for total records, likes (`feedback_value = 1`), dislikes (`feedback_value = 2`), and unrated records (`feedback_value is null`)

## File Storage Subsystem

Vocky stores feedback image attachments as opaque binary objects outside the database, behind a small storage seam so the backend can change without touching callers. This is the first file-storage subsystem in the codebase.

- `AttachmentStorage` (`src/vocky/storage/base.py`) is the backend-neutral interface: `save(key, data)`, `load(key) -> bytes`, and `delete(key)`. It raises `StorageError` for write/read/delete failures and `StorageObjectNotFoundError` (a `StorageError` subclass) when an object is missing.
- `LocalFilesystemAttachmentStorage` (`src/vocky/storage/local.py`) is the only implementation today. It stores each object as a file under `VOCKY_ATTACHMENTS_DIR`, rejects keys that are absolute or escape the root (`resolve()` + `is_relative_to`), creates intermediate directories, and writes through a sibling temp file plus atomic `os.replace` so a reader never observes a partial object.
- `get_attachment_storage()` (`src/vocky/storage/__init__.py`) is the dependency accessor, mirroring `get_feedback_service()`: it returns a backend built from the cached settings.

An S3-compatible backend is deliberately deferred behind this same interface; storage keys are server-generated UUIDs (never client filenames), so adding object-store backends needs no key-format change. Size, count, and allowed-type limits are configuration (`VOCKY_ATTACHMENTS_*`) and are enforced at the HTTP and capture layers, not inside the storage backend, which stays a dumb byte store.

## Feedback Attachment Store

Attachment metadata lives in a `feedback_attachments` table; the bytes live in the File Storage Subsystem above, referenced by `storage_key`. The table mirrors `feedback_comments` but its `feedback_id` is nullable because attachments are uploaded before the feedback row exists (see Async Capture and Attachment Linking).

- `id UUID` primary key
- `feedback_id UUID` **nullable**, foreign key to `feedback_events.id` with `ON DELETE CASCADE`. Nullable because an attachment is uploaded and stored before the async capture path persists its feedback row; the worker links it afterward. The cascade still applies once linked, so deleting a feedback event removes its attachment rows.
- `storage_key TEXT` not null, the server-generated UUID key into the storage backend
- `content_type TEXT` not null, the MIME type derived from magic-byte sniffing at upload (never the client-declared header)
- `byte_size INTEGER` not null
- `filename TEXT` null, the client-supplied display name (sanitized when echoed in headers)
- `claimed_user_id TEXT` null, the `user_id` asserted at upload time
- `claimed_source_product TEXT` not null, the `source_product` asserted at upload time
- `created_at TIMESTAMPTZ` not null, defaulting to `CURRENT_TIMESTAMP`

Indexes cover `feedback_id`, the composite `(feedback_id, created_at)` for a single event's attachments and batched multi-event lookups, and `created_at` to keep the deferred orphan-upload sweep (`D3`) cheap. The repository exposes a batched `list_attachments_for_feedback_ids` mirroring the comment store so list reads stay free of N+1 lookups.

The `claimed_user_id` / `claimed_source_product` columns are the identity binding that makes "an end user sees only their own attachments" enforceable. The worker links an attachment only when its claimed scope matches the feedback event's `(user_id, source_product)` via a guarded `UPDATE ... WHERE feedback_id IS NULL AND claimed_source_product = :sp AND claimed_user_id = :uid` (with an `IS NULL` branch for anonymous feedback). The `feedback_id IS NULL` guard makes linking idempotent and blocks one feedback event from stealing another's attachment. The store reuses the same SQLAlchemy async session, repository, and service layering as `feedback_events`, with the same `FeedbackPersistenceError` / `FeedbackReadError` wrapping; `create_feedback_event_with_attachments` performs the event insert and the guarded link in one transaction.

Reads and downloads reuse the P1 scoping model. The operator-review detail and the scoped end-user read each inject an `attachments` array (oldest-first), fetched with a single batched `list_attachments_for_feedback_ids` query alongside comments to avoid N+1 lookups. Bytes are served by authenticated download endpoints: the operator download (`/admin/api/feedback/{id}/attachments/{id}`, admin token) serves any attachment linked to that feedback; the end-user download (`/api/feedback/{id}/attachments/{id}`) is authorized off the linked feedback row's `(user_id, source_product)` and answers `404` on any mismatch, unlinked attachment, or missing object so existence is never leaked, with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. Deleting a feedback event cascades the attachment rows; the admin delete path gathers the attachments' `storage_key`s in the same transaction before the cascade and then deletes the files best-effort (logged, never failing the committed delete). Never-linked uploads are the only residue and are left to the deferred orphan sweep (`D3`). In Docker the attachment files live on a named volume mounted on both the app and worker at `VOCKY_ATTACHMENTS_DIR`.

## Async Capture and Attachment Linking

Capture is asynchronous (`202 Accepted` → Redis queue → worker persist), and the feedback row's UUID exists only after the worker persists it, so attachments cannot be created at capture time and binaries cannot ride the JSON queue. The adopted protocol is upload-first async-link:

- The client uploads each image synchronously to `POST /api/feedback/attachments` and receives an `attachment_id` for an unlinked `feedback_attachments` row that records the bytes' `storage_key` and the claimed `(user_id, source_product)`.
- The capture payload carries `attachment_ids` (UUID strings only) through the existing Redis queue. The queue serializer adds `attachment_ids` to its explicit field allowlist and the deserializer defaults it to empty, so jobs enqueued before this field existed still deserialize.
- When a job carries non-empty `attachment_ids`, the worker calls `create_feedback_event_with_attachments`, which inserts the feedback row and runs the guarded scope-verified link in one transaction. A job with no attachments takes the unchanged `create_feedback_event` path. Missing, mis-scoped, or already-linked attachments are skipped and logged; they never dead-letter the job, because a missing screenshot must not fail real feedback.

REST capture validates and normalizes `attachment_ids` (parse to UUID, dedupe, cap at `VOCKY_ATTACHMENTS_MAX_COUNT`).

## Query Read Model

The implemented P1 read query model uses these constraints:

- Read filters are limited to `ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `feedback_value`, `channel`, `target_type`, `trigger_type`, and exact single-tag membership.
- The P1 read model does not add filters for `trigger_message`, `trigger_metadata`, `target_id`, `target_role`, `target_text`, arbitrary JSONB fields, or records where an optional string field is unset.
- Channel read filters use exact matching after trimming blank input to absence. They should continue to support legacy stored channel strings even though new capture and Admin edit writes are limited to `web`, `mobile`, `support`, or `null`.
- `target_type` read filters use exact matching after trimming blank input to absence. Accepted non-blank filter values are `message`, `conversation`, and `surface`; this phase does not add filters for `target_id`, `target_role`, `target_text`, or records where `target_type is null`.
- `trigger_type` read filters use exact matching after trimming blank input to absence. Accepted non-blank filter values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`; this phase does not add a filter for records where `trigger_type is null`.
- Time filtering uses `ingested_at` only. `start_ingested_at` is inclusive and `end_ingested_at` is exclusive after normalization to UTC.
- The list reads (the scoped end-user `GET /api/feedback` and `GET /admin/api/feedback`) return full stored records ordered newest-first by `(ingested_at desc, id desc)`.
- The list reads default to `50` records per page and reject values outside `1` through `100`.
- List pagination uses an opaque base64url-encoded JSON cursor derived from the last returned record's `ingested_at` and `id`.
- `GET /admin/api/feedback/metrics` returns window totals plus UTC `daily_counts`, with zero-filled missing days inside the requested window.
- The base phase does not add full-text search, JSONB filtering, target-id filtering, target-role filtering, target-text filtering, or new summary dimensions.
- Admin dashboard metrics remain ingest-window-only and do not add `user_id`, `trigger_type`, trigger-message, trigger-metadata, or other dimension filters in this phase.
- The list reads return action fields and stored JSON context with each record so operators can inspect likes and dislikes without a separate transcript store.
- Accepted capture jobs are not queryable until the background worker persists them into `feedback_events`.

## Architecture Constraints

- Keep public contracts explicit in `docs/api.md`.
- Keep durable technical context here, not in transient work items.
- Keep execution history under `works/`.
- Keep currently scheduled work in `works/backlog.md` and intentionally deferred work in `works/deferred.md`.
- Prefer small slices and explicit review loops over large untracked changes.
- Keep the capture service self-hostable with one app process, one worker process, Redis, and PostgreSQL for the MVP.
- Normalize capture timestamps to UTC before persistence.
- Normalize query timestamps to UTC before filtering or aggregation.
- Return REST capture validation failures as `400` JSON responses.
- Reject non-null channel values outside `web`, `mobile`, and `support` on new REST capture and Admin REST patch writes.
- Normalize optional string capture fields, including `user_id`, `trigger_type`, and `trigger_message`, by trimming leading and trailing whitespace and converting blank values to `null`.
- Reject non-null `trigger_type` values outside `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other` on REST capture writes.
- Require `trigger_metadata` to be a JSON object when supplied; omit or default it to `{}` when absent.
- Return REST queue-accept failures as `503` JSON responses.
- Return REST read validation failures as `400` JSON responses and storage read failures as JSON error responses (`500`, or `503` for attachment downloads).
- Keep public REST capture and Admin REST handlers separate while sharing validation helpers, service, queue, and repository layers where appropriate.

## Open Questions

- Auth and permission boundaries for self-hosted deployments, including whether capture and review capabilities should eventually be separated
- Whether completed-job receipts or dead-letter inspection should become part of a later public review surface
