# Phase P2: Accounts, Tenancy & Projects Core

_Intent: see [intent.md](intent.md)._

## Objective

Replace static env-var bearer-token auth with real user accounts (signup/login) and introduce the multi-tenant SaaS core: tenants, projects, and per-project credentials. Free service — no paid plans or billing.

## Context

## Decomposition

Four implementation slices in a strict S1→S4 dependency chain (each builds on the prior),
then `P2.REVIEW`. The split follows the natural build order data → auth → account API →
credentials/ingest-swap: every layer needs the one below it to exist first.

- **P2.S1 — Identity & tenancy data model + persistence** · `medium` · order 1
  One Alembic migration (chained on head `20260604_2305`) creating `users`, `tenants`,
  `tenant_members`, `projects`, `project_credentials`, `auth_tokens`; ORM models in
  `persistence/models.py` (+ export); new `src/vocky/accounts/` domain package
  (`types/repository/service` + `get_accounts_service()`) mirroring `src/vocky/feedback/`.
  Terse persistence tests. Load-bearing schema — orchestrator may bump to high at plan time.
- **P2.S2 — Account auth: signup / login / session tokens + user-auth guard** · `high` · order 2 · depends_on S1
  Adds `argon2-cffi`; password-hash helpers; signup (user + tenant + owner membership),
  login/logout, token issue/validate; public routes under a **top-level `/auth/*`** prefix
  (outside `/api/*` so the public-API middleware never guards them); user-auth guard populating
  `request.state.user`/`tenant`. Security-sensitive → high.
- **P2.S3 — Tenants & projects account-scoped API (CRUD)** · `medium` · order 3 · depends_on S2
  User-authenticated endpoints to read the caller's tenant and create/list/read projects,
  authorized via S2's guard with owner/membership checks. Terse tests.
- **P2.S4 — Per-project credentials + swap public ingest auth** · `high` · order 4 · depends_on S3
  Credential endpoints (`POST /api/projects/{id}/credentials` returning plaintext `vk_...` once,
  list metadata, revoke); replace `APIBearerAuthMiddleware`'s static-token compare with a
  hashed-credential lookup resolving project+tenant onto `request.state` (401 on miss); retire
  `VOCKY_API_AUTH_TOKEN`. Changes the public ingest auth boundary → high.

**Rationale for the 4-way split + chain:** S1 lands the schema every later slice reads/writes;
S2 needs the `users`/`tenants`/`auth_tokens` tables before it can mint sessions; S3 needs S2's
user-auth guard before it can scope tenant/project CRUD to the caller; S4 needs S3's projects
before it can attach credentials and needs the auth guard to gate credential management. Keeping
the two security-sensitive slices (S2 auth, S4 ingest-auth swap) at `high` and the two
schema/CRUD slices at `medium` targets executor cost at the risk that actually warrants it.

## Findings & Notes

**Confirmed design decisions (operator-approved — do not re-litigate):**

1. **Account auth = email + password + opaque DB-backed bearer tokens.** argon2id password
   hashing (`argon2-cffi`, new dep). Login mints a random opaque token stored **hashed** (sha256;
   high-entropy tokens, no pepper) in `auth_tokens` (`user_id` + expiry), sent as
   `Authorization: Bearer <token>` by web (P4) and CLI (P5). Revoke = delete row. No JWT.
2. **Tenancy = multi-tenant schema, solo-owner MVP flow.** Tables `users`, `tenants`,
   `tenant_members(user_id, tenant_id, role)`, `projects(tenant_id)`,
   `project_credentials(project_id)`. Signup auto-creates a tenant with the user as sole `owner`
   member. Invites/roles UI deferred.
3. **Capture-scoping boundary = identity only in P2.** S4 swaps public `/api/*` auth to validate a
   per-project credential → resolve project+tenant onto `request.state`. Do **NOT** add
   `project_id` to `feedback_events` or reshape the capture payload — that is P3's job.
4. **Admin auth untouched.** `VOCKY_ADMIN_AUTH_TOKEN` / `AdminBearerAuthMiddleware` stay as-is;
   operator-surface reshaping is P4. S4 scopes to the **public** ingest auth only.

