---
doc_id: data
version: v0004
created_at: 2026-07-28T23:41:58+09:00
source: P10.REVIEW
summary: P10: migration 20260728_1200 — projects UNIQUE(tenant_id,name) with an oldest-wins de-dupe, project_credentials.tenant_id NOT NULL, and project_id nullable (IS NULL = org-level)
previous: v0003_p3_feedback_events.project_id_fk_index_migration_20260716_1500_pg_trgm_trigram_gin_search_index_20260716_1600_head_credential_auth-token_last_used_at_now_stamped
---

# Data

## Status

This doc covers the **accounts and tenancy** schema (landed by migration `20260715_1200`), the **P3 feedback project-scoping and search** schema changes (migrations `20260716_1500` and `20260716_1600`), and the **P10 org-level credential** changes (migration `20260728_1200`, the current DB head). The full feedback data model (`feedback_events`, `feedback_comments`, `feedback_attachments`) is documented in `architecture.md` (Capture Storage Model / Operator Comment Store / Feedback Attachment Store); this doc records only the P3 additions to `feedback_events` and does not repeat the base shape.

**P10 in one line:** `projects` gained `UNIQUE (tenant_id, name)`, and `project_credentials` gained a `NOT NULL` `tenant_id` while its `project_id` became **nullable**, where `project_id IS NULL` means *the credential is scoped to the whole org*. See `security.md` for what that means for the trust boundary — the nullability is a real widening, not a bookkeeping change.

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
- **`20260716_1600` (`add_feedback_search_index`)**, chained on `20260716_1500`. `upgrade()` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` then creates the trigram GIN index `ix_feedback_events_search_trgm` over the immutable concatenated search expression (see below). `downgrade()` drops the index only and **leaves the `pg_trgm` extension** installed.
- **`20260728_1200` (`add_org_level_credentials`)**, chained on `20260716_1600`. The current DB head. See "P10 Org-Level Credentials" below for the step order, which is load-bearing.

`tests/test_persistence.py` pins the head at `20260728_1200` and includes `ix_feedback_events_project_id` and `ix_feedback_events_search_trgm` in its expected feedback-index list. **That pinned revision string is the one assertion in the suite that hard-codes the head — every future migration must bump it.** The chain is reversible end-to-end (re-verified at the P10 review: `head → 20260716_1600 → head`, clean both ways).

`alembic check` reports **no** drift on `projects` / `project_credentials` — the ORM and the migration agree. It does report a **pre-existing** `remove_index ix_feedback_events_search_trgm`, because that trigram index is deliberately unmodelled in `__table_args__` (the migration is its source of truth, see below). That is not caused by P10; any future `alembic check` CI gate must whitelist it.

## P10 Org-Level Credentials (migration `20260728_1200`)

`upgrade()` runs in **four phases, and the order is load-bearing**:

1. **De-dupe existing duplicate `(tenant_id, name)` projects, oldest-wins.** The survivor is chosen with `first_value(id) OVER (PARTITION BY tenant_id, name ORDER BY created_at, id)` — deliberately the *same* order `get_project_by_name` resolves at runtime, so the migration and the application agree on which row "the" project is. Before deleting the losing rows it **repoints both** `project_credentials.project_id` **and** `feedback_events.project_id` at the survivor; missing the second would orphan feedback.
2. **Add the constraint** `UNIQUE (tenant_id, name)` on `projects` (`uq_projects_tenant_id`).
3. **Three-phase backfill of `project_credentials.tenant_id`**: add the column nullable → backfill by joining **through** `project_id` → `SET NOT NULL`, then add FK `fk_project_credentials_tenant_id_tenants` (`ON DELETE CASCADE`) and index `ix_project_credentials_tenant_id`. This only works while `project_id` is still `NOT NULL`, which is why step 4 comes last.
4. **Relax `project_credentials.project_id` to nullable.**

`downgrade()` reverses it, and is destructive by necessity in exactly one place: it **deletes** every `project_credentials` row with a `NULL` `project_id` before restoring `NOT NULL`, because an org-level credential has no project to fall back to. Downgrading therefore revokes every org key. The de-dupe is not reversible either — deleted duplicate projects do not come back.

**Deployment note (P12 owns the live bring-up).** Migration-before-code ordering is load-bearing: the new code reads `project_credentials.tenant_id`, so deploying code first 500s *every* `vk_` request. Old-code + new-schema is the only safe overlap. Before the UNIQUE lands on a populated database, run the read-only pre-check `SELECT tenant_id, name, count(*) FROM projects GROUP BY tenant_id, name HAVING count(*) > 1` so the operator knows what the de-dupe will merge. P10's first landing runs against an **empty** schema, so neither applies yet — they become blocking the moment vocky is live.

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

A named unit under a tenant (the **org**, in product-facing naming) that owns feedback ingestion and per-project credentials.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `tenant_id` | `UUID NOT NULL` | FK → `tenants.id` `ON DELETE CASCADE`; indexed (`ix_projects_tenant_id`) |
| `name` | `TEXT NOT NULL` | trimmed, 1–200 chars |
| `created_at` | `TIMESTAMPTZ NOT NULL` | `CURRENT_TIMESTAMP` |

Constraints: **`UNIQUE (tenant_id, name)`** (`uq_projects_tenant_id`, P10). Project names are therefore **unique per org** — a claim that was explicitly false before P10, and any older doc or comment saying "names are not unique" is stale. The constraint is what makes get-or-create-by-name well-defined: `get_project_by_name(tenant_id, name)` resolves oldest-wins by `(created_at, id)`, matching the migration's de-dupe order.

Every new account arrives with exactly one project, named **`"default"`**, created by `provision_signup` in the same transaction as the org and the owner membership. Note that only the **project** is named `"default"` — the org keeps its friendly auto-name `"<localpart>'s workspace"`. Existing orgs are never renamed and acquire `"default"` lazily via get-or-create.

### `project_credentials`

An ingest key (`vk_…`) scoped **either to one project or to the whole org**. Only the hash and a short display prefix are stored; soft-revoked via `revoked_at`.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID` PK | `uuid4` |
| `tenant_id` | `UUID NOT NULL` | **P10.** FK → `tenants.id` `ON DELETE CASCADE` (`fk_project_credentials_tenant_id_tenants`); indexed (`ix_project_credentials_tenant_id`). Always set, at **both** scopes — it is the owning org, and the outer authorization boundary |
| `project_id` | `UUID NULL` | FK → `projects.id` `ON DELETE CASCADE`; indexed (`ix_project_credentials_project_id`). **Nullable as of P10:** a UUID means the key is bound to that one project; **`NULL` means the key is org-level** and authorizes every project under `tenant_id`, including projects created later. There is no scope enum — the nullable column *is* the discriminator, and it is what the API serializes as `project_id: null` |
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

