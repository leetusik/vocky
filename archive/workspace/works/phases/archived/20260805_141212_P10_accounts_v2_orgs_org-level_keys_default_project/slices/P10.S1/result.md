# P10.S1 — Schema + provisioning — result

**Status: done.** The schema now *permits* `project_credentials.project_id IS NULL`, and **no NULL row
exists**. No org-level credential is mintable and no org-level route was added, so every downstream
footgun stays unreachable until S2 fixes them and S3 turns minting on.

Verified directly rather than assumed:

```
SELECT count(*) FROM project_credentials WHERE project_id IS NULL;  ->  0
```

There is exactly one `CreateProjectCredential` call site in the tree (`src/vocky/app_api.py:231`) and it
sets both `tenant_id` and `project_id`.

## What landed

**Migration** — `alembic/versions/20260728_1200_add_org_level_credentials.py`,
`down_revision = "20260716_1600"`. Knowledge's `0003` step for step, in the load-bearing order:
de-dupe → UNIQUE → add-nullable/backfill/SET-NOT-NULL/FK/index → relax `project_id` **last** (the
`tenant_id` backfill joins *through* `project_id`, so it is total only while `project_id` is still
`NOT NULL`). House DDL style throughout: `op.f(...)` for every constraint name, `sa.UUID()`, explicit
`ondelete="CASCADE"`.

- `_DUPES` is the module-level oldest-wins CTE from the plan, `first_value(id) OVER (PARTITION BY
  tenant_id, name ORDER BY created_at, id)` — the same order the new `get_project_by_name` resolves and
  `list_projects_for_tenant` already used, so migration and runtime agree on which row "the" project is.
- **vocky's addition over knowledge:** `feedback_events.project_id` is repointed alongside
  `project_credentials.project_id`, both **before** the `DELETE FROM projects` (so the subquery still
  resolves for both updates). Knowledge repointed `usage_events`; missing vocky's analogue would orphan
  feedback. This is covered by a test, not just by reading.
- Downgrade exists and is destructive by design (fix-forward repo): delete NULL-project credentials →
  restore `NOT NULL` → drop index/FK/column → drop the UNIQUE. The de-dupe is irreversible and the
  docstring says so.

**ORM + types**
- `ProjectModel.__table_args__` gains `UniqueConstraint("tenant_id", "name")`. The repo naming
  convention renders it `uq_projects_tenant_id`, which is exactly the name the migration creates —
  confirmed in the live schema, not inferred.
- `ProjectCredentialModel` gains `tenant_id` (`nullable=False`, FK `tenants.id` CASCADE) plus
  `ix_project_credentials_tenant_id`; `project_id` is now `Mapped[UUID | None]` / `nullable=True`. The
  class docstring states the new contract (`tenant_id` always set and authorizing at org scope;
  `project_id IS NULL` ⇒ org-level).
- `CreateProjectCredential` and `ProjectCredentialRecord` both gain `tenant_id: UUID` and
  `project_id: UUID | None`, **both required, no defaults**, so every call site states its scope.

**Repository / service**
- New `AccountsRepository.get_project_by_name(tenant_id, name)` ordered `created_at, id`, mirroring
  `list_projects_for_tenant`; `create_project_credential` passes `tenant_id` through;
  `_to_credential_record` maps it. The repository still never commits.
- `DEFAULT_PROJECT_NAME = "default"` in `src/vocky/accounts/service.py`, re-exported from
  `vocky.accounts`. **No `DEFAULT_ORG_NAME`** (operator decision 3) — the comment above the constant
  says why.
- `provision_signup(user_id, tenant_name) -> (TenantRecord, TenantMemberRecord, ProjectRecord)` —
  tenant + `owner` membership + the `"default"` project in one session, one commit.
  `create_tenant_with_owner` is untouched for bare-tenant callers.
