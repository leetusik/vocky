# vocky

Feedback capture and review for agents. Turn customer conversations into structured voice-of-customer signals.

Vocky is pre-MVP, but the first runnable feedback capture and review service is now implemented.

## What Vocky Is

Vocky is a feedback layer for agent products, with MCP tools for agent workflows and a server-to-server REST capture endpoint for normal product integrations. The idea is simple: when users talk to an AI agent, they often reveal bugs, friction points, requests, and positive reactions. Vocky aims to capture those moments, structure them, and make them useful.

The name comes from VoC, short for voice of customer.

## Why It Exists

- Agent conversations already contain valuable product feedback.
- Most of that feedback gets lost in logs, transcripts, or support noise.
- Teams need a simple way to turn conversational feedback into product insight.

## What The Current Pre-MVP Does

- Accept explicit user action feedback from agent interactions through MCP or server-to-server REST without blocking on database writes
- Store like/dislike values, optional comments, exact target context, conversation context, and metadata for later review
- Expose minimal MCP review/query tools for retrieving records and simple counts
- Retrieve liked conversations through MCP for AI-agent few-shot use
- Expose separate Admin REST endpoints for human/operator review and management
- Provide a self-hosted Admin Web UI served by the Vocky app, including dashboard metrics, feedback list/filter/detail/edit/delete workflows, and in-app operator documentation for API/auth, REST capture try-it, and self-hosting setup
- Support nullable channel category assignment with the built-in MVP categories `web`, `mobile`, and `support`
- Run as a self-hosted, single-tenant MVP

## What The First MVP Will Not Do

- Automatic classification or taxonomy assignment
- A production-grade analytics workspace or managed feedback operations suite
- Browser-direct unauthenticated ingestion
- Public REST review, query, summary, or management endpoints outside Admin REST
- Managed multi-tenant SaaS features

## Open Source + Managed Direction

Vocky is intended to follow a light open-core direction: a community, self-hostable base and a managed cloud offering later. The goal is to keep the core transparent and usable while building a hosted product around convenience, operations, and richer workflows.

## Current Status

- MCP feedback capture is implemented through the `capture_feedback` tool and now accepts explicit action feedback plus optional exact-target context quickly through a Redis-backed background worker path.
- Web/product feedback capture is implemented through `POST /api/feedback` for server-to-server integrations that cannot use MCP.
- MCP review/query tools are implemented through `list_feedback` and `summarize_feedback`.
- AI-agent liked conversation retrieval is implemented through `list_liked_conversations`.
- Human/operator review and management are available through separate Admin REST endpoints under `/admin/api`.
- A same-origin Admin Web UI is available under `/admin` for self-hosted operators, with dashboard metrics, feedback review management, and packaged in-app documentation for API/auth, REST capture try-it, local hosting, and public custom-domain setup.
- Completed feedback events persist to PostgreSQL with Alembic migrations.
- Self-hosted runtime now includes PostgreSQL, Redis, the MCP app process, and a dedicated worker process.
- The project is still pre-MVP and the contracts should be treated as early-stage.

## Local Development

The supported local workflow is Compose-first and uses the copied repo-root `.env` as the shared configuration source for Docker Compose, Alembic, smoke checks, and pytest.

1. Copy the example environment:
   `cp .env.example .env`
2. Bootstrap the stack on the default local ports from `.env`:
   `make bootstrap`
3. Verify the package and running stack:
   `make verify`
4. Inspect logs if needed:
   `make compose-logs`
5. Stop the stack when finished:
   `make compose-down`

The default `.env` values publish the app at `http://127.0.0.1:8000`, PostgreSQL at `127.0.0.1:55432`, and Redis at `127.0.0.1:56379`. Those loopback-only defaults come from `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST`, which all default to `127.0.0.1`.

Open the Admin Web UI at `http://127.0.0.1:8000/admin`. The Dashboard view shows feedback metrics, the Feedback view supports list/filter/detail/edit/delete review workflows, and the Docs view includes the in-app operator reference for API/auth, REST capture try-it, local self-hosting, and public custom-domain setup. If `VOCKY_ADMIN_AUTH_TOKEN` is set, paste that token into the Admin UI token field before checking protected Admin REST data. The Docs REST capture try-it form uses the separate `VOCKY_API_AUTH_TOKEN` value when `/api/*` auth is configured.

