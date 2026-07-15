# vocky

Human-triggered feedback capture and review. Turn product and customer feedback moments into structured voice-of-customer signals.

Vocky is pre-MVP, but the first runnable feedback capture and review service is now implemented.

## What Vocky Is

Vocky is a feedback layer for products and the surfaces around them. Server-to-server REST capture records explicit product or UI feedback actions, such as page feedback, widget feedback, surveys, ratings, and like/dislike controls. The idea is simple: when users react to product surfaces, they often reveal bugs, friction points, requests, and positive reactions. Vocky aims to capture those moments, structure them, and make them useful for operator review.

The name comes from VoC, short for voice of customer.

## Why It Exists

- Product surfaces and customer interactions already contain valuable feedback.
- Most of that feedback gets lost in logs, support noise, or one-off spreadsheets.
- Teams need a simple way to turn product feedback into product insight.

A product's own backend can forward feedback moments to Vocky over REST, so capture stays a deliberate, server-to-server product action rather than a scattered afterthought.

## What The Current Pre-MVP Does

- Accept explicit product/UI-triggered feedback through server-to-server REST without blocking on database writes
- Persist accepted events asynchronously through a Redis-backed background worker
- Store like/dislike values, optional comments, caller-owned user identity, trigger context, exact target context, conversation context, and metadata for later review
- Expose a scoped end-user read (`GET /api/feedback`) that returns a user's own records, operator comments, and attachment links
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

- Web/product feedback capture is implemented through `POST /api/feedback` for server-to-server product or UI integrations that send explicit user-triggered feedback, including optional user identity, trigger context, and exact-target context, quickly through a Redis-backed background worker path.
- Accepted capture events are queued and persisted by a dedicated background worker rather than written on the request path.
- A scoped end-user read is implemented through `GET /api/feedback?user_id=<id>&source_product=<product>`, returning that user's own records plus operator comments and attachment links.
- Human/operator review and management are available through separate Admin REST endpoints under `/admin/api`.
- A same-origin Admin Web UI is available under `/admin` for self-hosted operators, with dashboard metrics, feedback review management, and packaged in-app documentation for API/auth, REST capture try-it, local hosting, and public custom-domain setup.
- Completed feedback events persist to PostgreSQL with Alembic migrations.
- Self-hosted runtime now includes PostgreSQL, Redis, the app process, and a dedicated worker process.
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

`make verify` builds a fresh wheel and checks the packaged Admin UI assets, waits for `GET /healthz`, runs the REST smoke flow, and then runs the full pytest suite. The smoke path posts a feedback event to `POST /api/feedback` and confirms it becomes queryable through the scoped `GET /api/feedback` only after the worker persists it.

`TEST_DATABASE_URL` must point at a separate disposable database. `make test` refuses to run if it matches `DATABASE_URL`, and the pytest fixtures reset only the database named in `TEST_DATABASE_URL`.

If you need different host ports or interfaces, edit `.env` before you run the workflow. `VOCKY_PORT`, `POSTGRES_PORT`, and `REDIS_PORT` change the published ports. `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST` change which host interface Docker publishes on. `VOCKY_BASE_URL` remains the local smoke-check target, and `VOCKY_EXTERNAL_BASE_URL` is optional for public custom-domain access through Cloudflare Tunnel or another HTTPS reverse proxy.

Public custom-domain access has these additional settings:

- `VOCKY_API_AUTH_TOKEN`: bearer token required for `/api/*` when set. Set this before exposing REST capture and reads publicly.
- `VOCKY_ADMIN_AUTH_TOKEN`: bearer token required for `/admin/api/*` when set. Set this before exposing Admin REST endpoints.

Granular fallback commands remain available:

- `make sync`
- `make package-check`
- `make compose-up`
- `make migrate`
- `make smoke`
- `make test`
- `make compose-down`

The smoke target checks `GET /healthz`, then posts a feedback event to `POST /api/feedback` and polls the scoped `GET /api/feedback` until the worker-persisted record appears; it waits for readiness before the REST calls. If `VOCKY_API_AUTH_TOKEN` is set, the smoke client sends `Authorization: Bearer <token>`.

## Running The App Directly

The supported self-hosted flow is Compose-first. If PostgreSQL and Redis are already running outside Compose, point `DATABASE_URL` and `REDIS_URL` at them and start both processes:

`uv run vocky`

`uv run vocky-worker`

The Starlette host app exposes:

- `GET /healthz`
- Public REST capture at `POST /api/feedback`
- Scoped end-user read at `GET /api/feedback`
- Admin REST under `/admin/api/*`
- Admin Web UI under `/admin`

The Admin Web UI includes dashboard metrics, recent activity, feedback list/filter/detail inspection, review-field editing, guarded delete, and in-app documentation pages. Browser editing is intentionally limited to `feedback_value`, `comment`, `channel`, and `tags`; use Admin REST directly for broader patchable metadata fields. The Docs view can send a same-origin try request to `POST /api/feedback`; a successful request is a real capture event that is queued for worker persistence.

`channel` is optional and defaults to no category when omitted or blank. New capture and Admin edit writes accept only `web`, `mobile`, `support`, or `null`; older stored channel values remain visible and exact-filterable for review.

`target_type` is optional captured target context and the review discriminator for separating message, conversation, and surface feedback. Use `message` when the user judged a specific agent message, `conversation` when the user judged a whole thread, and `surface` when the user judged a page, widget, screen, or other product UI. Older records with no `target_type` remain visible in unfiltered review lists; they are excluded only when an exact `target_type` filter is supplied.

`user_id` is optional caller-owned identity for the product user or account member associated with the event. It does not replace `session_id`, which remains browser, runtime, or session correlation. Trigger fields explain why capture happened: use `trigger_type` for `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, or `other`; use `trigger_message` for button text, prompt copy, survey question, or action label; and use `trigger_metadata` for structured details such as control IDs, rating scale, selected option, or redacted runtime context.

For conversation or process context, send review-safe summaries, retrieved snippets, tool traces, prompt summaries, and redacted execution metadata. Do not send raw hidden chain-of-thought or private model reasoning.

## Access Modes

Vocky supports two clean operator modes:

- Internal self-hosting: keep the default `*_PUBLISH_HOST=127.0.0.1` values, use `VOCKY_BASE_URL` for host-side smoke and verification, and connect from the same machine or trusted private network.
- Public custom-domain deploy: publish Vocky through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL`, set `VOCKY_API_AUTH_TOKEN` before exposing `/api/*`, set `VOCKY_ADMIN_AUTH_TOKEN` before exposing `/admin/api/*`, and use `make external-verify` for public readiness and smoke checks.

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

Public REST capture clients should use `https://vocky.example.com/api/feedback` with `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`.
Public Admin REST requests should use `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>` when `/admin/api/*` is exposed.

`make external-smoke` runs only the public REST smoke flow, while `make external-verify` waits for public health first and then runs the same smoke flow.

## Web Capture REST Surface

Use REST capture from trusted server-side web or product code when the user explicitly triggers feedback in the product UI. It is intended for product and website feedback actions such as page feedback, widget feedback, surveys, ratings, and like/dislike controls. Send `user_id` when the backend has a stable product user identifier, send trigger fields for the control or workflow that caused capture, and set `target_type` to `surface` when the exact page, widget, or product surface is known. Put source-specific URL, page, widget, and backend context in `source_metadata`, and product dimensions such as plan, locale, or rollout cohort in `attributes`.

The optional `channel` field is a nullable review category. Omit it by default unless the caller can explicitly assign `web`, `mobile`, or `support`.

Implemented endpoint:

- `POST /api/feedback`

A successful capture returns `202` with `{request_id, accepted_at, status: "accepted"}`; the worker persists the record asynchronously.

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
    "user_id": "user_123",
    "trigger_type": "comment",
    "trigger_message": "Pricing page feedback form",
    "trigger_metadata": {"form_id": "pricing-feedback", "placement": "footer"},
    "target_type": "surface",
    "target_id": "pricing-page-feedback-button",
    "target_text": "Feedback",
    "event_at": "2026-04-24T09:30:00Z",
    "tags": ["website", "pricing"],
    "source_metadata": {"path": "/pricing", "referrer": "/"},
    "attributes": {"plan": "team", "locale": "en-US"}
  }'