- Deleting a `user` cascades their `tenant_members` and `auth_tokens`; deleting a `tenant` cascades its `tenant_members`, `projects`, and its `project_credentials` — as of P10 **directly**, via the new `tenant_id` FK, so org-level rows (which have no project to cascade through) are cleaned up too.
- Deleting a **project** cascades only that project's own credentials. An **org-level** credential survives, because it was never bound to the project. An org that has lost every project still owns its org keys and still sees them in its own usage view; those keys simply resolve to an empty project scope, which short-circuits to an empty result rather than an unscoped read.
- A user reaches their tenants by joining `tenant_members`; the MVP resolves the caller's "active" tenant as their first tenant (oldest-first). Creating additional orgs, member invites, and roles are deferred (`tenant_members.role` exists but only `"owner"` is ever written), which is also why no active-org selector exists yet.
- `feedback_events.project_id` now links a feedback row to its owning `projects.id` (`ON DELETE CASCADE`), so deleting a project cascades both its `project_credentials` and its feedback rows. The column is stamped at capture from the authenticating credential's project (P3); legacy rows stay NULL and are unreachable through project-scoped reads.

## Notes

- The ORM models live in `src/vocky/persistence/models.py` (`UserModel`, `TenantModel`, `TenantMemberModel`, `ProjectModel`, `ProjectCredentialModel`, `AuthTokenModel`), reusing the shared `Base` + `NAMING_CONVENTION` from `persistence/base.py`.
- The integration-test fixture (`tests/conftest.py`) truncates all six tables with `CASCADE` on setup and teardown, so accounts tests start from a clean schema. **It lists the tables by name twice** — any new table must be added to both lists.
- Unlike some sibling repos, vocky's test suite **does** exercise the real migration chain: `tests/conftest.py` builds the test schema with `alembic upgrade head`, not `create_all`. What that does *not* cover is `downgrade`, or the de-dupe branch (a clean database has no duplicates), so `tests/test_accounts_provisioning.py::test_org_credentials_migration_round_trip` seeds duplicate `(tenant_id, name)` projects with dependent `project_credentials` **and** `feedback_events` rows, upgrades, and asserts one survivor with children repointed. That test is deliberately **synchronous** (`alembic/env.py` calls `asyncio.run`, so it cannot run inside the anyio loop) and disposes the async pool first; it is order-independent only because of that disposal.
