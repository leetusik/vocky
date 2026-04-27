# Architecture

## Status

This architecture is intentionally lightweight. Vocky is still pre-MVP, and the current service accepts capture work through MCP or server-to-server REST using Redis-backed queueing plus a dedicated worker while exposing MCP read tools, liked-conversation retrieval, separate Admin REST endpoints, and a same-origin self-hosted Admin Web UI with dashboard metrics, feedback review management, and in-app operator documentation over the same PostgreSQL feedback store.

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `pyproject.toml`: Python project metadata and dependencies
- `src/vocky/`: service code, MCP server wiring, Admin REST and Web UI routing, persistence layer, and smoke script
- `alembic/` and `alembic.ini`: database migration environment
- `tests/`: validation, persistence, and MCP integration coverage
- `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile`: local run, package verification, external smoke checks, and self-hosted development workflow
- `docs/`: stable reference documents
- `works/`: active backlog, deferred queue, active work items, archives, and templates
- `scripts/`: workflow helpers

## First MVP System Shape

The first MVP should be built from these parts:

- MCP-facing feedback capture for agent/message workflows and server-to-server REST feedback capture for broader website or product feedback
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- MCP read tools that return stored records, simple counts or trends, and liked examples for AI-agent workflows
- Dedicated Admin REST endpoints for human operators, dashboard metrics, and review workflows
- A packaged same-origin Admin Web UI for self-hosted operators, including dashboard metrics, feedback review management, and in-app operator docs backed by Admin REST rather than a separate browser-facing data API

## Runtime Shape

The current service uses these choices:

- Python application managed with `uv`
- Application package under `src/vocky`
- A Starlette ASGI host process for MCP, REST, and health traffic
- A separate worker process for background capture persistence
- Redis-backed queueing between the app and worker
- Official MCP Python SDK `FastMCP` served by the host app at `/mcp` using Streamable HTTP
- Public REST capture route under `/api/*`
- Starlette Admin REST routes under `/admin/api/*`
- Starlette Admin Web UI routes under `/admin` and packaged static assets under `/admin/assets/*`
- Stateless MCP operation with JSON responses enabled
- A plain `/healthz` endpoint on the same host app for smoke checks
- Optional bearer-token protection for MCP traffic when public access is enabled
- Optional bearer-token protection for public REST capture traffic when `VOCKY_API_AUTH_TOKEN` is set
- Optional bearer-token protection for Admin REST traffic when `VOCKY_ADMIN_AUTH_TOKEN` is set
- Docker builds install runtime dependencies and the local project into the image, while Compose app and worker commands use `uv run --no-sync` so container startup does not repeat dependency sync
- Transport-specific capture adapters with shared validation helpers, service, and persistence layers so MCP and REST can express different integration intent while the worker reuses the same persistence path

Clients should use `/mcp` as the canonical MCP endpoint for agent workflows. Server-to-server product integrations should use `/api/feedback` for capture-only ingestion, including non-agent website or product-surface feedback. Human/operator tools should use `/admin/api/*`, while browser operators can load the packaged UI from `/admin`. The app avoids relying on a `/mcp` to `/mcp/` redirect so reverse proxies do not need to repair redirect schemes.

## Three-Track API Shape

Vocky now has three public-facing tracks over the same feedback schema:

- MCP track for AI-agent workflows: `capture_feedback`, `list_feedback`, `summarize_feedback`, and `list_liked_conversations`. MCP capture is optimized for message, conversation, and agent-context feedback.
- Public REST capture track for server-to-server product integrations: `POST /api/feedback`. REST capture uses the existing capture field set for general website or product feedback, including surface feedback represented with `target_type="surface"` when applicable.
- Admin REST track for humans and dashboards: `/admin/api/feedback` list/detail, `/admin/api/feedback/metrics` dashboard metrics, plus patch/delete management endpoints.

The Admin Web UI is a same-origin browser surface layered over the Admin REST track for protected dashboard data, feedback review management, and packaged static docs assets for operator reference content. All API tracks use the same PostgreSQL `feedback_events` table, feedback service, and repository. MCP tools should remain optimized for agent behavior; the liked-conversation MCP tool is intentionally limited to liked records for few-shot use. Public REST is capture-only and does not expose review, query, summary, or management endpoints. REST does not add a separate wire shape in this phase; website and product context should be represented with `target_type`, `target_id`, `target_text`, nullable `channel`, `tags`, `source_metadata`, and `attributes`. Admin REST is the surface that can inspect and manage all feedback records, including likes, dislikes, comments, channel category, metadata, target context, messages, and used context. The browser workflow intentionally exposes a narrower edit surface than Admin REST: `feedback_value`, `comment`, `channel`, and `tags`.

## Configuration Surface

The runtime configuration surface is intentionally small:

- `DATABASE_URL`: PostgreSQL connection URL for the async SQLAlchemy engine and Alembic migrations
- `REDIS_URL`: Redis connection URL shared by the app enqueue path and the background worker
- `VOCKY_HOST`: application bind host
- `VOCKY_PORT`: application bind port
- `VOCKY_LOG_LEVEL`: application log level
- `VOCKY_MCP_ALLOWED_HOSTS`: optional comma-separated Host header allowlist additions for MCP DNS rebinding protection, such as `vocky.example.com`.
- `VOCKY_MCP_ALLOWED_ORIGINS`: optional comma-separated Origin header allowlist additions for browser-origin MCP traffic, such as `https://vocky.example.com`.
- `VOCKY_MCP_AUTH_TOKEN`: optional bearer token required for MCP traffic. Public deployments should set it.
- `VOCKY_API_AUTH_TOKEN`: optional bearer token required for `/api/*` traffic. Public deployments that expose REST capture should set it.
- `VOCKY_ADMIN_AUTH_TOKEN`: optional bearer token required for Admin REST traffic. Public deployments that expose `/admin/api` should set it.

The supported local operator workflow adds these host-side settings:

- `TEST_DATABASE_URL`: dedicated disposable PostgreSQL database used by `make test`. It must not point at the same database as `DATABASE_URL`.
- `VOCKY_PUBLISH_HOST`: host interface Docker Compose publishes the app port on. The default is `127.0.0.1` for local-only access.
- `POSTGRES_PUBLISH_HOST`: host interface Docker Compose publishes PostgreSQL on. The default is `127.0.0.1`.
- `REDIS_PUBLISH_HOST`: host interface Docker Compose publishes Redis on. The default is `127.0.0.1`.
- `VOCKY_BASE_URL`: optional override for host-side smoke checks when the public base URL differs from `http://127.0.0.1:${VOCKY_PORT}`.
- `VOCKY_EXTERNAL_BASE_URL`: optional external URL used for public custom-domain deployments through Cloudflare Tunnel or another HTTPS reverse proxy, for example `https://vocky.example.com`.

`VOCKY_HOST` remains the application bind address inside the process. The `*_PUBLISH_HOST` variables control which host interface Docker publishes to. `VOCKY_BASE_URL` remains the local verification target, while `VOCKY_EXTERNAL_BASE_URL` is reserved for public custom-domain operator docs and client examples. Public MCP hosts must be present in `VOCKY_MCP_ALLOWED_HOSTS`; otherwise FastMCP rejects them with `421 Invalid Host header`.

The root `.env`, copied from `.env.example`, is the primary local configuration source for both Docker Compose and the Make-based host workflow. The Compose app service receives MCP, public REST, and Admin auth settings from this file, including `VOCKY_MCP_AUTH_TOKEN`, `VOCKY_API_AUTH_TOKEN`, and `VOCKY_ADMIN_AUTH_TOKEN`. The supported self-hosted path remains Compose-first and includes Redis plus the worker process. `make bootstrap` should bring up the service dependencies, apply migrations, and wait for readiness. `make verify` should build and inspect a fresh wheel for packaged Admin UI assets, wait for readiness, verify the eventual write path with the MCP smoke flow, and run the test suite. `make compose-down` should tear the stack back down.

The supported operator modes are:

- Internal self-hosting: Compose publishes on loopback by default and host-side checks use `VOCKY_BASE_URL`.
- Public custom-domain deploy: operators can publish the app through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to the public origin such as `https://vocky.example.com`, allow that Host and Origin through `VOCKY_MCP_ALLOWED_HOSTS` and `VOCKY_MCP_ALLOWED_ORIGINS`, and require `VOCKY_MCP_AUTH_TOKEN`. Operators should also require `VOCKY_API_AUTH_TOKEN` before exposing `/api/*` and `VOCKY_ADMIN_AUTH_TOKEN` before exposing Admin REST. `make external-smoke` and `make external-verify` run the public checks against `VOCKY_EXTERNAL_BASE_URL`; the older `tailscale-smoke` and `tailscale-verify` names remain compatibility aliases.

The `/admin` shell and `/admin/assets/*` static assets, including packaged operator docs, can load without server-side auth, but protected Admin data remains unavailable unless the browser supplies the configured Admin bearer token to `/admin/api/*`.

For Cloudflare Tunnel users, the recommended public shape is a hostname-to-service mapping from `vocky.example.com` to `http://127.0.0.1:8000`, with the local Vocky process still bound behind the tunnel and no inbound origin port requirement.

## MVP Boundaries

