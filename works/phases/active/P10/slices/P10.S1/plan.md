# P10.S1 — Schema + provisioning

`works/phases/active/P10/slices/P10.S1/plan.md` · kind `implementation` · risk **high** → `slice-executor-high`

## Context

P10 restructures vocky's accounts plane into user → org → project. `P10.DECOMP` cut the phase into five
slices and recorded the binding constraint in `works/phases/active/P10/phase.md`:

> **No slice may make an org key mintable until every credential-derived project filter is org-aware.**

S1 is the **schema and provisioning** slice. It lays the groundwork the rest of the phase stands on, and
its defining property is what it does **not** do:

**S1 ships a schema that *permits* `project_credentials.project_id IS NULL` while writing *no* NULL
rows.** Every footgun the widening creates — the `str(None) == "None"` serializer, the fail-open project
filters — stays unreachable until S2 fixes them and S3 turns minting on. Do not weaken this. **S1 mints
no org-level credential and adds no org-level route.**

Read `works/phases/active/P10/phase.md` first (objective, constraints, footguns, doc-impact list) and
`works/phases/active/P10/intent.md` when intent is unclear. Reference implementation:
`../knowledge/alembic/versions/0003_org_level_credentials.py` and
`../knowledge/server/accounts/service.py` — **read-only, never edit that repo**.

## Scope

### 1. The migration

New file `alembic/versions/20260728_1200_add_org_level_credentials.py`, `down_revision = "20260716_1600"`
(current head). Follow knowledge's `0003` step for step. **The order is load-bearing** — the `tenant_id`
backfill joins *through* `project_id`, so `project_id` must stay `NOT NULL` until the very last step.

Match the house DDL style in `alembic/versions/20260715_1200_add_accounts_tenancy.py`: `op.f(...)` for
every constraint name, `sa.UUID()`, explicit `ondelete="CASCADE"`.

