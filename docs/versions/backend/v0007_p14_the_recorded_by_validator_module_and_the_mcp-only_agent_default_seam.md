---
doc_id: backend
version: v0007
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: the recorded_by validator module and the MCP-only agent default seam
previous: v0006_p13_accounts_gains_get_owner_email_for_project_config_gains_the_vocky_smtp__settings_and_the_smtp_configured_gate_and_src_vocky_notifications.py_sends_the_owner_feedback_alert
---

# Backend

## Status

As of **P14** it also covers the **capture provenance backend** — the shared `recorded_by` validator module, the MCP-only default seam in `capture.py`, and the read-side filter validator (see "P14 Additions" below).

As of **P13** it also covers the **feedback email alert backend** — the accounts owner-email primitive, the `VOCKY_SMTP_*` settings, and `src/vocky/notifications.py` (see "P13 Additions" below). The worker hook that calls it and its containment rule are in `architecture.md`; the box env/secret plumbing is in `operations.md`.

This doc covers the **accounts / identity backend** landed in P2: the `src/vocky/accounts/` domain package, the reusable user-auth guard, the security primitives, and the `/auth/*` + `/app/*` route modules and their app wiring. As of **P7** it also covers the **MCP capture backend**: the FastMCP server bootstrap (`src/vocky/mcp_server.py`), the write-only `capture_feedback` tool module (`src/vocky/tools/capture_feedback.py`), the broadened ingest guard (`is_mcp_path`), and the thin MCP input model. As of **P6** it also records the **removal of the packaged Admin Web UI** from the backend (see "Admin Web UI Removal" below) — a deletion only; no accounts, MCP, or Admin REST behavior changed. As of **P10** it covers the **org-level credential backend** — new accounts primitives, the credential project-scope resolver, and the shared ingest project resolver (see "P10 Additions" below). The feedback capture/read backend (service, repository, worker, queue, storage) is documented in `architecture.md`; this doc does not repeat it.

## P14 Additions — the `recorded_by` capture provenance marker

One new module plus small, mechanical threading. The design rationale is in `decisions.md` (D-P14-1/2/3) and the wire contract in `api.md`; this is the module surface.

**`src/vocky/recorded_by.py` (new, a single module)**

- `ALLOWED_RECORDED_BY = ("agent", "human")`, `RECORDED_BY_VALIDATION_ERROR`, `RecordedByValidationError`, and `normalize_recorded_by(value)` (trim → blank collapses to `None` → unknown value rejected). It **mirrors `src/vocky/trigger.py` in shape** on purpose — the vocabulary, the trim/blank rule, and the public error string live in exactly one place.
- The public error string is `recorded_by must be one of: agent, human`, quoted verbatim in the docs and returned identically by the capture side (`400`), the MCP tool (an `isError` tool result), and the read-side filter.

**`src/vocky/capture.py` — the transport-specific default seam**

- `normalize_capture_recorded_by()` is the thin adapter that re-raises the validator's error as `CaptureFeedbackValidationError`, matching `normalize_capture_trigger_type`.
- `MCP_DEFAULT_RECORDED_BY = "agent"` is stamped in **`normalize_mcp_payload`** when the normalized value is `None` (covering both omitted and whitespace-blank). `normalize_rest_payload` is byte-for-byte unchanged, so REST keeps defaulting to `NULL`. **`_normalize_capture_payload` stays transport-neutral** — putting transport knowledge inside it is the mistake this seam exists to prevent.
- The MCP tool (`tools/capture_feedback.py`) gained an **explicit flat `recorded_by` parameter**. Adding the field to `BaseCaptureFeedbackInput` gives REST and MCP *body parsing* for free but does **not** publish it in the MCP tool schema — the flat parameter is what does that (see `architecture.md`).

**`src/vocky/tools/query_feedback_common.py` — the read side**

- `normalize_recorded_by_filter` **delegates** to `vocky.recorded_by.normalize_recorded_by` and re-raises as `FeedbackQueryValidationError`, exactly as `normalize_trigger_type_filter` wraps `normalize_trigger_type`. Delegating (rather than importing `ALLOWED_RECORDED_BY` and re-implementing the membership check) reuses the vocabulary **and** the trim/blank rule **and** the error string from one module. Blank or absent ⇒ **no filter**.

**Threading, and the two non-obvious spots**

- `FeedbackEventRecord.recorded_by` carries a **`None` default** where its sibling fields have none. That is load-bearing for additivity — `tests/test_notifications.py` builds a full field dict, and a required field would have forced an edit there — and `kw_only=True` is what makes a mid-list default legal. Do not "tidy" it away.
- **Field position is a convention worth keeping:** `recorded_by` sits immediately after `source_integration` in `FeedbackQueryFilters`, in `_apply_filters`, and in **both** serializers, mirroring `FeedbackEventRecord`. Any future read-side addition should mirror the record the same way.
- `recorded_by` is deliberately absent from the Admin/Project **PATCH allowlist** and from `FeedbackMetricsQuery` — provenance, not a review field, and no marker-specific metrics.
- **Two duplicated pairs, not one.** `admin_api.normalize_list_query` is imported verbatim by `app_feedback_api` and `project_feedback_api`, so one edit covers three REST surfaces; `api.py` carries its own duplicate `normalize_user_feedback_query` **and** `serialize_user_feedback_record`, which must be edited separately. Missing the second is how a field lands on three read surfaces and silently not the fourth.

