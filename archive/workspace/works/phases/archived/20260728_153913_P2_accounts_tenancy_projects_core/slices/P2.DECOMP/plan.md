# Plan — P2.DECOMP (decomposition slice)

**Slice job:** Break phase **P2 — Accounts, Tenancy & Projects Core** into its middle
implementation slices. Create the slices as **bare folders** (via `new-slice`) with deliberate
`--risk` ratings, and seed `phase.md` with the breakdown, rationale, findings, and a "Doc impact"
list. **Do not** implement code, pre-fill any slice's `plan.md`, run `doc-new-version`, commit, or
transition slice/phase status. This is structure-only.

## Phase intent recap

Replace the two static env-var bearer tokens with real accounts, and stand up the multi-tenant SaaS
core (tenants → projects → per-project credentials). Free service, no billing. Full operator intent
in `works/phases/active/P2/intent.md`.

## Design decisions (operator-confirmed — bake these into the breakdown; do not re-litigate)

1. **Account auth = email + password + opaque DB-backed bearer tokens.** argon2id password hashing
   (`argon2-cffi`, new dep). Login mints a random opaque token stored **hashed** (sha256; tokens are
   high-entropy so no pepper) in an `auth_tokens` table with `user_id` + expiry; sent as
   `Authorization: Bearer <token>` by web (P4) and CLI (P5). Revoke = delete row. No JWT.
2. **Tenancy = multi-tenant schema, solo-owner MVP flow.** Tables `users`, `tenants`,
   `tenant_members(user_id, tenant_id, role)`, `projects(tenant_id)`, `project_credentials(project_id)`.
   Signup auto-creates a tenant with the user as sole `owner` member. Invites/roles UI deferred.
3. **Capture-scoping boundary = identity only in P2.** Swap public `/api/*` auth to validate a
   per-project credential → resolve project+tenant onto `request.state`. **Do NOT** add `project_id`
   to `feedback_events` or reshape the capture payload — that is P3's job.
4. **Admin auth untouched.** `VOCKY_ADMIN_AUTH_TOKEN` / `AdminBearerAuthMiddleware` stay as-is;
   operator-surface reshaping is P4. Scope S4 to the **public** ingest auth only.

## Slices to create (order S1→S2→S3→S4, before P2.REVIEW; depends_on advisory, chain each on prior)

Use `python3 scripts/workflow.py new-slice --phase P2 --slice P2.S<n> --name "..." --kind implementation --risk <r> --order <n> [--depends-on <prev>]`.

- **P2.S1 — Identity & tenancy data model + persistence** · `--risk medium` · order 1
  One Alembic migration chained onto head `20260604_2305` creating `users`, `tenants`,
  `tenant_members`, `projects`, `project_credentials`, `auth_tokens`. ORM models in
  `src/vocky/persistence/models.py` (+ export in `persistence/__init__.py`). New
  `src/vocky/accounts/` domain package (`types.py`/`repository.py`/`service.py`, `get_accounts_service()`
  factory) mirroring `src/vocky/feedback/`. Terse persistence tests.
  *(Load-bearing schema; the orchestrator may bump to high at plan time.)*

- **P2.S2 — Account auth: signup / login / session tokens + user-auth guard** · `--risk high` · order 2
  Add `argon2-cffi`. Password-hash helpers; signup (creates user + tenant + owner membership),
  login/logout, token issue/validate. Public routes `POST /auth/signup`, `POST /auth/login`,
  `POST /auth/logout`, `GET /auth/me` under a **top-level `/auth/*`** prefix (outside `/api/*` so the
  public-API middleware never guards them). User-auth guard populating `request.state.user`/`tenant`.
  Terse auth tests. Security-sensitive.

- **P2.S3 — Tenants & projects account-scoped API (CRUD)** · `--risk medium` · order 3
  User-authenticated endpoints to read the caller's tenant and create/list/read projects
  (e.g. `GET /api/tenants` or `/api/me/tenant`, `GET/POST /api/projects`, `GET /api/projects/{id}`),
  authorized via S2's guard with owner/membership checks. Terse tests.

- **P2.S4 — Per-project credentials + swap public ingest auth** · `--risk high` · order 4
  User-authenticated credential endpoints: `POST /api/projects/{id}/credentials` (returns plaintext
  `vk_...` key **once**), list (metadata only), revoke. Replace `APIBearerAuthMiddleware`'s
  static-token compare with a hashed-credential lookup → resolve project+tenant onto `request.state`;
  401 on miss. Retire/deprecate `VOCKY_API_AUTH_TOKEN` (config + `.env.example` + `app.py`). Admin
  auth untouched. Update existing `/api/feedback` tests to use a project-credential fixture instead
  of the static token. Changes the public ingest auth boundary.

## Reuse pointers (record the salient ones in phase.md findings)

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

## Doc impact (seed this list in phase.md for P2.REVIEW to consolidate — do NOT version docs here)

- **product** — drop the multi-tenant / "SaaS account, organization, billing" non-goals; add the
  accounts + tenancy direction.
- **architecture** — identity + tenancy layer, per-project ingest auth, `/auth/*` surface.
- **api** — `/auth/*`, tenants/projects/credentials contracts, new public-ingest auth model.
- **data** — new tables (fill the bootstrap stub).
- **backend** — accounts domain (fill the stub).
- **security** — password hashing, session-token + project-credential handling (fill the stub).
- **decisions** — record the auth-model + tenancy-shape choices (fill the stub).

## Deliverables & verdict

- All four slices created (bare folders, only `slice.json`), ordered before `P2.REVIEW`.
- `phase.md` Decomposition / Findings & Notes / Doc-impact sections populated.
- `result.md` written (free-form): what was created + any rationale/risks surfaced.
- Return a structured verdict (`done` on success). No commits, no status transitions, no
  `doc-new-version`, no pre-filled slice `plan.md`.