`make bootstrap` runs `make sync`, `make compose-up`, the explicit migration step `make migrate`, and a final readiness check. The Compose stack includes `redis`, `postgres`, `app`, and `worker`. The app and worker images install dependencies during the Docker build and run with `uv run --no-sync` at container startup.

`make verify` builds a fresh wheel and checks the packaged Admin UI assets, waits for `GET /healthz`, runs the MCP smoke flow, and then runs the full pytest suite. The smoke path verifies that an accepted `capture_feedback` call becomes queryable only after the worker persists it.

`TEST_DATABASE_URL` must point at a separate disposable database. `make test` refuses to run if it matches `DATABASE_URL`, and the pytest fixtures reset only the database named in `TEST_DATABASE_URL`.

If you need different host ports or interfaces, edit `.env` before you run the workflow. `VOCKY_PORT`, `POSTGRES_PORT`, and `REDIS_PORT` change the published ports. `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST` change which host interface Docker publishes on. `VOCKY_BASE_URL` remains the local smoke-check target, and `VOCKY_EXTERNAL_BASE_URL` is optional for public custom-domain access through Cloudflare Tunnel or another HTTPS reverse proxy.

Public custom-domain access has these additional settings:

- `VOCKY_MCP_ALLOWED_HOSTS`: comma-separated public Host headers accepted by FastMCP DNS rebinding protection, for example `vocky.example.com`.
- `VOCKY_MCP_ALLOWED_ORIGINS`: comma-separated browser Origin values, for example `https://vocky.example.com`.
- `VOCKY_MCP_AUTH_TOKEN`: bearer token required for `/mcp` when set. Set this before exposing Vocky publicly.
- `VOCKY_API_AUTH_TOKEN`: bearer token required for `/api/*` when set. Set this before exposing REST capture publicly.
- `VOCKY_ADMIN_AUTH_TOKEN`: bearer token required for `/admin/api/*` when set. Set this before exposing Admin REST endpoints.

Granular fallback commands remain available:

- `make sync`
- `make package-check`
- `make compose-up`
- `make migrate`
- `make smoke`
- `make test`
- `make compose-down`

The smoke target checks `GET /healthz` plus MCP `capture_feedback`, `list_feedback`, and `summarize_feedback`, and it waits for readiness before the MCP calls. If `VOCKY_MCP_AUTH_TOKEN` is set, the smoke MCP client sends `Authorization: Bearer <token>`.

## Running The App Directly

The supported self-hosted flow is Compose-first. If PostgreSQL and Redis are already running outside Compose, point `DATABASE_URL` and `REDIS_URL` at them and start both processes:

`uv run vocky`

`uv run vocky-worker`

The Starlette host app exposes:

- `GET /healthz`
- Public REST capture at `POST /api/feedback`
- Admin REST under `/admin/api/*`
- Admin Web UI under `/admin`
- MCP Streamable HTTP at `/mcp`

Use `/mcp` exactly as the canonical MCP endpoint.

The Admin Web UI includes dashboard metrics, recent activity, feedback list/filter/detail inspection, review-field editing, guarded delete, and in-app documentation pages. Browser editing is intentionally limited to `feedback_value`, `comment`, `channel`, and `tags`; use Admin REST directly for broader patchable metadata fields. The Docs view can send a same-origin try request to `POST /api/feedback`; a successful request is a real capture event that is queued for worker persistence.

`channel` is optional and defaults to no category when omitted or blank. New capture and Admin edit writes accept only `web`, `mobile`, `support`, or `null`; older stored channel values remain visible and exact-filterable for review.

## Access Modes

Vocky supports two clean operator modes:

