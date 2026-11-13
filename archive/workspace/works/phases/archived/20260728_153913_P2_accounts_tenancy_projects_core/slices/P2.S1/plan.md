# Plan — P2.S1: Identity & tenancy data model + persistence

**Slice job:** Land the foundational accounts/tenancy **schema + persistence layer** for phase P2.
Persistence-only — **no HTTP routes, no `app.py`/middleware changes, no password hashing** (that is
S2), and **no `project_id` on `feedback_events`** (that is P3). Ship the data-access methods S2–S4
will call so those slices stay thin. Read `works/phases/active/P2/phase.md` for the confirmed design
decisions and reuse pointers before starting.

## Schema — six tables (one hand-authored Alembic migration, chained onto head `20260604_2305`)

Follow the existing conventions in `src/vocky/persistence/models.py`: `Mapped`/`mapped_column`,
`PG_UUID(as_uuid=True)` PK `default=uuid4`, `Text`, `DateTime(timezone=True)` with
`server_default=text("CURRENT_TIMESTAMP")` + `default=utc_now`, `ForeignKey(..., ondelete="CASCADE")`,
indexes in `__table_args__`. FK/constraint names derive from `persistence/base.py` `NAMING_CONVENTION`;
in the migration use `op.f("...")` names exactly like
`alembic/versions/20260604_2305_add_feedback_attachments.py` (hand-authored, date-based revision id).

- **users** — `id` PK · `email` Text NOT NULL **unique** (`uq_users_email`; store normalized-lowercase)
  · `password_hash` Text NOT NULL (argon2id string; S1 only stores it) · `created_at`.
- **tenants** — `id` PK · `name` Text NOT NULL · `created_at`. (Ownership lives in `tenant_members`,
  not an `owner_id` column. No slug.)
- **tenant_members** — `id` PK · `tenant_id` FK→tenants CASCADE NOT NULL · `user_id` FK→users CASCADE
  NOT NULL · `role` Text NOT NULL (`owner`/`admin`/`member`; MVP writes `owner`) · `created_at` ·
  **unique** `(tenant_id, user_id)` · indexes on `tenant_id`, `user_id`.
- **projects** — `id` PK · `tenant_id` FK→tenants CASCADE NOT NULL · `name` Text NOT NULL ·
  `created_at` · index on `tenant_id`.
- **project_credentials** — `id` PK · `project_id` FK→projects CASCADE NOT NULL · `name` Text NULL
  · `token_prefix` Text NOT NULL (short display prefix, e.g. `vk_ab12…`) · `token_hash` Text NOT NULL
  **unique** (sha256 hex of the plaintext key) · `created_at` · `last_used_at` TIMESTAMPTZ NULL ·
  `revoked_at` TIMESTAMPTZ NULL (soft revoke; active-lookup filters `revoked_at IS NULL`) · index on
  `project_id`.
- **auth_tokens** — `id` PK · `user_id` FK→users CASCADE NOT NULL · `token_hash` Text NOT NULL
  **unique** (sha256 hex of the opaque session token) · `created_at` · `expires_at` TIMESTAMPTZ NULL
  (NULL = no expiry; S2 sets policy) · `last_used_at` TIMESTAMPTZ NULL · index on `user_id`.

Add all six models to `src/vocky/persistence/models.py`; export them from
`src/vocky/persistence/__init__.py` (`alembic/env.py` already imports `models`).

## Persistence layer — new `src/vocky/accounts/` package (mirror `src/vocky/feedback/`)

- **`types.py`** — `@dataclass(slots=True, kw_only=True)` transport-neutral types: `Create*` inputs
  (`CreateUser` carrying an already-computed `password_hash`, `CreateProject`,
  `CreateProjectCredential` carrying `token_prefix`+`token_hash`, `CreateAuthToken` carrying
  `token_hash`) and `*Record` outputs (`UserRecord`, `TenantRecord`, `TenantMemberRecord`,
  `ProjectRecord`, `ProjectCredentialRecord` — metadata only, **never** the raw token/hash beyond
  `token_prefix`, `AuthTokenRecord`). No ORM leakage across the boundary.
- **`repository.py`** — `class AccountsRepository(session: AsyncSession)`, the **sole ORM boundary**
  (no commit inside; `add`/`flush`/`refresh`/`_to_record`). Methods:
  - users: `create_user`, `get_user_by_email`, `get_user_by_id`
  - tenancy: `create_tenant`, `add_tenant_member`, `get_tenant`, `list_tenants_for_user`
  - projects: `create_project`, `get_project`, `list_projects_for_tenant`
  - credentials: `create_project_credential`, `list_project_credentials`,
    `get_active_credential_by_token_hash`, `revoke_credential`, `touch_credential_last_used`
  - sessions: `create_auth_token`, `get_active_auth_token_by_hash`, `delete_auth_token`,
    `touch_auth_token_last_used`
- **`service.py`** — `class AccountsService(session_maker)` owning the session lifecycle
  (`async with self._session_maker() as session:` + commit/rollback), translating `SQLAlchemyError`
  → domain errors. Define `AccountsPersistenceError`, `AccountsReadError`, and `DuplicateEmailError`
  (raised on the `uq_users_email` `IntegrityError` so S2 returns a clean 409). Provide
  **`create_tenant_with_owner(user_id, name)`** inserting tenant + owner `tenant_members` row in one
  transaction (the signup primitive S2 calls). Module-level factory `get_accounts_service()`
  (mirrors `get_feedback_service()`), reusing `get_session_maker()` from `src/vocky/db.py`.

## Test-fixture update + terse tests

- **`tests/conftest.py`** — extend the `configured_database` `TRUNCATE` (currently the 3 feedback
  tables) to also clear the six new tables, with `CASCADE`.
- **`tests/test_accounts_persistence.py`** (new, terse) — high-value cases via `configured_database`:
  create user + fetch by email/id; duplicate email → `DuplicateEmailError`; `create_tenant_with_owner`
  yields an `owner` membership; project under tenant; credential create → active lookup by
  `token_hash` → revoke (revoked excluded from active lookup); auth-token create → lookup-by-hash →
  delete. Minimal — no factory/fixture sprawl.

## Do NOT touch

`src/vocky/app.py`, `src/vocky/auth.py`, `src/vocky/api.py`, any routes/middleware, the
`feedback_events` schema, or `docs/`. Durable-doc changes are already captured in `phase.md`'s
"Doc impact" list (versioned at P2.REVIEW) — do not run `doc-new-version`.

## Verification (run before returning)

- `uv run alembic upgrade head` applies cleanly; `uv run alembic downgrade -1` then `upgrade head`
  round-trips without error.
- `uv run pytest tests/test_accounts_persistence.py` passes; full `uv run pytest` stays green.
- `get_accounts_service()` imports/returns with no HTTP surface added; `app.py` unchanged.

## Deliverables

Write `result.md` (free-form: what shipped, final table/column names, any surfaced risk). Append
cross-slice notes to `phase.md`: the final schema names, the `create_tenant_with_owner` primitive,
the `token_hash`/`token_prefix` credential convention (S4 reuses), and the session-token convention
(S2 reuses). Return a structured verdict (`done` when verification passes). Do **not** commit or
transition status. Escalate with findings only if the plan is genuinely unworkable.
