# vocky

Human-triggered feedback capture and review. Turn product and customer feedback moments into structured voice-of-customer signals.

Vocky is a **free, multi-tenant feedback SaaS** (still pre-MVP). You sign up for an account, immediately get an **org** with a `"default"` project, and mint a `vk_` key — scoped to one project or to the whole org — that your product backend uses to capture feedback. There are several ways in: the **web app**, the **`vocky` CLI**, server-to-server **`/api/*` REST capture**, and a write-only **`/mcp`** endpoint for AI agents.

The name comes from VoC, short for voice of customer.

> **Just want to use vocky from your terminal or a coding agent?** Jump to [Quickstart — the `vocky` CLI](#quickstart--the-vocky-cli), or read the full [CLI & agent guide](docs/cli.md). You never have to visit the website.

## What Vocky Is

Vocky is a feedback layer for products and the surfaces around them. When users react to product surfaces — page feedback, widget feedback, surveys, ratings, like/dislike controls — they reveal bugs, friction, requests, and praise. Vocky captures those moments, structures them, and makes them reviewable and searchable (Korean- and English-safe).

Vocky is delivered as a **free, multi-tenant SaaS** with a simple identity model:

- A **user** signs up with an email and password and immediately gets an **org** *and* a project named `"default"` — no setup step.
- An **org** owns **projects**, whose names are unique within the org (creating one by an existing name returns it).
- You mint `vk_`-prefixed **ingest keys**, shown exactly once at creation, at **either scope**: a **project key** for one project, or an **org key** that works across every project in the org.
- A product backend sends the `vk_` key as `Authorization: Bearer` to capture feedback. With an org key it names the destination project in the request (defaulting to `"default"`); a project key always captures into its own.

> "Org" is the product-facing word; the table and every API field are still `tenant` / `tenant_id`. They mean the same thing.

The service is free — there are no paid plans, billing, or usage metering.

### Surfaces

- **Web app** — vocky's primary user-facing browser surface. Sign up, see your org dashboard (projects, usage, and your org keys), drill into a project to mint/revoke its keys, and read/search feedback across your projects. Live in production at [https://vocky.hi2vi.com](https://vocky.hi2vi.com) (since 2026-08-04); it also runs locally for development.
- **`vocky` CLI** — the same account/project/credential setup and cross-project feedback read from your terminal, so you (or a coding agent acting for you) can onboard and use vocky **without visiting the website**. See [Quickstart](#quickstart--the-vocky-cli) and the [CLI & agent guide](docs/cli.md).
- **`/api/*` REST capture** — trusted server-to-server capture and reads, authenticated by a `vk_` key (project- or org-scoped).
- **`/mcp` write-only capture** — an AI agent linked to a project's MCP endpoint saves feedback at its own judgement through a single `capture_feedback` tool, authenticated by the same `vk_` key.
- **Admin REST (`/admin/api/*`)** — the self-hosted operator review API, guarded by its own separate `VOCKY_ADMIN_AUTH_TOKEN` bearer.

The packaged self-hosted operator Admin Web UI that used to ship under `/admin` was **removed in P6** — only the bearer-guarded Admin REST API (`/admin/api/*`) survives, and it now **fails closed**: without a configured `VOCKY_ADMIN_AUTH_TOKEN` every Admin REST request answers `503`.

## Why It Exists

- Product surfaces and customer interactions already contain valuable feedback.
- Most of that feedback gets lost in logs, support noise, or one-off spreadsheets.
- Teams need a simple way to turn product feedback into product insight.

A product's own backend forwards feedback moments to vocky over REST (or an agent captures them over MCP), so capture stays a deliberate, authenticated action rather than a scattered afterthought.

## Quickstart — the `vocky` CLI

The fastest way to start. Everything below runs against a local vocky at `http://127.0.0.1:8000` by default (start the stack with `make bootstrap`, or point at another server with `--base-url`).

### Install

The console script is `vocky` (the server entry point is the separate `vocky-server`). **The hosted installer
is live** and is the fastest path:

```sh
curl -fsSL https://vocky.hi2vi.com/install.sh | bash
```

It's a small, auditable `curl | bash` script (`web/public/install.sh`) that bootstraps `uv` if needed and
installs `vocky` under `$HOME/.local` — nothing system-wide. Re-run the same line any time to upgrade.

**Developing against this checkout** (or if you'd rather not `curl | bash`), install from it instead:

```sh
# Option A — run it straight from a repo checkout (no install)
uv run vocky --help

# Option B — install the `vocky` command onto your PATH
uv tool install .

# Option C — run it ephemerally from the checkout
uvx --from . vocky --help
```

vocky is a lean/`server`-extra split package (`pyproject.toml`): a plain `uv tool install` or `pip install`
resolves only the **lean CLI** (httpx + typer + their transitives — no pydantic/sqlalchemy/uvicorn); the
full server stack lives behind the `server` extra, e.g. `pip install ".[server]"` from a checkout.

### The onboarding spine

Sign up → mint a key → capture feedback → read it back. Each account command prompts for anything you omit; nothing is destructive.

```sh
# 1. Sign up (creates your account, your org, AND a "default" project; stores a 30-day session token)
vocky signup --email you@example.com
#    -> Signed up and signed in as you@example.com.
#    -> An org "you's workspace" was created for you automatically.
#    -> A "default" project was created too.

# 2. Mint a vk_ key — SHOWN ONCE, copy it now. Pick the scope:
vocky keys mint                              # ORG key: every project in your org
vocky keys mint --project <project-id>       # PROJECT key: just that one
#    -> Copy this key now — it is shown only once and cannot be recovered.
#    -> Scope: org (all projects)
#    -> vk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
#    (the key is always the LAST line, at either scope)

# 2b. Only if you want more projects — idempotent on name, safe to re-run
vocky projects create "marketing-site"
#    -> Created project "marketing-site" (<project-id>).

# 3. Capture a feedback event from your backend with that vk_ key
#    ("project" is honored ONLY by an org key — get-or-created, defaults to "default";
#     a project key ignores it entirely, so sending it never breaks an existing client)
curl -X POST "http://127.0.0.1:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer vk_<your-key>" \
  -d '{
    "message": "Pricing page feedback button was hard to find",
    "source": {"product": "marketing-site", "integration": "web-backend"},
    "project": "marketing-site",
    "feedback_value": 2,
    "channel": "web",
    "user_id": "user_123",
    "trigger_type": "comment",
    "target_type": "surface",
    "recorded_by": "human"
  }'
#    -> 202 {"request_id": "...", "accepted_at": "...", "status": "accepted"}

# 4. Read it back once the worker has persisted it (Korean- and English-safe search)
vocky feedback search "pricing"
vocky feedback list
vocky usage

# 5. Manage keys later — same scope rule as minting
vocky keys list                              # your org keys
vocky keys list --project <project-id>       # that project's keys
vocky keys revoke <credential-id>            # an org key (add --project for a project key)
```

`vocky` authenticates to the account control-plane (`/auth/*`, `/app/*`) with your **session token**; the `vk_` key you mint is what your *product backend* (or an agent) later sends to `/api/*` + `/mcp` to capture feedback. The session token lives in `~/.config/vocky/config.json` (see below). Full command reference and the equivalent raw HTTP for every step are in [docs/cli.md](docs/cli.md).

### For coding agents

The CLI is built to be driven headlessly from Claude Code, Codex, or any agent runtime — no browser, no interactive prompts:

- **`--password-stdin`** — pipe the password as one line of stdin so it never lands on `argv` or in shell history:

  ```sh
  printf '%s\n' "$VOCKY_PASSWORD" | vocky signup --email you@example.com --password-stdin
  printf '%s\n' "$VOCKY_PASSWORD" | vocky login  --email you@example.com --password-stdin
  ```

- **`--base-url <url>`** — target a specific server per invocation (precedence: `--base-url` flag > `VOCKY_BASE_URL` env > stored config > `http://127.0.0.1:8000`).
- **`VOCKY_CONFIG_DIR`** — point the config/session store at an isolated directory so parallel or throwaway sessions never collide:

  ```sh
  export VOCKY_CONFIG_DIR="$(mktemp -d)"
  printf '%s\n' "$VOCKY_PASSWORD" | vocky login --email you@example.com --password-stdin
  ```

- **Session token on disk** — after login, the 30-day session token is stored in `~/.config/vocky/config.json` (XDG-aware; overridable with `VOCKY_CONFIG_DIR`), written with `0600` permissions (its directory `0700`). It is the only session state; `vocky logout` best-effort revokes it server-side and clears the file.
- **Exit codes** — commands print errors to **stderr** and exit non-zero on failure; a `401` on any authenticated call prints `Not signed in — run \`vocky login\`.`.

The complete agent contract — every command, its output shape, the equivalent raw HTTP, and a cross-reference to `/mcp` for agent-decided write-only capture — is in **[docs/cli.md](docs/cli.md)**.

## What The Current Pre-MVP Does

- Real user accounts (email + password signup/login) over a multi-tenant core: each account owns an **org** with projects (one, `"default"`, provisioned at signup) and ingest credentials at **project or org** scope
- Free service — no paid plans, billing, usage metering, or plan tiers
- Server-to-server REST capture (`POST /api/feedback`) for explicit product/UI-triggered feedback, authenticated by a mandatory `vk_` credential, accepted without blocking on database writes and persisted asynchronously through a Redis-backed background worker
- A write-only MCP `capture_feedback` tool at `/mcp` for agent-decided capture, gated by the same `vk_` credential and feeding the same store as REST
- A `vocky` CLI and an authenticated web app that both drive the same account/project/credential control-plane and cross-project feedback read
- Store like/dislike values, optional comments, caller-owned user identity, trigger context, exact target context, conversation context, metadata, and a `recorded_by` capture-provenance marker (`agent` vs. `human`) for later review — see [Agent Capture Over MCP](#agent-capture-over-mcp-write-only)
- A scoped end-user read (`GET /api/feedback`) that returns a product user's own records plus operator comments and attachment links
- A project-scoped read+manage surface (`/api/project/feedback`) for a product's own admin panel, using the same `vk_` key
- A signed-in cross-project read + search surface (`/app/feedback`), Korean-safe
- Derived usage monitoring (`/app/usage`, `/api/project/usage`) — capture volume + credential last-used, operational visibility only (no billing or metering)
- Separate Admin REST endpoints (`/admin/api/*`) for self-hosted human/operator review and management
- Nullable channel category assignment with the built-in MVP categories `web`, `mobile`, and `support`
- A published agent skill (`vocky-feedback`, [skills/vocky-feedback/SKILL.md](skills/vocky-feedback/SKILL.md)) served from the live site so a coding agent can install and use vocky directly
- Worker-side feedback alert email: the owning org's owner gets a plain-text notification for every persisted event when `VOCKY_SMTP_*` is configured on the worker; alerts are silently off otherwise

## What The First MVP Will Not Do

- Automatic classification or taxonomy assignment
- A production-grade analytics workspace or managed feedback operations suite
- Browser-direct unauthenticated ingestion
- Broad *unauthenticated* public REST review/query/management — every review/query surface is scoped and authenticated
- Paid plans, billing, usage metering, or plan tiers — the SaaS is free
- Multi-user tenant collaboration UI (invites, roles): the tenancy schema supports members and roles, but the MVP flow is solo-owner

## Open Source + Managed Direction

Vocky follows a light open-core direction: a community, self-hostable base plus a managed cloud offering later. The goal is to keep the core transparent and usable while building a hosted product around convenience, operations, and richer workflows.

## Current Status

- vocky is **live in production** at [https://vocky.hi2vi.com](https://vocky.hi2vi.com) (since 2026-08-04); the `vocky` CLI installs via the hosted `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` line (see [Install](#install) above) — nothing is published to PyPI.
- Account signup/login/logout/identity are implemented over `/auth/*`, minting an opaque, 30-day session bearer token.
- The account control-plane (`/app/*`) manages the caller's org, projects, `vk_` credentials at project **or** org scope, usage, and cross-project feedback read/search — driven by the web app and the `vocky` CLI.
- `/api/*` capture and reads are authenticated by a mandatory `vk_` credential, scoped to one project or to the whole org (the old optional static `VOCKY_API_AUTH_TOKEN` is retired).
- `/mcp` exposes a single write-only `capture_feedback` tool for agents, authenticated by the same `vk_` credential.
- Accepted capture events are queued and persisted by a dedicated background worker rather than written on the request path; completed events persist to PostgreSQL with Alembic migrations.
- The worker also emails the owning org's owner a plain-text alert for every persisted event once `VOCKY_SMTP_HOST`/`VOCKY_SMTP_USER`/`VOCKY_SMTP_PASSWORD` (plus optional `VOCKY_SMTP_PORT`/`VOCKY_SMTP_FROM`) are configured; it is silently off otherwise.
- Self-hosted runtime includes PostgreSQL, Redis, the app process, and a dedicated worker process.
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

Open the web app locally with the `web/` Next.js dev server (see `web/README.md`), or use the `vocky` CLI above. The packaged Admin Web UI is gone (removed in P6); check protected Admin REST data with `curl`/an HTTP client, sending `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>` — without a configured token, `/admin/api/*` answers `503` rather than accepting requests.

`make bootstrap` runs `make sync`, `make compose-up`, the explicit migration step `make migrate`, and a final readiness check. The Compose stack includes `redis`, `postgres`, `app`, and `worker`. The app and worker images install dependencies during the Docker build and run with `uv run --no-sync` at container startup.

`make verify` waits for `GET /healthz`, runs the REST smoke flow, and then runs the full pytest suite (`smoke test` — there is no packaging step). The smoke path **signs up a throwaway account, mints a real `vk_` key**, posts a feedback event to `POST /api/feedback` with it, and confirms the record becomes queryable through the scoped `GET /api/feedback` only after the worker persists it.

`TEST_DATABASE_URL` must point at a separate disposable database. `make test` refuses to run if it matches `DATABASE_URL`, and the pytest fixtures reset only the database named in `TEST_DATABASE_URL`.

If you need different host ports or interfaces, edit `.env` before you run the workflow. `VOCKY_PORT`, `POSTGRES_PORT`, and `REDIS_PORT` change the published ports. `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST` change which host interface Docker publishes on. `VOCKY_BASE_URL` remains the local smoke-check target, and `VOCKY_EXTERNAL_BASE_URL` is optional for public custom-domain access through Cloudflare Tunnel or another HTTPS reverse proxy.

Public custom-domain access has these additional settings:

- `VOCKY_ADMIN_AUTH_TOKEN`: bearer token required for `/admin/api/*`. **Mandatory to expose Admin REST at all** — without it every `/admin/api/*` request answers `503` (the middleware fails closed, it does not fall back to an open surface).
- `VOCKY_MCP_ALLOWED_HOSTS`: comma-separated extra `Host` values allowed by the `/mcp` DNS-rebinding protection. A public `/mcp` deployment must add its public host (with port) here.

`/api/*` needs no extra env gating before exposure — it is always authenticated by `vk_` credentials.

Granular fallback commands remain available:

- `make sync`
- `make compose-up`
- `make migrate`
- `make smoke`
- `make test`
- `make compose-down`
- `make check-skill-parity` — verifies the served `skills/vocky-feedback/SKILL.md` is byte-identical to the canonical copy (also runs in CI)

The smoke target checks `GET /healthz`, then provisions a `vk_` key, posts a feedback event to `POST /api/feedback`, and polls the scoped `GET /api/feedback` until the worker-persisted record appears; it waits for readiness before the REST calls.

## Running The App Directly

The supported self-hosted flow is Compose-first. If PostgreSQL and Redis are already running outside Compose, point `DATABASE_URL` and `REDIS_URL` at them and start both processes:

`uv run vocky-server`

`uv run vocky-worker`

(`vocky-server` is the server console script; the bare `vocky` command is the user/agent CLI.)

The Starlette host app exposes:

- `GET /healthz`
- Account auth under `/auth/*` (signup, login, logout, me)
- Session-authed account control-plane under `/app/*` (org, projects, ingest credentials at project **or** org scope, usage, cross-project feedback read/search)
- Public REST capture at `POST /api/feedback` (`vk_` credential, project- or org-scoped)
- Scoped end-user read at `GET /api/feedback`
- Project-scoped read+manage at `/api/project/feedback` and per-project usage at `/api/project/usage`
- Write-only agent capture at `/mcp` (single `capture_feedback` tool, `vk_` credential)
- Admin REST under `/admin/api/*` (bearer-guarded, fails closed with `503` when `VOCKY_ADMIN_AUTH_TOKEN` is unset)

`channel` is optional and defaults to no category when omitted or blank. New capture and Admin edit writes accept only `web`, `mobile`, `support`, or `null`; older stored channel values remain visible and exact-filterable for review.

`target_type` is optional captured target context and the review discriminator for separating message, conversation, and surface feedback. Use `message` when the user judged a specific agent message, `conversation` when the user judged a whole thread, and `surface` when the user judged a page, widget, screen, or other product UI.

`user_id` is optional caller-owned identity for the product user associated with the event. It does not replace `session_id`, which remains browser, runtime, or session correlation. Trigger fields explain why capture happened: use `trigger_type` for `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, or `other`; use `trigger_message` for button text, prompt copy, survey question, or action label; and use `trigger_metadata` for structured details such as control IDs, rating scale, selected option, or redacted runtime context.

`recorded_by` answers the separate question of **who recorded the event**, orthogonal to the trigger fields' *why*. It is optional and accepts only `agent` (an AI agent runtime decided to record this) or `human` (an explicit human action such as a like/dislike button or a submitted form); anything else is rejected with `recorded_by must be one of: agent, human`. Omitting it stores `null`, meaning *unspecified* — never assume `null` means human, and note that every record captured before the marker existed reads back as `null`. The one inference is on `/mcp`, the agent surface, where an omitted value is stored as `agent`; REST and the CLI leave it `null`. The marker is capture-time provenance: it is not backfilled, not inferred from anything else, and not editable through Admin PATCH.

For conversation or process context, send review-safe summaries, retrieved snippets, tool traces, prompt summaries, and redacted execution metadata. Do not send raw hidden chain-of-thought or private model reasoning.

## Access Modes

Vocky supports two clean operator modes for self-hosting:

- Internal self-hosting: keep the default `*_PUBLISH_HOST=127.0.0.1` values, use `VOCKY_BASE_URL` for host-side smoke and verification, and connect from the same machine or trusted private network.
- Public custom-domain deploy: publish vocky through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL`, set `VOCKY_ADMIN_AUTH_TOKEN` (required — `/admin/api/*` answers `503` until it is set, it is never openly reachable), add the public host to `VOCKY_MCP_ALLOWED_HOSTS` if you expose `/mcp`, and use `make external-verify` for public readiness and smoke checks.

`/api/*` and `/mcp` are always authenticated by `vk_` credentials, so they need no extra env gating before exposure. For public custom-domain access, set `VOCKY_EXTERNAL_BASE_URL` to the external HTTPS origin after DNS and proxying are active.

## Public Custom Domain With Cloudflare

Use Cloudflare Tunnel for `vocky.example.com`. This keeps the vocky origin private: `cloudflared` opens outbound tunnel connections to Cloudflare, and Cloudflare forwards public HTTPS traffic to your local `http://127.0.0.1:8000` service.

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
   - Install `cloudflared` on the machine running vocky.
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

5. Configure vocky for public access in `.env`:

```env
VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com
VOCKY_ADMIN_AUTH_TOKEN=<a-long-random-secret>
# Only if you expose the write-only agent MCP endpoint publicly:
VOCKY_MCP_ALLOWED_HOSTS=vocky.example.com
```

6. Restart the vocky app after changing `.env`, then verify:

```sh
make external-verify
```

If you prefer not to store the external origin in `.env`, pass it on the command line:

```sh
make external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com
```

Public REST capture clients should use `https://vocky.example.com/api/feedback` with `Authorization: Bearer vk_<your-project-key>`.
Public Admin REST requests should use `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>` when `/admin/api/*` is exposed.

`make external-smoke` runs only the public REST smoke flow, while `make external-verify` waits for public health first and then runs the same smoke flow.

## Web Capture REST Surface

Use REST capture from trusted server-side web or product code when the user explicitly triggers feedback in the product UI. It is intended for product and website feedback actions such as page feedback, widget feedback, surveys, ratings, and like/dislike controls. Send `user_id` when the backend has a stable product user identifier, send trigger fields for the control or workflow that caused capture, and set `target_type` to `surface` when the exact page, widget, or product surface is known. Put source-specific URL, page, widget, and backend context in `source_metadata`, and product dimensions such as plan, locale, or rollout cohort in `attributes`.

The optional `channel` field is a nullable review category. Omit it by default unless the caller can explicitly assign `web`, `mobile`, or `support`.

Implemented endpoint:

- `POST /api/feedback`

**Authentication is mandatory.** Every `/api/*` request must send a valid, non-revoked per-project credential as `Authorization: Bearer vk_<token>`; a missing, malformed, unknown, or revoked key returns `401`. Mint the key with the web app, the `vocky` CLI (`vocky keys mint` for an org key, `vocky keys mint --project <id>` for a project key), or `POST /app/credentials` / `POST /app/projects/{id}/credentials`. A key's scope is reported by `credential.project_id` — a UUID for project-bound, `null` for org-level; both use the same `vk_` prefix. The old optional static `VOCKY_API_AUTH_TOKEN` is retired; there is no unauthenticated or shared-token path.

A successful capture returns `202` with `{request_id, accepted_at, status: "accepted"}`; the worker persists the record asynchronously.

Example REST surface-feedback capture:

```sh
curl -X POST "http://127.0.0.1:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer vk_<your-project-key>" \
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
    "recorded_by": "human",
    "target_type": "surface",
    "target_id": "pricing-page-feedback-button",
    "target_text": "Feedback",
    "event_at": "2026-04-24T09:30:00Z",
    "tags": ["website", "pricing"],
    "source_metadata": {"path": "/pricing", "referrer": "/"},
    "attributes": {"plan": "team", "locale": "en-US"}
  }'
```

Example Python capture with the standard `httpx` client:

```python
import httpx


async def main() -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/feedback",
            headers={"Authorization": "Bearer vk_<your-project-key>"},
            json={
                "message": "Users keep asking for CSV export",
                "source": {"product": "my-product", "integration": "web-backend"},
                "feedback_value": 1,
                "comment": "Helpful answer",
                "channel": "web",
                "session_id": "sess_123",
                "user_id": "user_123",
                "trigger_type": "like",
                "recorded_by": "human",
            },
        )
        response.raise_for_status()
        print(response.json())
```

The examples above use the default local loopback URL. If you connect through a public custom domain or another reverse proxy, replace it with `${VOCKY_EXTERNAL_BASE_URL}/api/feedback`.

REST capture is ingestion-only. To read records back, use the scoped end-user read (`GET /api/feedback`), the project read+manage surface (`/api/project/feedback`), the signed-in cross-project read (`/app/feedback`, or `vocky feedback`), or Admin REST.

For client integration guidance, see [archive/workspace/docs/current/experience.md](archive/workspace/docs/current/experience.md). For the terminal/agent flow, see [docs/cli.md](docs/cli.md).

## Agent Capture Over MCP (write-only)

If your product is an AI agent, the agent can save feedback at its own judgement through vocky's **write-only** MCP endpoint instead of (or alongside) REST. Point the agent's MCP client at the project's `/mcp` URL and authenticate with the **same `vk_` project key** — the whole endpoint (the `initialize` handshake included) requires it. There is exactly one tool, `capture_feedback` (no read/query tools); its inputs are the same capture fields as REST minus `attachment_ids`, `recorded_by` included. A successful call returns the same `{request_id, accepted_at, status: "accepted"}` receipt as REST. See [archive/workspace/docs/current/experience.md](archive/workspace/docs/current/experience.md) for a client example.

**The agent-capture convention.** Both halves of an agent-recorded event are free text — vocky has no sentiment enum — and both go in fields that already exist:

- **`message`** carries the user's own feedback or sentiment, verbatim where possible (a word such as `답답함` or `감사`, or a whole sentence). It is required and non-blank, and it is the voice of the customer — not a paraphrase.
- **`comment`** carries the agent's note about that feedback: what happened, what the user was doing, why it was recorded. The schema leaves it optional so existing clients keep working, but an agent capture without it is one no reviewer can act on, so it is documented as required for agent capture.
- **`recorded_by`** is the marker itself (`agent` / `human`), and `/mcp` defaults it to `agent` when the call omits it — an agent that never learns the argument still produces correctly marked data, and an explicit value always wins. REST does not infer it.
- **`source.integration`** (e.g. `langchain-mcp`) stays what it always was: a free-text runtime hint, **not** the marker.

Both `message` and `comment` sit inside the same substring-search expression, so an agent's sentiment *and* its note are searchable — Korean included — from the signed-in cross-project read (`/app/feedback?q=`, or `vocky feedback search`) with no extra setup.

**Key scope, stated plainly.** A `vk_` key is **not** capture-only: within its scope it can capture, read, PATCH, and delete feedback, and an org-level key spans every project in the org. When you put a key inside a third-party or agent runtime, mint a **project-bound** key (`vocky keys mint --project <project-id>`) so the blast radius is that one project, and never hand out an org key. Per-credential capture-only scopes are not implemented yet.

The `/mcp` transport also enforces DNS-rebinding protection on the request `Host`: a public hostname must appear in `VOCKY_MCP_ALLOWED_HOSTS` or the call answers `421 Invalid Host header` regardless of the key. Non-browser MCP clients send no `Origin` header, so `VOCKY_MCP_ALLOWED_ORIGINS` usually needs no configuration.

## Read Back Feedback

The worker persists accepted jobs in the background. There are four scoped, authenticated ways to read:

- **Scoped end-user read** — a product user's own records, for a "my feedback" view:

  ```sh
  curl "http://127.0.0.1:8000/api/feedback?user_id=user_123&source_product=marketing-site" \
    -H "Authorization: Bearer vk_<your-project-key>"
  ```

- **Project read + manage** — your product's own admin panel reads and manages its project's feedback with the same `vk_` key over `/api/project/feedback` (list/get/PATCH/DELETE/comments).
- **Signed-in cross-project read** — search across all your projects with your session token over `/app/feedback`, or from the terminal with `vocky feedback list` / `vocky feedback search "<query>"` (Korean-safe substring).
- **Admin REST** — self-hosted operator review under `/admin/api/*`.

Every one of these read surfaces returns `recorded_by` in the record body (`"agent"`, `"human"`, or `null` for unspecified) and accepts an optional `?recorded_by=agent|human` filter, so agent-recorded feedback can be separated from human-recorded feedback on any of them. The filter is exact-match; omitting it returns every record regardless of marker, and there is no filter value that selects only the unspecified (`null`) rows.

## Admin REST Surface

The Admin REST API is separate from the public capture/read API and is intended for self-hosted human operators, scripts, and dashboards. It can query and manage all feedback records, including likes, dislikes, comments, caller-owned user identity, trigger context, target context, metadata, messages, and used context.

Implemented endpoints:

- `GET /admin/api/healthz`
- `GET /admin/api/feedback`
- `GET /admin/api/feedback/metrics`
- `GET /admin/api/feedback/{feedback_id}`
- `PATCH /admin/api/feedback/{feedback_id}`
- `DELETE /admin/api/feedback/{feedback_id}`

`VOCKY_ADMIN_AUTH_TOKEN` is **required**: without it, every `/admin/api/*` request answers `503` (fails closed — the surface is never openly reachable). Once configured, Admin REST requests send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`. This is a **separate** boundary from the `vk_` ingest credential that guards `/api/*`.

Admin REST patch writes apply the same channel category rule as capture: blank clears to `null`, and non-null values must be `web`, `mobile`, or `support`. Admin list filters exact-match stored channel text, `user_id`, `target_type`, `trigger_type`, and `recorded_by`. `recorded_by` is capture-time provenance and is deliberately **not** patchable — Admin edits can review a record, not restate who recorded it.

## Documentation

- **[docs/cli.md](docs/cli.md)** — the complete `vocky` CLI & coding-agent guide: full command reference, an end-to-end walkthrough with the equivalent raw HTTP for every step, and the agent contract.
- **[archive/workspace/docs/current/experience.md](archive/workspace/docs/current/experience.md)** — (frozen) the product integration guide (REST capture, MCP capture, reads).
- **[archive/workspace/docs/current/api.md](archive/workspace/docs/current/api.md)** — (frozen) public API contracts.

## License

Vocky is licensed under the MIT License. See [LICENSE](./LICENSE).
