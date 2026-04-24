# vocky

Feedback MCP for agents. Turn customer conversations into structured voice-of-customer signals.

Vocky is pre-MVP, but the first runnable feedback capture and review service is now implemented.

## What Vocky Is

Vocky is a Model Context Protocol (MCP)-based feedback layer for agent products. The idea is simple: when users talk to an AI agent, they often reveal bugs, friction points, requests, and positive reactions. Vocky aims to capture those moments, structure them, and make them useful.

The name comes from VoC, short for voice of customer.

## Why It Exists

- Agent conversations already contain valuable product feedback.
- Most of that feedback gets lost in logs, transcripts, or support noise.
- Teams need a simple way to turn conversational feedback into product insight.

## What It Will Do First

- Capture feedback events from agent interactions through MCP
- Store raw feedback with basic metadata for later review
- Expose minimal MCP review/query tools for retrieving records and simple counts
- Run as a self-hosted, single-tenant MVP

## What The First MVP Will Not Do

- Automatic classification or taxonomy assignment
- A dashboard UI
- Non-MCP ingestion paths
- Managed multi-tenant SaaS features

## Open Source + Managed Direction

Vocky is intended to follow a light open-core direction: a community, self-hostable base and a managed cloud offering later. The goal is to keep the core transparent and usable while building a hosted product around convenience, operations, and richer workflows.

## Current Status

- MCP feedback capture is implemented through the `capture_feedback` tool.
- MCP review/query tools are implemented through `list_feedback` and `summarize_feedback`.
- Feedback events persist to PostgreSQL with Alembic migrations.
- The project is still pre-MVP and the contracts should be treated as early-stage.

## Local Development

The repo uses `uv` for Python workflows and Docker Compose for the app plus PostgreSQL stack.

1. Copy the example environment:
   `cp .env.example .env`
2. Sync the local Python environment:
   `make sync`
3. Start the stack:
   `POSTGRES_PORT=55432 VOCKY_PORT=8011 make compose-up`
4. Apply the migration:
   `DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky make migrate`
5. Run the test suite against the dedicated test database:
   `DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky TEST_DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky_test make test`
6. Run the smoke check:
   `APP_BASE_URL=http://127.0.0.1:8011 make smoke`
7. Stop the stack when finished:
   `POSTGRES_PORT=55432 VOCKY_PORT=8011 make compose-down`

The pytest fixtures reset only the database named in `TEST_DATABASE_URL`. The smoke target checks `GET /healthz` plus MCP `capture_feedback`, `list_feedback`, and `summarize_feedback`.

## Running The App Directly

If PostgreSQL is already running outside Compose, point `DATABASE_URL` at it and start the service with:

`uv run vocky`

The Starlette host app exposes:

- `GET /healthz`
- MCP Streamable HTTP at `/mcp`

Some clients may follow the framework redirect from `/mcp` to `/mcp/` automatically.

## MCP Surface

The implemented MCP tools are:

- `capture_feedback`: store one feedback event with source metadata, optional conversation/session context, optional event time, tags, and arbitrary JSON metadata.
- `list_feedback`: retrieve stored feedback records with ingest-time filters, exact tag matching, newest-first ordering, and opaque cursor pagination. The default page size is `50` and the maximum is `100`.
- `summarize_feedback`: return `total_count` plus zero-filled UTC `daily_counts` for an explicit ingest-time window and the supported review filters.

## License

Vocky is licensed under the GNU Affero General Public License v3.0. See [LICENSE](./LICENSE).
