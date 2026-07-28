---
doc_id: api
version: v0007
created_at: 2026-07-28T16:37:48+09:00
source: P6.REVIEW
summary: P6: the packaged Admin Web UI routes are deleted — /admin and /admin/assets/* no longer exist, only the bearer-guarded /admin/api/* REST surface remains, and it is 404d at the production edge
previous: v0006_p4_correct_the_stale_admin-docs-try-it_forward_reference_p4_superseded_the_packaged_operator_ui_with_the_web_app_rather_than_updating_its_docs_removal_moves_to_p6_no_api_contract_change
---

# API

## Status

The Web Feedback Capture REST API, the Feedback Attachment Upload REST API, the scoped End-User Feedback Read REST API (with `target_type` and other read filters), and the Admin REST API (list/detail/metrics filters, review-field patch, operator comments, and delete) are implemented. As of **P7**, capture also has a **write-only MCP surface**: a single `capture_feedback` tool at the `/mcp` endpoint (see the MCP Capture Tool contract below). Reads remain REST-only — the three MCP review/query/liked-conversation tools retired in P1 stay retired (recoverable through git history).

The account and tenancy surfaces are also implemented: a public **Account Auth API** (`/auth/*`: signup, login, logout, me) and a session-token-authed **Account Control-Plane API** (`/app/*`: the caller's tenant, projects, and per-project credentials). Public `/api/*` ingest auth changed: the optional static-token model (`VOCKY_API_AUTH_TOKEN`) is retired and replaced by **mandatory per-project credential auth** — every `/api/*` request must present a valid, non-revoked project key (`vk_…`) as `Authorization: Bearer`, and missing/malformed/unknown/revoked all answer `401`.

**Feedback API v2 (P3)** is also implemented: feedback is now project-scoped, and three new surfaces sit over it — the project-credential-authed **Project Feedback API** (`/api/project/feedback`: an external service's own admin panel reads and manages **its own project's** feedback), the session-authed **App Feedback API** (`/app/feedback`: a signed-in user reads and searches feedback across **all their projects**, Korean-safe), and **Usage Monitoring** (`/app/usage`, `/app/projects/{id}/usage`, `/api/project/usage`: derived capture volume + credential last-used, operational-only, no metering). All project/tenant-scoped reads answer **404 (never 403)** on a foreign id.

**P6 changed no endpoint contract.** It removed the packaged Admin Web UI, which deleted the non-API routes `/admin` and `/admin/assets/*`; the nine `/admin/api/*` endpoints, their auth boundary, and every request/response shape in this doc are untouched. P6 also authored (but did not deploy) the production edge, which **404s the `/admin` prefix** — see the Admin REST notes below.

These contracts should still be treated as early-stage MVP contracts rather than long-term stable commitments.

## Purpose

Use this file to record public-facing contracts as they are implemented. The current contracts are usable for the pre-MVP service, but they are still early-stage and should not be treated as long-term stable commitments.

## MVP Surfaces

- Account Auth API contract for user signup, login, logout, and identity (`/auth/*`)
- Account Control-Plane API contract for a user's tenant, projects, and per-project credentials (`/app/*`)
- Web Feedback Capture REST API contract for server-to-server website and product feedback ingestion (the operator-only Admin Docs try-it flow against the same endpoint was removed with the Admin Web UI in P6)
- MCP Capture Tool contract for agent-decided, write-only feedback capture at the `/mcp` endpoint (`capture_feedback`)
- Feedback Attachment Upload REST API contract for uploading an image and receiving an `attachment_id` to reference from a later capture call
- End-User Feedback Read REST API contract for a scoped server-to-server read of a single user's own feedback plus operator comments
- Project Feedback API (v2) contract for a project credential to read and manage its own project's feedback (`/api/project/feedback`)
- App Feedback API contract for a signed-in user to read and search feedback across all their projects (`/app/feedback`)
- Usage Monitoring API contract for derived per-tenant/project capture volume and credential last-used (`/app/usage`, `/app/projects/{id}/usage`, `/api/project/usage`)
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

### Account Auth API

- Status: implemented
- Consumers: The Vocky web app (P4) and CLI (P5); any client establishing a user session
- Purpose: Real user accounts — email + password signup/login — issuing an opaque DB-backed session bearer token
- Base path: `/auth` (public; outside `/api/*` and `/admin/api/*`, so no ingest/admin middleware guards it)
- Auth or permissions:
  - `signup` and `login` are unauthenticated (they establish a session)
  - `logout` and `me` take the session bearer token: `Authorization: Bearer <token>`
- Endpoints:
  - `POST /auth/signup`
    - Body: `{ "email": string, "password": string }`. Email is trimmed + lowercased and must contain `@`; password must be at least 8 characters.
    - Provisions a user, a tenant (auto-named `"<email-local-part>'s workspace"`), and the caller's `owner` membership, then mints a session token.
    - `201` with `{ "token": string, "user": {id, email, created_at}, "tenant": {id, name, created_at} }`
    - `409 {"detail":"a user with this email already exists"}` on a duplicate email
    - `400 {"detail":"..."}` on a malformed body, a blank/invalid email, or a short password
  - `POST /auth/login`
    - Body: `{ "email": string, "password": string }` (same normalization)
    - `200` with `{ "token": string, "user": {...}, "tenants": [{id, name, created_at}, ...] }`
    - `401 {"detail":"invalid email or password"}` — **identical** for an unknown email and a wrong password, so registered accounts cannot be enumerated
    - `400 {"detail":"..."}` on a malformed body
  - `POST /auth/logout`
    - Takes the bearer token; deletes that session token. Idempotent.
    - `204` (always, even when the token is missing or already gone)
  - `GET /auth/me`
    - Takes the bearer token; returns the caller and their tenants.
    - `200` with `{ "user": {...}, "tenants": [...] }`
    - `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer` on a missing/invalid/expired token
- Notes:
  - The session token is opaque and high-entropy; only its sha256 hash is stored, with a 30-day expiry. Raw tokens are returned once (signup/login) and never re-exposed.
  - `user` serializes as `{id, email, created_at}` and `tenant` as `{id, name, created_at}`; responses never include `password_hash` or any `token_hash`.

### Account Control-Plane API — Tenant & Projects

- Status: implemented
- Consumers: The Vocky web app (P4) and CLI (P5), acting for a signed-in user
- Purpose: Read the caller's tenant and create/list/read the tenant's projects
- Base path: `/app` (session-token authed; outside `/api/*` and `/admin/api/*`)
- Auth or permissions:
  - Every endpoint requires the session bearer token: `Authorization: Bearer <token>`
  - A missing/invalid/expired token returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - All reads/writes are scoped to the caller's tenant (solo-owner MVP: the caller's first/only tenant)
- Endpoints:
  - `GET /app/tenant` → `200 { "tenant": {id, name, created_at} }`
  - `GET /app/projects` → `200 { "projects": [<project>, ...] }` (tenant-scoped, oldest-first)
  - `POST /app/projects`
    - Body: `{ "name": string }`. Name is trimmed, `min_length=1`, `max_length=200`; stored trimmed.
    - `201 { "project": <project> }`; `400 {"detail":"..."}` on a bad/blank/oversized name or malformed body
  - `GET /app/projects/{project_id}`
    - `200 { "project": <project> }`
    - `400 {"detail":"project_id must be a valid UUID"}` on a malformed id
    - `404 {"detail":"project not found"}` when the project is missing **or** belongs to another tenant (cross-tenant existence is never leaked — 404, never 403)
- Project shape: `{ "id": string, "name": string, "tenant_id": string, "created_at": string }` (ISO-8601)

### Account Control-Plane API — Project Credentials

- Status: implemented
- Consumers: The Vocky web app (P4) and CLI (P5); a user minting the per-project keys their product backend uses on `/api/*`
- Purpose: Mint, list, and revoke a project's ingest credentials
- Base path: `/app` (session-token authed; same tenant scoping and cross-tenant-404 rule as projects)
- Auth or permissions:
  - Session bearer token required (same `401` behavior as above)
  - Every credential endpoint resolves the project scoped to the caller's tenant **first**: `400` on a malformed `project_id`, `404` when the project is missing or cross-tenant — so a caller cannot probe or mutate another tenant's projects/credentials
- Endpoints:
  - `POST /app/projects/{project_id}/credentials`
    - Optional body: `{ "name"?: string }` (trimmed; blank → `null`). An empty body is allowed.
    - `201 { "credential": <credential>, "key": "vk_<token>" }`
    - The plaintext `key` is emitted **once, only in this response**. Only its sha256 hash (`token_hash`) and a short display `token_prefix` (`key[:12]`) are stored; the raw key is never recoverable.
  - `GET /app/projects/{project_id}/credentials`
    - `200 { "credentials": [<credential>, ...] }` (oldest-first, metadata only, active and revoked)
  - `DELETE /app/projects/{project_id}/credentials/{credential_id}`
    - Soft-revokes the credential (sets `revoked_at`; idempotent). `204` on success.
    - `400` on a malformed `credential_id`; `404 {"detail":"credential not found"}` when the credential is not in that project
- Credential shape: `{ "id": string, "project_id": string, "name": string | null, "token_prefix": string, "created_at": string, "last_used_at": string | null, "revoked_at": string | null }` — never `token_hash` or the raw key
- Notes:
  - A credential is minted as `key = "vk_" + <opaque token>`. Send it as `Authorization: Bearer vk_…` on `/api/*` (see the Public `/api/*` Credential Auth Model below).
  - Revoking a credential fails `/api/*` auth immediately (the ingest lookup filters `revoked_at IS NULL`).
  - `last_used_at` is stamped best-effort on each successful `/api/*` ingest auth (P3) and surfaced by the usage endpoints; it stays `null` until the credential is first used.

### Public `/api/*` Credential Auth Model

- Status: implemented
- Applies to: every public REST endpoint under `/api/*` (`POST /api/feedback`, `POST /api/feedback/attachments`, `GET /api/feedback`, the end-user attachment download, and the P3 `/api/project/feedback` + `/api/project/usage` surfaces)
- Model:
  - Auth is **mandatory** — there is no unauthenticated or globally-shared-token path. The old optional static `VOCKY_API_AUTH_TOKEN` bearer is retired.
  - Each request must send a valid, non-revoked per-project credential as `Authorization: Bearer vk_<token>`.
  - `ProjectCredentialAuthMiddleware` extracts the bearer, hashes it (sha256), and requires an active credential (`revoked_at IS NULL`) to match.
  - Missing, malformed, unknown, and revoked keys **all** return an identical `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`.
- Notes:
  - As of P3 the guard threads project scope: on success it stashes the resolved credential (carrying its `project_id`) on the ASGI scope, so `/api/*` handlers scope capture and reads to the credential's project with no path/query project parameter. Capture stamps the record's `project_id` from it, and the guard best-effort stamps the credential's `last_used_at` (a stamping failure never fails the request).
  - The credential's project is a single project; there are no per-credential scopes — one `vk_` key does capture **and** project read+manage (`/api/project/feedback`) for its project.

### MCP Capture Tool (`capture_feedback`)

- Status: implemented (P7)
- Consumers: AI agents / agent runtimes linked to a project's Vocky MCP endpoint, deciding at their own judgement that an interaction should be captured as feedback
- Purpose: Agent-decided, **write-only** feedback capture that feeds the **same** shared queue/store as REST capture — no separate storage path. Reads stay REST-only (the three retired MCP read/query tools are not revived).
- Endpoint: `/mcp` — a FastMCP **Streamable HTTP** transport. The sole registered tool is `capture_feedback`; `initialize` + `tools/list` return exactly this one tool.
- Auth or permissions (the `/mcp` Per-Project `vk_` Auth Model):
  - The **whole** `/mcp` endpoint (the `initialize` handshake included) requires a valid, non-revoked per-project credential as `Authorization: Bearer vk_<token>` — the **same** `ProjectCredentialAuthMiddleware` boundary as `/api/*` (its predicate is `is_api_path(p) or is_mcp_path(p)`).
  - Missing, malformed, unknown, and revoked keys **all** return `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer` before the MCP transport runs.
  - The retired static `VOCKY_MCP_AUTH_TOKEN` bearer is **not** revived. The captured event is scoped to the **authenticating credential's project** — there is no project parameter in the tool inputs; the credential resolved by the middleware supplies `project_id`.
  - Transport security: DNS-rebinding protection is on by default with a localhost `Host`/`Origin` allowlist, extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS` (a public host must be added there, with its port).
- Inputs (flat tool parameters — the same capture field set as REST **minus** `attachment_ids`; agents have no upload flow):
  - `message: string` required; `source: { product: string, integration?: string }` required (the only nested input).
  - Optional: `feedback_value` (`1` like / `2` dislike), `comment`, `channel` (`web` / `mobile` / `support` / null), `conversation_id`, `session_id`, `user_id`, `trigger_type` (`like`/`dislike`/`comment`/`rating`/`survey`/`manual`/`other`), `trigger_message`, `trigger_metadata` (object), `target_type` (`message`/`conversation`/`surface`), `target_id`, `target_role` (`user`/`assistant`/`system`/`tool`), `target_text`, `event_at` (timezone-aware ISO 8601), `tags` (string[]), `messages` (array), `used_context` (array), `source_metadata` (object), `attributes` (object).
  - Normalization/validation is identical to REST capture (shared `normalize_*_payload` seam). There is **no** `attachment_ids` parameter, and no `project_id` parameter (it comes from the credential).
- Outputs: an MCP `CallToolResult`:
  - Success: `isError=false` with a `structuredContent` capture receipt `{ request_id, accepted_at, status: "accepted" }` plus a text block `Accepted feedback capture <request_id>`. As with REST, success means the job was accepted for background persistence, not that the record is already queryable.
- Errors (returned as `isError=true` tool results, not transport errors):
  - Capture validation failures return an error result carrying the validation message.
  - A queue-accept failure returns an error result `capture queue unavailable`.
  - (Auth failures are handled earlier by the `/mcp` middleware as a transport-level `401`, so an unauthenticated caller never reaches the tool.)
- Notes:
  - Write-only by construction: `capture_feedback` is the only tool; there is no MCP read, query, summary, or liked-conversation surface.
  - The tool reuses the transport-neutral capture pipeline (`enqueue_feedback` → worker → `feedback_events`) and stamps `project_id` from the credential the transport authenticated — identical downstream behavior to `POST /api/feedback`. No DB schema change.

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
  - Mandatory per-project credential auth (see the Public `/api/*` Credential Auth Model). Every request must send `Authorization: Bearer vk_<token>` for a valid, non-revoked project credential; missing/malformed/unknown/revoked all return `401`.
  - The retired static `VOCKY_API_AUTH_TOKEN` bearer is gone. (The packaged Admin Docs try-it flow that still referenced it was **deleted in P6** along with the rest of the Admin Web UI, so no in-product surface describes the retired model any more.)
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
  - A missing, invalid, unknown, or revoked per-project credential returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
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
  - Same boundary as REST capture: mandatory per-project credential auth (`Authorization: Bearer vk_<token>`); missing/invalid/revoked → `401`.
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
  - A missing, invalid, unknown, or revoked per-project credential returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
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
  - Trusted server-to-server. The integrating product authenticates its own end user, then calls Vocky with that `user_id` and a per-project credential; Vocky has no native end-user accounts (the capture `user_id` is the product's own end user, distinct from a Vocky account).
  - Mandatory per-project credential auth (`Authorization: Bearer vk_<token>`), the same boundary as REST capture; missing/invalid/revoked → `401`.
  - Vocky enforces `user_id` + `source_product` scoping server-side and never returns cross-user or cross-product data. As of P3 (D-P3-6, defense in depth) the read is **additionally** scoped to the authenticating credential's project, so it never returns another project's rows even under a colliding `(user_id, source_product)`; legacy rows with a NULL `project_id` fall out of this read.
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
  - A missing, invalid, unknown, or revoked per-project credential returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - Missing or blank `user_id` or `source_product`, invalid filter values, invalid limits, blank `tag`, invalid time windows, and invalid cursors return `400 {"detail":"..."}`
  - Storage read failures return `500 {"detail":"storage read failed"}`
- Notes:
  - This is the **end-user self-read**: deliberately scoped to a single product user's own feedback (by `user_id` + `source_product` + the credential's project). It is not a general query or management API. Project-scoped operator review/management is the separate **Project Feedback API** (`/api/project/feedback`) below; cross-project read/search for a signed-in user is the **App Feedback API** (`/app/feedback`); self-hosted operator review remains Admin REST.
  - Operator comments are returned read-only. This phase is one-way operator-to-user visibility with no end-user replies or two-way threads.
  - The read reuses the same `feedback_events` store, indexed `user_id` / `source_product` filters, and cursor pagination as the Admin read surface, with batched operator-comment and attachment fetches to avoid N+1 lookups.
  - Each record's image attachments are surfaced as an `attachments` array; the bytes are served by the scoped end-user attachment download below.

#### End-User Feedback Attachment Download

- Endpoint: `GET /api/feedback/{feedback_id}/attachments/{attachment_id}`
- Auth: same `/api/*` bearer boundary as the read.
- Inputs (query parameters): `user_id` and `source_product`, both required and non-blank (the same scope as the read).
- Authorization: the attachment is authorized off its linked feedback row's `(user_id, source_product)`. A request for another user's or product's attachment, an unlinked attachment, a missing attachment, or a missing feedback all return `404` — existence is never leaked.
- Outputs: `200 OK` streaming the attachment bytes with the stored `content_type`, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, and `Cache-Control: private, no-store`.
- Errors: missing/invalid/revoked per-project credential → `401`; missing/blank `user_id` or `source_product`, or a malformed id → `400`; any authorization miss or a missing stored object → `404`; storage read failure → `503`.

### Project Feedback API (v2)

- Status: implemented
- Consumers: An external service's own admin panel / operator page (for example the operator's changple5 projects) reading and managing its project's feedback directly by API
- Purpose: Let a project's `vk_` credential read **and manage** its own project's feedback — the external-admin-panel path (D-P3-2). Ports the operator verbs from Admin REST, scoped to one project.
- Base path: `/api/project/feedback`
- Auth or permissions:
  - Mandatory per-project credential auth (`Authorization: Bearer vk_<token>`), the same `/api/*` boundary as capture; missing/invalid/revoked → `401`.
  - The project is **implicit in the credential** — there is no project path or query parameter. Every operation is scoped to `credential.project_id`. There are no per-credential scopes: one `vk_` key does capture and full read+manage for its project.
  - Any feedback id belonging to another project answers **404 (never 403)** so cross-project existence is never leaked (mirrors D-P2-5); mutating ops verify ownership before the mutation.
- Endpoints:
  - `GET /api/project/feedback`
    - Lists the credential's own project's feedback, newest-first, with keyset pagination. Supports the same optional filters as the Admin list (`start_ingested_at`, `end_ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `feedback_value`, exact `channel`, exact `target_type`, exact `trigger_type`, `tag`, `limit`, `cursor`). The project filter is **forced** to the credential's project and overrides any caller-supplied value.
    - `200 { "records": [<record>, ...], "next_cursor"?: string }`. Records use the Admin record shape **without** a `project_id` field (the caller knows its own project).
  - `GET /api/project/feedback/{feedback_id}`
    - `200 { "record": <record + comments[] + attachments[]> }`; attachment `url` = `/api/project/feedback/{feedback_id}/attachments/{id}`.
    - `404 {"detail":"feedback not found"}` when missing or in another project; `400` on a malformed id.
  - `PATCH /api/project/feedback/{feedback_id}`
    - Updates review-oriented fields only: `feedback_value`, `comment`, `channel`, `tags`, `source_metadata`, `attributes` (same rules as Admin patch). Ownership is verified before the update.
    - `200 { "record": <record> }`; `400` on an empty/invalid body or invalid non-null `channel`; `404` cross-project/missing.
  - `DELETE /api/project/feedback/{feedback_id}`
    - Deletes the record (comments + attachment rows cascade) and best-effort deletes the attachment files → `204`. `404` cross-project/missing.
  - `GET|POST /api/project/feedback/{feedback_id}/comments`
    - `GET` lists the record's operator comments oldest-first (`200 { "comments": [...] }`). `POST` adds one (`body` required non-blank, optional `author`) → `201 { "comment": <comment> }`. `404` cross-project/missing; `400` on a blank/missing `body`.
  - `GET /api/project/feedback/{feedback_id}/attachments/{attachment_id}`
    - Streams one attachment linked to the project's feedback (`X-Content-Type-Options: nosniff`). `404` cross-project, unlinked, or missing object; `503` on storage failure.
- Errors: `401` (auth), `400` (malformed id/body/filters), `404` (cross-project or missing — never 403), `500 {"detail":"storage read failed"}` / `503` (attachment storage) on storage errors.
- Notes:
  - Record / comment / attachment shapes match the Admin Feedback REST API below, except the record omits `project_id`. `serialize_record` is shared with Admin REST (`tools/query_feedback_common.py`); Admin REST output is unchanged.

### App Feedback API (cross-project read + search)

- Status: implemented
- Consumers: The Vocky web app (P4) and CLI (P5), acting for a signed-in user who owns many projects
- Purpose: Let a signed-in user **read and search** feedback across **all their tenant's projects** at once. Read + search only — management stays on the Project Feedback API.
- Base path: `/app/feedback` (session-token authed; outside `/api/*` and `/admin/api/*`)
- Auth or permissions:
  - Session bearer token required (`Authorization: Bearer <token>`); a missing/invalid/expired token returns `401 {"detail":"Unauthorized"}`.
  - Scoped to the caller's tenant's project set (`list_projects_for_tenant`). Any feedback outside that set — including legacy NULL-`project_id` rows — answers **404 (never 403)**.
- Endpoints:
  - `GET /app/feedback`
    - Cross-project list/search, newest-first, keyset paginated. Query: `q` (free-text search), optional `project_id` (narrow to one owned project), plus the standard filters (`start_ingested_at`, `end_ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `feedback_value`, `channel`, `target_type`, `trigger_type`, `tag`, `limit`, `cursor`).
    - `200 { "records": [<record + project_id>, ...], "next_cursor"?: string }`. Each record **includes** `project_id` (the caller has many projects). A caller with no projects (or an empty owned narrow) returns `{ "records": [] }`.
    - `?project_id` narrowing validates membership: malformed → `400 {"detail":"project_id must be a valid UUID"}`, not-owned/unknown → `404 {"detail":"project not found"}`.
  - `GET /app/feedback/{feedback_id}`
    - `200 { "record": <record + project_id + comments[] + attachments[]> }`; attachment `url` = `/app/feedback/{feedback_id}/attachments/{id}`. `404` cross-tenant/missing; `400` malformed id.
  - `GET /app/feedback/{feedback_id}/attachments/{attachment_id}`
    - Streams one attachment linked to a feedback record in the caller's tenant (`X-Content-Type-Options: nosniff`). `404` cross-tenant, unlinked, or missing object; `503` storage failure.
- Search (`q`) semantics:
  - Case-insensitive **substring** (`ILIKE`) match over the concatenated user-visible text (`message`, `comment`, `target_text`, `trigger_message`). Language-agnostic: it matches Korean 조사-attached forms (`결제` matches both `결제 오류` and `결제를`) and English uniformly. Deliberately **no** `to_tsvector('english', …)` (D-P3-4).
  - Search is a **filter, newest-first** — not relevance ranking — and composes with the standard filters and keyset paging. It is accelerated by a `pg_trgm` trigram GIN index but returns identical results with or without it.
- Errors: `401` (session), `400` (malformed id/`project_id`/filters), `404` (cross-tenant/not-owned/missing — never 403), `500 {"detail":"storage read failed"}` / `503` (attachment storage).

### Usage Monitoring API

- Status: implemented
- Consumers: The Vocky web app (P4) and CLI (P5); an external admin panel viewing its project's usage
- Purpose: Report **derived** feedback-capture volume over a time window plus surfaced credential `last_used_at` — operational visibility, **not** billing (D-P3-5). No new tables, no request-count metering; the metrics reuse the same feedback query as Admin metrics, scoped by project/tenant.
- Endpoints:
  - `GET /app/usage` (session): the caller's **whole-tenant** capture volume aggregated across every project it owns, plus a light project list.
    - `200 { "window": {...}, "totals": {...}, "daily_counts": [...], "projects": [{ "id", "name", "created_at" }, ...] }`. A tenant with no projects returns zeroed metrics and an empty `projects` list.
  - `GET /app/projects/{project_id}/usage` (session): one owned project's capture volume plus that project's credentials (each carrying `last_used_at`).
    - `200 { "window": {...}, "totals": {...}, "daily_counts": [...], "credentials": [<credential>, ...] }`. `400` malformed id; `404` cross-tenant/unknown project.
  - `GET /api/project/usage` (project `vk_` credential): the credential's own project's capture volume plus its credentials.
    - `200 { "window": {...}, "totals": {...}, "daily_counts": [...], "credentials": [<credential>, ...] }`. `401` on missing/invalid/revoked key.
- Window:
  - Optional `start_ingested_at` / `end_ingested_at` (timezone-aware ISO 8601). With **both omitted** the window defaults to the **last 30 days** ending now; with only one given the other is filled (`end` = now, or `start` = `end` − 30d). A malformed bound or an inverted window → `400`.
- Response shape:
  - `window.start_ingested_at` / `window.end_ingested_at` (UTC ISO 8601), `totals.{total,liked,disliked,unrated}`, and zero-filled UTC `daily_counts` (each `{day,total,liked,disliked,unrated}`) — the same metrics shape as the Admin metrics contract. `credentials[]` use the control-plane credential shape (with `last_used_at`); `projects[]` are `{id,name,created_at}`.
- Errors: `401` (auth), `400` (bad window / malformed `project_id`), `404` (cross-tenant project), `500 {"detail":"storage read failed"}`.

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
  - **Admin REST has no first-party client as of P6.** The packaged Admin Web UI that consumed it (dashboard metrics, list/filter/detail review, review-field editing, guarded delete) was physically removed; consumers are now operator scripts, curl, or a self-hosted operator's own dashboard. The endpoint contracts below are unchanged.
  - **`/admin` and `/admin/assets/*` no longer exist.** They were static Web UI routes, not Admin REST endpoints, and were deleted in P6. After the removal the **only** routes under the `/admin` prefix are the nine `/admin/api/*` endpoints, and every one of them is bearer-guarded — there is no unauthenticated `/admin` path left.
  - **The production edge does not expose `/admin` at all.** `deploy/vocky.conf` answers `location /admin/ { return 404; }`, so Admin REST is reachable only from inside the deployment's Docker network (or an SSH tunnel), never from `https://vocky.hi2vi.com`. The Admin bearer remains required regardless — see `security.md`.
  - Browser editing (in the packaged UI, while it existed) intentionally exposed only `feedback_value`, `comment`, `channel`, and `tags`, even though Admin REST can also patch `source_metadata` and `attributes`.
  - Exact `target_type` filtering is implemented for Admin list review, but target fields remain immutable and are not editable review fields in this phase.
</content>
</invoke>