- Self-hosted and single-tenant
- Capture ingestion is limited to MCP and server-to-server REST in the MVP; browser-direct unauthenticated ingestion is outside scope
- No automatic classification or summarization in the MVP
- Admin Web UI includes a same-origin self-hosted operator shell, dashboard metrics, recent activity, feedback list/filter/detail inspection, review-field editing, guarded delete, and in-app operator docs
- Channel handling uses the built-in nullable MVP categories `web`, `mobile`, and `support`; custom category management and deployment-configured category lists are outside the MVP
- No separate Admin REST database or MCP-specific feedback store
- No managed-cloud or multi-tenant architecture in the MVP
- No public job-status API or dashboard in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, explicit feedback value, optional comment, nullable channel category, the exact reviewed target when available, surrounding conversation messages, used context, creation time, and optional caller-provided tags or attributes.
- `message` is the required human-readable feedback summary or display text. It is not an implicit target selector.
- `conversation_id` identifies the conversation or thread that the feedback belongs to.
- `session_id` is optional runtime, browser, or user-session scope that can correlate repeated interactions without replacing `conversation_id`.
- `channel` is an optional nullable review category. New captures and Admin edits should only assign `web`, `mobile`, `support`, or `null`; blank input is normalized to `null`, and no channel is inferred by default.
- Target fields identify the exact reviewed item when known: `target_type` describes whether the target is a `message`, `conversation`, or `surface`; `target_id` stores the caller's stable identifier; `target_role` stores the reviewed message role when applicable; and `target_text` stores a snapshot of the exact reviewed text.
- `messages` stores surrounding conversation context supplied by the caller. `used_context` stores context that the agent used while producing the reviewed response.
- REST product or website feedback can omit conversation-specific fields and store page, widget, URL, account, or runtime context in `target_*`, `source_metadata`, and `attributes`.
- The storage layer only needs to support the retrieval and aggregate queries required by the MCP review tools; it does not need analytics-warehouse style modeling for the first MVP.

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

Initial indexes should cover:

- `ingested_at`
- `event_at`
- `source_product`
- `feedback_value`
- `channel`
- `conversation_id`
- `session_id`
- GIN on `tags`

The schema keeps the most important review dimensions visible as first-class columns while leaving room for source-specific metadata in JSONB fields. `channel` remains nullable `TEXT` rather than a database enum so older arbitrary channel values can stay readable and exact-filterable without destructive migration; write validation prevents new arbitrary channel values on capture and Admin edits. Target fields are captured review context in this phase; they do not add query filters or indexes.

The async capture path is layered as:

- MCP tool or REST route input normalization and error mapping
- Redis enqueue on the request path
- A dedicated worker process
- A transport-neutral feedback service
- A repository backed by SQLAlchemy async sessions
- PostgreSQL plus Alembic-managed schema

The read path reuses the same service and repository layers:

- MCP tool input normalization and error mapping for `list_feedback` and `summarize_feedback`
- Transport-neutral read methods on the feedback service
- Repository queries against `feedback_events`
- No public REST query stack in the base MVP

The Admin dashboard metrics path uses the same read layers:

- Admin REST query normalization and JSON error mapping for `GET /admin/api/feedback/metrics`
- Required timezone-aware `start_ingested_at` and `end_ingested_at` query parameters normalized to UTC
- A transport-neutral feedback service metrics method backed by repository aggregates over `feedback_events`
- UTC day bucketing with zero-filled daily buckets for the requested inclusive-start/exclusive-end ingest-time window
- Aggregate counts for total records, likes (`feedback_value = 1`), dislikes (`feedback_value = 2`), and unrated records (`feedback_value is null`)

## Query Read Model

The implemented `P3` query model uses these constraints:

- Read filters are limited to `ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `feedback_value`, `channel`, and exact single-tag membership.
- Channel read filters use exact matching after trimming blank input to absence. They should continue to support legacy stored channel strings even though new capture and Admin edit writes are limited to `web`, `mobile`, `support`, or `null`.
- Time filtering uses `ingested_at` only. `start_ingested_at` is inclusive and `end_ingested_at` is exclusive after normalization to UTC.
- `list_feedback` returns full stored records ordered newest-first by `(ingested_at desc, id desc)`.
- `list_feedback` defaults to `50` records per page and rejects values outside `1` through `100`.
- `list_feedback` pagination uses an opaque base64url-encoded JSON cursor derived from the last returned record's `ingested_at` and `id`.
- `summarize_feedback` returns only `total_count` plus UTC `daily_counts`, with zero-filled missing days inside the requested window.
- The base phase does not add full-text search, JSONB filtering, new summary dimensions, or new storage indexes beyond the `P2` baseline.
- `list_feedback` returns action fields and stored JSON context with each record so operators can inspect likes and dislikes without a separate transcript store.
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
- Return MCP capture validation failures and storage write failures as MCP tool execution errors instead of protocol errors.
- Return REST capture validation failures as `400` JSON responses.
- Reject non-null channel values outside `web`, `mobile`, and `support` on new MCP capture, REST capture, and Admin REST patch writes.
- Return MCP queue-accept failures as MCP tool execution errors instead of protocol errors.
- Return REST queue-accept failures as `503` JSON responses.
- Return query validation failures and storage read failures as MCP tool execution errors instead of protocol errors.
- Keep unknown-tool failures at the MCP protocol layer.
- Keep public REST capture and Admin REST handlers separate from MCP tool handlers while sharing validation helpers, service, queue, and repository layers where appropriate.

## Open Questions

- Auth and permission boundaries for self-hosted deployments, including whether capture and review capabilities should eventually be separated
- Whether completed-job receipts or dead-letter inspection should become part of a later public review surface