**Reuse pointers:**

- Auth swap points: `src/vocky/auth.py`, `src/vocky/app.py:53-56` (middleware wiring),
  `src/vocky/config.py` (settings). Auth routes go in `create_app()`'s `routes=[...]`.
- Data conventions: `src/vocky/persistence/models.py` (SQLAlchemy 2 `Mapped`/`mapped_column`,
  `PG_UUID(as_uuid=True)` PK w/ `uuid4`, `TIMESTAMPTZ`, JSONB), `persistence/base.py` (`Base`,
  `NAMING_CONVENTION`), `src/vocky/db.py` (`get_session_maker()` async singleton).
- Domain triad to mirror: `src/vocky/feedback/{types,repository,service}.py` + `get_feedback_service()`.
- Migrations: `alembic/versions/` (head `20260604_2305`), `alembic/env.py` autogenerate; apply
  `uv run alembic upgrade head`.
- Tests: real-Postgres integration + `fakeredis` + in-process ASGI via `httpx`; shared
  `tests/conftest.py`. Keep new test files terse.

**S1 delivered — schema + accounts persistence (what S2–S4 build on):**

- **New head migration: `20260715_1200`** (`add_accounts_tenancy`, chained on `20260604_2305`).
  Any later migration chains onto `20260715_1200`. The head-version pin in
  `tests/test_persistence.py` now asserts `"20260715_1200"` — bump it again if you add a migration.
- **Final table/column names** (all `id` UUID PK `default=uuid4`, `created_at` TIMESTAMPTZ
  `CURRENT_TIMESTAMP`):
  - `users(email UNIQUE, password_hash)` — S2 stores the argon2id hash here; `email` is
    normalized-lowercase by the *caller* (schema does not lowercase).
  - `tenants(name)` — ownership is a `tenant_members` row, NOT an `owner_id` column.
  - `tenant_members(tenant_id→tenants, user_id→users, role)` — UNIQUE `(tenant_id, user_id)`;
    MVP writes `role="owner"`.
  - `projects(tenant_id→tenants, name)`.
  - `project_credentials(project_id→projects, name NULL, token_prefix, token_hash UNIQUE,
    last_used_at NULL, revoked_at NULL)`.
  - `auth_tokens(user_id→users, token_hash UNIQUE, expires_at NULL, last_used_at NULL)`.
  - All FKs `ON DELETE CASCADE`.
- **Domain package `src/vocky/accounts/`** mirrors `feedback/`: `AccountsService` (session
  lifecycle + commit + error translation), `AccountsRepository` (sole ORM boundary, no commit),
  transport-neutral `types.py`, and `get_accounts_service()` factory. Import surface:
  `from vocky.accounts import get_accounts_service, AccountsService, CreateUser, CreateProject,
  CreateProjectCredential, CreateAuthToken, DuplicateEmailError, ...`.
- **`create_tenant_with_owner(user_id, name) -> (TenantRecord, TenantMemberRecord)`** — the
  signup primitive: inserts tenant + `owner` membership in ONE transaction. S2's signup calls
  `create_user(...)` then this. `create_user` raises **`DuplicateEmailError`** (subclass of
  `AccountsPersistenceError`) on the `uq_users_email` violation → S2 returns 409.
- **Credential convention (S4 reuses):** caller computes `token_prefix` (short display, e.g.
  `vk_ab12…`) + `token_hash` = **sha256 hex of the plaintext key**; raw key never stored.
  `get_active_credential_by_token_hash(hash)` filters `revoked_at IS NULL` (the ingest lookup);
  `touch_credential_last_used(id)`; `revoke_credential(id)` is a soft revoke (idempotent, sets
  `revoked_at`), does NO authz. `ProjectCredentialRecord` exposes `token_prefix`, never the hash.
- **Session-token convention (S2 reuses):** caller generates a high-entropy opaque token, stores
  `token_hash` = **sha256 hex** via `create_auth_token(CreateAuthToken(user_id, token_hash,
  expires_at=None|dt))`. `get_active_auth_token_by_hash(hash)` filters
  `expires_at IS NULL OR expires_at > now()` (S2 sets expiry policy). Logout =
  `delete_auth_token(hash) -> bool`. `touch_auth_token_last_used(hash)` for last-seen. Records
  never expose `token_hash`.
