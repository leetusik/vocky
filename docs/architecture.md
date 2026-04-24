# Architecture

## Status

This architecture is intentionally lightweight. Vocky is still pre-MVP, and the current service accepts capture work through Redis-backed queueing plus a dedicated worker while exposing MCP read tools, liked-conversation retrieval, and separate Admin REST endpoints over the same PostgreSQL feedback store.

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `pyproject.toml`: Python project metadata and dependencies
- `src/vocky/`: service code, MCP server wiring, persistence layer, and smoke script
- `alembic/` and `alembic.ini`: database migration environment
- `tests/`: validation, persistence, and MCP integration coverage
- `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile`: local run and self-hosted development workflow
- `docs/`: stable reference documents
- `works/`: active backlog, deferred queue, active work items, archives, and templates
- `scripts/`: workflow helpers

## First MVP System Shape

The first MVP should be built from these parts:

- An MCP-facing feedback capture layer that accepts explicit user action feedback from agent products
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- MCP read tools that return stored records, simple counts or trends, and liked examples for AI-agent workflows
- Dedicated Admin REST endpoints for human operators and dashboards

## Runtime Shape

The current service uses these choices:

- Python application managed with `uv`
- Application package under `src/vocky`
- A Starlette ASGI host process for MCP and health traffic
- A separate worker process for background capture persistence
- Redis-backed queueing between the app and worker
- Official MCP Python SDK `FastMCP` served by the host app at `/mcp` using Streamable HTTP
- Starlette Admin REST routes under `/admin/api/*`
- Stateless MCP operation with JSON responses enabled
- A plain `/healthz` endpoint on the same host app for smoke checks
- Optional bearer-token protection for MCP traffic when public access is enabled
- Optional bearer-token protection for Admin REST traffic when `VOCKY_ADMIN_AUTH_TOKEN` is set
- Transport-neutral service and persistence layers so the worker can reuse the same persistence path as the MCP tools

Clients should use `/mcp` as the canonical MCP endpoint. Human/operator tools should use `/admin/api/*`. The app avoids relying on a `/mcp` to `/mcp/` redirect so reverse proxies do not need to repair redirect schemes.

## Two-Track API Shape

Vocky now has two public-facing tracks over the same feedback schema:

- MCP track for AI-agent workflows: `capture_feedback`, `list_feedback`, `summarize_feedback`, and `list_liked_conversations`.
- Admin REST track for humans and dashboards: `/admin/api/feedback` list/detail plus patch/delete management endpoints.

Both tracks use the same PostgreSQL `feedback_events` table, feedback service, and repository. MCP tools should remain optimized for agent behavior; the liked-conversation MCP tool is intentionally limited to liked records for few-shot use. Admin REST is the surface that can inspect and manage all feedback records, including likes, dislikes, comments, metadata, messages, and used context.

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
- `VOCKY_ADMIN_AUTH_TOKEN`: optional bearer token required for Admin REST traffic. Public deployments that expose `/admin/api` should set it.

The supported local operator workflow adds these host-side settings:

- `TEST_DATABASE_URL`: dedicated disposable PostgreSQL database used by `make test`. It must not point at the same database as `DATABASE_URL`.
- `VOCKY_PUBLISH_HOST`: host interface Docker Compose publishes the app port on. The default is `127.0.0.1` for local-only access.
- `POSTGRES_PUBLISH_HOST`: host interface Docker Compose publishes PostgreSQL on. The default is `127.0.0.1`.
- `REDIS_PUBLISH_HOST`: host interface Docker Compose publishes Redis on. The default is `127.0.0.1`.
- `VOCKY_BASE_URL`: optional override for host-side smoke checks when the public base URL differs from `http://127.0.0.1:${VOCKY_PORT}`.
- `VOCKY_EXTERNAL_BASE_URL`: optional external URL used for public custom-domain deployments through Cloudflare Tunnel or another HTTPS reverse proxy, for example `https://vocky.example.com`.

