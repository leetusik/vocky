# Result — P2.S4: Per-project credentials + strictly-mandatory `/api/*` ingest auth

Completes P2's objective: the static `VOCKY_API_AUTH_TOKEN` global capture token is replaced by
per-project credentials, and public `/api/*` ingest auth is now strictly mandatory. Done in the
plan's order (Part 1 → 2 → 3). Full test suite green (153 passed).

## Part 1 — Credential control-plane (`src/vocky/app_api.py`, `/app/*`, user-authed)

Added three handlers + serializer + helpers, wired into `routes`:

- `POST /app/projects/{project_id}/credentials` — optional body `CreateCredentialInput{name?}`
  (blank → null). Mints `key = "vk_" + generate_opaque_token()`, stores
  `token_prefix = key[:12]` + `token_hash = sha256_hex(key)` via `create_project_credential`, and
  returns **201** `{credential: serialize_credential(rec), key: "<plaintext>"}`. The plaintext key is
  emitted only here, once.
- `GET /app/projects/{project_id}/credentials` → **200** `{credentials: [...]}` (metadata only,
  oldest-first).
- `DELETE /app/projects/{project_id}/credentials/{credential_id}` → **204**; **404** when the
  credential id is not in that project's list (checked before revoke). Soft-revoke via
  `revoke_credential`.
- `serialize_credential(ProjectCredentialRecord)` → `{id, project_id, name, token_prefix,
  created_at, last_used_at, revoked_at}` — never `token_hash`.
- `_load_scoped_project(request, ctx)` centralizes the S3 cross-tenant-404 rule for all three
  handlers: 400 on a malformed `project_id` UUID, **404** when the project is missing *or*
  `project.tenant_id != ctx.tenant.id` — resolved **before** any credential work.
- `_parse_optional_body` tolerates an empty POST body (yields model defaults) so
  `POST .../credentials` works with or without a body.

## Part 2 — Mandatory ingest auth (`/api/*`)

- `src/vocky/auth.py`: added `ProjectCredentialAuthMiddleware` (raw ASGI, mirrors the old middleware's
  scope-header extraction) and `extract_bearer_credential`. On http + `is_api_path`, it looks up
  `get_active_credential_by_token_hash(sha256_hex(token))`; **missing / malformed / unknown / revoked
  all → 401** `{"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer`. Always enforces (no token arg,
  no open fallback). Identity-only: does not stash project state on the scope and does not touch
  `last_used_at` (both P3). Removed `APIBearerAuthMiddleware`; kept
  `is_api_path`/`is_admin_api_path`/`is_authorized_bearer`/`AdminBearerAuthMiddleware`.
- `src/vocky/app.py`: middleware line now `Middleware(ProjectCredentialAuthMiddleware)` (no token);
  admin middleware untouched.
- `src/vocky/config.py`: removed the `api_auth_token` field + `api_auth_token_value` property (admin
  token kept).
- `.env.example`: removed the `VOCKY_API_AUTH_TOKEN` line; added a note that `/api/*` now needs a
  per-project credential minted via `POST /app/projects/{id}/credentials`.

## Part 3 — Tests + smoke migration

- `tests/conftest.py`: added `configured_project_credential` fixture (on `configured_database`) seeding
  user→tenant→project→active credential and returning a `SeededCredential(key, project_id, tenant_id,
  user_id, credential_id)` NamedTuple; the `key` is a valid `/api/*` Bearer.
- `tests/test_capture_api.py`, `tests/test_user_feedback_api.py`, `tests/test_attachments_api.py`: each
  `make_*_app()` now installs `ProjectCredentialAuthMiddleware`; requests carry the fixture key. Each
  file's former static-`token="secret"` auth test became a **no key / bad key → 401, seeded key →
  passes** test. Added `test_capture_feedback_requires_project_credential` (POST ingest path).
- `tests/test_public_access.py`: dropped `APIBearerAuthMiddleware` import + its two static-token tests;
  added `test_project_credential_auth_middleware_enforces_mandatory_ingest_auth` (no key 401 / bad key
  401 / seeded key 200; `/healthz` unguarded) and a credential-route registration assertion. Path-helper
  and admin-middleware tests kept.
- `tests/test_credentials_api.py` (new): the credential E2E — mint 201 (plaintext once, no hash) → list
  (metadata only) → key authenticates `POST /api/feedback` 202 → DELETE 204 → same key now 401; plus
  cross-tenant POST/GET/DELETE credential ops → 404.
- `tests/test_admin_ui.py`: **no change needed** — its `VOCKY_API_AUTH_TOKEN` assertion checks the
  packaged `admin_assets/docs.json` content, which the plan leaves untouched (admin UI retires in P4),
  so it stays green.
- `src/vocky/smoke.py`: `run_rest_smoke` rewritten to E2E — `POST /auth/signup` → `POST /app/projects`
  → `POST /app/projects/{id}/credentials`, then the returned `vk_` key as Bearer for `POST /api/feedback`
  → `GET /api/feedback`. Removed `make_smoke_request_headers` (the `VOCKY_API_AUTH_TOKEN` logic); health
  helpers kept.

## Validation

| Command | Result |
| --- | --- |
| `uv run pytest` (full suite) | **153 passed** |
| `uv run pytest tests/test_credentials_api.py tests/test_public_access.py tests/test_capture_api.py tests/test_user_feedback_api.py tests/test_attachments_api.py tests/test_admin_ui.py` | 39 passed |
| `grep -rn "api_auth_token" src/ tests/` | no matches |
| `grep -rn "APIBearerAuthMiddleware" src/ tests/` | no matches |
| `grep -rn "VOCKY_API_AUTH_TOKEN" src/ tests/` | only `admin_assets/*` + `tests/test_admin_ui.py:232` (intentional — P4) |
| `uv run python -c "import vocky.smoke"` / `ast.parse` | OK |
| `python3 scripts/workflow.py validate` | passed |

DB was reachable (Postgres on `127.0.0.1:55432`, migrations current); no `blocked`/`needs_operator`
conditions. `make smoke` (live server) was not run: the running `vocky-app-1` container is the stale
pre-S4 image and lacks the new `/app/*` credential endpoints, so it would not exercise the rewritten
flow; the smoke rewrite is validated structurally and its flow is exactly the passing E2E test's flow.

## Deviations / judgment calls

- **Grep scope (interpretation, not a code deviation).** The plan's verification asks for no
  `VOCKY_API_AUTH_TOKEN` in `src/`+`tests/`, but also explicitly says **do NOT touch `admin_assets/*`**
  (admin UI retires in P4) and to change `test_admin_ui.py` only if needed to keep it green. Those two
  directives conflict for the packaged admin-UI docs. I resolved it per the plan's explicit intent: the
  live auth path is fully scrubbed (`config.py`, `app.py`, `auth.py`, `smoke.py`, all `/api/*` tests),
  and `VOCKY_API_AUTH_TOKEN` remains only in `src/vocky/admin_assets/{docs.json,app.js}` and the
  `test_admin_ui.py` assertion over that untouched content — the P4 operator-surface work.
  `test_admin_ui.py` needed no edit and stays green.
- Added one extra POST-path 401 test in `test_capture_api.py` (the primary ingest endpoint) and a
  credential-route registration assertion in `test_public_access.py` — small, high-value additions in
  the spirit of the plan's "valid key passes / missing/bad/revoked → 401" requirement.
- No source/behavior deviations from `plan.md`.
