---
doc_id: api
version: v0002
created_at: 2026-07-15T16:25:45+09:00
source: P1.REVIEW
summary: Retire MCP/agent-capture; REST-only feedback surface
previous: v0001_bootstrap
---

# API

## Status

The Web Feedback Capture REST API, the Feedback Attachment Upload REST API, the scoped End-User Feedback Read REST API (with `target_type` and other read filters), and the Admin REST API (list/detail/metrics filters, review-field patch, operator comments, and delete) are implemented. REST is the sole capture and read ingress; the AI-agent-decided MCP capture tool and the MCP review/query/liked-conversation tools have been retired (recoverable through git history). These contracts should still be treated as early-stage MVP contracts rather than long-term stable commitments.

## Purpose

Use this file to record public-facing contracts as they are implemented. The current contracts are usable for the pre-MVP service, but they are still early-stage and should not be treated as long-term stable commitments.

## MVP Surfaces

- Web Feedback Capture REST API contract for server-to-server website and product feedback ingestion, plus operator-only Admin Docs try-it against the same endpoint
- Feedback Attachment Upload REST API contract for uploading an image and receiving an `attachment_id` to reference from a later capture call
- End-User Feedback Read REST API contract for a scoped server-to-server read of a single user's own feedback plus operator comments
- Admin REST API contract for human/operator review and dashboard metrics

## Documentation Rules

- Only document a contract as stable when it is implemented or explicitly accepted.
- Mark experimental surfaces as draft.
- Record breaking changes once external consumers exist.
- Keep implementation notes out of this file unless they affect consumers.

## Contract Template

### Surface Name

- Status:
- Consumers:
- Purpose:
- Inputs:
- Outputs:
- Errors:
- Auth or permissions:
- Notes:

## Contracts

### Shared Channel Category Rules

- Status: implemented
- Applies to: REST capture (`POST /api/feedback`), the scoped end-user read (`GET /api/feedback`), Admin REST list filters, and Admin REST patch
- Values:
  - `null` or omitted means no channel category is assigned
  - `web`, `mobile`, and `support` are the built-in MVP categories
- Write behavior:
  - New capture writes and Admin REST patch writes trim leading and trailing whitespace
  - Blank write values are normalized to `null`
  - Non-null write values outside `web`, `mobile`, and `support` are rejected
  - The service does not infer a default channel category
- Read/filter behavior:
  - Response records return the stored channel value or `null`
  - Older stored arbitrary channel strings remain readable
  - Channel filters are exact-match filters after trimming blank input to absence, so legacy stored values remain discoverable

### Shared Target Type Rules

- Status: implemented
- Applies to: REST capture (`POST /api/feedback`), the scoped end-user read (`GET /api/feedback`), and Admin REST list filters
- Values:
  - `null` or omitted means the caller did not identify an exact target category
  - `message` means feedback on a specific message
  - `conversation` means feedback on a whole conversation or thread
  - `surface` means feedback on a concrete non-message product, page, widget, or UI surface
- Capture write behavior:
  - New capture writes trim leading and trailing whitespace
  - Blank write values are normalized to `null`
  - Non-null write values outside `message`, `conversation`, and `surface` are rejected
- Read/filter behavior:
  - Response records return the stored `target_type` value or `null`
  - The read filter is exact-match after trimming blank input to absence
  - Non-blank filter values must be `message`, `conversation`, or `surface`
  - This phase does not add a filter for records where `target_type` is unset

### Shared Identity and Trigger Rules

- Status: implemented
- Applies to: REST capture (`POST /api/feedback`), the scoped end-user read (`GET /api/feedback`), and Admin REST list/detail record responses
- Fields:
  - `user_id: string | null` optionally identifies the caller-owned end user, account member, or product user associated with the feedback event
  - `trigger_type: string | null` optionally categorizes the action or workflow that caused capture
  - `trigger_message: string | null` optionally stores the action label, prompt copy, button text, survey question, or event description that caused capture
  - `trigger_metadata: object` stores structured trigger-specific context and defaults to `{}`
