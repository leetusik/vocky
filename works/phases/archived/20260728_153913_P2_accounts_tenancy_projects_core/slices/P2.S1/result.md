# Result — P2.S1: Identity & tenancy data model + persistence

**Status:** done. Persistence-only landing of the accounts/tenancy schema + domain
package. No HTTP routes, no `app.py`/`auth.py`/`api.py`/middleware, no password hashing,
no `project_id` on `feedback_events`, no `docs/` edits.

## What shipped

### Schema — one hand-authored migration
`alembic/versions/20260715_1200_add_accounts_tenancy.py`, revision `20260715_1200`,
`down_revision = "20260604_2305"` (prior head). Real `downgrade()` drops all six tables +
indexes in FK-safe order. `op.f(...)` names throughout for pk/fk/uq (matching
`persistence/base.py` `NAMING_CONVENTION`); plain names for indexes (matching the attachments
migration style). Verified: `upgrade head` clean, `downgrade -1` → `upgrade head` round-trips,
and `alembic check` reports **"No new upgrade operations detected"** (ORM models == migrated DDL).

### Six tables / final column names
- **users** — `id` PK · `email` Text NOT NULL, unique `uq_users_email` · `password_hash` Text
  NOT NULL · `created_at` TIMESTAMPTZ (`CURRENT_TIMESTAMP`).
- **tenants** — `id` PK · `name` Text NOT NULL · `created_at`. (No `owner_id`, no slug.)
- **tenant_members** — `id` PK · `tenant_id` FK→tenants CASCADE · `user_id` FK→users CASCADE ·
  `role` Text NOT NULL · `created_at` · unique `uq_tenant_members_tenant_id` on
  `(tenant_id, user_id)` · indexes `ix_tenant_members_tenant_id`, `ix_tenant_members_user_id`.
- **projects** — `id` PK · `tenant_id` FK→tenants CASCADE · `name` Text NOT NULL · `created_at` ·
  index `ix_projects_tenant_id`.
- **project_credentials** — `id` PK · `project_id` FK→projects CASCADE · `name` Text NULL ·
  `token_prefix` Text NOT NULL · `token_hash` Text NOT NULL unique `uq_project_credentials_token_hash`
  · `created_at` · `last_used_at` TIMESTAMPTZ NULL · `revoked_at` TIMESTAMPTZ NULL · index
  `ix_project_credentials_project_id`.
- **auth_tokens** — `id` PK · `user_id` FK→users CASCADE · `token_hash` Text NOT NULL unique
  `uq_auth_tokens_token_hash` · `created_at` · `expires_at` TIMESTAMPTZ NULL · `last_used_at`
  TIMESTAMPTZ NULL · index `ix_auth_tokens_user_id`.

Models added to `src/vocky/persistence/models.py` (`UserModel`, `TenantModel`,
`TenantMemberModel`, `ProjectModel`, `ProjectCredentialModel`, `AuthTokenModel`) and exported
from `src/vocky/persistence/__init__.py` (`alembic/env.py` already imports `models`).

### Domain package `src/vocky/accounts/` (mirrors `src/vocky/feedback/`)
- **`types.py`** — `@dataclass(slots=True, kw_only=True)` transport-neutral types. Inputs:
  `CreateUser` (pre-computed `password_hash`), `CreateProject`, `CreateProjectCredential`
  (`token_prefix` + `token_hash`), `CreateAuthToken` (`token_hash`, optional `expires_at`).
  Records: `UserRecord` (carries `password_hash` for login verification), `TenantRecord`,
  `TenantMemberRecord`, `ProjectRecord`, `ProjectCredentialRecord` (metadata only — exposes
  `token_prefix`, **not** `token_hash`), `AuthTokenRecord` (metadata only — no `token_hash`).
- **`repository.py`** — `AccountsRepository(session)`, sole ORM boundary, no commit
  (`add`/`flush`/`refresh`/`_to_*_record`). All planned methods present: users
  (`create_user`, `get_user_by_email`, `get_user_by_id`); tenancy (`create_tenant`,
  `add_tenant_member`, `get_tenant`, `list_tenants_for_user`); projects (`create_project`,
  `get_project`, `list_projects_for_tenant`); credentials (`create_project_credential`,
  `list_project_credentials`, `get_active_credential_by_token_hash`, `revoke_credential`,
  `touch_credential_last_used`); sessions (`create_auth_token`,
  `get_active_auth_token_by_hash`, `delete_auth_token`, `touch_auth_token_last_used`).
- **`service.py`** — `AccountsService(session_maker)` owns session lifecycle + commit/rollback +
  `SQLAlchemyError` → domain error translation. Errors: `AccountsPersistenceError`,
  `AccountsReadError`, `DuplicateEmailError` (subclass of `AccountsPersistenceError`, raised on
  the `IntegrityError` from `uq_users_email` in `create_user`). Primitive
  `create_tenant_with_owner(user_id, name) -> (TenantRecord, TenantMemberRecord)` inserts tenant
  + `owner` membership in one transaction. Module factory `get_accounts_service()` reuses
  `get_session_maker()` from `src/vocky/db.py`.

### Tests / fixtures
- `tests/conftest.py` — extended the `configured_database` TRUNCATE (both setup and teardown) to
  add `users, tenants, tenant_members, projects, project_credentials, auth_tokens` with `CASCADE`.
- `tests/test_accounts_persistence.py` (new, terse, 8 cases): user create + fetch by email/id;
  duplicate email → `DuplicateEmailError`; `create_tenant_with_owner` → `owner` membership;
  project under tenant; credential create → active lookup by `token_hash` → revoke (revoked
  excluded from active lookup, still listed); auth-token create → lookup-by-hash → delete
  (idempotent-false on repeat); factory returns an `AccountsService`.

## Validation
- `uv run alembic upgrade head` — clean (`20260604_2305 -> 20260715_1200`).
- `uv run alembic downgrade -1` then `uv run alembic upgrade head` — round-trips, no error.
- `uv run alembic check` — "No new upgrade operations detected" (models match migration).
- `uv run pytest tests/test_accounts_persistence.py` — 7 passed (+1 sync factory test = 8 tests).
- `uv run pytest` — 139 passed.
- `python3 scripts/workflow.py validate` — passed.
- `get_accounts_service()` imports and returns; `app.py`/`auth.py`/`api.py` unchanged.

## Deviations from plan.md
- **`tests/test_persistence.py:45`** — updated the head-version pin assertion from
  `"20260604_2305"` to `"20260715_1200"`. Required so full pytest stays green after chaining the
  new migration; the plan's "Do NOT touch" list does not cover this file, and keeping the suite
  green is an explicit verification requirement.

## Surfaced risk / notes for later slices
- `UserRecord` intentionally carries `password_hash` (login in S2 needs it to verify). Credential
  and auth-token records deliberately omit the hash — S4/S2 look up by hash, never read it back.
- `revoke_credential` is idempotent (sets `revoked_at` only if currently NULL) and does no
  authorization — owner/tenant checks are S3/S4's job.
- `get_active_auth_token_by_hash` filters `expires_at IS NULL OR expires_at > now()` using a
  Python-side `utc_now()` bound param; S2 sets the expiry policy. `get_active_credential_by_token_hash`
  filters `revoked_at IS NULL` only (credentials have no expiry column).