- **Test fixture:** `configured_database` TRUNCATE now clears all six new tables with `CASCADE`
  (setup + teardown) — later slices' tests inherit a clean accounts schema automatically.

**S2 delivered — account auth surface + reusable user-auth guard (what S3/S4/P4/P5 build on):**

- **New dep:** `argon2-cffi==25.1.0` (argon2id). No new env var.
- **`/auth/*` contract (public, outside `/api/*`):**
  - `POST /auth/signup` `{email,password}` → **201** `{token, user, tenant}`; provisions
    user + tenant (`"<email-local-part>'s workspace"`) + owner membership, then mints a token.
    **409** on duplicate email; **400** on bad body.
  - `POST /auth/login` `{email,password}` → **200** `{token, user, tenants:[...]}`; unknown-email
    and wrong-password both return an **identical 401** `{"detail":"invalid email or password"}`
    (no user enumeration); **400** on bad body.
  - `POST /auth/logout` (Bearer) → **204**, idempotent.
  - `GET /auth/me` (Bearer) → **200** `{user, tenants:[...]}`; miss → **401**
    `{"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer`.
  - `user`/`tenant` serializers expose `{id,email,created_at}` / `{id,name,created_at}` only —
    **never** `password_hash` or `token_hash`.
- **Reusable guard (S3/S4 import):** `from vocky.accounts.auth import require_user, AuthContext,
  AuthError, auth_error_handler`. `require_user(request) -> AuthContext(user, tenant)` (raises
  `AuthError` on any miss); tenant is `list_tenants_for_user(user.id)[0]` (solo-owner MVP).
  It does **not** touch `last_used_at` (deferred to P3). Host apps must register
  `exception_handlers={AuthError: auth_error_handler}` — `create_app()` already does. S2 does not
  yet populate `request.state.user`/`tenant`; S3/S4 add that if wanted.
- **Primitives (S4 reuses for `vk_...` credentials):** `from vocky.accounts.security import
  sha256_hex, generate_opaque_token, hash_password, verify_password`. Tokens minted with
  `secrets.token_urlsafe(32)`, persisted only as `sha256_hex(raw)`; `verify_password` returns
  `False` (never raises) on mismatch/bad hash.
- **`SESSION_TTL = timedelta(days=30)`** in `vocky.auth_api`; auth tokens stored with
  `expires_at = utc_now() + SESSION_TTL`.
- **App wiring:** `vocky.auth_api.routes` registered first in `create_app()`'s `routes=[...]`;
  `exception_handlers={AuthError: auth_error_handler}` passed to `Starlette(...)`. Both existing
  middlewares untouched (`/auth/*` matches neither path predicate → public).
- **Reuse note (`format_pydantic_error`):** `auth_api` imports `format_pydantic_error` from
  `vocky.api` (not re-defined) — if S3 also needs Pydantic error formatting, import it from there.

**S3 delivered — `/app/*` account control-plane (what S4/P4/P5 build on):**

- **New route module `src/vocky/app_api.py`**, wired into `create_app()` as `*app_api_routes`
  (right after `*auth_routes`). Top-level **`/app/*`** prefix — matches neither `is_api_path` nor
  `is_admin_api_path`, so it bypasses **both** bearer middlewares and is guarded per-handler by
  S2's `require_user` (each handler starts `ctx = await require_user(request)`; the app-wide
  `AuthError` handler renders the generic 401 — no per-handler catch). Reuses `serialize_tenant`
  (`vocky.auth_api`) and `format_pydantic_error` (`vocky.api`); no new deps, no schema/middleware
  changes.
- **`/app/*` contract (Bearer user token):**
  - `GET /app/tenant` → **200** `{tenant: serialize_tenant(ctx.tenant)}`.
  - `GET /app/projects` → **200** `{projects: [...]}` (tenant-scoped, oldest-first).
  - `POST /app/projects` `{name}` → **201** `{project: ...}`; **400** on bad body
    (`CreateProjectInput`: name stripped, `min_length=1`, `max_length=200`; stored value stripped).
  - `GET /app/projects/{project_id}` → **200** `{project: ...}`; **400** on malformed (non-UUID)
    id; **404** when missing **or** cross-tenant.
  - All routes → **401** on missing/invalid token (shared generic `{"detail":"Unauthorized"}` +
    `WWW-Authenticate: Bearer`).
