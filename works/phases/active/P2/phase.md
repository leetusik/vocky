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

## Constraints

## Open Questions

-
