# Result — P2.S3: Tenants & projects account-scoped API (CRUD)

## What shipped

A thin user-authenticated **control-plane** at the top-level `/app/*` prefix, wiring HTTP +
tenant authorization onto S1's `AccountsService` via S2's `require_user` guard. No new deps, no
schema changes, no middleware changes.

- **`src/vocky/app_api.py` (new)** — routes + handlers, mirroring `src/vocky/api.py` /
  `src/vocky/auth_api.py`. Each handler starts `ctx = await require_user(request)`; a raised
  `AuthError` is rendered as the shared generic 401 by the app-wide handler already registered in
  `create_app()` (S2), so no per-handler catch. Imports `serialize_tenant` from `vocky.auth_api`
  and `format_pydantic_error` from `vocky.api` to stay DRY.
- **`src/vocky/app.py` (modified)** — `from vocky.app_api import routes as app_api_routes`;
  `*app_api_routes` added to `create_app()`'s `routes=[...]` (right after `*auth_routes`). No
  middleware or exception-handler changes.
- **`tests/test_app_api.py` (new, terse)** — combined `Starlette(routes=[*auth_routes,
  *app_api_routes], exception_handlers={AuthError: auth_error_handler})`; each test signs up via
  `/auth/signup` to get a real token, then drives `/app/*`. In-process ASGI (`httpx.ASGITransport`
  + `AsyncClient`, `@pytest.mark.anyio`, `configured_database`).

## `/app/*` control-plane contract

| Method + path                 | Auth        | Success | Body                                            |
|-------------------------------|-------------|---------|-------------------------------------------------|
| `GET /app/tenant`             | Bearer user | 200     | `{tenant: {id, name, created_at}}`              |
| `GET /app/projects`           | Bearer user | 200     | `{projects: [<project>, ...]}` (oldest-first)   |
| `POST /app/projects`          | Bearer user | 201     | `{project: <project>}`                          |
| `GET /app/projects/{id}`      | Bearer user | 200     | `{project: <project>}`                          |

`<project>` = `serialize_project(ProjectRecord)` →
`{id, name, tenant_id, created_at}` (all strings; `created_at` ISO-8601).

Error codes:
- **401** — missing/invalid/expired bearer token, on every route (shared `AuthError` → generic
  `{"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer`).
- **400** — `POST /app/projects` with a bad body (non-JSON, non-object, missing/blank/over-long
  `name`) via Pydantic `CreateProjectInput` → `format_pydantic_error`; and `GET
  /app/projects/{id}` with a malformed (non-UUID) path id.
- **404** — `GET /app/projects/{id}` when the project is missing **or** belongs to another tenant.

`CreateProjectInput.name`: stripped, `min_length=1`, `max_length=200`; the stored name is the
stripped value (`"  Website  "` → `"Website"`).

## Cross-tenant isolation (the load-bearing authorization rule)

`GET /app/projects/{id}` returns **404 (never 403)** when
`project is None or project.tenant_id != ctx.tenant.id` — a project owned by a different tenant is
indistinguishable from a missing one, so a caller can never probe another tenant's project ids
(no existence leak). `list_projects_for_tenant(ctx.tenant.id)` is inherently tenant-scoped, and
`create_project` binds `tenant_id=ctx.tenant.id`, so writes/lists cannot cross tenants either.
Verified with a second signed-up user: the intruder gets 404 for the owner's project id and an
empty `/app/projects` list. **S4's credential endpoints must apply the same rule** — resolve the
project, then 404 on `project.tenant_id != ctx.tenant.id` before doing any credential work.

## Validation

- `uv run pytest tests/test_app_api.py -q` → **6 passed** (create→list→get; cross-tenant 404 +
  empty list; `/app/tenant`; auth-required 401; blank/missing-name 400; malformed-id 400 +
  unknown-id 404).
- `uv run pytest -q` (full suite) → **151 passed** — no regressions.
- `python3 scripts/workflow.py validate` → passed.

## Deviations from plan.md

None. Implemented exactly as specified: `/app/*` prefix, four routes, `serialize_project` shape,
the cross-tenant-404 rule, and boundaries respected (no touch to `auth.py`, `api.py`,
`auth_api.py`, `/api/*` middleware, `feedback_events`, or `docs/`; no credential endpoints; no
`doc-new-version`).

## Surfaced note / risk

- **Prefix choice `/app/*` (not `/api/*`)** is deliberate and matches neither `is_api_path` nor
  `is_admin_api_path`, so both existing bearer middlewares are bypassed and the routes are guarded
  purely per-handler by `require_user`. If a future slice broadens either middleware's path
  predicate, re-verify `/app/*` still bypasses it.
- Solo-owner MVP: `ctx.tenant` is `list_tenants_for_user(user.id)[0]`. No membership/role check
  beyond "user has a tenant" — adequate for the current single-tenant-per-user model; multi-tenant
  selection is out of scope here.