- Internal self-hosting: keep the default `*_PUBLISH_HOST=127.0.0.1` values, use `VOCKY_BASE_URL` for host-side smoke and verification, and connect from the same machine or trusted private network.
- Public custom-domain deploy: publish Vocky through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL`, allow the public Host and Origin, and require `VOCKY_MCP_AUTH_TOKEN`. Set `VOCKY_API_AUTH_TOKEN` before exposing `/api/*`, set `VOCKY_ADMIN_AUTH_TOKEN` before exposing `/admin/api/*`, and use `make external-verify` for public readiness and smoke checks.

For public custom-domain access, set `VOCKY_EXTERNAL_BASE_URL` to the external HTTPS origin after DNS and proxying are active.

## Public Custom Domain With Cloudflare

Use Cloudflare Tunnel for `vocky.example.com`. This keeps the Vocky origin private: `cloudflared` opens outbound tunnel connections to Cloudflare, and Cloudflare forwards public HTTPS traffic to your local `http://127.0.0.1:8000` service.

1. Add your apex domain to Cloudflare:
   - In Cloudflare, choose **Onboard a domain** and enter your apex domain, for example `example.com`.
   - Use the normal full DNS setup and choose a plan.
   - Review any DNS records Cloudflare imports. Do not delete existing email records unless you know they are unused.
2. Point your registrar at Cloudflare:
   - In your registrar, find the domain nameserver settings.
   - Replace the current nameservers with the two Cloudflare nameservers assigned to your domain.
   - If DNSSEC is enabled at your registrar, disable it before the nameserver change, then re-enable DNSSEC from Cloudflare after the zone is active.
   - Nameserver changes can take time to propagate; Cloudflare will show when the zone is active.
3. Create and route the tunnel:
   - Install `cloudflared` on the machine running Vocky.
   - Run `cloudflared tunnel login`.
   - Run `cloudflared tunnel create vocky`.
   - Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <Tunnel-UUID>
credentials-file: /Users/<you>/.cloudflared/<Tunnel-UUID>.json

ingress:
  - hostname: vocky.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

4. Create the DNS route and run the tunnel:

```sh
cloudflared tunnel route dns vocky vocky.example.com
cloudflared tunnel ingress validate
cloudflared tunnel run vocky
```

5. Configure Vocky for public access in `.env`:

```env
VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com
VOCKY_MCP_ALLOWED_HOSTS=vocky.example.com
VOCKY_MCP_ALLOWED_ORIGINS=https://vocky.example.com
VOCKY_MCP_AUTH_TOKEN=<long-random-secret>
VOCKY_API_AUTH_TOKEN=<another-long-random-secret>
VOCKY_ADMIN_AUTH_TOKEN=<different-long-random-secret>
```

6. Restart the Vocky app after changing `.env`, then verify:

```sh
make external-verify
```

If you prefer not to store the external origin in `.env`, pass it on the command line:

```sh
make external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com
```

Public MCP clients should use `https://vocky.example.com/mcp` with `Authorization: Bearer <token>`.
Public REST capture clients should use `https://vocky.example.com/api/feedback` with `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`.
Public Admin REST requests should use `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>` when `/admin/api/*` is exposed.

`make external-smoke` runs only the public MCP smoke flow, while `make external-verify` waits for public health first and then runs the same smoke flow. Existing `tailscale-smoke` and `tailscale-verify` targets remain as aliases for the generic external targets.

## MCP Surface

The implemented MCP tools are:

- `capture_feedback`: validate one feedback event, including optional action feedback and target fields, enqueue it for background persistence, and return a receipt with `request_id`, `accepted_at`, and `status="accepted"`.
- `list_feedback`: retrieve stored feedback records with ingest-time, source, action value, channel, exact tag, newest-first ordering, and opaque cursor pagination. The default page size is `50` and the maximum is `100`.
- `summarize_feedback`: return `total_count` plus zero-filled UTC `daily_counts` for an explicit ingest-time window and the supported review filters.
- `list_liked_conversations`: retrieve only liked conversations with stored messages and used context for AI-agent few-shot use.

`capture_feedback` success means the request was accepted for background processing, not that the feedback record is immediately queryable. `list_feedback` and `summarize_feedback` surface completed records only after the worker persists them.

For client integration guidance, see [docs/action-feedback-integration.md](docs/action-feedback-integration.md).

## Web Capture REST Surface

Use REST capture from server-side web or product code when the integration is not an MCP client. REST uses the same core capture fields as MCP, but it is intended for broader website and product feedback. For page, widget, or product-surface feedback, set `target_type` to `surface` when the exact surface is known and put product-specific context in `source_metadata` or `attributes`.

The optional `channel` field is a nullable review category. Omit it by default unless the caller can explicitly assign `web`, `mobile`, or `support`.

Implemented endpoint:

- `POST /api/feedback`

Example REST surface-feedback capture:

```sh
curl -X POST "http://127.0.0.1:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>" \
  -d '{
    "message": "Pricing page feedback button was hard to find",
    "source": {"product": "marketing-site", "integration": "web-backend"},
    "comment": "I wanted to send feedback but did not notice the button",
    "channel": "web",
    "session_id": "sess_123",
    "target_type": "surface",
    "target_id": "pricing-page-feedback-button",
    "target_text": "Feedback",
    "event_at": "2026-04-24T09:30:00Z",
    "tags": ["website", "pricing"],
    "source_metadata": {"path": "/pricing", "referrer": "/"},
    "attributes": {"plan": "team", "locale": "en-US"}
  }'
```

Omit the bearer header only when `VOCKY_API_AUTH_TOKEN` is unset in a trusted local or private deployment. REST capture is ingestion-only; use MCP read tools or Admin REST for review.

The Admin Docs REST capture try-it form exercises this same endpoint from the browser for self-hosted operators. Enter `VOCKY_API_AUTH_TOKEN` there only when `/api/*` auth is configured; that API token is separate from the Admin token and is kept only in the browser session. The try flow does not create a public REST review, query, job-status, or management API, and successful tries create normal queued feedback records.

## Admin REST Surface

The Admin REST API is separate from MCP and is intended for human operators, scripts, dashboards, and the packaged Admin Web UI. It can query and manage all feedback records, including likes, dislikes, comments, target context, metadata, messages, and used context.

Implemented endpoints:

- `GET /admin/api/healthz`
- `GET /admin/api/feedback`
- `GET /admin/api/feedback/metrics`
- `GET /admin/api/feedback/{feedback_id}`
- `PATCH /admin/api/feedback/{feedback_id}`
- `DELETE /admin/api/feedback/{feedback_id}`

Set `VOCKY_ADMIN_AUTH_TOKEN` before exposing `/admin/api/*` outside a trusted local/private environment.

The Admin Web UI consumes these endpoints same-origin. Its edit form only patches `feedback_value`, `comment`, `channel`, and `tags`; captured target fields, messages, used context, `source_metadata`, and `attributes` remain read-only in the browser.

Admin REST patch writes apply the same channel category rule as capture: blank clears to `null`, and non-null values must be `web`, `mobile`, or `support`. Admin list filters still exact-match stored channel text, including older legacy values.

## Self-Hosted Usage

For local or private-network access, point your MCP-capable client or agent runtime at:

`http://<host>:<port>/mcp`

For server-to-server REST capture, post to:

`http://<host>:<port>/api/feedback`

For public custom-domain access, point clients at:

`https://vocky.example.com/mcp`

REST capture clients should use:

`https://vocky.example.com/api/feedback`

Set `VOCKY_EXTERNAL_BASE_URL=https://<external-host>` in `.env` when you want clients or operator scripts to refer to the public origin.

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
                    "feedback_value": 1,
                    "comment": "Helpful answer",
                    "channel": "web",
                    "conversation_id": "conv_123",
                    "session_id": "sess_123",
                    "target_type": "message",
                    "target_id": "msg_assistant_789",
                    "target_role": "assistant",
                    "target_text": "Yes, use the export menu.",
                    "messages": [
                        {"role": "user", "content": "Can I export this as CSV?"},
                        {"role": "assistant", "content": "Yes, use the export menu."},
                    ],
                    "used_context": [
                        {"source": "help-center", "snippet": "CSV export is available."}
                    ],
                    "tags": ["feature-request"],
                    "source_metadata": {"channel": "support"},
                },
            )
            print(result.structuredContent)
```

The example above uses the default local loopback URL. If you connect through a public custom domain or another reverse proxy, replace it with `${VOCKY_EXTERNAL_BASE_URL}/mcp`.

For public token-protected access, pass a bearer header through your MCP client's HTTP client. With the MCP Python SDK:

```python
import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with httpx.AsyncClient(
        headers={"Authorization": "Bearer <VOCKY_MCP_AUTH_TOKEN>"}
    ) as http_client:
        async with streamable_http_client(
            "https://vocky.example.com/mcp",
            http_client=http_client,
        ) as streams:
            read_stream, write_stream, _ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                print([tool.name for tool in tools.tools])
```

The worker persists accepted jobs in the background. If you need to verify that the record landed, poll `list_feedback` or `summarize_feedback` using your own source or session filters.

Example Caddy reverse proxy:

```caddy
vocky.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

If you publish Vocky through Caddy or another reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to that external `https://...` URL, keep `VOCKY_BASE_URL` pointed at the local verification target, and use `make external-verify` for the public path.

## License

Vocky is licensed under the GNU Affero General Public License v3.0. See [LICENSE](./LICENSE).
