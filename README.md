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

- Accept feedback events from agent interactions through MCP without blocking on database writes
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

- MCP feedback capture is implemented through the `capture_feedback` tool and now accepts requests quickly through a Redis-backed background worker path.
- MCP review/query tools are implemented through `list_feedback` and `summarize_feedback`.
- Completed feedback events persist to PostgreSQL with Alembic migrations.
- Self-hosted runtime now includes PostgreSQL, Redis, the MCP app process, and a dedicated worker process.
- The project is still pre-MVP and the contracts should be treated as early-stage.

## Local Development

The supported local workflow is Compose-first and uses the copied repo-root `.env` as the shared configuration source for Docker Compose, Alembic, smoke checks, and pytest.

1. Copy the example environment:
   `cp .env.example .env`
2. Bootstrap the stack on the default local ports from `.env`:
   `make bootstrap`
3. Verify the running stack:
   `make verify`
4. Inspect logs if needed:
   `make compose-logs`
5. Stop the stack when finished:
   `make compose-down`

The default `.env` values publish the app at `http://127.0.0.1:8000`, PostgreSQL at `127.0.0.1:55432`, and Redis at `127.0.0.1:56379`. Those loopback-only defaults come from `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST`, which all default to `127.0.0.1`.

`make bootstrap` runs `make sync`, `make compose-up`, and the explicit migration step `make migrate`. The Compose stack now includes `redis`, `postgres`, `app`, and `worker`.

`make verify` waits for `GET /healthz`, then runs the MCP smoke flow and the full pytest suite. The smoke path now verifies that an accepted `capture_feedback` call becomes queryable only after the worker persists it.

`TEST_DATABASE_URL` must point at a separate disposable database. `make test` refuses to run if it matches `DATABASE_URL`, and the pytest fixtures reset only the database named in `TEST_DATABASE_URL`.

If you need different host ports or interfaces, edit `.env` before you run the workflow. `VOCKY_PORT`, `POSTGRES_PORT`, and `REDIS_PORT` change the published ports. `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST` change which host interface Docker publishes on. `VOCKY_BASE_URL` remains the local smoke-check target, and `VOCKY_EXTERNAL_BASE_URL` is optional for remote access through Tailscale Serve or another reverse proxy.

Granular fallback commands remain available:

- `make sync`
- `make compose-up`
- `make migrate`
- `make smoke`
- `make test`
- `make compose-down`

The smoke target checks `GET /healthz` plus MCP `capture_feedback`, `list_feedback`, and `summarize_feedback`, and it waits for readiness before the MCP calls.

Optional external-access helpers are also available for operators who use Tailscale:

- `make tailscale-serve`
- `make tailscale-serve-status`
- `make tailscale-serve-reset`
- `make tailscale-smoke`
- `make tailscale-verify`

These helpers are not part of the required local workflow. They only use `VOCKY_EXTERNAL_BASE_URL` when you want to verify the service through an external URL.

## Running The App Directly

The supported self-hosted flow is Compose-first. If PostgreSQL and Redis are already running outside Compose, point `DATABASE_URL` and `REDIS_URL` at them and start both processes:

`uv run vocky`

`uv run vocky-worker`

The Starlette host app exposes:

- `GET /healthz`
- MCP Streamable HTTP at `/mcp`

Some clients may follow the framework redirect from `/mcp` to `/mcp/` automatically.

There is no dashboard UI in the current MVP. Vocky is an MCP service plus background worker, not a browser app.

## Self-Hosted Access Modes

Vocky supports two clean operator modes:

- Local or private self-hosting: keep the default `*_PUBLISH_HOST=127.0.0.1` values and use `VOCKY_BASE_URL` for host-side smoke and verification.
- Optional Tailscale self-hosting: run `make tailscale-serve`, set `VOCKY_EXTERNAL_BASE_URL`, and let remote devices reach the service through that external URL.

For Tailscale users, the recommended `VOCKY_EXTERNAL_BASE_URL` is your node's MagicDNS HTTPS name, for example `https://<your-node>.<your-tailnet>.ts.net`. Prefer that over a raw Tailscale IP so the remote URL stays stable and certificate-friendly.

## MCP Surface

The implemented MCP tools are:

- `capture_feedback`: validate one feedback event, enqueue it for background persistence, and return a receipt with `request_id`, `accepted_at`, and `status="accepted"`.
- `list_feedback`: retrieve stored feedback records with ingest-time filters, exact tag matching, newest-first ordering, and opaque cursor pagination. The default page size is `50` and the maximum is `100`.
- `summarize_feedback`: return `total_count` plus zero-filled UTC `daily_counts` for an explicit ingest-time window and the supported review filters.

`capture_feedback` success means the request was accepted for background processing, not that the feedback record is immediately queryable. `list_feedback` and `summarize_feedback` surface completed records only after the worker persists them.

## Self-Hosted Usage

For local or private-network access, point your MCP-capable client or agent runtime at:

`http://<host>:<port>/mcp`

If you expose the service through Tailscale Serve, point remote devices at:

`https://<your-node>.<your-tailnet>.ts.net/mcp`

In the Tailscale case, set `VOCKY_EXTERNAL_BASE_URL=https://<your-node>.<your-tailnet>.ts.net` in `.env` and use `make tailscale-serve-status`, `make tailscale-smoke`, or `make tailscale-verify` when you want to check the externally reachable path.

Example Python client:

```python
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with streamable_http_client("http://127.0.0.1:8000/mcp") as streams:
        read_stream, write_stream, _ = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "capture_feedback",
                {
                    "message": "Users keep asking for CSV export",
                    "source": {"product": "my-agent", "integration": "web-chat"},
                    "conversation_id": "conv_123",
                    "session_id": "sess_123",
                    "tags": ["feature-request"],
                    "source_metadata": {"channel": "support"},
                },
            )
            print(result.structuredContent)
```

The example above uses the default local loopback URL. If you connect through Tailscale or another reverse proxy, replace it with `${VOCKY_EXTERNAL_BASE_URL}/mcp`.

The worker persists accepted jobs in the background. If you need to verify that the record landed, poll `list_feedback` or `summarize_feedback` using your own source or session filters.

Example Caddy reverse proxy:

```caddy
vocky.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

If you publish Vocky through Caddy or another reverse proxy instead of Tailscale Serve, set `VOCKY_EXTERNAL_BASE_URL` to that external `https://...` URL and keep `VOCKY_BASE_URL` pointed at the local verification target.

## License

Vocky is licensed under the GNU Affero General Public License v3.0. See [LICENSE](./LICENSE).
