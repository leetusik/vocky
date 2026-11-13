---
doc_id: backend
version: v0005
created_at: 2026-07-28T23:47:56+09:00
source: P10.REVIEW
summary: P10: accounts gains provision_signup, get_or_create_project, get_project_by_name, list_org_credentials and get_credential; auth gains the credential project-scope resolver; capture gains resolve_capture_project
previous: v0004_p6_create_app_no_longer_registers_admin_ui_routes_the_admin_web_ui_module_and_its_assets_are_deleted_middleware_and_the_admin_api_routes_are_unchanged
---

# Backend

## Status

This doc covers the **accounts / identity backend** landed in P2: the `src/vocky/accounts/` domain package, the reusable user-auth guard, the security primitives, and the `/auth/*` + `/app/*` route modules and their app wiring. As of **P7** it also covers the **MCP capture backend**: the FastMCP server bootstrap (`src/vocky/mcp_server.py`), the write-only `capture_feedback` tool module (`src/vocky/tools/capture_feedback.py`), the broadened ingest guard (`is_mcp_path`), and the thin MCP input model. As of **P6** it also records the **removal of the packaged Admin Web UI** from the backend (see "Admin Web UI Removal" below) — a deletion only; no accounts, MCP, or Admin REST behavior changed. As of **P10** it covers the **org-level credential backend** — new accounts primitives, the credential project-scope resolver, and the shared ingest project resolver (see "P10 Additions" below). The feedback capture/read backend (service, repository, worker, queue, storage) is documented in `architecture.md`; this doc does not repeat it.

## P10 Additions — org-level credentials

New primitives, grouped by module. The design rationale is in `architecture.md` ("Credential Project Scope") and the boundary consequences in `security.md`; this is the API surface.

**`src/vocky/accounts/` (types)**
- `ProjectCredentialRecord` and `CreateProjectCredential` gained **`tenant_id: UUID`** (always set, at both scopes) and their `project_id` widened to **`UUID | None`**. `CreateProjectCredential` requires **both** with **no defaults** — deliberately, so an org-level mint has to say `project_id=None` out loud rather than fall into it.
- Because the record already carries `tenant_id`, an org key's org identity is available to the resolver with **zero extra queries** — it is on the record the middleware resolves by `token_hash`.

**`src/vocky/accounts/service.py` / `repository.py`**
- `provision_signup(user_id, tenant_name)` — org + owner membership + the `"default"` project in **one session, one commit**. Returns `(tenant, member, project)`. (vocky has no session-injection seam, so atomicity comes from the shared session.)
- `get_or_create_project(tenant_id, name)` — race-safe against the new `UNIQUE (tenant_id, name)`: read-first → insert → catch `IntegrityError` → rollback → re-read. **Its `except` nesting is load-bearing** — `IntegrityError` *is* a `SQLAlchemyError`, so the race handler only ever runs because it is nested **inside** the outer `except SQLAlchemyError`. Flattening the two into sibling clauses silently turns every duplicate-name race back into a 500. There is a comment in the code saying so; do not "tidy" it.
- `get_project_by_name(tenant_id, name)` — resolves **oldest-wins** by `(created_at, id)`, deliberately the same order migration `20260728_1200`'s de-dupe picks its survivor by, so the migration and the runtime agree on which row "the" project is.
- `list_org_credentials(tenant_id)` — `tenant_id = :tid AND project_id IS NULL`, ordered `(created_at, id)`, revoked included.
- `get_credential(credential_id)` — an **unscoped by-PK read**; the *caller* owns the ownership check, and there is no safety net in the repository layer. It is deliberately not modelled on `delete_credential`'s list-and-scan-in-Python shape: one indexed read plus an explicit check is O(1) and states the rule in one place.
- Constant `DEFAULT_PROJECT_NAME = "default"` lives in `vocky.accounts.service` and is re-exported from `vocky.accounts`. There is deliberately **no `DEFAULT_ORG_NAME`** — the org keeps `f"{email.split('@')[0]}'s workspace"`, and a test asserts the constant's *absence* so a later slice adopting a literal `"default"` org fails loudly instead of drifting.

**`src/vocky/auth.py`**
- `resolve_credential_project_ids(credential) -> tuple[UUID, ...]`, `get_request_project_ids(request) -> tuple[UUID, ...]`, and `CREDENTIAL_PROJECT_IDS_SCOPE_KEY = "vocky.credential_project_ids"`. **`get_request_project_ids` is the only correct way to scope a credential-authenticated read or write**; `credential.project_id` is nullable and a `None` project filter reads every project in every tenant. The non-`None` return type *is* the enforcement.
- `get_request_credential` survives only where a handler needs the credential's **shape** (the serializer fork) or passes it to the capture resolver.