```

Omit the bearer header only when `VOCKY_API_AUTH_TOKEN` is unset in a trusted local or private deployment. REST capture is ingestion-only; use the scoped end-user read (`GET /api/feedback`) or Admin REST for review.

For client integration guidance, see [docs/current/experience.md](docs/current/experience.md).

The Admin Docs REST capture try-it form exercises this same endpoint from the browser for self-hosted operators. Enter `VOCKY_API_AUTH_TOKEN` there only when `/api/*` auth is configured; that API token is separate from the Admin token and is kept only in the browser session. The try flow does not create a public REST review, query, job-status, or management API, and successful tries create normal queued feedback records.

## Admin REST Surface

The Admin REST API is separate from the public capture/read API and is intended for human operators, scripts, dashboards, and the packaged Admin Web UI. It can query and manage all feedback records, including likes, dislikes, comments, caller-owned user identity, trigger context, target context, metadata, messages, and used context.

Implemented endpoints:

- `GET /admin/api/healthz`
- `GET /admin/api/feedback`
- `GET /admin/api/feedback/metrics`
- `GET /admin/api/feedback/{feedback_id}`
- `PATCH /admin/api/feedback/{feedback_id}`
- `DELETE /admin/api/feedback/{feedback_id}`

Set `VOCKY_ADMIN_AUTH_TOKEN` before exposing `/admin/api/*` outside a trusted local/private environment.

The Admin Web UI consumes these endpoints same-origin. Its edit form only patches `feedback_value`, `comment`, `channel`, and `tags`; captured `user_id`, trigger fields, target fields, messages, used context, `source_metadata`, and `attributes` remain read-only in the browser.

Admin REST patch writes apply the same channel category rule as capture: blank clears to `null`, and non-null values must be `web`, `mobile`, or `support`. Admin list filters exact-match stored channel text, including older legacy values, and exact-match `user_id`, `target_type`, and `trigger_type` when filtering identity, message/conversation/surface, or trigger categories.

## Self-Hosted Usage

For local or private-network access, send server-to-server REST capture to:

`http://<host>:<port>/api/feedback`

For public custom-domain access, REST capture clients should use:

`https://vocky.example.com/api/feedback`

Set `VOCKY_EXTERNAL_BASE_URL=https://<external-host>` in `.env` when you want clients or operator scripts to refer to the public origin.

Example REST capture with curl:

```sh
curl -X POST "http://127.0.0.1:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>" \
  -d '{
    "message": "Users keep asking for CSV export",
    "source": {"product": "my-product", "integration": "web-backend"},
    "feedback_value": 1,
    "comment": "Helpful answer",
    "channel": "web",
    "session_id": "sess_123",
    "user_id": "user_123",
    "trigger_type": "like",
    "trigger_message": "Assistant response thumbs-up",
    "trigger_metadata": {"control_id": "msg_assistant_789_like"},
    "target_type": "message",
    "target_id": "msg_assistant_789",
    "target_role": "assistant",
    "target_text": "Yes, use the export menu.",
    "messages": [
      {"role": "user", "content": "Can I export this as CSV?"},
      {"role": "assistant", "content": "Yes, use the export menu."}
    ],
    "used_context": [
      {"source": "help-center", "snippet": "CSV export is available."}
    ],
    "tags": ["feature-request"],
    "source_metadata": {"channel": "support"},
    "attributes": {"plan": "team"}
  }'
```

Example Python capture with the standard `httpx` client:

```python
import httpx


async def main() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/feedback",
            headers={"Authorization": "Bearer <VOCKY_API_AUTH_TOKEN>"},
            json={
                "message": "Users keep asking for CSV export",
                "source": {"product": "my-product", "integration": "web-backend"},
                "feedback_value": 1,
                "comment": "Helpful answer",
                "channel": "web",
                "session_id": "sess_123",
                "user_id": "user_123",
                "trigger_type": "like",
            },
        )
        response.raise_for_status()
        print(response.json())
```

The examples above use the default local loopback URL. If you connect through a public custom domain or another reverse proxy, replace it with `${VOCKY_EXTERNAL_BASE_URL}/api/feedback`. Omit the bearer header only when `VOCKY_API_AUTH_TOKEN` is unset in a trusted local or private deployment.

The worker persists accepted jobs in the background. To read back a user's own records, call the scoped end-user read with the required `user_id` and `source_product` (the `source.product` you sent at capture):

```sh
curl "http://127.0.0.1:8000/api/feedback?user_id=user_123&source_product=my-product" \
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>"
```

It returns that user's own records — newest-first, plus operator comments and attachment links. If you need to verify that a record landed, poll `GET /api/feedback` (scoped) or use Admin REST or the Admin Web UI.

Example Caddy reverse proxy:

```caddy
vocky.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

If you publish Vocky through Caddy or another reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to that external `https://...` URL, keep `VOCKY_BASE_URL` pointed at the local verification target, and use `make external-verify` for the public path.

## License

Vocky is licensed under the MIT License. See [LICENSE](./LICENSE).