- **`serialize_project(ProjectRecord)` shape** → `{id, name, tenant_id, created_at}` (all strings,
  `created_at` ISO-8601). Reuse this exact shape for any later project serialization.
- **Cross-tenant-isolation (404) authorization rule — S4 MUST also follow:** any per-project read
  answers **404, never 403**, when `project is None or project.tenant_id != ctx.tenant.id`, so
  cross-tenant existence never leaks. `create_project` binds `tenant_id=ctx.tenant.id` and
  `list_projects_for_tenant` is tenant-scoped, so writes/lists can't cross tenants either. S4's
  credential endpoints (`POST/GET/DELETE .../projects/{id}/credentials`) must resolve the project
  and 404 on a tenant mismatch **before** any credential work.

**S4 delivered — per-project credentials + strictly-mandatory `/api/*` ingest auth (phase objective complete):**

- **Credential `/app/*` contract (user-token authed, cross-tenant-404 like S3's project reads):**
  - `POST /app/projects/{project_id}/credentials` — optional body `{name?}` (blank → null) → **201**
    `{credential: {...}, key: "vk_<token>"}`. The plaintext `vk_` key is emitted **once, only here**;
    only `token_hash = sha256_hex(key)` + display `token_prefix = key[:12]` are stored.
  - `GET /app/projects/{project_id}/credentials` → **200** `{credentials: [{...}]}` (oldest-first,
    metadata only — active and revoked).
  - `DELETE /app/projects/{project_id}/credentials/{credential_id}` → **204** (soft-revoke via
    `revoke_credential`; idempotent). **404** when the credential id isn't in that project's list.
  - `serialize_credential` shape → `{id, project_id, name, token_prefix, created_at, last_used_at,
    revoked_at}` — **never** `token_hash`/`key`. Reuse this exact shape for later credential serialization.
  - Every credential handler resolves the project scoped to the caller's tenant **first** (`_load_scoped_project`):
    400 on a malformed project_id UUID, **404** when the project is missing *or* cross-tenant — so a
    caller can't probe/mutate another tenant's projects or credentials.
- **Key convention (reuse everywhere a project key is minted):** `key = "vk_" + generate_opaque_token()`;
  `token_prefix = key[:12]`; `token_hash = sha256_hex(key)`. The shared test fixture
  `configured_project_credential` (in `tests/conftest.py`, on `configured_database`) seeds
  user→tenant→project→active credential and returns a `SeededCredential(key, project_id, tenant_id,
  user_id, credential_id)` — use it for any `/api/*` test.
- **Mandatory ingest-auth model (`/api/*`):** `ProjectCredentialAuthMiddleware` (in `src/vocky/auth.py`,
  raw ASGI) replaces the retired `APIBearerAuthMiddleware`. On http + `is_api_path`, it extracts the
  bearer (`extract_bearer_credential`) and requires
  `get_active_credential_by_token_hash(sha256_hex(token))` to return a non-None (non-revoked) credential;
  **missing/malformed/unknown/revoked all → generic 401** `{"detail":"Unauthorized"}` + `WWW-Authenticate:
  Bearer`. **No token arg, no open fallback** — auth is always enforced. **Identity-only:** it does NOT
  stash project state on the scope and does NOT touch `last_used_at` (both are P3). Wired in
  `create_app()` as `Middleware(ProjectCredentialAuthMiddleware)` (no token); `AdminBearerAuthMiddleware`
  untouched. `is_api_path`/`is_admin_api_path`/`is_authorized_bearer` all kept.
- **`VOCKY_API_AUTH_TOKEN` fully retired:** removed the `api_auth_token` field + `api_auth_token_value`
  property from `config.py`, the `.env.example` line (replaced with a note that `/api/*` needs a
  per-project credential), and all live references. **Left intentionally untouched (P4 retires the admin
  UI):** `src/vocky/admin_assets/{docs.json,app.js}` and the `tests/test_admin_ui.py` assertion over that
  packaged docs content still mention `VOCKY_API_AUTH_TOKEN` — do NOT scrub these in P2; they are the P4
  operator-surface reshaping. So the "no `VOCKY_API_AUTH_TOKEN`" scrub is complete in the live auth path
  but the packaged admin-UI docs still carry the string by design.
- **Smoke E2E (`src/vocky/smoke.py`):** `run_rest_smoke` now provisions a real key end-to-end:
  `POST /auth/signup` → `POST /app/projects` → `POST /app/projects/{id}/credentials`, then uses the
  returned `vk_` key as the Bearer for `POST /api/feedback` → `GET /api/feedback`. `make_smoke_request_headers`
  (the old `VOCKY_API_AUTH_TOKEN` logic) was removed; health-check helpers kept.
- **Tests:** all `/api/*` test apps (`test_capture_api`, `test_user_feedback_api`, `test_attachments_api`)
  now install `ProjectCredentialAuthMiddleware` and authenticate with the fixture key; each file's former
  static-`token="secret"` case became a "no key / bad key → 401, seeded key → passes" case.
  `test_public_access.py` swapped its two static-token middleware tests for one
  `ProjectCredentialAuthMiddleware` test and asserts the credential route is registered. New
  `tests/test_credentials_api.py` is the credential lifecycle + cross-tenant E2E. Full suite: 153 passed.

## Doc impact

Durable-doc changes for `P2.REVIEW` to consolidate (do not version docs per slice):

- **product** — drop the multi-tenant / "SaaS account, organization, billing" non-goals; add the
  accounts + tenancy direction.
- **architecture** — identity + tenancy layer, per-project ingest auth, `/auth/*` surface.
- **api** — `/auth/*`, tenants/projects/credentials contracts, new public-ingest auth model.
- **data** — new tables (fill the bootstrap stub).
- **backend** — accounts domain (fill the stub).
- **security** — password hashing, session-token + project-credential handling (fill the stub).
- **decisions** — record the auth-model + tenancy-shape choices (fill the stub).

_S1 additions (durable truth landed this slice, for REVIEW to consolidate):_

- **data** — six new tables shipped by migration `20260715_1200`: `users`, `tenants`,
  `tenant_members`, `projects`, `project_credentials`, `auth_tokens` (final columns/constraints
  in the S1 notes above; DB head is now `20260715_1200`).
- **backend** — new `src/vocky/accounts/` domain package (`types`/`repository`/`service` +
  `get_accounts_service()`) mirroring `feedback/`; `create_tenant_with_owner` signup primitive;
  `DuplicateEmailError`.
- **security** — credentials stored as sha256 `token_hash` (+ display `token_prefix`, raw key
  never persisted); session tokens stored as sha256 `token_hash` with optional `expires_at`;
  credential soft-revoke via `revoked_at`. (Password hashing itself is S2.)

_S2 additions (durable truth landed this slice, for REVIEW to consolidate):_

- **api** — public `/auth/*` surface: `POST /auth/signup` (201), `POST /auth/login` (200),
  `POST /auth/logout` (204), `GET /auth/me` (200); signup/login return `{token, user, tenant(s)}`,
  duplicate-email 409, generic 401 for both bad-password and unknown-email (no enumeration),
  Bearer-token auth via `require_user`/`AuthError`.
- **security** — argon2id password hashing (`argon2-cffi`); opaque session tokens
  (`secrets.token_urlsafe(32)`) stored only as sha256 `token_hash` with a 30-day `SESSION_TTL`;
  responses never emit `password_hash`/`token_hash`; login answers an identical generic 401 to
  avoid user enumeration.
- **backend** — reusable `require_user` / `AuthContext` / `AuthError` guard in
  `vocky.accounts.auth`; pure primitives in `vocky.accounts.security`
  (`hash_password`/`verify_password`/`generate_opaque_token`/`sha256_hex`); `vocky.auth_api` routes
  wired into `create_app()` with `exception_handlers={AuthError: auth_error_handler}`.

_S3 additions (durable truth landed this slice, for REVIEW to consolidate):_

- **api** — user-authenticated **`/app/*`** control-plane (top-level prefix, guarded by
  `require_user`, outside `/api/*` so no bearer middleware touches it): `GET /app/tenant` (200),
  `GET /app/projects` (200, tenant-scoped list), `POST /app/projects` (201; 400 on bad name),
  `GET /app/projects/{id}` (200; 400 malformed id; **404 when missing or cross-tenant** — no
  existence leak); project serialized as `{id, name, tenant_id, created_at}`.
- **architecture** — the account/tenant management surface lives on `/app/*` (user-token auth),
  distinct from the `/api/*` product data-plane (per-project credential auth after S4) and the
  admin surface; tenant isolation is enforced per-handler by comparing `project.tenant_id` against
  the caller's `ctx.tenant.id` and answering 404 on mismatch.

_S4 additions (durable truth landed this slice, for REVIEW to consolidate):_

- **api** — per-project credential control-plane on `/app/*` (user-token authed): `POST
  /app/projects/{id}/credentials` (201; returns the plaintext `vk_` key **once** + credential
  metadata), `GET /app/projects/{id}/credentials` (200, metadata list), `DELETE
  /app/projects/{id}/credentials/{credential_id}` (204 soft-revoke); all answer **404 when the
  project is missing or cross-tenant** (400 on malformed id). Credential serialized as `{id,
  project_id, name, token_prefix, created_at, last_used_at, revoked_at}` — never `token_hash`.
- **api / architecture** — public `/api/*` ingest auth is now **strictly mandatory per-project
  credential auth**: every request needs a valid, non-revoked project key; missing/malformed/unknown/
  revoked → generic 401. No open/no-token fallback. The middleware is identity-only in P2 (does not
  yet thread project scope into capture — that's P3).
- **security** — per-project ingest keys: `vk_`-prefixed opaque token, stored only as `sha256_hex`
  `token_hash` (+ display `token_prefix`), plaintext returned once at creation and never recoverable;
  soft-revoke via `revoked_at` immediately fails ingest (`get_active_credential_by_token_hash` filters
  `revoked_at IS NULL`). The static `VOCKY_API_AUTH_TOKEN` global capture token is **retired**.
- **config / deployment** — `VOCKY_API_AUTH_TOKEN` (and the `api_auth_token` setting) removed;
  `.env.example` documents that `/api/*` now requires a per-project credential. (The packaged admin-UI
  docs under `admin_assets/*` still reference `VOCKY_API_AUTH_TOKEN` — intentionally deferred to P4.)

## P2.REVIEW — verdict: PASS (docs consolidated)

Validated all four slices together, then consolidated the phase's durable-doc versions.

**Validation (all green):**
- `uv run pytest` → **153 passed** (hard gate).
- `uv run alembic upgrade head` → clean; DB head `20260715_1200`.
- `python3 scripts/workflow.py validate` → passed.
- Scrub: `api_auth_token` / `APIBearerAuthMiddleware` → none in `src/` or `tests/`; `VOCKY_API_AUTH_TOKEN` remains only in `admin_assets/{docs.json,app.js}` + one `test_admin_ui.py:232` assertion (all P4-deferred, as designed).
- Objective met end-to-end from code: accounts (S2 `/auth/*`), tenants+projects (S1 schema, S3 `/app/*`), per-project credentials (S1 schema, S4 mint/list/revoke), mandatory `/api/*` credential auth via `ProjectCredentialAuthMiddleware` with the static token retired (S4), free/no billing. No regressions or security gaps found; the `/api/*` guard is correctly identity-only (project scoping left to P3).

**Docs consolidated (8, all `--source P2.REVIEW`):** product v0003, architecture v0003, api v0003, experience v0003 (evolved); data v0002, backend v0002, security v0002, decisions v0002 (stubs authored). `frontend`/`operations`/`qa` left untouched. `rebuild-docs` regenerated `docs/current/*`. All lingering `VOCKY_API_AUTH_TOKEN` mentions in the durable docs are explicit "retired / P4-deferred" notes, not live guidance.

## Constraints

## Open Questions

-