**`src/vocky/capture.py`**
- `resolve_capture_project(credential, project_name) -> UUID` and `MAX_CAPTURE_PROJECT_NAME_LENGTH`. It lives here so both the REST writer and the MCP tool can import it without a cycle (`app_api` is deliberately not reached into). It never returns `None`.
- `RestCaptureFeedbackInput` gained `project: str | None = None`; the MCP `capture_feedback` tool gained the same argument (placed after `channel`, **`ctx` still last**). The MCP one is deliberately **not** routed through `McpCaptureFeedbackInput` — the project is stamped onto the normalized payload after `normalize_mcp_payload`, outside caller control.

**`src/vocky/feedback/types.py`**
- **`FeedbackQueryFilters.project_id` and its `_apply_query_filters` branch are deleted.** Project scoping is expressible only as `project_ids`, a set — so the "`None` means no filter" footgun no longer exists in the type.

**Rewrites rather than additions**
- `project_feedback_api._load_project_feedback` is now **set membership** rather than equality, which also excludes legacy NULL-`project_id` rows for free.
- `usage_api._project_usage_response` is **scope-taking** (`project_ids: tuple[UUID, ...]`) with a keyword-only `org_tenant_id` that unions org-level rows in for an org-level caller only. Per-project listings each sort `(created_at, id)`, but concatenating several does not, so it re-sorts on the same key — chosen to match the repository's `ORDER BY` exactly, which is why a single-project payload stays byte-identical.
- `serialize_credential` is **NULL-safe** (`str(x) if x is not None else None`); it is shared with both `usage_api` surfaces, so the fix covers all of them at once.
- **`serialize_project` moved from `app_api` to `auth_api`** (signup now returns a project). `app_api → auth_api` is the pre-existing import direction and the reverse would cycle, so it moved rather than being duplicated. **Anything needing `serialize_project` must import it from `auth_api`.**

## Accounts Domain Package (`src/vocky/accounts/`)

Mirrors the `src/vocky/feedback/` triad so the layering is consistent across domains:

- **`types.py`** — transport-neutral dataclasses (`kw_only`, `slots`): `CreateUser`/`UserRecord`, `TenantRecord`, `TenantMemberRecord`, `CreateProject`/`ProjectRecord`, `CreateProjectCredential`/`ProjectCredentialRecord`, `CreateAuthToken`/`AuthTokenRecord`. No ORM object crosses this boundary. Records carry only metadata; `ProjectCredentialRecord`/`AuthTokenRecord` never expose `token_hash`, and raw session tokens / project keys are never returned by any record.
- **`repository.py`** (`AccountsRepository`) — the sole ORM boundary. Maps `Create*` inputs to models and models to `*Record` outputs; flushes/refreshes but **never commits** (the service owns the transaction). Key reads: `get_user_by_email` / `get_user_by_id`, `list_tenants_for_user` (join through `tenant_members`, oldest-first), `list_projects_for_tenant` (tenant-scoped, oldest-first), `get_active_credential_by_token_hash` (filters `revoked_at IS NULL`), `get_active_auth_token_by_hash` (filters `expires_at IS NULL OR expires_at > now()`). Writes: `create_user`, `create_tenant` + `add_tenant_member`, `create_project`, `create_project_credential`, `create_auth_token`. Lifecycle: `revoke_credential` (idempotent soft-revoke), `delete_auth_token` (logout; returns whether a row was removed), and `touch_*_last_used` stamps (unused in P2, reserved for P3).
- **`service.py`** (`AccountsService`, `get_accounts_service()`) — owns the async session lifecycle (open, commit/rollback) and translates SQLAlchemy errors into domain errors: `AccountsPersistenceError` / `AccountsReadError`, plus `DuplicateEmailError` (a subclass raised when `create_user` hits the single `uq_users_email` unique constraint, so signup can answer a clean `409`). `create_tenant_with_owner(user_id, name)` inserts the tenant + `owner` membership in one transaction — the signup primitive. `get_accounts_service()` returns a service bound to the shared `get_session_maker()`, mirroring `get_feedback_service()`.

## Security Primitives (`src/vocky/accounts/security.py`)

Pure functions, no HTTP or persistence surface:

- `hash_password(password)` / `verify_password(password_hash, password)` — argon2id via `argon2-cffi` (new dependency `argon2-cffi==25.1.0`). `verify_password` returns `False` (never raises) on a mismatch or a malformed stored hash, so login can answer an identical generic 401.
- `generate_opaque_token()` — a high-entropy URL-safe token (`secrets.token_urlsafe(32)`), used for both session tokens and (with a `vk_` prefix) project keys.
- `sha256_hex(raw)` — the hex sha256 digest stored at rest for session tokens and credential keys (raw values are never persisted).

## User-Auth Guard (`src/vocky/accounts/auth.py`)