`VOCKY_HOST` remains the application bind address inside the process. The `*_PUBLISH_HOST` variables control which host interface Docker publishes to. `VOCKY_BASE_URL` remains the local verification target, while `VOCKY_EXTERNAL_BASE_URL` is reserved for public custom-domain operator docs and client examples. Public MCP hosts must be present in `VOCKY_MCP_ALLOWED_HOSTS`; otherwise FastMCP rejects them with `421 Invalid Host header`.

The root `.env`, copied from `.env.example`, is the primary local configuration source for both Docker Compose and the Make-based host workflow. The Compose app service receives MCP and Admin auth settings from this file, including `VOCKY_MCP_AUTH_TOKEN` and `VOCKY_ADMIN_AUTH_TOKEN`. The supported self-hosted path remains Compose-first and now includes Redis plus the worker process. `make bootstrap` should bring up the service dependencies and apply migrations, `make verify` should wait for readiness and then verify the eventual write path plus the test suite, and `make compose-down` should tear the stack back down.

The supported operator modes are:

- Internal self-hosting: Compose publishes on loopback by default and host-side checks use `VOCKY_BASE_URL`.
- Public custom-domain deploy: operators can publish the app through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to the public origin such as `https://vocky.example.com`, allow that Host and Origin through `VOCKY_MCP_ALLOWED_HOSTS` and `VOCKY_MCP_ALLOWED_ORIGINS`, and require `VOCKY_MCP_AUTH_TOKEN`. Operators should also require `VOCKY_ADMIN_AUTH_TOKEN` before exposing Admin REST.

For Cloudflare Tunnel users, the recommended public shape is a hostname-to-service mapping from `vocky.example.com` to `http://127.0.0.1:8000`, with the local Vocky process still bound behind the tunnel and no inbound origin port requirement.

## MVP Boundaries

- Self-hosted and single-tenant
- MCP is the only ingestion surface in the MVP
- No automatic classification or summarization in the MVP
- No dashboard UI in the MVP
- No separate Admin REST database or MCP-specific feedback store
- No managed-cloud or multi-tenant architecture in the MVP
- No public job-status API or dashboard in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, explicit feedback value, optional comment, channel, available conversation messages, used context, creation time, and optional caller-provided tags or attributes.
- The storage layer only needs to support the retrieval and aggregate queries required by the MCP review tools; it does not need analytics-warehouse style modeling for the first MVP.

## Capture Storage Model

The completed-feedback persistence layer uses PostgreSQL with SQLAlchemy async sessions and Alembic migrations.

The primary table is `feedback_events` with this hybrid shape:

- `id UUID` primary key
- `message TEXT` not null
- `source_product TEXT` not null
- `feedback_value INTEGER` null, where `1` represents like and `2` represents dislike for explicit action feedback
- `comment TEXT` null
- `channel TEXT` null
- `source_integration TEXT` null
- `conversation_id TEXT` null
- `session_id TEXT` null
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

The schema keeps the most important review dimensions queryable as first-class columns while leaving room for source-specific metadata in JSONB fields.

The async capture path is layered as:

- MCP tool input normalization and error mapping
- Redis enqueue on the request path
- A dedicated worker process
- A transport-neutral feedback service
- A repository backed by SQLAlchemy async sessions
- PostgreSQL plus Alembic-managed schema

The read path reuses the same service and repository layers:

- MCP tool input normalization and error mapping for `list_feedback` and `summarize_feedback`
- Transport-neutral read methods on the feedback service
- Repository queries against `feedback_events`
- No separate HTTP JSON transport or parallel query stack in the base MVP

## Query Read Model

The implemented `P3` query model uses these constraints:

- Read filters are limited to `ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `feedback_value`, `channel`, and exact single-tag membership.
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
- Return capture validation failures and storage write failures as MCP tool execution errors instead of protocol errors.
- Return queue-accept failures as MCP tool execution errors instead of protocol errors.
- Return query validation failures and storage read failures as MCP tool execution errors instead of protocol errors.
- Keep unknown-tool failures at the MCP protocol layer.
- Keep Admin REST handlers separate from MCP tool handlers while sharing the transport-neutral service and repository layers.

## Open Questions

- Auth and permission boundaries for self-hosted deployments, including whether capture and review capabilities should eventually be separated
- Whether completed-job receipts or dead-letter inspection should become part of a later public review surface