**Step 0 — the de-dupe CTE**, as a module-level constant (knowledge's `_DUPES`), oldest-wins:

```sql
SELECT id AS dead_id, survivor_id FROM (
    SELECT id, first_value(id) OVER (
        PARTITION BY tenant_id, name ORDER BY created_at, id
    ) AS survivor_id
    FROM projects
) ranked WHERE id <> survivor_id
```

The `ORDER BY created_at, id` is deliberately the same order the new `get_project_by_name` resolves and
the same order `list_projects_for_tenant` already uses (`src/vocky/accounts/repository.py:135-141`), so
the migration and the runtime agree on which row "the" project is. Empty on a clean database.

**Step 1 — repoint dependents, then delete.** `UPDATE project_credentials … FROM (_DUPES) d WHERE
pc.project_id = d.dead_id`, then **the same for `feedback_events`** — this is vocky's addition;
knowledge repointed `usage_events`, vocky's analogue is `feedback_events.project_id`
(`alembic/versions/20260716_1500_add_feedback_project_id.py`). **Missing it orphans feedback.** Then
`DELETE FROM projects … USING (_DUPES) d WHERE p.id = d.dead_id` — deletes last, so the subquery still
resolves for both updates.

**Step 2 — the UNIQUE:** `op.create_unique_constraint(op.f("uq_projects_tenant_id"), "projects",
["tenant_id", "name"])`. That name is what the repo's naming convention
(`src/vocky/persistence/base.py:6-18`, `uq_%(table_name)s_%(column_0_name)s`) renders for
`UniqueConstraint("tenant_id", "name")` — model and migration must agree.

**Step 3 — three-phase backfill of `project_credentials.tenant_id`:** add nullable → `UPDATE … SET
tenant_id = p.tenant_id FROM projects p WHERE pc.project_id = p.id` → `SET NOT NULL` → FK
`op.f("fk_project_credentials_tenant_id_tenants")` CASCADE → index `ix_project_credentials_tenant_id`.
The backfill is total precisely because every row still has a `project_id` at this point.

**Step 4 — `project_id` → nullable.** The existing CASCADE FK is unchanged: a bound key still dies with
its project; a NULL org-level row is unaffected.

**Downgrade exists and is destructive by design** (fix-forward repo, same as knowledge): `DELETE FROM
project_credentials WHERE project_id IS NULL` → restore `NOT NULL` → drop the index/FK/column → drop the
UNIQUE. The de-dupe is irreversible; say so in the docstring.

### 2. ORM + types

- `src/vocky/persistence/models.py:234-252` — `ProjectModel.__table_args__` gains
  `UniqueConstraint("tenant_id", "name")` beside the existing `Index`.
- `src/vocky/persistence/models.py:255-283` — `ProjectCredentialModel` gains `tenant_id` (`nullable=False`,
  FK `tenants.id` CASCADE) and an `ix_project_credentials_tenant_id` index; `project_id` becomes
  `Mapped[UUID | None]` / `nullable=True`. Update the class docstring: `tenant_id` is always set and is
  what authorizes at org scope; `project_id IS NULL` ⇒ org-level.
- `src/vocky/accounts/types.py:72-96` — `CreateProjectCredential` gains `tenant_id: UUID` and
  `project_id: UUID | None`; `ProjectCredentialRecord` likewise. Keep both **required** (no default) so
  every call site states its intent explicitly.

### 3. Repository (`src/vocky/accounts/repository.py`)

- New `get_project_by_name(tenant_id, name) -> ProjectRecord | None`, ordered `created_at, id` — mirror
  `list_projects_for_tenant` (`:135-141`) and take the first row.
- `create_project_credential` (`:146-160`) passes `tenant_id` through to the model.
- `_to_credential_record` maps `tenant_id`.

The repository still **never commits** — that contract is unchanged.

### 4. Service (`src/vocky/accounts/service.py`)

Module constant `DEFAULT_PROJECT_NAME = "default"`. **No `DEFAULT_ORG_NAME`** — per operator decision 3
the org keeps its friendly auto-name, so unlike knowledge this is a *project*-only default.

**`provision_signup(user_id: UUID, tenant_name: str) -> tuple[TenantRecord, TenantMemberRecord,
ProjectRecord]`** — tenant + `owner` membership + the `"default"` project in **one session, one commit**.
Model it on `create_tenant_with_owner` (`:99-126`), which stays as-is for bare-tenant callers. Note the
signature difference from knowledge's `provision_signup(user_id)`: knowledge hardcoded its org name, vocky
passes it in.

**`get_or_create_project(tenant_id: UUID, name: str) -> ProjectRecord`** — read-first → insert → catch
`IntegrityError` → rollback → re-read, race-safe against the new UNIQUE. **The nesting matters:**
`IntegrityError` *is* a `SQLAlchemyError`, so the inner `except IntegrityError` must sit inside the outer
`except SQLAlchemyError` or the race handler never runs. `service.py:62` already has an `IntegrityError`
handler (and the import) to model on. Re-raise only when the re-read still finds nothing — that is a
genuine integrity failure, not a race.

### 5. Signup (`src/vocky/auth_api.py:124-153`)

Swap `create_tenant_with_owner` for `provision_signup(user.id, workspace_name)`; `workspace_name` stays
`f"{payload.email.split('@')[0]}'s workspace"` (`:142`). The 201 response gains an **additive** `project`
field beside `token` / `user` / `tenant`.

**Import-cycle note.** `src/vocky/app_api.py:33` already imports `serialize_tenant` / `serialize_user`
**from** `auth_api`, so `auth_api` cannot import `serialize_project` back from `app_api`. Knowledge solved
this by copy-pasting the serializer. Vocky does better at the same cost: **move `serialize_project`
(`src/vocky/app_api.py:68-76`) into `auth_api.py` and import it in `app_api.py`** alongside the two
serializers already crossing that seam — the dependency direction is unchanged and there is no duplicate.

Footgun 4 stands: `create_user` still commits separately, so a failure after it still orphans a
tenant-less user. `provision_signup` narrows the window; it does not close it. **Do not claim it fixed.**

### 6. The `POST /app/projects` fold — moved into this slice by `DECOMP`

`src/vocky/app_api.py:177-191` currently calls `create_project`. Step 2's UNIQUE turns a duplicate name
into `IntegrityError` → `AccountsPersistenceError` → **500**. Fold the handler onto
`get_or_create_project(ctx.tenant.id, payload.name)`, returning the existing row with the **same 201
shape** — idempotent on name. Say so in the docstring. Knowledge hit this exact latent 500 and cleaned it
up a slice later (`../knowledge/.../P18/phase.md:97`); closing it here means no commit boundary ever
carries a known 500.

Also `src/vocky/app_api.py:230-245` — `create_credential` must now pass `tenant_id=project.tenant_id`
(available from `_load_scoped_project`) alongside `project_id=project.id`. **Still project-bound; still
never NULL.**

`serialize_credential` (`src/vocky/app_api.py:79-94`) is **S2's** job, not this slice's — it stays
unconditional here because no NULL row exists to trip it.

### 7. Tests

**Update the stale ones — in scope, not scope creep** (phase.md footgun 5):

- `tests/conftest.py:185` — `CreateProjectCredential` gains `tenant_id=tenant.id`. Same at
  `tests/test_project_feedback_api.py:69` and `tests/test_accounts_persistence.py:98`.
- `tests/test_auth_api.py:36` — the signup response now carries `project`.
- `tests/test_app_api.py:41`, `tests/test_usage_api.py:126`, `tests/test_credentials_api.py:28-36` —
  exact project-set assertions are now stale; a fresh tenant starts with `"default"`.
- No new table, so the two `TRUNCATE` lists (`tests/conftest.py:142-146`, `:151-156`) are unchanged —
  **verify** rather than assume.

**Add, terse** (`AGENTS.md` wants minimal high-value tests — one small module, a couple of cases):

- **`get_or_create_project` is idempotent**: two calls with one name return the same id; two
  `POST /app/projects` with the same name both 201 with the same id (the fold, proven).
- **Signup provisions the default project**: `GET /app/projects` on a fresh account returns exactly
  `["default"]`, and the tenant name is still `"<localpart>'s workspace"` — **decision 3, pinned in a
  test** so a later slice cannot quietly adopt knowledge's `"default"` org.
- **A minted credential carries `tenant_id`** — read the column back directly; the API never exposes it.
- **The migration round-trip, including the de-dupe branch.** `tests/conftest.py:113-119` already builds
  the schema with `alembic upgrade head`, so vocky *does* exercise the migration — but never `downgrade`
  and never the de-dupe (a clean DB has no duplicates). Cover both in one test: `alembic downgrade -1` →
  insert two same-named projects with dependent `project_credentials` **and** `feedback_events` rows →
  `alembic upgrade head` → assert one survivor, children repointed, UNIQUE now rejects a re-insert. It
  ends back at head, so it is self-restoring. **Call `dispose_engine()` before running alembic** (the
  pattern conftest already uses at `:124`) so the async pool does not hold DDL locks. If it proves flaky
  against the shared test database, fall back to knowledge's approach — exercise it manually against a
  disposable Postgres — and **record that decision in `result.md`**; do not silently drop the coverage.

### 8. Not this slice

The serializer NULL-safety, every project-filter call site, the MCP `project` argument, `/app/credentials`,
the tenant-aware resolver, web, CLI, docs. `doc-new-version` is **never** run here — append one-line
**Doc impact** notes to `phase.md` instead; `P10.REVIEW` consolidates.

## Verification

```bash
uv run alembic upgrade head          # against the dev DB — the real migration path
uv run alembic downgrade -1 && uv run alembic upgrade head   # round-trip by hand once
make test                            # = check-test-db + uv run pytest (schema built by alembic)
python3 scripts/workflow.py validate # state integrity
```

The suite is the gate: it hard-requires a live Postgres and there is no CI test job, so `make test` green
is the slice's proof. `make verify` (smoke + test) needs a running app — the review runs it; if it is
cheap to run here, confirm `src/vocky/smoke.py:28-79` still passes, since it hard-codes signup → create
project → mint key → capture and both of the first two responses changed shape (additively).

## Definition of done

Migration applies **and** reverses cleanly; a fresh signup yields one `"default"` project under a tenant
still named `"<localpart>'s workspace"`; duplicate-named creates are idempotent instead of 500; every
credential row carries `tenant_id`; **no row has a NULL `project_id`**; the full suite passes; `result.md`
and the `phase.md` notes are written.