The reusable guard imported by every `/app/*` handler and by `/auth/me`:

- `AuthContext(user, tenant)` — the authenticated caller (their `UserRecord` + active `TenantRecord`).
- `AuthError` — raised on any authentication miss.
- `require_user(request) -> AuthContext` — extracts the bearer token, hashes it, resolves the active `auth_token`, loads the user, and picks their first tenant (solo-owner MVP). Any miss raises `AuthError`. It does **not** touch `last_used_at` (deferred to P3).
- `auth_error_handler(request, exc)` — renders `AuthError` as `401 {"detail":"Unauthorized"}` with `WWW-Authenticate: Bearer`. Host apps register it via `exception_handlers={AuthError: auth_error_handler}`; `create_app()` already does.
- `extract_bearer_token(request)` — scheme-insensitive bearer extraction, returns `None` when absent or malformed.

## Route Modules

- **`src/vocky/auth_api.py`** — the public `/auth/*` routes (`signup`, `login`, `logout`, `me`). Pydantic `SignupInput`/`LoginInput` normalize email (trim + lowercase, must contain `@`) and require an 8+ char password. Signup calls `create_user` then (P10) **`provision_signup`** — org + owner membership + the `"default"` project in one commit — then mints a token; login verifies the password and mints a token, returning an identical generic 401 for unknown-email vs wrong-password (no enumeration). **`create_user` still commits in its own transaction ahead of `provision_signup`, so a failure between them still orphans an org-less user: narrowed, not closed, and `signup`'s docstring says so.** `SESSION_TTL = timedelta(days=30)`. Serializers `serialize_user` / `serialize_tenant` / **`serialize_project`** (moved here from `app_api`) expose only `{id, email, created_at}` / `{id, name, created_at}` / `{id, name, tenant_id, created_at}`; the signup response carries an additive `project`. Reuses `format_pydantic_error` from `vocky.api` rather than redefining it.
- **`src/vocky/app_api.py`** — the session-token-authed `/app/*` control-plane: `get_tenant`, `list_projects`, `create_project`, `get_project`, the per-project credential handlers `create_credential` / `list_credentials` / `delete_credential`, and (P10) the org-level `create_org_credential` / `list_org_credentials` / `delete_org_credential`. Every handler starts `ctx = await require_user(request)`. Per-project reads/mutations go through `_load_scoped_project`, which resolves the project and returns a `400` (malformed id) or `404` (missing **or** cross-tenant) response before any work — the cross-tenant-isolation rule (404, never 403). `create_credential` mints `key = "vk_" + generate_opaque_token()`, stores `token_hash = sha256_hex(key)` + `token_prefix = key[:12]`, and returns the plaintext `key` once; the org-level mint is identical except `project_id=None`. `delete_org_credential` does **one** `get_credential` by PK and then checks `record.tenant_id == ctx.tenant.id and record.project_id is None`, 404ing otherwise — so a project-bound credential of the caller's own tenant 404s here too. The pre-existing per-project `delete_credential` still lists-and-scans in Python and was deliberately left alone; it is still correct, and rewriting it was not P10's job. `serialize_project` now lives in `auth_api`; `serialize_credential` → `{id, project_id, name, token_prefix, created_at, last_used_at, revoked_at}` with `project_id` **nullable** (never `token_hash`).

## MCP Capture Backend (P7) — `src/vocky/mcp_server.py`, `src/vocky/tools/capture_feedback.py`

The write-only MCP capture surface (architecture: "MCP Write-Only Capture Surface"). Two new modules plus a broadened guard and a thin input model:

