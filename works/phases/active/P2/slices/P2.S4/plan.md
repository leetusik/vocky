# Plan — P2.S4: Per-project credentials + swap public ingest auth (strictly mandatory)

**Slice job:** Complete P2's objective — replace the static `VOCKY_API_AUTH_TOKEN` with per-project
credentials. Two coupled parts: (1) credential management on the `/app/*` control-plane; (2) swap
the `/api/*` ingest auth to **strictly mandatory** per-project credential validation. Read
`works/phases/active/P2/phase.md` first (S1–S3 cross-slice notes + confirmed decisions). Highest-risk
slice — get the auth boundary and the test/smoke migration right.

**Operator decision:** ingest auth is **strictly mandatory** — every `/api/*` request needs a valid,
non-revoked project key; missing/bad/revoked → **401**. No open fallback; `VOCKY_API_AUTH_TOKEN` is
retired. **Identity-only** (P2/P3 boundary): the middleware authenticates but does NOT stamp
`project_id` on `feedback_events` or thread it into the capture pipeline (P3). **Admin auth
untouched.** The packaged admin-UI try-it (`admin_assets/*`) is retiring in P4 — do NOT rewire it.

Reuse (all exist): `get_accounts_service()` → `create_project_credential`, `list_project_credentials`,
`get_active_credential_by_token_hash` (filters `revoked_at IS NULL`), `revoke_credential`,
`get_project`; `CreateProjectCredential(project_id, token_prefix, token_hash, name)`;
`ProjectCredentialRecord` (no `token_hash`); `sha256_hex`/`generate_opaque_token` +
`hash_password` in `src/vocky/accounts/security.py`; `require_user`/`AuthContext` in
`src/vocky/accounts/auth.py`; the S3 cross-tenant-404 rule; `format_pydantic_error` from `vocky.api`.

## Part 1 — Credential management (extend `src/vocky/app_api.py`, `/app/*`, user-authed)

Each handler: `ctx = await require_user(request)`; enforce project ∈ tenant (**404** when
`get_project(id)` is None or `project.tenant_id != ctx.tenant.id`):
- `POST /app/projects/{project_id}/credentials` → optional `CreateCredentialInput{name?}` → key =
  `"vk_" + generate_opaque_token()`; `token_prefix = key[:12]`; `token_hash = sha256_hex(key)` →
  `create_project_credential(...)` → **201** `{credential: serialize_credential(rec), key: "<plaintext>"}`
  — plaintext key returned **once, only here**.
- `GET /app/projects/{project_id}/credentials` → `list_project_credentials(project_id)` → **200**
  `{credentials: [serialize_credential(r), ...]}` (metadata only).
- `DELETE /app/projects/{project_id}/credentials/{credential_id}` → confirm `credential_id` ∈
  `list_project_credentials(project_id)` (else **404**) → `revoke_credential(credential_id)` → **204**.
- `serialize_credential(ProjectCredentialRecord) -> {id, project_id, name, token_prefix, created_at,
  last_used_at, revoked_at}` — never `token_hash`. Add the 3 routes to `app_api.py`'s `routes`.

## Part 2 — Ingest-auth swap (`/api/*` mandatory credential auth)

- `src/vocky/auth.py` — add `ProjectCredentialAuthMiddleware` (raw ASGI, mirror the old middleware's
  header extraction): on http + `is_api_path(path)`, extract bearer from scope headers; absent → 401;
  else `cred = await get_accounts_service().get_active_credential_by_token_hash(sha256_hex(token))`;
  None → 401 (`{"detail":"Unauthorized"}`, `WWW-Authenticate: Bearer`); else pass. Always enforces (no
  token arg); do NOT stash project state (P3). **Remove `APIBearerAuthMiddleware`.** Keep
  `is_api_path`/`is_admin_api_path`/`is_authorized_bearer`/`AdminBearerAuthMiddleware`.
- `src/vocky/app.py` — replace the `APIBearerAuthMiddleware` line with
  `Middleware(ProjectCredentialAuthMiddleware)`. Admin middleware untouched.
- `src/vocky/config.py` — remove `api_auth_token` field + `api_auth_token_value` property (keep admin).
  `.env.example` — remove the `VOCKY_API_AUTH_TOKEN` line (keep `VOCKY_ADMIN_AUTH_TOKEN`).

## Part 3 — Migrate `/api/*` tests + smoke

- `tests/conftest.py` — add a shared fixture (e.g. `configured_project_credential`, on
  `configured_database`) seeding user→tenant→project→credential via `get_accounts_service()`
  (+ `hash_password`, `generate_opaque_token`, `sha256_hex`), returning the plaintext key (+ project_id).
- `tests/test_capture_api.py`, `tests/test_user_feedback_api.py`, `tests/test_attachments_api.py` —
  each `make_api_app()` installs `ProjectCredentialAuthMiddleware`; requests send `Authorization:
  Bearer <fixture key>`; old `token="secret"` cases → valid key passes / missing/bad/revoked → 401.
- `tests/test_public_access.py` — drop `APIBearerAuthMiddleware` import + its two static-token tests;
  add `ProjectCredentialAuthMiddleware` tests (no key 401, bad key 401, seeded valid key passes); keep
  path-helper + route-registration tests.
- `tests/test_admin_ui.py` — minimal change only if it references the retired token (P4 retires the UI).
- `src/vocky/smoke.py` — rewrite `run_rest_smoke` to E2E over HTTP: `POST /auth/signup` →
  `POST /app/projects` → `POST /app/projects/{id}/credentials` → use the returned key as the Bearer
  for `POST /api/feedback` → `GET /api/feedback`. Drop the `VOCKY_API_AUTH_TOKEN` header logic.

## Do NOT touch

`src/vocky/auth_api.py` (import-only), `feedback_events`/capture pipeline (P3), `AdminBearerAuthMiddleware`
+ admin routes, `admin_assets/*` (P4), `docs/`. No `doc-new-version`.

## Verification (before returning)

- Full `uv run pytest` green (hard gate) — all migrated `/api/*` tests + new credential tests.
- Credential E2E test: mint key 201 (plaintext once) → list (no key) → key authenticates
  `POST /api/feedback` 202 → `DELETE` revokes → same key now 401 on `/api/feedback`; cross-tenant →
  404 on the credential endpoints.
- Grep: no `api_auth_token` / `VOCKY_API_AUTH_TOKEN` / `APIBearerAuthMiddleware` left in `src/`+`tests/`.
- If Postgres/stack isn't reachable, write all code and return `blocked`/`needs_operator` — do NOT fake green.

## Deliverables

Write `result.md` (free-form: credential contract, the mandatory-auth swap, what the migrated tests
now assert, any surfaced risk). Append cross-slice notes to `phase.md`: the credential `/app/*`
contract + the mint-once/`vk_` key convention, the mandatory `/api/*` credential-auth model +
`VOCKY_API_AUTH_TOKEN` retirement, and the smoke E2E flow. Do NOT commit or transition status.
Escalate with findings if the slice exceeds your depth; `blocked`/`needs_operator` on an impediment
you can't resolve (this is a wide change — surface it rather than doing a sloppy partial job).
