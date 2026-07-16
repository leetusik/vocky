# Plan — P2.S3: Tenants & projects account-scoped API (CRUD)

**Slice job:** Give the authenticated user a **control-plane** to manage their tenant's **projects**.
Thin: HTTP + tenant authorization wired onto S1's `AccountsService` (`create_project`, `get_project`,
`list_projects_for_tenant`) using S2's `require_user` guard. Read `works/phases/active/P2/phase.md`
first (S1/S2 cross-slice notes + confirmed decisions).

**Control-plane prefix = `/app/*`** (operator-approved), NOT `/api/*`. `/api/*` is the product
data-plane (feedback ingest/read), guarded by the bearer middleware and by per-project credentials
after S4; project management needs **user-token** auth. `/app/*` matches neither `is_api_path` nor
`is_admin_api_path`, so it bypasses both existing middlewares and is guarded per-handler by
`require_user`.

Reuse surface (confirmed in `src/vocky/accounts/auth.py`):
`from vocky.accounts.auth import require_user, AuthContext, AuthError` —
`ctx = await require_user(request)` gives `ctx.user` + `ctx.tenant`; `AuthError` → 401 is already
wired app-wide in `create_app()` (S2), so a raised `AuthError` needs no per-handler catch.
`from vocky.api import format_pydantic_error`. `serialize_tenant` exists in `src/vocky/auth_api.py`
(import to stay DRY). Handler/route style per `src/vocky/api.py`.

## Components

**`src/vocky/app_api.py` (new)** — routes + handlers, mirroring `src/vocky/api.py`. Each handler
begins `ctx = await require_user(request)`:
- `GET /app/tenant` → **200** `{tenant: serialize_tenant(ctx.tenant)}`.
- `GET /app/projects` → `list_projects_for_tenant(ctx.tenant.id)` → **200**
  `{projects: [serialize_project(p), ...]}`.
- `POST /app/projects` → Pydantic `CreateProjectInput{name}` (stripped, `min_length=1`, sane
  `max_length`; `ValidationError` → `format_pydantic_error` → **400**) →
  `create_project(CreateProject(tenant_id=ctx.tenant.id, name=...))` → **201** `{project: ...}`.
- `GET /app/projects/{project_id}` → `UUID(path_params["project_id"])` (malformed → **400**) →
  `get_project(id)`; **None OR `project.tenant_id != ctx.tenant.id` → 404** (cross-tenant → 404, never
  403 — no existence leak); else **200** `{project: ...}`.
- `serialize_project(ProjectRecord) -> {id, name, tenant_id, created_at}`.
- `routes = [Route("/app/tenant", GET), Route("/app/projects", GET), Route("/app/projects", POST),
  Route("/app/projects/{project_id}", GET)]`.

**`src/vocky/app.py` (modify)** — `from vocky.app_api import routes as app_api_routes`; add
`*app_api_routes` to the `create_app()` `routes=[...]` list. No middleware/exception-handler changes.

**`tests/test_app_api.py` (new, terse)** — combined test app
`Starlette(routes=[*auth_routes, *app_api_routes], exception_handlers={AuthError: auth_error_handler})`
so a test signs up (→ token) then drives `/app/*`. `configured_database`, `@pytest.mark.anyio`,
`httpx.ASGITransport`+`AsyncClient`. Cases: create project 201 → list shows it → get by id 200;
**cross-tenant isolation** (second user's token → 404 for the first user's project); `GET /app/tenant`
returns the caller's tenant; missing/invalid token → 401; malformed project id → 400. Lean.

## Do NOT touch

`src/vocky/auth.py`, `src/vocky/api.py` (import-only), `/api/*` middleware wiring,
`src/vocky/auth_api.py` (import-only), `feedback_events`, `docs/`. No credential endpoints (S4). No
`doc-new-version`.

## Verification (before returning)

`uv run pytest tests/test_app_api.py` passes; full `uv run pytest` stays green. If Postgres isn't
reachable, write all code and return `blocked`/`needs_operator` with specifics — do not fake green.

## Deliverables

Write `result.md` (free-form: the `/app/*` contract, cross-tenant-404 rule, any surfaced risk).
Append cross-slice notes to `phase.md`: the `/app/*` control-plane contract + status codes, the
`serialize_project` shape, and the cross-tenant-isolation (404) authorization rule S4's credential
endpoints must also follow. Do NOT commit or transition status. If the slice exceeds your depth,
return `escalate` with findings; `blocked`/`needs_operator` on an impediment you can't resolve.
