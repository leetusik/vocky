---
doc_id: architecture
version: v0007
created_at: 2026-07-18T11:15:57+09:00
source: P5.REVIEW
summary: P5: the vocky CLI as a new pure-client surface over /auth/* + /app/* (Typer app in src/vocky/cli/, no backend change), mirroring the web-app client framing; server console entry renamed to vocky-server
previous: v0006_p4_the_web_next.js_app_server-side_bff_as_vocky_s_browser_surface_sealed_httponly_cookie_no_cors_no_web-side_db_admin-ui_convergence_resolved_replacement_built_in_p4_physical_removal_deferred_to_p6
---

# Architecture

## Status

This architecture is intentionally lightweight. Vocky is still pre-MVP, and the current service accepts capture work through server-to-server REST using Redis-backed queueing plus a dedicated worker while exposing a scoped end-user REST read, separate Admin REST endpoints, and a same-origin self-hosted Admin Web UI with dashboard metrics, feedback review management, in-app operator documentation, and REST capture try-it over the same PostgreSQL feedback store. As of **P7**, a **write-only MCP capture surface** is also mounted at `/mcp` (see "MCP Write-Only Capture Surface" below): agents linked to a project's MCP endpoint save feedback through a single `capture_feedback` tool that feeds the same queue/store as REST. The three MCP read/query tools retired in P1 (`list_feedback`, `summarize_feedback`, `list_liked_conversations`) stay retired — reads remain REST-only.

On top of that capture core, Vocky now has an **identity and tenancy layer**: real user accounts (email + password), a multi-tenant model (tenants → projects), per-project ingest credentials, a public `/auth/*` auth surface, a session-token-authed `/app/*` account control-plane, and a `src/vocky/accounts/` domain package. Public `/api/*` ingestion is guarded by **mandatory per-project credential auth** (`ProjectCredentialAuthMiddleware`), which replaced the old optional static-token `APIBearerAuthMiddleware`.

As of **P4**, vocky also has a **browser surface of its own**: a Next.js app in `web/` that talks to `/auth/*` + `/app/*` through a **server-side BFF proxy** (sealed httpOnly cookie, no CORS, no web-side DB). It is the replacement for the packaged same-origin Admin Web UI — **built** in P4, with the old UI's **physical removal deferred to P6**. See "The Web App and the BFF Boundary" below.

As of **P5**, vocky also has a **`vocky` CLI**: a Typer app in `src/vocky/cli/` that is a **pure session-token client** of `/auth/*` + `/app/*` — the same "client only, no backend change" shape as the web app. The server console entry was renamed `vocky` → `vocky-server` to free the `vocky` name for the CLI. See "The `vocky` CLI" below.

On top of that, **P3 makes feedback project-scoped** (Feedback API v2). `feedback_events` gains a nullable `project_id`; the ingest middleware threads the resolved credential onto the ASGI scope so capture stamps the record's project and reads scope to it; three new feedback surfaces sit over the scoped store — the project-credential-authed `/api/project/feedback` (an external service's own admin panel reads + manages its own project's feedback), the session-authed `/app/feedback` (a signed-in user reads + searches across all their projects, Korean-safe via a `pg_trgm` substring-search subsystem), and derived usage-monitoring endpoints (`/app/usage`, `/app/projects/{id}/usage`, `/api/project/usage`). The ingest guard now also best-effort stamps `last_used_at`. See "Feedback Project Scoping & the P3 Feedback API" below.

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `pyproject.toml`: Python project metadata and dependencies
- `src/vocky/`: service code, public REST and Admin REST/Web UI routing, persistence layer, and smoke script
- `web/`: the Next.js browser app (P4) — vocky's authenticated web surface and its server-side BFF; TypeScript/pnpm, its own gate (see `frontend.md`, `operations.md`)
- `alembic/` and `alembic.ini`: database migration environment
- `tests/`: validation, persistence, and REST/persistence coverage
- `Dockerfile`, `docker-compose.yml`, `.env.example`, `Makefile`: local run, package verification, external smoke checks, and self-hosted development workflow
- `docs/`: stable reference documents
- `works/`: active backlog, deferred queue, active work items, archives, and templates
- `scripts/`: workflow helpers

## First MVP System Shape

The first MVP should be built from these parts:

- Server-to-server REST feedback capture for explicit human-triggered website or product feedback
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- A scoped end-user REST read that returns one user's own records plus operator comments
- Dedicated Admin REST endpoints for human operators, dashboard metrics, and review workflows
- A packaged same-origin Admin Web UI for self-hosted operators, including dashboard metrics, feedback review management, in-app operator docs, and an operator REST capture try-it flow backed by the existing capture endpoint rather than a separate browser-facing data API

## Runtime Shape

The current service uses these choices:

- Python application managed with `uv`
- Application package under `src/vocky`
- A Starlette ASGI host process for REST and health traffic
- A separate worker process for background capture persistence
- Redis-backed queueing between the app and worker
- Public REST capture route and scoped end-user read route under `/api/*`
- A write-only **FastMCP Streamable-HTTP** transport mounted at `/mcp` (its `session_manager` nested in the host lifespan), exposing the single `capture_feedback` tool
- Public account-auth routes under `/auth/*` (signup, login, logout, me)
- Session-token-authed account control-plane routes under `/app/*` (tenant, projects, per-project credentials)
- Starlette Admin REST routes under `/admin/api/*`
- Starlette Admin Web UI routes under `/admin` and packaged static assets under `/admin/assets/*`
- A plain `/healthz` endpoint on the same host app for smoke checks
- **Mandatory** per-project credential auth for public REST `/api/*` **and** `/mcp` traffic via `ProjectCredentialAuthMiddleware` (no open fallback)
- Optional bearer-token protection for Admin REST traffic when `VOCKY_ADMIN_AUTH_TOKEN` is set
- Docker builds install runtime dependencies and the local project into the image, while Compose app and worker commands use `uv run --no-sync` so container startup does not repeat dependency sync
- REST capture and Admin REST handlers share validation helpers, service, and persistence layers, and the worker reuses the same persistence path

Server-to-server product integrations should use `/api/feedback` for capture-only ingestion, especially explicit product/UI-triggered feedback from pages, widgets, controls, surveys, or other product surfaces. Human/operator tools should use `/admin/api/*`, while browser operators can load the packaged UI from `/admin`. The Admin Docs try-it flow may send same-origin browser requests to `POST /api/feedback` as an operator verification convenience, but it uses the existing capture-only contract and creates normal queued feedback on success.

## Two-Track API Shape

Vocky now has two public-facing tracks over the same feedback schema:

- Public REST track for server-to-server product integrations: `POST /api/feedback` capture plus `GET /api/feedback`, a scoped end-user read of one user's own feedback (required `user_id` + `source_product`) together with operator comments and cursor pagination. REST capture uses the shared capture field set for explicit human-triggered product/UI feedback, including surface feedback represented with `target_type="surface"` when applicable.
- Admin REST track for humans and dashboards: `/admin/api/feedback` list/detail, `/admin/api/feedback/metrics` dashboard metrics, `/admin/api/feedback/{feedback_id}/comments` operator comment add/list (with the feedback detail response carrying a `comments` array), plus patch/delete management endpoints.

The Admin Web UI is a same-origin browser surface layered over the Admin REST track for protected dashboard data, feedback review management, and packaged static docs assets for operator reference content. It can also render an internal REST capture try-it docs block that posts to same-origin `/api/feedback`. Its packaged docs still reference the retired static `VOCKY_API_AUTH_TOKEN` bearer and no longer reflect the live `/api/*` per-project credential model. **P4 resolved the reshaping question by replacement rather than repair:** the `web/` app (below) is now vocky's browser surface, and this packaged UI is superseded rather than updated — its physical removal is **P6** work, so its stale packaged docs stay as-is until then and should not be treated as current guidance. Both API tracks use the same PostgreSQL `feedback_events` table, feedback service, and repository. Public REST is capture plus a single scoped end-user read (`GET /api/feedback`); it does not expose broad review, query, summary, job-status, or management endpoints. The scoped read returns only the caller-identified user's own records, scoped by required `user_id` + `source_product`, together with operator comments; any optional filters are AND-combined with that mandatory scope so the read never returns cross-user data. REST does not add a separate wire shape; website and product context should be represented with `target_type`, `target_id`, `target_text`, nullable `channel`, `tags`, `source_metadata`, and `attributes`. `target_type` is the review discriminator for message, conversation, and surface feedback; it does not create a second feedback store or a new capture endpoint. Admin REST is the surface that can inspect and manage all feedback records, including likes, dislikes, comments, channel category, metadata, target context, messages, and used context. The browser workflow intentionally exposes a narrower edit surface than Admin REST: `feedback_value`, `comment`, `channel`, and `tags`.

## Identity and Tenancy Layer

The accounts layer adds three route groups and one domain package on top of the feedback core, all wired in `create_app()`:

- **`/auth/*` (public account auth, `src/vocky/auth_api.py`)** — `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`. Registered first in the route list. These paths match neither `is_api_path` nor `is_admin_api_path`, so no bearer middleware guards them. Signup provisions a user + tenant + owner membership and mints a session token; login re-issues one.
- **`/app/*` (account control-plane, `src/vocky/app_api.py`)** — `GET /app/tenant`, `GET|POST /app/projects`, `GET /app/projects/{id}`, and `POST|GET|DELETE /app/projects/{id}/credentials[/{credential_id}]`. Also outside `/api/*` and `/admin/api/*`, so it bypasses both bearer middlewares and is guarded per-handler by `require_user` (each handler starts `ctx = await require_user(request)`; a raised `AuthError` renders the shared generic 401 via the app-wide `exception_handlers={AuthError: auth_error_handler}`).
- **`/api/*` credential guard (`ProjectCredentialAuthMiddleware`, `src/vocky/auth.py`)** — a raw-ASGI middleware that, on every `/api/*` HTTP request, extracts the bearer, hashes it, and requires `get_active_credential_by_token_hash` to return a non-revoked credential; missing/malformed/unknown/revoked all answer a generic 401. It takes no token argument and has no open fallback — auth is always enforced. As of P3 it also **stashes the resolved `ProjectCredentialRecord` on the ASGI scope** under the namespaced key `vocky.project_credential` (constant `PROJECT_CREDENTIAL_SCOPE_KEY`; handlers read it via `get_request_credential(request)`) and **best-effort stamps the credential's `last_used_at`** (wrapped so a stamping failure never 500s a valid ingest). It replaced the retired static-token `APIBearerAuthMiddleware`. `AdminBearerAuthMiddleware` is untouched.
- **`src/vocky/accounts/` domain package** — mirrors `src/vocky/feedback/`: `types.py` (transport-neutral dataclasses), `repository.py` (the sole ORM boundary, no commit), `service.py` (`AccountsService` owning the session lifecycle + commit + error translation, plus `get_accounts_service()`), `security.py` (argon2id password hashing + opaque-token/sha256 primitives), and `auth.py` (the reusable `require_user` / `AuthContext` / `AuthError` guard). Raw session tokens and project keys never cross this boundary; records carry only hashes' display prefixes, never the hashes themselves.

**Tenant isolation** is enforced in the control-plane handlers, not the database: `create_project` binds `tenant_id = ctx.tenant.id`, list reads are tenant-scoped, and every per-project read/mutation resolves the project first and answers **404 (never 403)** when `project is None or project.tenant_id != ctx.tenant.id`, so a caller can neither read nor probe the existence of another tenant's projects or credentials.

## Feedback Project Scoping & the P3 Feedback API

P3 threads the authenticated project through capture and reads, and adds three feedback surfaces over the now project-scoped store. All of it reuses the existing feedback service/repository — the only schema change is the `feedback_events.project_id` column plus the search index (see `data.md`).

- **Scope threading (capture).** `ProjectCredentialAuthMiddleware` stashes the resolved credential on the ASGI scope (`vocky.project_credential`); `POST /api/feedback` reads it via `get_request_credential(request)` and sets `payload.project_id = credential.project_id` before enqueue. The value rides the existing Redis capture queue (serializer/deserializer carry `project_id`) and the worker persists it unchanged. Legacy rows stay NULL (no backfill).
- **Read-model chokepoint.** `FeedbackQueryFilters` gained `project_id` (single), `project_ids` (set → `IN`), and `search`; `FeedbackRepository._apply_query_filters` applies each additively. This one chokepoint serves every scoped read: the single-project `/api/*` surfaces set `project_id`, the cross-project `/app/*` surfaces set `project_ids` to the tenant's project set, and usage reuses the same filters. An empty project set is short-circuited in the handler (return an empty page / zeroed metrics) — never passed to a query.
- **Project Feedback API (`src/vocky/project_feedback_api.py`, `/api/project/feedback`).** Project-credential-authed (auto-guarded by the `/api/*` middleware). Ports the operator verbs from `admin_api.py` — list / get-one / PATCH review fields / DELETE / operator comments add+list / attachment download — scoped to `credential.project_id`. The list **forces** the project filter; per-feedback ops load through `_load_project_feedback`, which returns the record only when `record.project_id == credential.project_id`, else 404 (never 403). `serialize_record` was lifted into `src/vocky/tools/query_feedback_common.py` and is now shared by Admin REST, `/api/project/*`, and `/app/*` (Admin output unchanged); the `/api/project/*` record omits `project_id` (single project).
- **App Feedback API (`src/vocky/app_feedback_api.py`, `/app/feedback`).** Session-authed (`require_user`, wired outside both `/api/*` middlewares; a raised `AuthError` renders the app-wide 401). Read + search only. Each handler resolves the caller's project set via `list_projects_for_tenant(ctx.tenant.id)`; feedback outside that set (incl. legacy NULL-project rows) answers 404 via `_load_scoped_feedback`. Optional `?project_id` narrowing validates membership (400 malformed / 404 not-owned). Records are serialized with the shared serializer **augmented with `project_id`** (the caller has many projects).
- **Multilingual substring-search subsystem (D-P3-4).** The `search` predicate is a case-insensitive substring match (`_feedback_search_target().icontains(q, autoescape=True)`) over the immutable concatenation `coalesce(message,'')||' '||coalesce(comment,'')||' '||coalesce(target_text,'')||' '||coalesce(trigger_message,'')`. It is language-agnostic (Korean 조사-attached forms + English), with **no** `to_tsvector('english', …)`. A `pg_trgm` trigram GIN index (`ix_feedback_events_search_trgm`, migration `20260716_1600`) over that same expression accelerates it — the predicate expression and the index expression are kept byte-for-byte in lock-step (only immutable `||`/`coalesce`, since STABLE `concat`/`concat_ws` cannot back an expression index), and the planner uses a `Bitmap Index Scan` on it. Search is a filter, newest-first — it composes with the existing keyset paging; `list_feedback` is unchanged.
- **Usage monitoring (`src/vocky/usage_api.py`).** Three read-only endpoints (`/app/usage`, `/app/projects/{id}/usage`, `/api/project/usage`) are **pure reuse** of `get_feedback_metrics` scoped through the same `_apply_query_filters` chokepoint — no new query, table, or migration. The window defaults to the last 30 days when omitted. The per-project surfaces also list the project's credentials (surfacing the ingest-stamped `last_used_at`). This is operational visibility, not billing (D-P3-5); `serialize_metrics` is imported from `admin_api` (admin metrics untouched).

## The Web App and the BFF Boundary (P4)

P4 adds vocky's first frontend: a **Next.js app in `web/`** (D-P4-1 — a repo subdirectory, not a separate repo) that is the authenticated browser surface for tenants. It required **no backend change at all** — no new route, no CORS, no schema change. It is a pure client of the P2/P3 surfaces. Implementation detail lives in `frontend.md`; what is architectural is the boundary.

- **The app is a session-token client only.** It calls `/auth/*` + `/app/*` and **never** the `vk_`-keyed `/api/*` surface (that is the external-service credential path). Everything it renders — tenant, projects, credentials, usage, cross-project feedback search — already existed as P2/P3 endpoints.
- **The browser never talks to vocky (D-P4-2).** The Next.js server calls vocky server-to-server with `Authorization: Bearer`; the browser talks only to the Next.js origin. This is why **no CORS change was needed** and why vocky's API surface is untouched by having a web app.
- **The session token lives in a sealed httpOnly cookie**, not in browser JS. `vocky_session` = `v1.<iv>.<ct>.<tag>`, **AES-256-GCM**, key `sha256(SESSION_SECRET)`, fresh IV per seal, sealed plaintext `{token, exp}`, `SameSite=Strict`, `maxAge` 30d (matching vocky's own token TTL), `Secure` in production. The Next server unseals it per request to inject the bearer. **There is no web-side database** — the cookie is the only session state, so the app is stateless and horizontally trivial.
- **Two server-only env keys**: `VOCKY_API_BASE_URL`, `SESSION_SECRET`. Neither is `NEXT_PUBLIC_`; both are read lazily behind `server-only`. See `operations.md`.

**Two kinds of server endpoint, and the rule that separates them.** The app has both server actions and route handlers, and the split is deliberate:

- **Server actions** (3 total: create-project, mint-credential, revoke-credential) carry every **authenticated mutation**. They already have the session cookie, so they need no auth surface of their own.
- **BFF route handlers** are only the **public, unauthenticated** entry — `POST /api/auth/{login,signup,logout}` — the one place a caller has no session yet. They are the app's attack surface and run one audited pipeline (`JSON-only 415 → same-origin 403 → per-IP rate limit 429 → parse/zod 400/422 → vocky → seal cookie 200`), never echoing vocky's `detail`.
- One further route handler exists for a structural reason: the **binary attachment proxy**. The browser holds no bearer, so bytes cannot be fetched directly; the Next server relays them and **forces `Content-Disposition: attachment`** rather than serving inline. That force is a security control — the bytes and their declared content type are uploader-supplied, and `nosniff` does not help when the declared type genuinely *is* `text/html`; serving that inline from our own origin would be stored XSS against our own session cookie. See `security.md`.

**The backend's authorization stance is preserved end-to-end, not re-implemented.** The web app enforces nothing on its own: **404-never-403** on foreign ids surfaces because the app maps vocky's `404`/`400` → Next's `notFound()` (a malformed id is effectively not-found; distinguishing them would leak the shape of what exists), and legacy NULL-`project_id` rows stay invisible because `/app/feedback` already scopes them out. Tenant isolation remains a backend property; the app renders it.

**Admin-UI convergence (the P4 open question) is resolved: by replacement, not repair.** The `web/` app *is* the reshaped operator/tenant browser surface. The packaged same-origin Admin Web UI (`src/vocky/admin_ui.py`, `admin_assets/*`, the `/admin` mount) is **superseded but still mounted** — its physical removal is deferred to **P6**, when the new app is actually deployed, so no browser surface disappears in the interim. Admin REST (`/admin/api/*`) and its separate bearer boundary are untouched.

**Deployment is P6.** P4 is local-dev-runnable only (`output: "standalone"` is set for a later container, but no Dockerfile, compose service, or nginx config ships).

## The `vocky` CLI (P5)

P5 adds a **`vocky` command-line client** in `src/vocky/cli/` (a Typer app). Like the web app, it required **no backend change at all** — no new route, no schema change; it is a pure client of the existing P2/P3 surfaces. What is architectural is the boundary and the packaging.

- **A pure session-token client.** The CLI authenticates to `/auth/*` + `/app/*` with the account **session token** and drives exactly the endpoints that already existed: `signup|login|logout|whoami` (`/auth/*`), `projects` / `keys` / `usage` (`/app/*`), and read-only `feedback list|search|show` (`/app/feedback`). It **mints** `vk_` keys through `/app/*` but, like the web app, **never calls the `vk_`-keyed `/api/*` surface itself** — that is the external-service path a product backend uses. It adds no capability the API did not already have.
- **Package layout.** `src/vocky/cli/` holds `app.py` (the root `typer.Typer`, `--version`, `--base-url`, and the `CliContext` stashed on `ctx.obj`), `context.py` (shared helpers: base-URL resolution, the `authed_client()` "must be signed in" seam, `cli_errors`/`fail`), `client.py` (a sync `httpx.Client` wrapper with uniform error mapping — any authenticated `401` → "run `vocky login`"), `config_store.py` (the on-disk session/base-URL store), and one module per command group (`auth.py`, `projects.py`, `feedback.py`) each exposing `register(app)`.
- **Console-script rename.** `[project.scripts]` now maps `vocky = "vocky.cli:main"` (the CLI) and **`vocky-server = "vocky.main:main"`** (the server, renamed from `vocky`); `vocky-worker` and `vocky-smoke` are unchanged. Every server-run reference (`Dockerfile` CMD, `docker-compose.yml` app command, README) moved to `vocky-server`. `typer` was promoted from a transitive (via `mcp[cli]`) to a **direct** dependency. Install/config detail is in `operations.md`; the on-disk token posture is in `security.md`.

## MCP Write-Only Capture Surface (P7)

P7 revives the agent-decided capture path retired in P1 as a **write-only** MCP surface, re-aligned to the P2/P3 tenancy + v2-capture shape (not a verbatim restore of the retired code). It reuses the existing transport-neutral capture pipeline end-to-end — no engine change, no schema change.

- **Transport (`src/vocky/mcp_server.py`).** A module-level `FastMCP` singleton (bundled with the official `mcp[cli]` SDK) is mounted into the Starlette host via `Mount("/mcp", app=mcp.streamable_http_app())`, with the server's inner `streamable_http_path="/"` so the external endpoint is `/mcp` (a non-empty sub-path — the "no root catch-all mount" invariant still holds). `streamable_http_app()` builds its own sub-Starlette whose lifespan the host `Mount` does **not** trigger, so `create_app()`'s `lifespan` **nests `async with mcp.session_manager.run():`** around the whole app lifetime; without it `/mcp` 500s at request time. `stateless_http=True`, `json_response=True`.
- **Transport security.** `make_transport_security_settings` enables DNS-rebinding protection with a localhost allowlist (`127.0.0.1:*`, `localhost:*`, `[::1]:*`) extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`. The allowlist matcher requires a port, so a public deployment must add its `Host` (with port) to `VOCKY_MCP_ALLOWED_HOSTS`.
- **Auth (whole endpoint).** `/mcp` is guarded by the same `ProjectCredentialAuthMiddleware` as `/api/*`: its predicate is now `is_api_path(p) or is_mcp_path(p)`, so the **entire** transport (including `initialize`) requires a valid, non-revoked per-project `vk_` credential; missing/unknown/revoked answer the same generic `401`, and `last_used_at` is stamped best-effort. The static `VOCKY_MCP_AUTH_TOKEN` is **not** revived. Because the app-level middleware runs before the mount dispatches, its `scope[PROJECT_CREDENTIAL_SCOPE_KEY]` stash propagates into the mounted sub-app.
- **The `capture_feedback` tool (`src/vocky/tools/capture_feedback.py`).** The **sole** registered tool (`mcp.list_tools() == ["capture_feedback"]`), write-only. Flat parameter list (`source` nested), with an injected `ctx: Context` that FastMCP excludes from the tool schema. It builds a thin `McpCaptureFeedbackInput` → `normalize_mcp_payload` (no `attachment_ids` — agents have no upload flow), reads the stashed credential back off `ctx.request_context.request` via `get_request_credential`, stamps `payload.project_id = credential.project_id`, then `get_capture_queue().enqueue_feedback(...)` — the **same** shared queue → worker → `feedback_events` path as REST. It returns a raw `CallToolResult` (structured capture receipt, or an `isError=True` result on validation / queue failure); `install_protocol_aware_call_handler(mcp)` passes that raw result straight through as the `ServerResult` and keeps unknown-tool a protocol error.

## Configuration Surface

The runtime configuration surface is intentionally small:

- `DATABASE_URL`: PostgreSQL connection URL for the async SQLAlchemy engine and Alembic migrations
- `REDIS_URL`: Redis connection URL shared by the app enqueue path and the background worker
- `VOCKY_HOST`: application bind host
- `VOCKY_PORT`: application bind port
- `VOCKY_LOG_LEVEL`: application log level
- `VOCKY_ADMIN_AUTH_TOKEN`: optional bearer token required for Admin REST traffic. Public deployments that expose `/admin/api` should set it.

`/api/*` traffic no longer uses an env-var bearer token. The retired `VOCKY_API_AUTH_TOKEN` / `api_auth_token` setting has been removed; `/api/*` is now authenticated exclusively by per-project credentials minted through `/app/*`, and auth is mandatory rather than deployment-optional. `/mcp` uses the **same** per-project credential auth (P7); the retired static `VOCKY_MCP_AUTH_TOKEN` / `mcp_auth_token` setting is likewise not restored.
- `VOCKY_MCP_ALLOWED_HOSTS`: comma-separated extra `Host` values allowed by the `/mcp` DNS-rebinding matcher (P7). Localhost (`127.0.0.1:*`, `localhost:*`, `[::1]:*`) is always allowed; a public deployment must add its public `Host` **with port**. Default `""`.
- `VOCKY_MCP_ALLOWED_ORIGINS`: comma-separated extra `Origin` values allowed by the `/mcp` DNS-rebinding matcher (P7). Localhost origins are always allowed. Default `""`.
- `VOCKY_ATTACHMENTS_DIR`: directory the local attachment storage backend reads and writes. In Docker this is a named volume mounted on both the app and worker.
- `VOCKY_ATTACHMENTS_MAX_BYTES`: maximum size in bytes of a single uploaded attachment. Default `5242880` (5 MiB).
- `VOCKY_ATTACHMENTS_MAX_COUNT`: maximum number of attachments that may be linked to one feedback event. Default `10`.
- `VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES`: comma-separated allowed attachment MIME types, validated by magic-byte sniffing. Default `image/jpeg,image/png,image/gif,image/webp`.

The supported local operator workflow adds these host-side settings:

- `TEST_DATABASE_URL`: dedicated disposable PostgreSQL database used by `make test`. It must not point at the same database as `DATABASE_URL`.
- `VOCKY_PUBLISH_HOST`: host interface Docker Compose publishes the app port on. The default is `127.0.0.1` for local-only access.
- `POSTGRES_PUBLISH_HOST`: host interface Docker Compose publishes PostgreSQL on. The default is `127.0.0.1`.
- `REDIS_PUBLISH_HOST`: host interface Docker Compose publishes Redis on. The default is `127.0.0.1`.
- `VOCKY_BASE_URL`: optional override for host-side smoke checks when the public base URL differs from `http://127.0.0.1:${VOCKY_PORT}`.
- `VOCKY_EXTERNAL_BASE_URL`: optional external URL used for public custom-domain deployments through Cloudflare Tunnel or another HTTPS reverse proxy, for example `https://vocky.example.com`.

`VOCKY_HOST` remains the application bind address inside the process. The `*_PUBLISH_HOST` variables control which host interface Docker publishes to. `VOCKY_BASE_URL` remains the local verification target, while `VOCKY_EXTERNAL_BASE_URL` is reserved for public custom-domain operator docs and client examples.

The root `.env`, copied from `.env.example`, is the primary local configuration source for both Docker Compose and the Make-based host workflow. The Compose app service receives its Admin auth setting (`VOCKY_ADMIN_AUTH_TOKEN`) from this file; `/api/*` auth is no longer env-configured (per-project credentials replaced `VOCKY_API_AUTH_TOKEN`). The supported self-hosted path remains Compose-first and includes Redis plus the worker process. `make bootstrap` should bring up the service dependencies, apply migrations, and wait for readiness. `make verify` should build and inspect a fresh wheel for packaged Admin UI assets, wait for readiness, verify the eventual write path with the REST smoke flow, and run the test suite. `make compose-down` should tear the stack back down.

The supported operator modes are:

- Internal self-hosting: Compose publishes on loopback by default and host-side checks use `VOCKY_BASE_URL`.
- Public custom-domain deploy: operators can publish the app through Cloudflare Tunnel or another HTTPS reverse proxy, set `VOCKY_EXTERNAL_BASE_URL` to the public origin such as `https://vocky.example.com`, and require `VOCKY_ADMIN_AUTH_TOKEN` before exposing Admin REST. `/api/*` is always credential-authed (per-project keys), so it needs no extra env gating before exposure. `make external-smoke` and `make external-verify` run the public checks against `VOCKY_EXTERNAL_BASE_URL`.

The `/admin` shell and `/admin/assets/*` static assets, including packaged operator docs, can load without server-side auth, but protected Admin data remains unavailable unless the browser supplies the configured Admin bearer token to `/admin/api/*`. `/api/*` and `/admin/api/*` have separate auth boundaries: `/api/*` requires a per-project credential and `/admin/api/*` uses the Admin bearer token. (The packaged Admin Docs try-it block still references the retired `VOCKY_API_AUTH_TOKEN`. P4 superseded that surface with the `web/` app rather than updating it; the packaged UI and its stale docs are removed in P6.)

The `web/` app has its own, separate configuration surface — two server-only keys, `VOCKY_API_BASE_URL` and `SESSION_SECRET` — documented in `operations.md`. It shares no env with the service and needs no DB or Redis credentials.

For Cloudflare Tunnel users, the recommended public shape is a hostname-to-service mapping from `vocky.example.com` to `http://127.0.0.1:8000`, with the local Vocky process still bound behind the tunnel and no inbound origin port requirement.

## MVP Boundaries

- Multi-tenant: real accounts, tenants, projects, and per-project credentials; the MVP tenancy flow is solo-owner (invites/roles management UI is out of scope)
- Capture ingestion is server-to-server REST **plus** a write-only MCP `capture_feedback` tool (P7) for agents; browser-direct unauthenticated ingestion is outside scope. MCP is write-only — no MCP read/query tools
- `/api/*` and `/mcp` ingest auth is mandatory per-project credential auth; there is no unauthenticated or globally-shared-token ingest path
- Free service — no billing, usage metering, or plan tiers
- No automatic classification or summarization in the MVP
- Admin Web UI includes a same-origin self-hosted operator shell, dashboard metrics, recent activity, feedback list/filter/detail inspection, review-field editing, guarded delete, in-app operator docs, and an operator-only REST capture try-it form. **Superseded as of P4** by the `web/` app (its packaged docs still reference the retired static token and are not current guidance); it stays mounted until P6 removes it
- The `web/` Next.js app (P4) is vocky's authenticated browser surface for tenants: signup/login, tenant dashboard, project detail with credential mint/revoke, and cross-project feedback read/search. It is a session-token BFF client of `/auth/*` + `/app/*` — never the `vk_`-keyed `/api/*` surface — and adds no backend capability of its own. Feedback **management** is not in it (that stays on `/api/project/feedback`); production deploy is P6
- Channel handling uses the built-in nullable MVP categories `web`, `mobile`, and `support`; custom category management and deployment-configured category lists are outside the MVP
- No separate Admin REST database or per-surface feedback store
- Feedback is project-scoped: `feedback_events.project_id` is stamped at capture from the authenticating credential; project-scoped review/manage (`/api/project/feedback`), cross-project read/search (`/app/feedback`), and derived usage monitoring are implemented. Usage is operational only — derived capture volume + last-used, no metering/billing
- No public job-status API or dashboard in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, explicit feedback value, optional comment, nullable channel category, the exact reviewed target when available, surrounding conversation messages, used context, creation time, and optional caller-provided tags or attributes.
- `message` is the required human-readable feedback summary or display text. It is not an implicit target selector.
- `conversation_id` identifies the conversation or thread that the feedback belongs to.
- `session_id` is optional runtime, browser, or user-session scope that can correlate repeated interactions without replacing `conversation_id`.
- `user_id` is an optional caller-owned end-user or account-member identifier. It is stored as opaque identity context and does not replace `session_id`, product auth, or tenancy concepts.
- Trigger fields preserve why capture happened: `trigger_type` stores the normalized trigger category, `trigger_message` stores optional event copy or action text, and `trigger_metadata` stores structured trigger-specific context.
- `channel` is an optional nullable review category. New captures and Admin edits should only assign `web`, `mobile`, `support`, or `null`; blank input is normalized to `null`, and no channel is inferred by default.
- Target fields identify the exact reviewed item when known: `target_type` describes whether the target is a `message`, whole `conversation`, or product/UI `surface`; `null` means no exact target category was supplied; `target_id` stores the caller's stable identifier; `target_role` stores the reviewed message role when applicable; and `target_text` stores a snapshot of the exact reviewed text.
- `messages` stores surrounding conversation context supplied by the caller. `used_context` stores context that the agent used while producing the reviewed response.
- REST product or website feedback can omit conversation-specific fields and store page, widget, URL, account, or runtime context in `target_*`, `source_metadata`, and `attributes`.
- The storage layer only needs to support the retrieval and aggregate queries required by the scoped end-user read and Admin REST review surfaces; it does not need analytics-warehouse style modeling for the first MVP.

## Field Responsibilities

The capture schema backs public REST capture. The fields are organized by responsibility so callers can choose the right amount of context without creating transport-specific payload shapes or split storage. Admin REST reads the same stored shape and can manage only the fields that are review-oriented in the current MVP.

| Responsibility | Current fields | Role |
| --- | --- | --- |
| Display and action | `message`, `feedback_value`, `comment` | Human-readable record label plus explicit like, dislike, or comment details. |
| Source identity | `source.product` / `source_product`, `source.integration` / `source_integration` | Caller-provided product and integration identity for grouping and filtering. |
| Caller identity | `user_id` | Caller-owned opaque user or account-member identity associated with the feedback event. |
| Trigger context | `trigger_type`, `trigger_message`, `trigger_metadata` | Captures the action, copy, survey, rating, manual workflow, or other product event that caused feedback capture. |
| Review category | `channel`, `tags` | Operator-facing classification and exact filters. `channel` is constrained for new writes; `tags` remain caller-provided labels. |
| Exact target | `target_type`, `target_id`, `target_role`, `target_text` | Identifies the reviewed message, conversation, or product surface when known. `target_type` is the first-class review discriminator. |
| Conversation and session context | `conversation_id`, `session_id`, `messages` | Groups records with conversation/thread scope, runtime/session scope, and supplied surrounding messages. |
| Agent and process context | `used_context` | Preserves the documents, snippets, tool context, or other context the agent used while producing the reviewed response. |
| Metadata | `id`, `event_at`, `ingested_at`, `source_metadata`, `attributes` | Stores record identity, event and ingest time, source-specific context, and product-specific dimensions. |

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
- `user_id TEXT` null
- `trigger_type TEXT` null, accepted values `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`
- `trigger_message TEXT` null
- `trigger_metadata JSONB` not null with default empty object
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

Indexes for the intended P1 read model should cover:

- `ingested_at`
- `event_at`
- `source_product`
- `feedback_value`
- `channel`
- `conversation_id`
- `session_id`
- `user_id`
- `trigger_type`
- `target_type`
- GIN on `tags`

The schema keeps the most important review dimensions visible as first-class columns while leaving room for source-specific metadata in JSONB fields. `channel` remains nullable `TEXT` rather than a database enum so older arbitrary channel values can stay readable and exact-filterable without destructive migration; write validation prevents new arbitrary channel values on capture and Admin edits. `target_type` is the only target field promoted to a first-class review discriminator in P1; other target fields remain captured context and are not filters or editable review fields.

## Operator Comment Store

Operator-authored comments are a separate first-class store, not an overload of the user-supplied `comment` column on `feedback_events` (which remains the end user's own comment captured at feedback time). The store lets operators annotate a stored feedback event for review and for one-way operator-to-user visibility.

The secondary table is `feedback_comments`:

- `id UUID` primary key
- `feedback_id UUID` not null, foreign key to `feedback_events.id` with `ON DELETE CASCADE` (deleting a feedback event removes its comments)
- `author TEXT` null, an optional caller-supplied operator label; Vocky has no native operator accounts
- `body TEXT` not null, the comment text
- `created_at TIMESTAMPTZ` not null, defaulting to `CURRENT_TIMESTAMP`

Indexes cover `feedback_id` and the composite `(feedback_id, created_at)` so a single feedback event's comments and batched multi-event lookups both read efficiently. Comments are returned oldest-first ordered by `(created_at, id)`. The repository exposes a batched `list_comments_for_feedback_ids` so list-style reads (the end-user feedback read) fetch all comments for a page in one query instead of N+1 per-record lookups. This is the only genuinely new subsystem in P1; the comment store reuses the same SQLAlchemy async session, repository, and service layering as `feedback_events`, with the same `FeedbackPersistenceError` / `FeedbackReadError` wrapping.

The async capture path is layered as:

- REST route input normalization and error mapping
- Redis enqueue on the request path
- A dedicated worker process
- A transport-neutral feedback service
- A repository backed by SQLAlchemy async sessions
- PostgreSQL plus Alembic-managed schema

The read path reuses the same service and repository layers:

- REST route input normalization and error mapping for the scoped end-user read and Admin REST list/detail
- Transport-neutral read methods on the feedback service
- Repository queries against `feedback_events`
- A single scoped public REST read (`GET /api/feedback`) over the same service and repository, restricted to one user's own records by required `user_id` + `source_product` and returning operator comments via a batched `feedback_comments` fetch; no broad public REST query stack

The Admin dashboard metrics path uses the same read layers:

- Admin REST query normalization and JSON error mapping for `GET /admin/api/feedback/metrics`
- Required timezone-aware `start_ingested_at` and `end_ingested_at` query parameters normalized to UTC
- A transport-neutral feedback service metrics method backed by repository aggregates over `feedback_events`
- UTC day bucketing with zero-filled daily buckets for the requested inclusive-start/exclusive-end ingest-time window
- Aggregate counts for total records, likes (`feedback_value = 1`), dislikes (`feedback_value = 2`), and unrated records (`feedback_value is null`)

## File Storage Subsystem

Vocky stores feedback image attachments as opaque binary objects outside the database, behind a small storage seam so the backend can change without touching callers. This is the first file-storage subsystem in the codebase.

- `AttachmentStorage` (`src/vocky/storage/base.py`) is the backend-neutral interface: `save(key, data)`, `load(key) -> bytes`, and `delete(key)`. It raises `StorageError` for write/read/delete failures and `StorageObjectNotFoundError` (a `StorageError` subclass) when an object is missing.
- `LocalFilesystemAttachmentStorage` (`src/vocky/storage/local.py`) is the only implementation today. It stores each object as a file under `VOCKY_ATTACHMENTS_DIR`, rejects keys that are absolute or escape the root (`resolve()` + `is_relative_to`), creates intermediate directories, and writes through a sibling temp file plus atomic `os.replace` so a reader never observes a partial object.
- `get_attachment_storage()` (`src/vocky/storage/__init__.py`) is the dependency accessor, mirroring `get_feedback_service()`: it returns a backend built from the cached settings.

An S3-compatible backend is deliberately deferred behind this same interface; storage keys are server-generated UUIDs (never client filenames), so adding object-store backends needs no key-format change. Size, count, and allowed-type limits are configuration (`VOCKY_ATTACHMENTS_*`) and are enforced at the HTTP and capture layers, not inside the storage backend, which stays a dumb byte store.

## Feedback Attachment Store

Attachment metadata lives in a `feedback_attachments` table; the bytes live in the File Storage Subsystem above, referenced by `storage_key`. The table mirrors `feedback_comments` but its `feedback_id` is nullable because attachments are uploaded before the feedback row exists (see Async Capture and Attachment Linking).

- `id UUID` primary key
- `feedback_id UUID` **nullable**, foreign key to `feedback_events.id` with `ON DELETE CASCADE`. Nullable because an attachment is uploaded and stored before the async capture path persists its feedback row; the worker links it afterward. The cascade still applies once linked, so deleting a feedback event removes its attachment rows.
- `storage_key TEXT` not null, the server-generated UUID key into the storage backend
- `content_type TEXT` not null, the MIME type derived from magic-byte sniffing at upload (never the client-declared header)
- `byte_size INTEGER` not null
- `filename TEXT` null, the client-supplied display name (sanitized when echoed in headers)
- `claimed_user_id TEXT` null, the `user_id` asserted at upload time
- `claimed_source_product TEXT` not null, the `source_product` asserted at upload time
- `created_at TIMESTAMPTZ` not null, defaulting to `CURRENT_TIMESTAMP`

Indexes cover `feedback_id`, the composite `(feedback_id, created_at)` for a single event's attachments and batched multi-event lookups, and `created_at` to keep the deferred orphan-upload sweep (`D3`) cheap. The repository exposes a batched `list_attachments_for_feedback_ids` mirroring the comment store so list reads stay free of N+1 lookups.

The `claimed_user_id` / `claimed_source_product` columns are the identity binding that makes "an end user sees only their own attachments" enforceable. The worker links an attachment only when its claimed scope matches the feedback event's `(user_id, source_product)` via a guarded `UPDATE ... WHERE feedback_id IS NULL AND claimed_source_product = :sp AND claimed_user_id = :uid` (with an `IS NULL` branch for anonymous feedback). The `feedback_id IS NULL` guard makes linking idempotent and blocks one feedback event from stealing another's attachment. The store reuses the same SQLAlchemy async session, repository, and service layering as `feedback_events`, with the same `FeedbackPersistenceError` / `FeedbackReadError` wrapping; `create_feedback_event_with_attachments` performs the event insert and the guarded link in one transaction.

Reads and downloads reuse the P1 scoping model. The operator-review detail and the scoped end-user read each inject an `attachments` array (oldest-first), fetched with a single batched `list_attachments_for_feedback_ids` query alongside comments to avoid N+1 lookups. Bytes are served by authenticated download endpoints: the operator download (`/admin/api/feedback/{id}/attachments/{id}`, admin token) serves any attachment linked to that feedback; the end-user download (`/api/feedback/{id}/attachments/{id}`) is authorized off the linked feedback row's `(user_id, source_product)` and answers `404` on any mismatch, unlinked attachment, or missing object so existence is never leaked, with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. Deleting a feedback event cascades the attachment rows; the admin delete path gathers the attachments' `storage_key`s in the same transaction before the cascade and then deletes the files best-effort (logged, never failing the committed delete). Never-linked uploads are the only residue and are left to the deferred orphan sweep (`D3`). In Docker the attachment files live on a named volume mounted on both the app and worker at `VOCKY_ATTACHMENTS_DIR`.

## Async Capture and Attachment Linking

Capture is asynchronous (`202 Accepted` → Redis queue → worker persist), and the feedback row's UUID exists only after the worker persists it, so attachments cannot be created at capture time and binaries cannot ride the JSON queue. The adopted protocol is upload-first async-link:

- The client uploads each image synchronously to `POST /api/feedback/attachments` and receives an `attachment_id` for an unlinked `feedback_attachments` row that records the bytes' `storage_key` and the claimed `(user_id, source_product)`.
- The capture payload carries `attachment_ids` (UUID strings only) through the existing Redis queue. The queue serializer adds `attachment_ids` to its explicit field allowlist and the deserializer defaults it to empty, so jobs enqueued before this field existed still deserialize.
- When a job carries non-empty `attachment_ids`, the worker calls `create_feedback_event_with_attachments`, which inserts the feedback row and runs the guarded scope-verified link in one transaction. A job with no attachments takes the unchanged `create_feedback_event` path. Missing, mis-scoped, or already-linked attachments are skipped and logged; they never dead-letter the job, because a missing screenshot must not fail real feedback.

REST capture validates and normalizes `attachment_ids` (parse to UUID, dedupe, cap at `VOCKY_ATTACHMENTS_MAX_COUNT`).

## Query Read Model

The implemented P1 read query model uses these constraints:

- Read filters are limited to `ingested_at`, `source_product`, `source_integration`, `conversation_id`, `session_id`, `user_id`, `feedback_value`, `channel`, `target_type`, `trigger_type`, and exact single-tag membership.
- The P1 read model does not add filters for `trigger_message`, `trigger_metadata`, `target_id`, `target_role`, `target_text`, arbitrary JSONB fields, or records where an optional string field is unset.
- Channel read filters use exact matching after trimming blank input to absence. They should continue to support legacy stored channel strings even though new capture and Admin edit writes are limited to `web`, `mobile`, `support`, or `null`.
- `target_type` read filters use exact matching after trimming blank input to absence. Accepted non-blank filter values are `message`, `conversation`, and `surface`; this phase does not add filters for `target_id`, `target_role`, `target_text`, or records where `target_type is null`.
- `trigger_type` read filters use exact matching after trimming blank input to absence. Accepted non-blank filter values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`; this phase does not add a filter for records where `trigger_type is null`.
- Time filtering uses `ingested_at` only. `start_ingested_at` is inclusive and `end_ingested_at` is exclusive after normalization to UTC.
- The list reads (the scoped end-user `GET /api/feedback` and `GET /admin/api/feedback`) return full stored records ordered newest-first by `(ingested_at desc, id desc)`.
- The list reads default to `50` records per page and reject values outside `1` through `100`.
- List pagination uses an opaque base64url-encoded JSON cursor derived from the last returned record's `ingested_at` and `id`.
- `GET /admin/api/feedback/metrics` returns window totals plus UTC `daily_counts`, with zero-filled missing days inside the requested window.
- The base phase does not add full-text search, JSONB filtering, target-id filtering, target-role filtering, target-text filtering, or new summary dimensions.
- Admin dashboard metrics remain ingest-window-only and do not add `user_id`, `trigger_type`, trigger-message, trigger-metadata, or other dimension filters in this phase.
- The list reads return action fields and stored JSON context with each record so operators can inspect likes and dislikes without a separate transcript store.
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
- Return REST capture validation failures as `400` JSON responses.
- Reject non-null channel values outside `web`, `mobile`, and `support` on new REST capture and Admin REST patch writes.
- Normalize optional string capture fields, including `user_id`, `trigger_type`, and `trigger_message`, by trimming leading and trailing whitespace and converting blank values to `null`.
- Reject non-null `trigger_type` values outside `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other` on REST capture writes.
- Require `trigger_metadata` to be a JSON object when supplied; omit or default it to `{}` when absent.
- Return REST queue-accept failures as `503` JSON responses.
- Return REST read validation failures as `400` JSON responses and storage read failures as JSON error responses (`500`, or `503` for attachment downloads).
- Keep public REST capture and Admin REST handlers separate while sharing validation helpers, service, queue, and repository layers where appropriate.

## Open Questions

- When the packaged same-origin Admin Web UI is physically removed (`admin_ui.py`, `admin_assets/*`, the `/admin` mount) — **P6**, once the `web/` app is deployed. P4 answered the *convergence* question (the web app replaces it as the browser surface); what remains is only the removal timing. Whether Admin REST (`/admin/api/*`) itself outlives the UI it served is a separate open question
- Whether the `web/` app should ever surface feedback **management** (PATCH/DELETE/comments). P4 deliberately kept it read+search only, since management lives on the `vk_`-keyed `/api/project/feedback`; a signed-in owner arguably wants it too, but that would be a new decision
- Whether completed-job receipts or dead-letter inspection should become part of a later public review surface
- Whether the end-user attachment download (`GET /api/feedback/{id}/attachments/{id}`) should also be project-scoped for parity with the D-P3-6 self-read tightening (currently `user_id`+`source_product`+exact-UUID scoped; a possible future hardening)
- Whether per-credential scopes are ever needed (P3 MVP deliberately gives one `vk_` key full capture + project read/manage)
