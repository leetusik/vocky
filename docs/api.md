# API

## Status

The feedback capture MCP tool, Web Feedback Capture REST API, and the `P3` read tools are implemented. They should still be treated as early-stage MVP contracts rather than long-term stable commitments.

## Purpose

Use this file to record public-facing contracts as they are implemented. The current contracts are usable for the pre-MVP service, but they are still early-stage and should not be treated as long-term stable commitments.

## MVP Surfaces

- MCP tool contract for feedback capture
- Web Feedback Capture REST API contract for server-to-server ingestion
- MCP tool contracts for review and query access
- MCP tool contract for liked-conversation retrieval
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

### Feedback Capture MCP Tool

- Status: implemented in `P1`
- Consumers: Agent products and agent-runtime integrations sending feedback into Vocky
- Purpose: Submit a single feedback event from an agent interaction for asynchronous persistence
- Inputs:
  - Tool name: `capture_feedback`
  - Request body:
    - `message: string` required. Leading and trailing whitespace is trimmed. The value must not be blank after trimming. This is the human-readable feedback summary or display text, not an implicit pointer to the reviewed message.
    - `source: object` required.
    - `source.product: string` required. Leading and trailing whitespace is trimmed. The value must not be blank after trimming.
    - `source.integration: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `feedback_value: integer` optional. When provided, must be `1` for like or `2` for dislike.
    - `comment: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`. Comments are recommended for dislikes but are not required.
    - `channel: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `conversation_id: string` optional. Caller-provided conversation or thread identifier. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `session_id: string` optional. Caller-provided runtime, browser, or user-session identifier. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_type: string` optional. Identifies the exact reviewed target category. Allowed values are `message`, `conversation`, and `surface`. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_id: string` optional. Caller-provided stable identifier for the reviewed target. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_role: string` optional. Role for a reviewed message target. Allowed values are `user`, `assistant`, `system`, and `tool`. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `target_text: string` optional. Snapshot of the exact reviewed message or product surface text. Leading and trailing whitespace is trimmed. Blank values are normalized to `null`.
    - `event_at: string` optional. Must be a timezone-aware ISO 8601 timestamp. Naive timestamps are rejected. Accepted values are normalized to UTC before persistence and in responses.
    - `tags: string[]` optional. Tags are trimmed. Blank tags are rejected. Duplicate tags after normalization are rejected. Persisted tag order follows the client-supplied order after normalization.
    - `messages: array` optional. JSON array of caller-provided surrounding conversation messages persisted as supplied.
    - `used_context: array` optional. JSON array of caller-provided context used by the agent persisted as supplied.
    - `source_metadata: object` optional. Arbitrary JSON object persisted to `source_metadata`.
    - `attributes: object` optional. Arbitrary JSON object persisted to `attributes`.
- Outputs:
  - Success MCP tool result:
    - A text acknowledgement in `content`
    - A structured response object in `structuredContent`
  - Structured response object:
    - `request_id: string` UUID generated when the capture job is accepted
    - `accepted_at: string` UTC ISO 8601 timestamp generated when the queue accepts the job
    - `status: string` fixed to `accepted`
- Errors:
  - Validation failures return an MCP tool execution error with `isError: true`
  - Queue-accept failures return an MCP tool execution error with `isError: true`
  - Unknown-tool and protocol-level failures remain MCP protocol errors
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - No managed-cloud auth model is defined yet
  - Public self-hosted deployments should require `Authorization: Bearer <VOCKY_MCP_AUTH_TOKEN>` on the MCP HTTP request
- Notes:
  - MCP capture is the agent-workflow ingestion surface. Server-to-server product integrations that cannot use MCP may use the Web Feedback Capture REST API.
  - Target fields are optional captured context. Omitting them preserves the legacy capture behavior and stores `null` target values.
  - The MVP stores raw feedback and metadata; it does not auto-classify events
  - The persisted record shape is defined in `docs/architecture.md` under `Capture Storage Model`
  - Validation and business-rule failures should be visible to MCP clients so models can correct and retry when possible
  - Success means the job was accepted for background processing, not that the feedback record is already queryable
  - The self-hosted service exposes this tool through the Starlette-hosted MCP endpoint at `/mcp`

### Web Feedback Capture REST API

- Status: implemented in `P1`
- Consumers: Server-to-server web and product integrations sending feedback into Vocky without using MCP
- Purpose: Submit a single feedback event for asynchronous persistence
- Base path: `/api`
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - When `VOCKY_API_AUTH_TOKEN` is set, `/api/*` requests must include `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`
  - Public deployments should set `VOCKY_API_AUTH_TOKEN` before exposing `/api/*`
- Endpoint:
  - `POST /api/feedback`
- Inputs:
  - JSON request body with the same fields and validation semantics as the `capture_feedback` MCP tool:
    - `message: string` required
    - `source.product: string` required
    - `source.integration: string` optional
    - `feedback_value: integer` optional, `1` for like or `2` for dislike
    - `comment`, `channel`, `conversation_id`, `session_id`, `target_type`, `target_id`, `target_role`, `target_text`, and timezone-aware `event_at` optional
    - `tags`, `messages`, `used_context`, `source_metadata`, and `attributes` optional
- Outputs:
  - Success status: `202 Accepted`
  - Response body:
    - `request_id: string` UUID generated when the capture job is accepted
    - `accepted_at: string` UTC ISO 8601 timestamp generated when the queue accepts the job
    - `status: string` fixed to `accepted`
- Errors:
  - Missing or invalid bearer token when auth is configured returns `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`
  - Malformed JSON, non-object request bodies, schema errors, and semantic validation failures return `400 {"detail":"..."}`
  - Queue-accept failures return `503 {"detail":"capture queue unavailable"}`
- Notes:
  - This REST API is capture-only. It does not add public REST review, query, summary, job-status, or management endpoints.
  - Target fields are optional captured context. Omitting them preserves the legacy capture behavior and stores `null` target values.
  - Success means the job was accepted for background processing, not that the feedback record is already queryable.
  - Accepted REST capture jobs use the same Redis queue, worker, feedback service, and PostgreSQL table as MCP capture jobs.

### Feedback Listing MCP Tool

- Status: implemented in `P3`
- Consumers: Operators, scripts, or MCP clients reviewing stored feedback through MCP
- Purpose: Retrieve stored feedback records with a small, explicit filter set and cursor pagination
- Inputs:
  - Tool name: `list_feedback`
  - Request body:
    - `start_ingested_at: string` optional. Must be a timezone-aware UTC-capable ISO 8601 timestamp. When provided, records are filtered with `ingested_at >= start_ingested_at` after normalization to UTC.
    - `end_ingested_at: string` optional. Must be a timezone-aware UTC-capable ISO 8601 timestamp. When provided, records are filtered with `ingested_at < end_ingested_at` after normalization to UTC.
    - `source_product: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `source_integration: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `conversation_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `session_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `feedback_value: integer` optional. When provided, must be `1` for like or `2` for dislike.
    - `channel: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `tag: string` optional. Leading and trailing whitespace is trimmed. Blank values are rejected.
    - `limit: integer` optional. When omitted, the server applies a default page size of `50`. Values must be between `1` and `100`.
    - `cursor: string` optional. Must be an opaque base64url-encoded JSON cursor returned from an earlier `list_feedback` call. Invalid cursor payloads are rejected.
- Outputs:
  - Success MCP tool result:
    - A text acknowledgement in `content`
    - A structured response object in `structuredContent`
  - Structured response object:
    - `records: object[]` newest-first records sorted by `(ingested_at desc, id desc)`
    - `next_cursor: string` opaque pagination cursor for the next page when more records exist. The field is omitted when no further page exists.
  - Record shape:
    - `id: string` UUID of the stored record
    - `message: string`
    - `source_product: string`
    - `feedback_value: integer | null`
    - `comment: string | null`
    - `channel: string | null`
    - `source_integration: string | null`
    - `conversation_id: string | null`
    - `session_id: string | null`
    - `target_type: string | null`
    - `target_id: string | null`
    - `target_role: string | null`
    - `target_text: string | null`
    - `event_at: string | null` UTC ISO 8601 timestamp when present
    - `ingested_at: string` UTC ISO 8601 timestamp
    - `tags: string[]`
    - `messages: array`
    - `used_context: array`
    - `source_metadata: object`
    - `attributes: object`
- Errors:
  - Invalid timestamps, invalid time windows, invalid limits, blank `tag`, and invalid cursors return MCP tool execution errors with `isError: true`
  - Storage read failures return MCP tool execution errors with `isError: true`
  - Unknown-tool and protocol-level failures remain MCP protocol errors
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - Public self-hosted deployments should require `Authorization: Bearer <VOCKY_MCP_AUTH_TOKEN>` on the MCP HTTP request
- Notes:
  - Time filtering is based on `ingested_at` only, not `event_at`
  - Target fields are returned for review context but are not filters in this phase.
  - `start_ingested_at` is inclusive and `end_ingested_at` is exclusive
  - The cursor payload is derived from the last returned record's `ingested_at` and `id`
  - `tag` matches exact single-tag membership against the stored `tags` array
  - Accepted capture jobs are not visible here until the background worker persists them
  - This is a machine-readable review surface, not a human-facing dashboard

### Feedback Summary MCP Tool

- Status: implemented in `P3`
- Consumers: Operators, scripts, or MCP clients reviewing stored feedback trends through MCP
- Purpose: Return total feedback volume and UTC daily counts for an explicit ingest-time window
- Inputs:
  - Tool name: `summarize_feedback`
  - Request body:
    - `start_ingested_at: string` required. Must be a timezone-aware ISO 8601 timestamp and is normalized to UTC. The summary window includes records with `ingested_at >= start_ingested_at`.
    - `end_ingested_at: string` required. Must be a timezone-aware ISO 8601 timestamp and is normalized to UTC. The summary window includes records with `ingested_at < end_ingested_at`.
    - `source_product: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `source_integration: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `conversation_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `session_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `feedback_value: integer` optional. When provided, must be `1` for like or `2` for dislike.
    - `channel: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `tag: string` optional. Leading and trailing whitespace is trimmed. Blank values are rejected.
- Outputs:
  - Success MCP tool result:
    - A text acknowledgement in `content`
    - A structured response object in `structuredContent`
  - Structured response object:
    - `total_count: integer` total number of matching records in the window
    - `daily_counts: object[]` UTC day buckets spanning the entire requested window, including zero-count days
  - Daily count shape:
    - `day: string` UTC calendar day in `YYYY-MM-DD` format
    - `count: integer`
- Errors:
  - Missing or invalid timestamps, invalid time windows, and blank `tag` return MCP tool execution errors with `isError: true`
  - Storage read failures return MCP tool execution errors with `isError: true`
  - Unknown-tool and protocol-level failures remain MCP protocol errors
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - Public self-hosted deployments should require `Authorization: Bearer <VOCKY_MCP_AUTH_TOKEN>` on the MCP HTTP request
- Notes:
  - Time filtering is based on `ingested_at` only, not `event_at`
  - `daily_counts` is a zero-filled UTC day series across the requested window
  - Accepted capture jobs are not counted until the background worker persists them
  - The MVP summary surface does not include by-product, by-tag, or by-integration breakdowns

### Liked Conversation Listing MCP Tool

- Status: implemented in `P2`
- Consumers: AI agents retrieving liked conversations for few-shot examples or response guidance
- Purpose: Retrieve only liked feedback records with stored messages and used context
- Inputs:
  - Tool name: `list_liked_conversations`
  - Request body:
    - `start_ingested_at: string` optional. Must be a timezone-aware UTC-capable ISO 8601 timestamp. When provided, records are filtered with `ingested_at >= start_ingested_at` after normalization to UTC.
    - `end_ingested_at: string` optional. Must be a timezone-aware UTC-capable ISO 8601 timestamp. When provided, records are filtered with `ingested_at < end_ingested_at` after normalization to UTC.
    - `source_product: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `source_integration: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `conversation_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `session_id: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `channel: string` optional. Leading and trailing whitespace is trimmed. Blank values are normalized to absent.
    - `tag: string` optional. Leading and trailing whitespace is trimmed. Blank values are rejected.
    - `limit: integer` optional. When omitted, the server applies a default page size of `50`. Values must be between `1` and `100`.
    - `cursor: string` optional. Must be an opaque base64url-encoded JSON cursor returned from an earlier `list_liked_conversations` call.
- Outputs:
  - Success MCP tool result:
    - A text acknowledgement in `content`
    - A structured response object in `structuredContent`
  - Structured response object:
    - `conversations: object[]` liked records sorted newest-first
    - `next_cursor: string` opaque pagination cursor for the next page when more liked records exist. The field is omitted when no further page exists.
  - Conversation shape:
    - `id: string`
    - `message: string`
    - `comment: string | null`
    - `channel: string | null`
    - `source_product: string`
    - `source_integration: string | null`
    - `conversation_id: string | null`
    - `session_id: string | null`
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
- Errors:
  - Invalid timestamps, invalid time windows, invalid limits, blank `tag`, and invalid cursors return MCP tool execution errors with `isError: true`
  - Storage read failures return MCP tool execution errors with `isError: true`
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - Public self-hosted deployments should require `Authorization: Bearer <VOCKY_MCP_AUTH_TOKEN>` on the MCP HTTP request
- Notes:
  - This tool always enforces `feedback_value = 1` server-side.
  - Target fields are returned for review context but are not filters in this phase.
  - Disliked records are stored but intentionally not returned here.
  - This is an AI-agent few-shot retrieval surface, not a human admin review API.

### Admin Feedback REST API

- Status: implemented in `P3`
- Consumers: Human operators, scripts, and admin dashboards
- Purpose: Query, inspect, manage, and summarize feedback records through REST endpoints separate from MCP tools
- Base path: `/admin/api`
- Auth or permissions:
  - Deployment-specific for the self-hosted MVP
  - When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST requests must include `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`
  - Public deployments should protect or avoid exposing `/admin/api`
- Endpoints:
  - `GET /admin/api/healthz`
    - Returns `{"service":"vocky","surface":"admin","status":"ok"}`
  - `GET /admin/api/feedback`
    - Lists all feedback records by default, not only liked records
    - Supports `start_ingested_at`, `end_ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `feedback_value`, `channel`, `tag`, `limit`, and `cursor`
    - Returns `records` and optional `next_cursor`
  - `GET /admin/api/feedback/metrics`
    - Returns dashboard metrics for a required ingest-time window
    - Requires `start_ingested_at` and `end_ingested_at` timezone-aware ISO 8601 query parameters
    - Normalizes the requested window to UTC
    - Counts records with `ingested_at >= start_ingested_at` and `ingested_at < end_ingested_at`
    - Returns `window`, `totals`, and zero-filled UTC `daily_counts`
  - `GET /admin/api/feedback/{feedback_id}`
    - Returns one full feedback record or `404` when missing
  - `PATCH /admin/api/feedback/{feedback_id}`
    - Updates review-oriented fields: `feedback_value`, `comment`, `channel`, `tags`, `source_metadata`, and `attributes`
    - Captured target fields, `messages`, and `used_context` are immutable in this MVP
    - Returns the updated record
  - `DELETE /admin/api/feedback/{feedback_id}`
    - Deletes one feedback record and returns `204` on success
- Record shape:
  - `id: string`
  - `message: string`
  - `source_product: string`
  - `feedback_value: integer | null`
  - `comment: string | null`
  - `channel: string | null`
  - `source_integration: string | null`
  - `conversation_id: string | null`
  - `session_id: string | null`
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
  - Validation failures return JSON `400` responses with `detail`
  - Missing records return JSON `404` responses with `detail`
  - Storage read or write failures return JSON `500` responses with `detail`
- Notes:
  - Admin REST is the human/operator review surface.
  - The Admin REST API and MCP tools share the same `feedback_events` schema and service/repository layer.
  - The packaged Admin Web UI consumes this same-origin Admin REST surface for dashboard metrics, feedback list/filter/detail review, review-field editing, and guarded delete.
  - `/admin` and `/admin/assets/*` are static Admin Web UI routes rather than Admin REST endpoints. They can load without an Admin bearer token, while protected data remains under `/admin/api/*`.
  - Browser editing intentionally exposes only `feedback_value`, `comment`, `channel`, and `tags`, even though Admin REST can also patch `source_metadata` and `attributes`.
  - Target fields are returned for review context but are not filters or editable review fields in this phase.
  - The liked-conversation MCP tool remains AI-agent-only and does not replace Admin REST review.