- Trigger type values:
  - `null` or omitted means the caller did not identify a trigger category
  - Allowed non-null values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`
- Capture write behavior:
  - `user_id`, `trigger_type`, and `trigger_message` trim leading and trailing whitespace
  - Blank `user_id`, `trigger_type`, and `trigger_message` values are normalized to `null`
  - Non-null `trigger_type` values outside the allowed set are rejected
  - `trigger_metadata` must be a JSON object when supplied; omitted values default to `{}`
- Read/filter behavior:
  - Stored record responses return `user_id`, `trigger_type`, `trigger_message`, and `trigger_metadata`
  - `GET /api/feedback` and `GET /admin/api/feedback` support exact `user_id` and `trigger_type` filters after trimming blank query input to absence
  - `trigger_message` and `trigger_metadata` are returned for inspection but are not filterable
  - Admin dashboard metrics remain limited to the required ingest-time window and do not add identity or trigger filters
- Compatibility:
  - `user_id` does not replace `session_id`; `session_id` remains runtime, browser, or user-session correlation
  - `trigger_message` does not replace the primary feedback `message` or the optional user `comment`
  - Trigger fields describe why capture happened; target fields describe what was reviewed; `used_context`, `messages`, `source_metadata`, and `attributes` keep their existing roles

### Shared Capture Field Responsibilities

- Status: implemented
- Applies to: REST capture (`POST /api/feedback`) inputs, stored feedback records, the scoped end-user read responses, and Admin REST record responses
- Contract shape:
  - REST capture is the single capture surface for trusted server-to-server product/UI feedback triggered by real humans.
  - Admin REST is the human/operator review and management surface over the same stored record shape; it is not a public capture variant.
- Field groups:
  - Display and action: `message`, `feedback_value`, and `comment`
  - Source identity: `source.product` / `source_product` and `source.integration` / `source_integration`
  - Caller identity: `user_id`
  - Trigger context: `trigger_type`, `trigger_message`, and `trigger_metadata`
  - Review category: `channel` and `tags`
  - Exact target: `target_type`, `target_id`, `target_role`, and `target_text`
  - Conversation and session context: `conversation_id`, `session_id`, and `messages`
  - Agent and process context: `used_context`
  - Metadata: `id`, `event_at`, `ingested_at`, `source_metadata`, and `attributes`
- Notes:
  - The shared field set does not create a separate wire shape per surface or split storage; the scoped read and Admin REST return the same stored record shape.
  - Admin REST can inspect all stored field groups but only patches the review-oriented fields documented in the Admin Feedback REST API contract.

### Web Feedback Capture REST API

- Status: implemented
- Consumers: Server-to-server web and product integrations sending explicit website, product-surface, UI-triggered, or human-triggered feedback into Vocky
- Purpose: Submit a single explicit product/UI feedback event for asynchronous persistence through the shared capture field set
- Base path: `/api`
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - When `VOCKY_API_AUTH_TOKEN` is set, `/api/*` requests must include `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`
  - Public deployments should set `VOCKY_API_AUTH_TOKEN` before exposing `/api/*`
  - The Admin Docs try-it flow uses this API token, not `VOCKY_ADMIN_AUTH_TOKEN`; the operator-entered API token is a browser-session value for trying capture and is not a durable Vocky setting.
- Endpoint:
  - `POST /api/feedback`
- Inputs:
  - JSON request body using the shared capture fields:
    - `message: string` required. Leading and trailing whitespace is trimmed. The value must not be blank after trimming. For REST, this may summarize explicit website, page, widget, product-surface, or UI-triggered feedback.
    - `source.product: string` required. Leading and trailing whitespace is trimmed. The value must not be blank after trimming.
    - `source.integration: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `feedback_value: integer` optional. When provided, must be `1` for like or `2` for dislike. General REST feedback may omit this when there is no explicit like/dislike action.
    - `comment: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `channel: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`. Non-null values must be one of the built-in channel categories: `web`, `mobile`, or `support`.
    - `conversation_id: string` optional. Caller-provided conversation or thread identifier when the REST feedback belongs to a conversation. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `session_id: string` optional. Caller-provided runtime, browser, or user-session identifier. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `user_id: string` optional. Caller-owned end-user or account-member identifier. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `trigger_type: string` optional. Allowed values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `trigger_message: string` optional. Action label, prompt copy, survey question, button text, or event description that caused capture. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `trigger_metadata: object` optional. Structured trigger context persisted as supplied; omitted values default to `{}`.
    - `target_type: string` optional. Allowed values are `message`, `conversation`, and `surface`. Use `surface` for page, widget, screen, or other non-message product-surface feedback when the exact target is known. `null` means the caller did not identify an exact target category.
    - `target_id: string` optional. Caller-provided stable identifier for the target, such as a message id, page id, widget id, or UI surface id. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_role: string` optional. Role for message targets. Allowed values are `user`, `assistant`, `system`, and `tool`. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_text: string` optional. Snapshot of the exact reviewed message or product surface text. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `event_at: string` optional. Must be a timezone-aware ISO 8601 timestamp. Naive timestamps are rejected. Accepted values are normalized to UTC before persistence and in responses.
    - `tags: string[]` optional. Tags are trimmed. Blank tags are rejected. Duplicate tags after normalization are rejected.
    - `messages: array` optional. JSON array of caller-provided surrounding conversation messages when relevant.
    - `used_context: array` optional. JSON array of caller-provided context used by the agent when relevant.
    - `source_metadata: object` optional. Arbitrary JSON object for source context such as URL, path, referrer, browser, page, widget, or backend integration detail.
    - `attributes: object` optional. Arbitrary JSON object for product-specific dimensions such as account plan, environment, locale, or rollout cohort.
    - `attachment_ids: string[]` optional. UUIDs returned by earlier `POST /api/feedback/attachments` uploads to attach to this feedback. Each must be a valid UUID; duplicates are dropped; the count must not exceed `VOCKY_ATTACHMENTS_MAX_COUNT`. The worker links only attachments whose upload-time `user_id` + `source_product` match this event's; non-matching, missing, or already-linked ids are skipped without failing capture.
- Outputs:
  - Success status: `202 Accepted`
  - Response body:
    - `request_id: string` UUID generated when the capture job is accepted
    - `accepted_at: string` UTC ISO 8601 timestamp generated when the queue accepts the job
    - `status: string` fixed to `accepted`
- Errors:
  - Missing or invalid bearer token when auth is configured returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - Malformed JSON, non-object request bodies, schema errors, invalid non-null `channel` or `trigger_type` values, and semantic validation failures return `400 {"detail":"..."}`
  - Queue-accept failures return `503 {"detail":"capture queue unavailable"}`
- Notes:
  - This REST API is capture-only. It does not add public REST review, query, summary, job-status, or management endpoints.
  - The Admin Docs try-it flow sends a same-origin browser `POST /api/feedback` request to this existing endpoint for self-hosted operator verification. It is not a separate public contract and does not change the server-to-server integration guidance.
  - Successful Admin Docs try requests create real queued feedback events with the same asynchronous persistence behavior as any other REST capture request.
  - Target fields are optional captured context. Omitting them stores `null` target values.
  - REST capture is the sole ingestion path for explicit product/UI-triggered website and product feedback through the shared fields; this phase does not add REST-only aliases, a versioned endpoint, or separate storage.
  - Success means the job was accepted for background processing, not that the feedback record is already queryable.
  - Accepted REST capture jobs use the Redis queue, worker, feedback service, and PostgreSQL table.
  - Image attachments are uploaded first via `POST /api/feedback/attachments`; only the resulting `attachment_ids` (UUID strings) travel through the capture queue. Binaries never enter Redis. The worker links the referenced attachments to the persisted feedback row, scope-verified against the event's `user_id` + `source_product`.

### Feedback Attachment Upload REST API

- Status: implemented
- Consumers: Server-to-server product integrations that let an end user attach an image (for example a screenshot) to feedback
- Purpose: Synchronously upload one image and receive an `attachment_id` to reference from a later capture call. Capture is asynchronous and binaries cannot ride the JSON queue, so images are uploaded first and linked to the feedback row after the worker persists it.
- Base path: `/api`
- Auth or permissions:
  - Same boundary as REST capture: when `VOCKY_API_AUTH_TOKEN` is set, `/api/*` requests must include `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`.
  - The caller asserts scope with required `user_id` + `source_product`; these are recorded on the attachment and the worker links the attachment only to a feedback event with the same `(user_id, source_product)`.
- Endpoint:
  - `POST /api/feedback/attachments`
- Inputs:
  - Query parameters:
    - `user_id: string` required. Trimmed; must not be blank. Recorded as the attachment's claimed user scope.
    - `source_product: string` required. Trimmed; must not be blank. Recorded as the attachment's claimed product scope.
  - Body: `multipart/form-data` with a single `file` part containing the image bytes. The content type is determined by magic-byte sniffing of the bytes, not the declared part header.
  - Allowed image types: `image/jpeg`, `image/png`, `image/gif`, `image/webp` (configurable via `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES`).
  - Maximum size: `VOCKY_ATTACHMENTS_MAX_BYTES` (default 5 MiB).
- Outputs:
  - Success status: `201 Created`
  - Response body:
    - `attachment_id: string` UUID of the stored, not-yet-linked attachment
    - `content_type: string` the sniffed canonical MIME type
    - `byte_size: integer` stored byte size
    - `filename: string | null` sanitized client filename, or `null`
- Errors:
  - Missing or invalid bearer token when auth is configured returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - Missing or blank `user_id` or `source_product`, a missing `file` part, an empty file, malformed multipart, or an invalid `Content-Length` return `400 {"detail":"..."}`
  - A file larger than the configured maximum returns `413 {"detail":"attachment too large"}`
  - A file whose sniffed type is not an allowed image type (including SVG and spoofed declarations) returns `415 {"detail":"unsupported image type"}`
  - Storage write failures return `503 {"detail":"attachment storage unavailable"}`
- Notes:
  - The returned `attachment_id` is referenced from `POST /api/feedback` via `attachment_ids` (see the capture contract). An uploaded attachment that is never referenced stays unlinked; a scheduled orphan sweep is deferred.
  - Storage keys are server-generated UUIDs; the client filename is stored only as display metadata.
  - The attachment is not visible in any read until the capture worker links it to a persisted feedback event.

### End-User Feedback Read REST API

- Status: implemented
- Consumers: Trusted server-to-server product integrations rendering a single end user's own feedback (for example a "my feedback" view), after the product has authenticated that user
- Purpose: Return one end user's own stored feedback, scoped strictly by `user_id` + `source_product`, together with operator comments, using basic review filters and cursor pagination
- Base path: `/api`
- Auth or permissions:
  - Trusted server-to-server. The integrating product authenticates its own user, then calls Vocky with that `user_id` and the API bearer token; Vocky has no native end-user accounts.
  - When `VOCKY_API_AUTH_TOKEN` is set, `/api/*` requests must include `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` (the same boundary as REST capture).
  - Vocky enforces `user_id` + `source_product` scoping server-side and never returns cross-user or cross-product data.
- Endpoint:
  - `GET /api/feedback`
- Inputs (query parameters):
  - `user_id: string` required. Trimmed; must not be blank. The scoping boundary; the read is never issued unscoped.
  - `source_product: string` required. Trimmed; must not be blank. The second scoping boundary.
  - `feedback_value: integer` optional. When provided, must be `1` for like or `2` for dislike.
  - `channel: string` optional. Exact channel filter after trimming blank input to absence.
  - `target_type: string` optional. Exact filter; non-blank values must be `message`, `conversation`, or `surface`.
  - `trigger_type: string` optional. Exact filter; non-blank values must be `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, or `other`.
  - `source_integration: string` optional. Exact filter after trimming blank input to absence.
  - `conversation_id: string` optional. Exact filter after trimming blank input to absence.
  - `session_id: string` optional. Exact filter after trimming blank input to absence.
  - `tag: string` optional. Exact single-tag membership; blank values are rejected.
  - `start_ingested_at: string` optional. Timezone-aware ISO 8601; filters `ingested_at >= start_ingested_at` after normalization to UTC.
  - `end_ingested_at: string` optional. Timezone-aware ISO 8601; filters `ingested_at < end_ingested_at` after normalization to UTC.
  - `limit: integer` optional. Defaults to `50`; values must be between `1` and `100`.
  - `cursor: string` optional. Opaque base64url cursor returned by an earlier `GET /api/feedback` call.
  - All optional filters are AND-combined with the required `user_id` + `source_product` scope.
- Outputs:
  - Success status: `200 OK`
  - Response body:
    - `records: object[]` newest-first by `(ingested_at desc, id desc)`
    - `next_cursor: string` opaque pagination cursor for the next page when more records exist; the field is omitted when no further page exists
  - Record shape: the same fields as the Admin Feedback REST API record shape (`id`, `message`, `source_product`, `feedback_value`, `comment`, `channel`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `trigger_type`, `trigger_message`, `trigger_metadata`, `target_type`, `target_id`, `target_role`, `target_text`, `event_at`, `ingested_at`, `tags`, `messages`, `used_context`, `source_metadata`, `attributes`), plus:
    - `comments: object[]` operator comments for the record, oldest-first, each `{id, author, body, created_at}` (the Admin Comment shape)
    - `attachments: object[]` image attachments for the record, oldest-first, each `{id, content_type, byte_size, filename, created_at, url}` where `url` is the relative end-user download path `/api/feedback/{feedback_id}/attachments/{id}`
- Errors:
  - Missing or invalid bearer token when auth is configured returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - Missing or blank `user_id` or `source_product`, invalid filter values, invalid limits, blank `tag`, invalid time windows, and invalid cursors return `400 {"detail":"..."}`
  - Storage read failures return `500 {"detail":"storage read failed"}`
- Notes:
  - This is the only public REST read. It is deliberately scoped to a single user's own feedback and is not a general query, review, or summary API; those remain Admin REST concerns.
  - Operator comments are returned read-only. This phase is one-way operator-to-user visibility with no end-user replies or two-way threads.
  - The read reuses the same `feedback_events` store, indexed `user_id` / `source_product` filters, and cursor pagination as the Admin read surface, with batched operator-comment and attachment fetches to avoid N+1 lookups.
  - Each record's image attachments are surfaced as an `attachments` array; the bytes are served by the scoped end-user attachment download below.

#### End-User Feedback Attachment Download

- Endpoint: `GET /api/feedback/{feedback_id}/attachments/{attachment_id}`
- Auth: same `/api/*` bearer boundary as the read.
- Inputs (query parameters): `user_id` and `source_product`, both required and non-blank (the same scope as the read).
- Authorization: the attachment is authorized off its linked feedback row's `(user_id, source_product)`. A request for another user's or product's attachment, an unlinked attachment, a missing attachment, or a missing feedback all return `404` — existence is never leaked.
- Outputs: `200 OK` streaming the attachment bytes with the stored `content_type`, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, and `Cache-Control: private, no-store`.
- Errors: missing/invalid bearer when configured → `401`; missing/blank `user_id` or `source_product`, or a malformed id → `400`; any authorization miss or a missing stored object → `404`; storage read failure → `503`.

### Admin Feedback REST API

- Status: implemented
- Consumers: Human operators, scripts, and admin dashboards
- Purpose: Query, inspect, manage, and summarize feedback records through REST endpoints for human/operator review
- Base path: `/admin/api`
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST requests must include `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`
  - Public deployments should protect or avoid exposing `/admin/api`
- Endpoints:
  - `GET /admin/api/healthz`
    - Returns `{"service":"vocky","surface":"admin","status":"ok"}`
  - `GET /admin/api/feedback`
    - Lists all feedback records by default
    - Supports `start_ingested_at`, `end_ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `feedback_value`, exact `channel`, exact `target_type`, exact `trigger_type`, `tag`, `limit`, and `cursor`
    - Returns `records` and optional `next_cursor`
  - `GET /admin/api/feedback/metrics`
    - Returns dashboard metrics for a required ingest-time window
    - Requires `start_ingested_at` and `end_ingested_at` timezone-aware ISO 8601 query parameters
    - Normalizes the requested window to UTC
    - Counts records with `ingested_at >= start_ingested_at` and `ingested_at < end_ingested_at`
    - Returns `window`, `totals`, and zero-filled UTC `daily_counts`
  - `GET /admin/api/feedback/{feedback_id}`
    - Returns one full feedback record or `404` when missing
    - The record response includes a `comments` array of operator comments, oldest-first
    - The record response includes an `attachments` array of image attachments, oldest-first
  - `GET /admin/api/feedback/{feedback_id}/attachments/{attachment_id}`
    - Streams one attachment's bytes for operator review (operators see all attachments for any feedback)
    - Responds with the stored `content_type` and `X-Content-Type-Options: nosniff`
    - Returns `404` when the attachment is not linked to that feedback, or `404` when its stored object is missing
  - `PATCH /admin/api/feedback/{feedback_id}`
    - Updates review-oriented fields: `feedback_value`, `comment`, `channel`, `tags`, `source_metadata`, and `attributes`
    - `channel`, when patched, is trimmed; blank values clear the category to `null`; non-null values must be `web`, `mobile`, or `support`
    - Captured target fields, trigger fields, `user_id`, `messages`, and `used_context` are immutable in this MVP
    - Returns the updated record
  - `DELETE /admin/api/feedback/{feedback_id}`
    - Deletes one feedback record and returns `204` on success
    - Also deletes that record's operator comments and attachment rows (`ON DELETE CASCADE`)
    - Best-effort deletes the attachment files from storage after the database delete commits; a failed file delete is logged and does not fail the request
  - `POST /admin/api/feedback/{feedback_id}/comments`
    - Adds one operator-authored comment to the feedback record
    - Request body: `body: string` required, trimmed, must not be blank after trimming; `author: string | null` optional, trimmed, blank normalized to `null`
    - Returns `201` with `{ "comment": <comment> }`
    - Returns `404` when the parent feedback record is missing
    - Returns `400` on a blank `body`, a missing `body`, or a malformed/non-object JSON body
  - `GET /admin/api/feedback/{feedback_id}/comments`
    - Lists the feedback record's operator comments, oldest-first
    - Returns `200` with `{ "comments": [<comment>, ...] }`
    - Returns `404` when the parent feedback record is missing
- Record shape:
  - `id: string`
  - `message: string`
  - `source_product: string`
  - `feedback_value: integer | null`
  - `comment: string | null`
  - `channel: string | null` stored channel value. New records should use `web`, `mobile`, `support`, or `null`; older records may contain legacy arbitrary strings.
  - `source_integration: string | null`
  - `conversation_id: string | null`
  - `session_id: string | null`
  - `user_id: string | null`
  - `trigger_type: string | null`
  - `trigger_message: string | null`
  - `trigger_metadata: object`
  - `target_type: string | null`
  - `target_id: string | null`
  - `target_role: string | null`
  - `target_text: string | null`
  - `event_at: string | null`
  - `ingested_at: string`
  - `tags: string[]`
  - `messages: array`
  - `used_context: array`
  - `source_metadata: object`
  - `attributes: object`
- Comment shape:
  - `id: string`
  - `author: string | null` optional caller-supplied operator label; Vocky has no native operator accounts
  - `body: string`
  - `created_at: string` UTC ISO 8601 timestamp
- Attachment shape:
  - `id: string`
  - `content_type: string` the stored image MIME type (derived from magic-byte sniffing at upload)
  - `byte_size: integer`
  - `filename: string | null` sanitized client filename
  - `created_at: string` UTC ISO 8601 timestamp
  - `url: string` relative download path for this surface (`/admin/api/feedback/{feedback_id}/attachments/{id}`)
- Metrics response shape:
  - `window.start_ingested_at: string` UTC ISO 8601 timestamp
  - `window.end_ingested_at: string` UTC ISO 8601 timestamp
  - `totals.total: integer`
  - `totals.liked: integer` count of records where `feedback_value` is `1`
  - `totals.disliked: integer` count of records where `feedback_value` is `2`
  - `totals.unrated: integer` count of records where `feedback_value` is `null`
  - `daily_counts: object[]` UTC day buckets spanning the requested window, including zero-count days
  - Each daily bucket includes `day`, `total`, `liked`, `disliked`, and `unrated`
- Errors:
  - Validation failures, including invalid non-null `channel` patch values, return JSON `400` responses with `detail`
  - Missing records return JSON `404` responses with `detail`
  - Storage read or write failures return JSON `500` responses with `detail`
- Notes:
  - Admin REST is the human/operator review surface.
  - Operator comments are a separate first-class store keyed by feedback id, distinct from the user-supplied `comment` field captured at feedback time. The `POST`/`GET /admin/api/feedback/{feedback_id}/comments` endpoints and the `comments` array in the detail response are the operator add/list surface; comments are not editable or deletable individually in this MVP.
  - The Admin REST API and the public REST surfaces share the same `feedback_events` schema and service/repository layer.
  - The packaged Admin Web UI consumes this same-origin Admin REST surface for dashboard metrics, feedback list/filter/detail review, review-field editing, and guarded delete.
  - `/admin` and `/admin/assets/*` are static Admin Web UI routes rather than Admin REST endpoints. They can load without an Admin bearer token, while protected data remains under `/admin/api/*`.
  - Browser editing intentionally exposes only `feedback_value`, `comment`, `channel`, and `tags`, even though Admin REST can also patch `source_metadata` and `attributes`.
  - Exact `target_type` filtering is implemented for Admin list review, but target fields remain immutable and are not editable review fields in this phase.
</content>
</invoke>