- **`src/vocky/mcp_server.py`** — bootstraps a module-level `FastMCP` singleton (`streamable_http_path="/"`, `json_response=True`, `stateless_http=True`, `transport_security=make_transport_security_settings(settings)`), imports `vocky.tools.capture_feedback` for side-effect tool registration, then calls `install_protocol_aware_call_handler(mcp)`. Helpers: `make_transport_security_settings` (DNS-rebinding on + localhost allowlist merged with `VOCKY_MCP_ALLOWED_HOSTS/_ORIGINS` via `append_unique`), `make_error_result`, and `install_protocol_aware_call_handler` (a `CallToolRequest` handler that returns a tool's raw `CallToolResult` straight through as the `ServerResult`, maps a caught tool exception to an error result, and raises `McpError(INVALID_PARAMS)` for an unknown tool).
- **`src/vocky/tools/capture_feedback.py`** — the sole `@mcp.tool(name="capture_feedback")`. Flat parameter list (`source` nested) plus an injected `ctx: Context` that FastMCP excludes from the tool schema. Body: build `McpCaptureFeedbackInput` → `normalize_mcp_payload` (→ `error_result` on `CaptureFeedbackValidationError`) → read the stashed credential via `get_request_credential(ctx.request_context.request)` and set `normalized.payload.project_id = await resolve_capture_project(credential, project)` (P10 — was a direct `credential.project_id` read) → `get_capture_queue().enqueue_feedback(...)` (→ `error_result("capture queue unavailable")` on `CaptureQueueError`) → return a `CallToolResult` with `structuredContent` from `serialize_capture_receipt(...)`. A defensive `None`-request guard never fires because the middleware enforces auth on the whole endpoint.
- **`src/vocky/auth.py`** — added `is_mcp_path(path)` (`== "/mcp"` or `startswith("/mcp/")`) and broadened `ProjectCredentialAuthMiddleware`'s predicate to `is_api_path(p) or is_mcp_path(p)`, so the whole `/mcp` endpoint reuses the same `vk_` resolution, generic 401, scope stash, and best-effort `last_used_at` stamp as `/api/*`. `get_request_credential` is now valid for `/api/*` **and** `/mcp` requests.
- **`src/vocky/capture.py`** — added the thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` (empty subclass, no `attachment_ids`) and `normalize_mcp_payload` next to the REST pair. No engine change — `_normalize_capture_payload` reads `attachment_ids` via `getattr`.

## App Wiring (`src/vocky/app.py`)

`create_app()` registers routes in order: `/healthz`, `*auth_routes`, `*app_api_routes`, `*app_feedback_routes`, `*usage_routes`, `*admin_routes`, `*api_routes`, `*project_feedback_routes`, `*attachment_routes`, and (P7) a trailing `Mount("/mcp", app=mcp.streamable_http_app())` — kept last so it cannot shadow the core routes. **(P6: the `*admin_ui_routes` spread and its `from vocky.admin_ui import routes as admin_ui_routes` import were removed with the Admin Web UI — see below.)** The host `lifespan` **nests `async with mcp.session_manager.run():`** around its existing resource-disposal `try/finally`, because the mounted FastMCP sub-app's own lifespan is not triggered by the host `Mount` and `/mcp` would otherwise 500 at request time. Middleware: `ProjectCredentialAuthMiddleware` (no token — now guards `/api/*` **and** `/mcp`) and `AdminBearerAuthMiddleware(token=settings.admin_auth_token_value)` (guards `/admin/api/*`). `exception_handlers={AuthError: auth_error_handler}` renders the shared 401. `/auth/*` and `/app/*` match neither middleware's path predicate, so they are guarded only per-handler (or unauthenticated, for signup/login).

## Admin Web UI Removal (P6)

The packaged operator Web UI is **deleted from the backend**. What went:

- **`src/vocky/admin_ui.py`** — the five flat Starlette Web-UI `Route`s (`/admin`, `/admin/assets/{app.css,app.js,docs.json}`).
- **`src/vocky/admin_assets/`** — the whole package (`__init__.py`, `index.html`, `app.css`, `app.js`, `docs.json`).
- **`scripts/check_admin_ui_package.py`** and the `Makefile`'s `package-check` target that built and inspected a wheel for those assets. `make verify` is now `smoke test`.
- **`tests/test_admin_ui.py`**, plus the UI-asset assertions inside `tests/test_public_access.py` (the `/admin` and `/admin/assets/*` route-registration checks and the `is_admin_api_path("/admin/assets/app.js")` case).

What deliberately **stayed**: `src/vocky/admin_api.py` and its nine `/admin/api/*` routes; `AdminBearerAuthMiddleware` and `is_admin_api_path` in `src/vocky/auth.py`; the `admin_auth_token` config; `VOCKY_ADMIN_AUTH_TOKEN` in `docker-compose.yml` / `.env.example`; and `tests/test_admin_api.py`. `pyproject.toml` needed no edit — the wheel's `packages = ["src/vocky"]` simply stops including the now-absent `admin_assets`.

The surviving route surface under the prefix is therefore **exactly nine `/admin/api/*` routes**, all bearer-guarded; bare `/admin`, `/admin/`, and `/admin/assets/*` return whatever the app's normal not-found path returns, because no route matches them.

## Config Change (`src/vocky/config.py`)

The `api_auth_token` field and its `api_auth_token_value` property were removed; `/api/*` auth is no longer env-configured. `admin_auth_token` / `admin_auth_token_value` and the attachment settings are unchanged. P7 re-added **only** the MCP allowlist settings — `mcp_allowed_hosts` (`VOCKY_MCP_ALLOWED_HOSTS`), `mcp_allowed_origins` (`VOCKY_MCP_ALLOWED_ORIGINS`), and their `mcp_allowed_host_values` / `mcp_allowed_origin_values` CSV properties; the static `mcp_auth_token` was **not** restored (per-project `vk_` auth replaces it). New dependency: `mcp[cli]>=1.27.0,<2.0.0` (the official SDK's bundled FastMCP).
