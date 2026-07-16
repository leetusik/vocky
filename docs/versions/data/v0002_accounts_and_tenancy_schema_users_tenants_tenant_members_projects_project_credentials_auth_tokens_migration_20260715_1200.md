---
doc_id: data
version: v0002
created_at: 2026-07-16T14:18:50+09:00
source: P2.REVIEW
summary: Accounts and tenancy schema: users, tenants, tenant_members, projects, project_credentials, auth_tokens (migration 20260715_1200)
previous: v0001_bootstrap
---

# Data

## Status

This doc covers the **accounts and tenancy** schema landed by migration `20260715_1200` (the DB head). The feedback data model (`feedback_events`, `feedback_comments`, `feedback_attachments`) is documented in `architecture.md` (Capture Storage Model / Operator Comment Store / Feedback Attachment Store); this doc does not repeat it.

## Conventions

All accounts/tenancy tables follow the same shape as the rest of the schema:

- `id` is a `UUID` primary key, application-generated with `uuid4` (constraint `pk_<table>`).
- `created_at` is `TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`.
- Foreign keys are `ON DELETE CASCADE`, named by the project naming convention (`fk_<table>_<col>_<reftable>`); unique constraints as `uq_<table>_<col>`; indexes as `ix_<table>_<col>`.
- Secrets are never stored in the clear: passwords are stored as an argon2id hash; session tokens and project-credential keys are stored only as a sha256 hex `token_hash`. See `security.md`.

## Migration

- **`20260715_1200` (`add_accounts_tenancy`)**, chained on `20260604_2305` (the previous feedback-attachments head). It is the current DB head; any later migration chains onto it. `tests/test_persistence.py` pins the head at `20260715_1200`. `upgrade()` creates the six tables and their indexes; `downgrade()` drops them in reverse FK order.

## Accounts & Tenancy Tables

### `users`

The account identity. One row per registered user.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `email` | `TEXT NOT NULL` | `UNIQUE` (`uq_users_email`); normalized lowercase by the caller (the schema does not lowercase) |
| `password_hash` | `TEXT NOT NULL` | argon2id hash of the password |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |

### `tenants`

A workspace. Ownership is expressed through `tenant_members`, not an `owner_id` column.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `name` | `TEXT NOT NULL` | signup sets `"<email-local-part>'s workspace"` |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |

### `tenant_members`

Membership join table between users and tenants, carrying the member's role. Signup writes one `owner` row (solo-owner MVP).

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `tenant_id` | `UUID NOT NULL` | FK → `tenants.id` `ON DELETE CASCADE` |
| `user_id` | `UUID NOT NULL` | FK → `users.id` `ON DELETE CASCADE` |
| `role` | `TEXT NOT NULL` | MVP writes `"owner"` |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |

Constraints/indexes: `UNIQUE (tenant_id, user_id)` (`uq_tenant_members_tenant_id`); indexes `ix_tenant_members_tenant_id`, `ix_tenant_members_user_id`.

### `projects`

A named unit under a tenant that owns feedback ingestion and per-project credentials.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `tenant_id` | `UUID NOT NULL` | FK → `tenants.id` `ON DELETE CASCADE`; indexed (`ix_projects_tenant_id`) |
| `name` | `TEXT NOT NULL` | trimmed, 1–200 chars |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |

### `project_credentials`

A per-project ingest key (`vk_…`). Only the hash and a short display prefix are stored; soft-revoked via `revoked_at`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `project_id` | `UUID NOT NULL` | FK → `projects.id` `ON DELETE CASCADE`; indexed (`ix_project_credentials_project_id`) |
| `name` | `TEXT NULL` | optional display label |
| `token_prefix` | `TEXT NOT NULL` | short display prefix, `key[:12]` (e.g. `vk_ab12cd34`) |
| `token_hash` | `TEXT NOT NULL` | `UNIQUE` (`uq_project_credentials_token_hash`); sha256 hex of the raw key |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |
| `last_used_at` | `TIMESTAMPTZ NULL` | not yet stamped by the ingest path (P3) |
| `revoked_at` | `TIMESTAMPTZ NULL` | soft-revoke marker; ingest lookup filters `revoked_at IS NULL` |

### `auth_tokens`

An account session (opaque bearer) minted on signup/login. Only the hash is stored; logout deletes the row.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `user_id` | `UUID NOT NULL` | FK → `users.id` `ON DELETE CASCADE`; indexed (`ix_auth_tokens_user_id`) |
| `token_hash` | `TEXT NOT NULL` | `UNIQUE` (`uq_auth_tokens_token_hash`); sha256 hex of the raw token |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |
| `expires_at` | `TIMESTAMPTZ NULL` | `NULL` = no expiry; signup/login set now + 30 days. Active lookup requires `expires_at IS NULL OR expires_at > now()` |
| `last_used_at` | `TIMESTAMPTZ NULL` | last-seen; not stamped by `require_user` (P3) |

## Relationships & Lifecycle

- Deleting a `user` cascades their `tenant_members` and `auth_tokens`; deleting a `tenant` cascades its `tenant_members`, `projects`, and (through projects) `project_credentials`.
- A user reaches their tenants by joining `tenant_members`; the MVP resolves the caller's "active" tenant as their first tenant (oldest-first).
- No `project_id` is attached to `feedback_events` yet; per-project feedback scoping is P3.

## Notes

- The ORM models live in `src/vocky/persistence/models.py` (`UserModel`, `TenantModel`, `TenantMemberModel`, `ProjectModel`, `ProjectCredentialModel`, `AuthTokenModel`), reusing the shared `Base` + `NAMING_CONVENTION` from `persistence/base.py`.
- The integration-test fixture (`tests/conftest.py`) truncates all six tables with `CASCADE` on setup and teardown, so accounts tests start from a clean schema.