## P13 Additions — feedback email alerts over SMTP

One plain-text email per persisted feedback event, addressed to the **owning org's owner**. Three pieces: a recipient primitive in accounts, SMTP settings in config, and a notifier module. The worker call site and its swallow-and-log containment are documented in `architecture.md` — **that containment is what makes this module's exception policy safe**, so read both together.

**`src/vocky/accounts/` — the recipient primitive**

- `AccountsRepository.get_owner_email_for_project(project_id: UUID) -> str | None` — one query walking `projects.tenant_id → tenant_members(role='owner') → users.email`, selecting `UserModel.email` directly (so it returns `str | None` from `.scalars().first()` with no new `*Record` and no mapper). **The join is anchored on `ProjectModel.id == project_id`**, which is the multi-tenant guarantee: a project can only ever resolve to its own tenant's owner. Dropping the `TenantMemberModel.role == "owner"` filter or re-anchoring the join is how one org's feedback would be mailed to another org's owner — this is the phase's correctness hot spot.
- **Oldest-wins by `(created_at, id)` with `.limit(1)`**, deliberately not `.one()` / `scalar_one_or_none()`: nothing in the schema forbids two `role='owner'` rows in one tenant (`tenant_members` is unique on `(tenant_id, user_id)` only), so an unordered single-row read would raise on a legitimate state. Same tie-break `get_project_by_name` uses.
- `role="owner"` stayed a **bare string literal**, matching the two existing write sites in `service.py`; no shared constant was introduced (changing the write sites was out of scope).
- `AccountsService.get_owner_email_for_project(project_id)` — thin passthrough on a fresh session, `SQLAlchemyError` → rollback → `AccountsReadError`, same shape as every other read. **"No owner" is `None`, not an exception**; `AccountsReadError` means a genuine DB failure.

**`src/vocky/config.py` — SMTP settings**

`smtp_host` (`VOCKY_SMTP_HOST`, default `""`), `smtp_port` (`VOCKY_SMTP_PORT`, default `587`), `smtp_user` (`VOCKY_SMTP_USER`, `""`), `smtp_password` (`VOCKY_SMTP_PASSWORD`, `""`), `smtp_from` (`VOCKY_SMTP_FROM`, `""`) — all optional, modelled on `admin_auth_token` (empty string = feature off), no required validation anywhere.

- `smtp_from_value` — the **effective** From/envelope sender: `smtp_from.strip() or smtp_user.strip()`. An operator who sets only `VOCKY_SMTP_USER` still gets a valid From header.
- `smtp_configured` — the single gate: non-blank `smtp_host` **and** a non-blank effective From. Everything else may stay at defaults; alerts are simply off. **Unconfigured never raises and never logs at ERROR per job** — that is the "cleanly disabled" contract.

**`src/vocky/notifications.py` (new, a single module, not a package)**

- `FeedbackAlertNotifier(*, settings: Settings, accounts_service: OwnerEmailResolver)` with `async notify_feedback_persisted(record: FeedbackEventRecord | None) -> None`. Four early returns before any work: `record is None` **or** `record.project_id is None` (debug log — `project_id` is `UUID | None` on the record, and the worker's own test doubles return `None`, so both are real paths), SMTP unconfigured (silent), owner lookup returned `None` (one `logger.warning`).
- `OwnerEmailResolver` — a `typing.Protocol` with just `get_owner_email_for_project`, so tests inject a fake without importing `AccountsService` (which satisfies it unmodified).
- `_render_message(settings, record, to_email)` — plain-text `email.message.EmailMessage`. Subject `Vocky feedback: <source_product>`, plus `(<feedback_value>)` when set; body is one line each for message, feedback value, comment, channel, source product, event/ingested timestamps, event id, project id. **No HTML part** — deliberately out of scope.
- `_send_message(settings, message)` — the **blocking** send, kept as a module-level function on purpose: it is the single isolation point, so swapping stdlib `smtplib` for an async client later touches one function. `SMTP_SSL` iff `smtp_port == 465`, else `SMTP` + `starttls()`; `login()` only when `smtp_user` is non-blank; 10s timeout; used as a context manager. Called via `asyncio.to_thread` so the worker's single asyncio loop is never blocked.
- `get_feedback_alert_notifier()` — constructor-per-call factory over `get_settings()` + `get_accounts_service()`, matching `get_feedback_service()`'s style (no `@lru_cache`).
- **Exception policy: this module deliberately does not swallow.** Steps up to the owner lookup return; the lookup (`AccountsReadError`) and the send (`smtplib`/socket errors) are allowed to propagate so the module stays honest and testable. The worker's `try/except Exception` is the only containment, and it is load-bearing — see `architecture.md`.
- **No new dependency, at any tier.** Stdlib only; the pip-installable CLI's `httpx` + `typer` core and the `server` extra are both untouched (`pyproject.toml`/`uv.lock` unchanged by the whole phase).

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