- `get_or_create_project(tenant_id, name)` — read-first → insert → `IntegrityError` → rollback →
  re-read, re-raising only when the re-read still finds nothing. The `except IntegrityError` is nested
  **inside** the outer `except SQLAlchemyError` (an `IntegrityError` is a `SQLAlchemyError`, so a
  sibling clause would never fire); a code comment pins that so it is not "tidied" into a bug.

**Signup** — `src/vocky/auth_api.py` now calls `provision_signup(user.id, workspace_name)`;
`workspace_name` is still `f"{payload.email.split('@')[0]}'s workspace"`. The 201 gains an additive
`project` field. `signup`'s docstring records that `create_user` still commits separately, so the
orphan window is **narrowed, not closed** (footgun 4) — not claimed fixed.

**Import cycle** — solved by *moving*, not duplicating: `serialize_project` now lives in `auth_api.py`
and `app_api.py` imports it from there, alongside `serialize_tenant` / `serialize_user`, which already
crossed that seam. The `app_api → auth_api` direction is unchanged and there is no duplicate.

**The `POST /app/projects` fold** — the handler now calls `get_or_create_project(ctx.tenant.id,
payload.name)` and returns the existing row with the same **201** shape; the docstring states it is
idempotent on name and that callers cannot distinguish created from already-existed. This closes, in
the same slice that creates it, the latent duplicate-name → `IntegrityError` → `AccountsPersistenceError`
→ 500 that the new UNIQUE would otherwise have left sitting at a commit boundary.
`create_credential` now passes `tenant_id=project.tenant_id` beside `project_id=project.id` — still
project-bound, still never NULL, with a comment saying so. `serialize_credential` is deliberately
**untouched** (S2's job).

## Tests

Stale ones updated (in scope per footgun 5): `tests/conftest.py`, `tests/test_project_feedback_api.py`,
`tests/test_accounts_persistence.py` (`tenant_id=` on `CreateProjectCredential`);
`tests/test_auth_api.py` (signup carries `project`); `tests/test_app_api.py` and
`tests/test_usage_api.py` (project-set assertions — a fresh tenant now starts with `"default"`).

Footgun 6 checked rather than assumed: no new table, so the two TRUNCATE lists in `tests/conftest.py`
are **unchanged**.

**One stale test the plan did not list:** `tests/test_persistence.py:45` hard-codes the alembic head
(`"20260716_1600"` → `"20260728_1200"`). Every future migration in this phase must bump it too; noted
in `phase.md`.

`tests/test_credentials_api.py` needed no change — its helpers create uniquely-named projects and it
asserts no project set.

New module `tests/test_accounts_provisioning.py`, four terse cases:
1. **Signup provisions the default project** — org name still `"alice's workspace"`,
   `DEFAULT_PROJECT_NAME == "default"`, `GET /app/projects` returns exactly `["default"]`, **and**
   `vocky.accounts.service` has no `DEFAULT_ORG_NAME`. Decision 3 is now pinned by an assertion, so a
   later slice cannot quietly adopt knowledge's `"default"` org.
2. **Project creation is idempotent on name** — two `POST /app/projects` with one name both 201 with
   the same id (the fold, proven), and the service primitive converges on the same row.
3. **A minted credential carries `tenant_id`** — read back straight from the column (the API never
   exposes it), and its `project_id` is still bound.
4. **Migration round-trip including the de-dupe branch** — `alembic downgrade -1` → seed two
   same-named projects with dependent `project_credentials` **and** `feedback_events` rows →
   `alembic upgrade head` → assert one survivor (the older), both children repointed, credential
   backfilled with `tenant_id`, and the UNIQUE now rejecting a re-insert. It ends back at head and
   truncates, so it is self-restoring.

   It runs **synchronously** on purpose: `alembic/env.py` calls `asyncio.run`, which cannot be nested
   in the anyio loop. It takes the session-scoped `test_database_url` fixture and calls
   `asyncio.run(dispose_engine())` first — conftest's `:124` pattern — so the async pool holds no
   connection while DDL runs. **It ran green against the shared test database**, so the plan's fallback
   (exercise it by hand against a disposable Postgres) was not needed and the coverage was not dropped.

## Verification — commands and actual outcomes

| command | outcome |
|---|---|
| `uv run alembic upgrade head` (dev DB) | **pass** — `Running upgrade 20260716_1600 -> 20260728_1200` |
| `uv run alembic downgrade -1 && uv run alembic upgrade head` | **pass** — down then up; `alembic current` → `20260728_1200 (head)` |
| `make test` (= `check-test-db` + `uv run pytest`) | **pass — 191 passed in 8.67s**, 0 failed |
| `python3 scripts/workflow.py validate` | **pass** — `Workflow validation passed.` |
| `make smoke` (extra, not required of this slice) | **pass** — `healthz ok`; `POST /api/feedback accepted`; `GET /api/feedback ok: 1 record(s)` |

`make test` was first run at **190 passed / 1 failed** — the failure was
`tests/test_persistence.py::test_migration_applies_and_expected_indexes_exist` asserting the old head
string. Fixed as described above; the re-run is the 191/0 in the table.

Extra checks beyond the plan's list:
- `uv run alembic check` — reports **no** drift on `projects` / `project_credentials`, i.e. the ORM and
  the migration agree. It does report a **pre-existing** `remove_index ix_feedback_events_search_trgm`
  (a deliberately unmodelled trigram index from `20260716_1600`, untouched by this slice).
- `\d project_credentials` / `\d projects` on the live DB — confirms `tenant_id` NOT NULL, the CASCADE
  FK to `tenants`, `ix_project_credentials_tenant_id`, `project_id` nullable with its CASCADE FK
  intact, and `uq_projects_tenant_id UNIQUE (tenant_id, name)`.

The smoke run needed `docker compose up --build -d --force-recreate app worker`: the previously cached
`app` container was running a stale image and died with `Failed to spawn: vocky-server`. That is a
stale-image artifact of the local environment, **not** a regression from this slice — a rebuilt image
starts and passes. Worth knowing for P12, which brings the stack up for real.

## Definition of done — checked

- Migration applies **and** reverses cleanly — yes, by hand against the dev DB and in a test.
- Fresh signup yields one `"default"` project under a tenant still named `"<localpart>'s workspace"` —
  yes, pinned by test.
- Duplicate-named creates are idempotent instead of 500 — yes, pinned by test.
- Every credential row carries `tenant_id` — yes, pinned by test (read from the column).
- **No row has a NULL `project_id`** — yes, verified by query; only one mint call site and it is bound.
- Full suite passes — 191/0.
- `result.md` + `phase.md` notes written — this file, plus a "P10.S1 landed" section and six Doc impact
  lines in `phase.md`.

## Doc impact (appended to `phase.md`, not versioned here)

No `doc-new-version` was run — `P10.REVIEW` consolidates. Six one-line notes appended: `data.md`
(UNIQUE + `tenant_id` NOT NULL + nullable `project_id`), `api.md` (additive signup `project`,
get-or-create `POST /app/projects`), `experience.md` (signup provisions a project; project names are
now unique per org, falsifying `:287`), `backend.md` (`provision_signup` / `get_or_create_project` /
`get_project_by_name`, `serialize_project` moved), `product.md` (a new account arrives usable),
`security.md` (the `:58` `NOT NULL` guarantee is false **as a statement about the schema** as of this
slice, though still true of behavior — the review must rewrite it, and S2/S3 own the actual boundary
widening).

## Deviations from `plan.md`

**One, additive.** The plan's stale-test list did not include `tests/test_persistence.py:45`, which
pins the alembic head revision string; it had to be bumped for the suite to go green. Same class of
change as the listed stale tests (in scope, not scope creep), recorded in `phase.md` because every
later migration in this phase must bump it too.

Everything else followed the plan as written, including the migration step order, the `feedback_events`
repoint, decision 3 (no `DEFAULT_ORG_NAME`), the serializer *move* rather than knowledge's copy-paste,
leaving `serialize_credential` to S2, and running the migration round-trip as a real test rather than
falling back to the manual disposable-Postgres option.
