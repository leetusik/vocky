---
doc_id: backend
version: v0003
created_at: 2026-07-16T18:52:17+09:00
source: P7.REVIEW
summary: P7: mcp_server.py FastMCP bootstrap, capture_feedback tool module, is_mcp_path broadened ingest guard, McpCaptureFeedbackInput
previous: v0002_accounts_domain_package_require_user_authcontext_autherror_guard_security_primitives_and_auth_api_app_api_route_modules
---

# Backend

## Status

This doc covers the **accounts / identity backend** landed in P2: the `src/vocky/accounts/` domain package, the reusable user-auth guard, the security primitives, and the `/auth/*` + `/app/*` route modules and their app wiring. As of **P7** it also covers the **MCP capture backend**: the FastMCP server bootstrap (`src/vocky/mcp_server.py`), the write-only `capture_feedback` tool module (`src/vocky/tools/capture_feedback.py`), the broadened ingest guard (`is_mcp_path`), and the thin MCP input model. The feedback capture/read backend (service, repository, worker, queue, storage) is documented in `architecture.md`; this doc does not repeat it.

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

- **`src/vocky/auth_api.py`** — the public `/auth/*` routes (`signup`, `login`, `logout`, `me`). Pydantic `SignupInput`/`LoginInput` normalize email (trim + lowercase, must contain `@`) and require an 8+ char password. Signup calls `create_user` then `create_tenant_with_owner` then mints a token; login verifies the password and mints a token, returning an identical generic 401 for unknown-email vs wrong-password (no enumeration). `SESSION_TTL = timedelta(days=30)`. Serializers `serialize_user` / `serialize_tenant` expose only `{id, email, created_at}` / `{id, name, created_at}`. Reuses `format_pydantic_error` from `vocky.api` rather than redefining it.
- **`src/vocky/app_api.py`** — the session-token-authed `/app/*` control-plane: `get_tenant`, `list_projects`, `create_project`, `get_project`, and the credential handlers `create_credential` / `list_credentials` / `delete_credential`. Every handler starts `ctx = await require_user(request)`. Per-project reads/mutations go through `_load_scoped_project`, which resolves the project and returns a `400` (malformed id) or `404` (missing **or** cross-tenant) response before any work — the cross-tenant-isolation rule (404, never 403). `create_credential` mints `key = "vk_" + generate_opaque_token()`, stores `token_hash = sha256_hex(key)` + `token_prefix = key[:12]`, and returns the plaintext `key` once. `serialize_project` → `{id, name, tenant_id, created_at}`; `serialize_credential` → `{id, project_id, name, token_prefix, created_at, last_used_at, revoked_at}` (never `token_hash`).

## MCP Capture Backend (P7) — `src/vocky/mcp_server.py`, `src/vocky/tools/capture_feedback.py`

The write-only MCP capture surface (architecture: "MCP Write-Only Capture Surface"). Two new modules plus a broadened guard and a thin input model:

- **`src/vocky/mcp_server.py`** — bootstraps a module-level `FastMCP` singleton (`streamable_http_path="/"`, `json_response=True`, `stateless_http=True`, `transport_security=make_transport_security_settings(settings)`), imports `vocky.tools.capture_feedback` for side-effect tool registration, then calls `install_protocol_aware_call_handler(mcp)`. Helpers: `make_transport_security_settings` (DNS-rebinding on + localhost allowlist merged with `VOCKY_MCP_ALLOWED_HOSTS/_ORIGINS` via `append_unique`), `make_error_result`, and `install_protocol_aware_call_handler` (a `CallToolRequest` handler that returns a tool's raw `CallToolResult` straight through as the `ServerResult`, maps a caught tool exception to an error result, and raises `McpError(INVALID_PARAMS)` for an unknown tool).
- **`src/vocky/tools/capture_feedback.py`** — the sole `@mcp.tool(name="capture_feedback")`. Flat parameter list (`source` nested) plus an injected `ctx: Context` that FastMCP excludes from the tool schema. Body: build `McpCaptureFeedbackInput` → `normalize_mcp_payload` (→ `error_result` on `CaptureFeedbackValidationError`) → read the stashed credential via `get_request_credential(ctx.request_context.request)` and set `normalized.payload.project_id = credential.project_id` → `get_capture_queue().enqueue_feedback(...)` (→ `error_result("capture queue unavailable")` on `CaptureQueueError`) → return a `CallToolResult` with `structuredContent` from `serialize_capture_receipt(...)`. A defensive `None`-request guard never fires because the middleware enforces auth on the whole endpoint.
- **`src/vocky/auth.py`** — added `is_mcp_path(path)` (`== "/mcp"` or `startswith("/mcp/")`) and broadened `ProjectCredentialAuthMiddleware`'s predicate to `is_api_path(p) or is_mcp_path(p)`, so the whole `/mcp` endpoint reuses the same `vk_` resolution, generic 401, scope stash, and best-effort `last_used_at` stamp as `/api/*`. `get_request_credential` is now valid for `/api/*` **and** `/mcp` requests.
- **`src/vocky/capture.py`** — added the thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` (empty subclass, no `attachment_ids`) and `normalize_mcp_payload` next to the REST pair. No engine change — `_normalize_capture_payload` reads `attachment_ids` via `getattr`.

## App Wiring (`src/vocky/app.py`)

`create_app()` registers routes in order: `/healthz`, `*auth_routes`, `*app_api_routes`, `*app_feedback_routes`, `*usage_routes`, `*admin_routes`, `*admin_ui_routes`, `*api_routes`, `*project_feedback_routes`, `*attachment_routes`, and (P7) a trailing `Mount("/mcp", app=mcp.streamable_http_app())` — kept last so it cannot shadow the core routes. The host `lifespan` **nests `async with mcp.session_manager.run():`** around its existing resource-disposal `try/finally`, because the mounted FastMCP sub-app's own lifespan is not triggered by the host `Mount` and `/mcp` would otherwise 500 at request time. Middleware: `ProjectCredentialAuthMiddleware` (no token — now guards `/api/*` **and** `/mcp`) and `AdminBearerAuthMiddleware(token=settings.admin_auth_token_value)` (guards `/admin/api/*`). `exception_handlers={AuthError: auth_error_handler}` renders the shared 401. `/auth/*` and `/app/*` match neither middleware's path predicate, so they are guarded only per-handler (or unauthenticated, for signup/login).

## Config Change (`src/vocky/config.py`)

The `api_auth_token` field and its `api_auth_token_value` property were removed; `/api/*` auth is no longer env-configured. `admin_auth_token` / `admin_auth_token_value` and the attachment settings are unchanged. P7 re-added **only** the MCP allowlist settings — `mcp_allowed_hosts` (`VOCKY_MCP_ALLOWED_HOSTS`), `mcp_allowed_origins` (`VOCKY_MCP_ALLOWED_ORIGINS`), and their `mcp_allowed_host_values` / `mcp_allowed_origin_values` CSV properties; the static `mcp_auth_token` was **not** restored (per-project `vk_` auth replaces it). New dependency: `mcp[cli]>=1.27.0,<2.0.0` (the official SDK's bundled FastMCP).
