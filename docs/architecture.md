# Architecture

## Status

This architecture is intentionally lightweight. Vocky is still pre-MVP, and the first runnable capture service is now implemented against the runtime and storage shape defined in `P2`.

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

- An MCP-facing feedback capture layer that accepts feedback events from agent products
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- A minimal review/query API that returns stored records and simple counts or trends

## Runtime Shape

The current capture service uses these choices:

- Python application managed with `uv`
- Application package under `src/vocky`
- A single Starlette ASGI host process
- Official MCP Python SDK `FastMCP` mounted on the host app at `/mcp` using Streamable HTTP
- Stateless MCP operation with JSON responses enabled
- A plain `/healthz` endpoint on the same host app for smoke checks
- Transport-neutral service and persistence layers so `P3` can add the review/query HTTP JSON surface to the same process

In the current Starlette mount setup, clients connect to `/mcp`; some will transparently follow a redirect to `/mcp/`.

## Configuration Surface

The initial service configuration surface is intentionally small:

- `DATABASE_URL`: PostgreSQL connection URL for the async SQLAlchemy engine and Alembic migrations
- `VOCKY_HOST`: application bind host
- `VOCKY_PORT`: application bind port
- `VOCKY_LOG_LEVEL`: application log level

Local development uses Docker Compose for the app and PostgreSQL together, while Python commands continue to run through `uv`.

## MVP Boundaries

- Self-hosted and single-tenant
- MCP is the only ingestion surface in the MVP
- No automatic classification or summarization in the MVP
- No dashboard UI in the MVP
- No managed-cloud or multi-tenant architecture in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, available conversation context, creation time, and optional caller-provided tags or attributes.
- The storage layer only needs to support the retrieval and aggregate queries required by the review/query API; it does not need analytics-warehouse style modeling for the first MVP.

## Capture Storage Model

The implemented persistence layer uses PostgreSQL with SQLAlchemy async sessions and Alembic migrations.

The primary table is `feedback_events` with this hybrid shape:

- `id UUID` primary key
- `message TEXT` not null
- `source_product TEXT` not null
- `source_integration TEXT` null
- `conversation_id TEXT` null
- `session_id TEXT` null
- `event_at TIMESTAMPTZ` null
- `ingested_at TIMESTAMPTZ` not null
- `tags TEXT[]` not null with default empty array
- `source_metadata JSONB` not null with default empty object
- `attributes JSONB` not null with default empty object

Initial indexes should cover:

- `ingested_at`
- `event_at`
- `source_product`
- `conversation_id`
- `session_id`
- GIN on `tags`

The schema keeps the most important review dimensions queryable as first-class columns while leaving room for source-specific metadata in JSONB fields.

The capture write path is layered as:

- MCP tool input normalization and error mapping
- A transport-neutral feedback service
- A repository backed by SQLAlchemy async sessions
- PostgreSQL plus Alembic-managed schema

## Architecture Constraints

- Keep public contracts explicit in `docs/api.md`.
- Keep durable technical context here, not in transient work items.
- Keep execution history under `works/`.
- Keep currently scheduled work in `works/backlog.md` and intentionally deferred work in `works/deferred.md`.
- Prefer small slices and explicit review loops over large untracked changes.
- Keep the capture service runnable as a single self-hosted process for the MVP.
- Normalize capture timestamps to UTC before persistence.
- Return capture validation failures and storage write failures as MCP tool execution errors instead of protocol errors.
- Keep unknown-tool failures at the MCP protocol layer.

## Open Questions

- Auth and permission boundaries for self-hosted deployments
- Which query filters and aggregate dimensions should be included in the first implemented API version
