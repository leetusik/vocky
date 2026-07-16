---
doc_id: data
version: v0003
created_at: 2026-07-16T16:31:14+09:00
source: P3.REVIEW
summary: P3: feedback_events.project_id FK+index (migration 20260716_1500), pg_trgm trigram GIN search index (20260716_1600, head); credential/auth-token last_used_at now stamped
previous: v0002_accounts_and_tenancy_schema_users_tenants_tenant_members_projects_project_credentials_auth_tokens_migration_20260715_1200
---

# Data

## Status

This doc covers the **accounts and tenancy** schema (landed by migration `20260715_1200`) plus the **P3 feedback project-scoping and search** schema changes (migrations `20260716_1500` and `20260716_1600`, the current DB head). The full feedback data model (`feedback_events`, `feedback_comments`, `feedback_attachments`) is documented in `architecture.md` (Capture Storage Model / Operator Comment Store / Feedback Attachment Store); this doc records only the P3 additions to `feedback_events` and does not repeat the base shape.

## Conventions

All accounts/tenancy tables follow the same shape as the rest of the schema:

- `id` is a `UUID` primary key, application-generated with `uuid4` (constraint `pk_<table>`).
- `created_at` is `TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`.
- Foreign keys are `ON DELETE CASCADE`, named by the project naming convention (`fk_<table>_<col>_<reftable>`); unique constraints as `uq_<table>_<col>`; indexes as `ix_<table>_<col>`.
- Secrets are never stored in the clear: passwords are stored as an argon2id hash; session tokens and project-credential keys are stored only as a sha256 hex `token_hash`. See `security.md`.

## Migrations

The migration chain, most recent last:

- **`20260715_1200` (`add_accounts_tenancy`)**, chained on `20260604_2305` (the previous feedback-attachments head). `upgrade()` creates the six accounts/tenancy tables and their indexes; `downgrade()` drops them in reverse FK order.
- **`20260716_1500` (`add_feedback_project_id`)**, chained on `20260715_1200`. Adds a nullable `feedback_events.project_id UUID` column, FK `fk_feedback_events_project_id_projects` → `projects.id` `ON DELETE CASCADE`, and index `ix_feedback_events_project_id`. `downgrade()` drops the index, the FK, then the column. No backfill — pre-existing rows stay `NULL`.
- **`20260716_1600` (`add_feedback_search_index`)**, chained on `20260716_1500`. The current DB head. `upgrade()` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` then creates the trigram GIN index `ix_feedback_events_search_trgm` over the immutable concatenated search expression (see below). `downgrade()` drops the index only and **leaves the `pg_trgm` extension** installed.

`tests/test_persistence.py` pins the head at `20260716_1600` and includes `ix_feedback_events_project_id` and `ix_feedback_events_search_trgm` in its expected feedback-index list. The full P3 chain is reversible end-to-end (verified: head → `20260715_1200` → head).

## P3 Feedback Project Scope & Search (additions to `feedback_events`)

The base `feedback_events` shape lives in `architecture.md`; P3 adds:

- **`project_id UUID NULL`** — FK → `projects.id` `ON DELETE CASCADE` (`fk_feedback_events_project_id_projects`), indexed by `ix_feedback_events_project_id`. Stamped at capture from the authenticating project credential's project (D-P3-1). Nullable so legacy pre-MVP rows (no backfill) remain valid; those NULL rows fall out of every project-scoped read. Deleting a project cascades its feedback rows.
- **`ix_feedback_events_search_trgm`** — a `pg_trgm` **trigram GIN** index over the immutable expression `coalesce(message,'') || ' ' || coalesce(comment,'') || ' ' || coalesce(target_text,'') || ' ' || coalesce(trigger_message,'')`. It accelerates the case-insensitive substring (`ILIKE`) free-text search on `/app/feedback` (D-P3-4). The index expression is kept byte-for-byte in lock-step with the predicate built in `vocky.feedback.repository._feedback_search_target()`; only immutable operators (`||`/`coalesce`) are used so the expression index is valid, and the planner uses a `Bitmap Index Scan` on it (verified for Korean and English substrings). The index is intentionally **not** modeled in `__table_args__` — the migration is its source of truth. No `to_tsvector('english', …)` anywhere.

The `pg_trgm` extension (v1.6) is confirmed available and installed on the target Postgres.

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
| `last_used_at` | `TIMESTAMPTZ NULL` | stamped best-effort on each successful `/api/*` ingest auth (P3, one indexed UPDATE by PK; a stamping failure never fails the request); surfaced by the usage endpoints |
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
| `last_used_at` | `TIMESTAMPTZ NULL` | last-seen; stamped best-effort by `require_user` on each authenticated `/app/*`/`/auth/*` call (P3; a stamping failure never fails the request) |

## Relationships & Lifecycle

- Deleting a `user` cascades their `tenant_members` and `auth_tokens`; deleting a `tenant` cascades its `tenant_members`, `projects`, and (through projects) `project_credentials`.
- A user reaches their tenants by joining `tenant_members`; the MVP resolves the caller's "active" tenant as their first tenant (oldest-first).
- `feedback_events.project_id` now links a feedback row to its owning `projects.id` (`ON DELETE CASCADE`), so deleting a project cascades both its `project_credentials` and its feedback rows. The column is stamped at capture from the authenticating credential's project (P3); legacy rows stay NULL and are unreachable through project-scoped reads.

## Notes

- The ORM models live in `src/vocky/persistence/models.py` (`UserModel`, `TenantModel`, `TenantMemberModel`, `ProjectModel`, `ProjectCredentialModel`, `AuthTokenModel`), reusing the shared `Base` + `NAMING_CONVENTION` from `persistence/base.py`.
- The integration-test fixture (`tests/conftest.py`) truncates all six tables with `CASCADE` on setup and teardown, so accounts tests start from a clean schema.
