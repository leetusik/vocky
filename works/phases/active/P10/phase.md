# Phase P10: Accounts v2: orgs, org-level keys & default project

_Intent: see [intent.md](intent.md)._

## Objective

Restructure vocky's accounts plane into an explicit user -> org -> project model: the existing `tenants` row becomes the org in product-facing naming (no table rename), signup auto-provisions a `default` org and a `default` project, `projects` gains UNIQUE(tenant_id, name) plus get-or-create-by-name, and credentials become mintable at org level (`project_credentials.tenant_id` NOT NULL, `project_id` nullable) so one `vk_` key works across every project in the org — while today's project-bound keys keep their exact current semantics. Org creation beyond the default, member invites, and roles stay out of scope (deferred).

## Constraints

### THE headline constraint — non-negotiable ordering

**No slice may make an org key mintable until every credential-derived project filter is org-aware.**

An org key (`project_id IS NULL`) that reaches today's handlers does not read *nothing* — it reads
**every project in every tenant**. `FeedbackQueryFilters.project_id = None` means *"no filter"*, not
*"no rows"* (`src/vocky/feedback/repository.py:562-568`, verified). So a NULL-project credential
**fails open to a global, cross-tenant read**. That is a data leak, not a bug.

Therefore: **enforcement (S2) lands before, or in the same slice as, the mint surface (S3). Never
after.** A future re-planner may merge S2 and S3; it may **not** reverse them, and it may not move any
part of the mint surface earlier than the enforcement it depends on.

The safety device that makes this work is knowledge's, mirrored here: **S1 ships a schema that
*permits* NULL while writing *no* NULL rows.** Every footgun below is therefore unreachable until the
slice that fixes it. **S1 must write no org-level credential rows** — that invariant is what buys S2 a
calm landing.

### Additive, byte-for-byte
Every **existing project-bound key keeps its current behavior exactly**: same binding, same
enforcement, same 404-never-403 isolation. An org key is a new, broader credential the user explicitly
opts into. Nothing about the widening may leak into the project-bound path.

### Naming, frozen
- No `tenants` → `orgs` table rename. "Org" is product-facing naming only (web copy, CLI output, docs).
  `tenant_id`, `tenants[]`, `VockyTenant`, and every route stay exactly as they are.
- The org keeps its friendly auto-name `"<localpart>'s workspace"`. **The `"default"` that matters is
  the project.** See decision 3.

### Lean-CLI invariant (`docs/current/experience.md:320-324`)
`src/vocky/cli/*` must not import server code, or `pip install vocky` breaks silently.
`src/vocky/cli/client.py:27` already imports `make_http_user_agent` from `vocky.smoke` — keep that
module server-free. Binds S5.

## Context

### Operator decisions confirmed at planning (verbatim from `P10.DECOMP/plan.md`)

1. **No Claude Design co-work round.** P10 decomposes in a **single pass** — no `co-work` slice, no
   `P10.DECOMP2`. Same call knowledge made for P18. Vocky already has every primitive the org-key
   surface needs (`web/src/components/ui/`: `Card`, `DataTable`, `Badge` incl. an unused `accent`
   variant, `Select`, plus the show-once key panel and revoke-confirm flow in
   `web/src/app/(app)/projects/[projectId]/`), and design round 01 is closed
   (`docs/reference/design/SIGNOFF.md`). The only open question was IA, and knowledge answered it:
   **the org-keys surface is a panel on `/dashboard`** — no new route, no new rail entry.
2. **Ingest under an org key: optional `project` name, get-or-create, defaulting to `"default"`.**
   Mirrors knowledge's `ensure_registry_project`. A project-bound key ignores the field entirely.
3. **The org keeps its friendly auto-name** `"<localpart>'s workspace"` — vocky does **not** adopt
   knowledge's literal `"default"` org name. Nothing resolves an org by name, so the literal buys
   nothing and would regress the dashboard (`web/src/components/app-shell/app-shell.tsx:27,37` renders
   `Workspace <b>{tenant.name}</b>`). **The `"default"` that matters is the project.** This is a
   deliberate, recorded divergence from both the reference implementation and the phase objective's
   wording — the executor must note it in `phase.md`, and `P10.REVIEW` must reflect it in the docs.
4. **P10 = app + CLI parity; P11 = onboarding ergonomics.** In scope: the dashboard org-key panel, the
   nullable `project_id` type widening, Workspace→Org copy in the app and CLI help, and an org-key mint
   path in the CLI. Out of scope, left to P11: `vocky init`, a stored default project, git-root project
   derivation, the env-var quickstart, and **all landing-page marketing copy**
   (`web/src/content/landing.ts:89-109,181-184,230-232` — P11's landing copy depicts the flow P10
   finalizes, per `intent.md`).

**Decision 3 is a live divergence from the phase objective's own wording.** The objective sentence
above still says signup provisions "a `default` org and a `default` project". Only the *project* half
is true in vocky. `P10.REVIEW` must reconcile the docs to the code, not to that sentence.

### Reference implementation

`../knowledge` P18, "Accounts v2: user/org/project with org-level keys" (read-only; **never edit that
repo**). Its five slices were S1 schema → S2 resolver+mint+get-or-create → S3 web → S4 CLI/skills →
S5 prod cutover. Vocky's shape differs in one decisive way, and it is the phase's centre of gravity:

**In knowledge, org-level keys were a *wording* change.** Its resolver already returned `ctx.tenant_id`
for a `vk_` key and its write path already authorized by tenant, so "org-level" only made de-facto
behavior honest — knowledge's own note: *"No trust-boundary change … security doc = wording update, not
a boundary shift"* (`../knowledge/.../P18/phase.md:95`).

**Vocky is not in that position.** Verified in code on 2026-07-28:
- `ProjectCredentialAuthMiddleware` (`src/vocky/auth.py:129-156`) resolves a credential by
  `token_hash` **alone** and never resolves a tenant on the ingest path.
- `ProjectCredentialRecord` (`src/vocky/accounts/types.py:85-96`) carries **no tenant identity** —
  `project_id: UUID`, and that is the only ownership it knows.
- Every handler then scopes by `credential.project_id`.

So vocky's keys are project-bound at **both** binding and enforcement, and `docs/current/security.md`
publishes that as a guarantee. **In vocky an org key is a real trust-boundary widening.** This is a
genuine security change, not a doc-wording update, and the phase must document it honestly.

## Decomposition

Five middle slices, orders 1-5 (`DECOMP`=0, `REVIEW`=9999 stays last). Backend first
(S1 schema → S2 enforcement → S3 mint), then the two client surfaces (S4 web, S5 CLI —
**parallel-safe with respect to each other**, both depend only on S3). **No slice is `low`** — every
one carries schema, hot-path, security-boundary, or cross-surface-parity judgment. `risk` selects the
executor tier, so it is the phase's cost lever.

| slice | kind | risk | order | depends | scope |
|---|---|---|---|---|---|
| `P10.S1` | implementation | high | 1 | — | Migration + ORM/types + `provision_signup` + `get_or_create_project` (**incl. the `POST /app/projects` fold**) |
| `P10.S2` | implementation | high | 2 | S1 | Org-scoped enforcement, landed **dark** — nothing mintable yet |
| `P10.S3` | implementation | high | 3 | S2 | Org-key mint surface + tenant-aware resolver — **turns org keys on** |
| `P10.S4` | implementation | medium | 4 | S3 | Web app: dashboard org-keys panel, nullable type, Workspace→Org copy |
| `P10.S5` | implementation | medium | 5 | S3 | CLI parity: org-key mint/list/revoke + Workspace→Org wording |

**Deviation from the plan's recommended breakdown (one, deliberate):** the plan put the
`POST /app/projects` → `get_or_create_project` fold in S3, noting *"If S2 and S3 stay separate, this
fix belongs in whichever slice lands first after S1, not at the end."* It is moved **into S1**
instead. S1 is the slice that *creates* the hazard (its new UNIQUE constraint turns a duplicate-name
create into `IntegrityError` → `AccountsPersistenceError` → **500**, exactly what knowledge hit at
`../knowledge/.../P18/phase.md:97`), and S1 already builds the `get_or_create_project` primitive the
fix needs. Closing it in the same slice means **no slice boundary is ever left with a known 500** —
which matters here because the orchestrator commits at every slice boundary. Everything else follows
the recommended breakdown.

**S2/S3 kept separate (not merged), also deliberate.** Knowledge merged them because it had no
enforcement work to do. Vocky has seven call sites. Keeping them apart buys a checkpoint that is worth
more than the extra dispatch: **S2 is a pure no-observable-behavior-change slice** — no org key exists
yet, so its validation is simply *"the entire existing suite still passes, byte-for-byte"*. That is
the cleanest possible proof that the widening is additive, and it is unavailable once minting is on.
The `depends_on` chain S1←S2←S3 plus the ordering invariant enforces the sequence.

### P10.S1 — Schema + provisioning (risk: high, order 1)

**Scope.**
- Migration on head `20260716_1600`, following
  `../knowledge/alembic/versions/0003_org_level_credentials.py` step for step:
  **de-dupe → UNIQUE → add-nullable/backfill/SET-NOT-NULL → relax `project_id`**. The order is
  load-bearing: the `tenant_id` backfill joins **through** `project_id`, so it only works while
  `project_id` is still NOT NULL. Relax it last.
- De-dupe oldest-wins by
  `first_value(id) OVER (PARTITION BY tenant_id, name ORDER BY created_at, id)` — deliberately the same
  order the new `get_project_by_name` resolves, so the migration and the runtime agree on which row
  "the" project is.
- **vocky must repoint `feedback_events.project_id` as well as `project_credentials.project_id`**
  before deleting dead rows. Knowledge repointed `usage_events`; vocky's analogue is `feedback_events`
  (`alembic/versions/20260716_1500_add_feedback_project_id.py`). Missing this orphans feedback.
- `src/vocky/persistence/models.py`: `ProjectModel` gains `UniqueConstraint("tenant_id","name")`;
  `ProjectCredentialModel` gains `tenant_id` (NOT NULL, FK CASCADE, indexed) and `project_id` →
  nullable.
- `src/vocky/accounts/types.py`: `CreateProjectCredential` / `ProjectCredentialRecord` gain
  `tenant_id`; `project_id` → `UUID | None`.
- `src/vocky/accounts/repository.py`: `get_project_by_name(tenant_id, name)` ordered `created_at, id`.
- `src/vocky/accounts/service.py`: `provision_signup(user_id)` — tenant + owner membership +
  `"default"` project in **one session, one commit** (vocky has no session-injection seam, so atomicity
  comes from the shared session exactly as knowledge's does) — and `get_or_create_project(tenant_id,
  name)` (read-first → insert → catch `IntegrityError` → rollback → re-read; the service already has
  an `IntegrityError` handler at `service.py:62` to model it on). Constant
  `DEFAULT_PROJECT_NAME = "default"`; **no `DEFAULT_ORG_NAME`** — the org keeps
  `f"{email.split('@')[0]}'s workspace"` (`src/vocky/auth_api.py:142`).
- `src/vocky/auth_api.py` signup switches to `provision_signup`; the response gains an **additive**
  `project` field. Existing tenants are never renamed and gain `"default"` lazily via get-or-create.
- **Moved here from the plan's S3:** fold `POST /app/projects` (`src/vocky/app_api.py:177-191`) into
  `get_or_create_project`, returning the existing row with the same **201** shape. See the deviation
  note above.

**S1 writes NO org-level (NULL `project_id`) rows.** That is what keeps every footgun below
unreachable until the slice that fixes it. Do not weaken this.

**Risk = high.** A migration with a de-dupe branch, a UNIQUE constraint, a three-phase backfill, and a
nullability change on the hot credential FK; plus a transactional primitive on the signup path.

### P10.S2 — Org-scoped enforcement, landed dark (risk: high, order 2, depends S1)

**Scope.** Make every consumer of `credential.project_id` org-aware **before any org key exists**. The
complete call list, verified against the tree on 2026-07-28:

| site | today | must become |
|---|---|---|
| `src/vocky/api.py:99` | stamps `project_id` on REST capture | resolve from request `project` name → get-or-create → else the org's `"default"` |
| `src/vocky/tools/capture_feedback.py:103` | same for the MCP tool | tool gains an optional `project` argument, same resolution |
| `src/vocky/api.py:236` | `filters.project_id = credential.project_id` (self-read) | org's project id set — **never `None`** |
| `src/vocky/project_feedback_api.py:94` | `filters.project_id = credential.project_id` | `filters.project_ids = <org's project ids>` |
| `src/vocky/project_feedback_api.py:121,189,218,274,302,335` | `_load_project_feedback(id, credential.project_id)` (`:64-79` equality check) | set-membership, mirroring `src/vocky/app_feedback_api.py:108-123` |
| `src/vocky/usage_api.py:202` | `_project_usage_response(credential.project_id, …)` | org-wide mode via `filters.project_ids` (template already exists at `usage_api.py:149-172`) |

- `src/vocky/app_feedback_api.py:143-144`'s empty-scope short-circuit is **the pattern to copy**: an
  empty project set must return an empty page, never an unfiltered `IN ()` query.
- `serialize_credential` (`src/vocky/app_api.py:84`) becomes NULL-safe
  (`str(x) if x is not None else None`) — unfixed, an org row serializes `project_id` as the literal
  string `"None"`, and the serializer is **reused** by `src/vocky/usage_api.py:38,135`.
- Adding an optional `project` field to `RestCaptureFeedbackInput` (`src/vocky/capture.py:66`) is
  additive and safe: pydantic's default is `extra="ignore"`, so no existing client is affected.

**Validation shape (this is the slice's whole point):** no org key exists yet, so **the existing suite
must pass unchanged**. Any diff in observable behavior for a project-bound key is a bug in this slice.

**Risk = high.** It rewrites the enforcement path on every `/api/*` and `/mcp` request, and the
failure mode is a silent cross-tenant read rather than an error.

### P10.S3 — Org-key mint surface (risk: high, order 3, depends S2)

**Scope.**
- `POST /app/credentials`, `GET /app/credentials`, `DELETE /app/credentials/{credential_id}` —
  org-level, **additive beside** the existing per-project routes. `project_id=None` on mint; list
  filtered `tenant_id = … AND project_id IS NULL`; delete **404-never-403** against the caller's
  **org-level list only**, so a project-bound credential id can neither be revoked nor probed through
  it.
- Middleware/resolver: `ProjectCredentialRecord` now carries `tenant_id`, so an org key authorizes
  from it with **zero extra queries**. Keep the "vanished project ⇒ unresolvable" guard, but **only
  where `project_id` is set** — see `../knowledge/server/api_auth.py:133-187`.
- `src/vocky/app_api.py:284-285` scopes credential delete by listing and scanning in Python; the org
  variant should **not** inherit that shape blindly.

**Risk = high.** This is the slice that opens the trust boundary. It is only safe because S2 landed.

### P10.S4 — Web app (risk: medium, order 4, depends S3)

**Scope.**
- `web/src/lib/vocky/types.ts:145` `project_id: string` → `string | null` with a P10 doc comment. This
  produces **exactly one** hard TS error today:
  `web/src/app/(app)/projects/[projectId]/page.tsx:109` (`projectId={credential.project_id}` into
  `RevokeCredentialButton`'s `projectId: string`). **Narrow it** — a project-detail credential is
  always project-bound — **do not fork the type**
  (`../knowledge/web/src/lib/knowledge/types.ts:158-176` records why the shared type was widened).
- Org-keys panel on `/dashboard`, reusing `Card`, `DataTable`, `Badge`, and the mint form + show-once
  key panel from `web/src/app/(app)/projects/[projectId]/`. New BFF client fns in
  `web/src/lib/vocky/app.ts` (`listOrgCredentials` / `createOrgCredential` / `revokeOrgCredential`) and
  server actions appended to `web/src/app/(app)/dashboard/actions.ts`.
- **Hard constraint documented at `web/src/app/(app)/projects/[projectId]/actions.ts:16-23`:** a
  `"use server"` file may export **only** async functions, so form initial state lives in the client
  island.
- Workspace → Org: `web/src/content/app.ts:33` `workspaceLabel` and the other copy tokens under
  `web/src/content/`. **Label values only** — `tenant_id`, `tenants[]`, `VockyTenant`, every route
  unchanged.
- **UNIQUE(tenant_id, name) falsifies three comments and one passing test.** All four must change:
  `web/src/lib/vocky/types.ts:56-58`, `web/src/lib/vocky/app.ts:62-63`,
  `web/src/app/(app)/dashboard/page.tsx:116-117`, and `web/tests/vocky-app.test.ts:101-108`
  ("keeps duplicate-named projects distinct" — now false by construction).
- `web/src/content/dashboard.ts:69` (`DASHBOARD.projects.empty`) and `web/src/content/project.ts:82`
  become near-unreachable states once signup provisions a project — worth a note, not necessarily a
  change.
- **Landing copy is out of scope** (decision 4).

**Risk = medium.** Web-only, reuses shipped components, no schema or auth-hot-path exposure — but new
surface + BFF wiring + a type widening that ripples, so not mechanical.

### P10.S5 — CLI parity (risk: medium, order 5, depends S3)

**Scope.**
- `keys mint/list/revoke` currently **require** `--project` (`src/vocky/cli/projects.py:35-40` — the
  bare `...` in `_PROJECT_OPTION` makes it mandatory, verified). Add an org-level path.
- Workspace → Org wording in help/output: `projects.py:27,55,201,210`; `feedback.py:29,38`;
  `auth.py:67,92,143,157`; and `docs/cli.md`.
- **Lean-CLI invariant** — see Constraints. `src/vocky/cli/client.py:27` imports `make_http_user_agent`
  from `vocky.smoke`; keep that module server-free.
- `vocky init`, a stored default project, and git-root derivation are **P11's**, not this slice's.

**Risk = medium.** Text-heavy, but the org-vs-project option shape is a real UX judgment call and the
lean-CLI import boundary is silently breakable.

**S4 and S5 are parallel-safe with respect to each other** — both depend only on S3 and touch disjoint
trees (`web/` vs `src/vocky/cli/`). They may run in either order.

## Findings & Notes

_Seeded by `P10.DECOMP` (2026-07-28). Cross-slice facts every later slice must honor; each slice
appends its own "landed" notes below when it finishes._

### Footguns

1. **Fail-open project filters — the single most dangerous consequence of relaxing the column.**
   `FeedbackQueryFilters.project_id = None` means *"no filter"*, not *"no rows"*
   (`src/vocky/feedback/repository.py:562-568`). See the headline constraint above.
   `docs/current/security.md:58` publishes the current guarantee and anchors it on **exactly the column
   this phase relaxes**: *"Because `project_credentials.project_id` is `NOT NULL`, the forced filter can
   never degrade to an unscoped read."* **That sentence must not survive this phase intact** — it must
   be rewritten, not reworded.
2. **`str(None) == "None"`.** `src/vocky/app_api.py:84` `serialize_credential` does
   `str(record.project_id)` unconditionally; it is **reused** by `src/vocky/usage_api.py:38,135`. An
   org row would serialize the literal string `"None"`. Knowledge caught this only because its schema
   slice wrote no NULL rows — the same reason vocky will.
3. **`require_user` silently picks `tenants[0]`** (`src/vocky/accounts/auth.py:89-93`) — oldest-first,
   no active-org selection. Fine while a user has exactly one org; it is precisely why multi-org is
   deferred (D6).
4. **Signup's three independent transactions** (`src/vocky/auth_api.py:124-153`): `create_user`,
   `create_tenant_with_owner`, `_mint_token` each commit separately, so a failure after `create_user`
   orphans a tenant-less user who can never authenticate. `provision_signup` **narrows but does not
   close** this — the user insert stays outside it. Note it; don't silently claim it fixed.
5. **Behavior change breaks existing tests, and that is in scope, not scope creep.** Signup
   provisioning a project makes exact project-set assertions stale: `tests/test_auth_api.py:36`,
   `tests/test_app_api.py:41`, `tests/test_usage_api.py:126`, `tests/test_credentials_api.py:28-36`.
   Also `tests/test_project_feedback_api.py:176` pins that `/api/project/*` never leaks `project_id`.
6. **vocky's suite *does* exercise the real migration** — unlike knowledge's.
   `tests/conftest.py:113-119` builds the test schema with `alembic upgrade head`, not `create_all`.
   What it does **not** exercise is `downgrade`, or the de-dupe branch (a clean DB has no duplicates).
   S1 should add a **terse** round-trip smoke that seeds duplicate `(tenant_id, name)` projects with
   dependent `project_credentials` **and** `feedback_events` rows, upgrades, and asserts one survivor
   with children repointed. `AGENTS.md` wants minimal high-value tests — keep it small.
   **`tests/conftest.py:142-156` lists TRUNCATE tables by name TWICE; any new table must go in both.**
7. **`src/vocky/smoke.py:28-79`** hard-codes signup → create project → mint key → capture, and is what
   the deploy smoke runs. Signup's additive `project` field and the get-or-create'd `POST /app/projects`
   must keep it green.
8. **The `vk_` prefix is never validated** — auth resolves purely by `sha256_hex`
   (`src/vocky/auth.py:130-133`). A distinct org-key prefix would authenticate fine but buys no cheap
   pre-DB branch. Recorded as an **option**, deliberately not decided at DECOMP.

### P10.S1 landed (2026-07-28) — what S2/S3 inherit

**The invariant held: the schema permits `project_credentials.project_id IS NULL`, and not one NULL
row exists.** Verified against the DB after the full suite: `SELECT count(*) FROM
project_credentials WHERE project_id IS NULL` → `0`. There is exactly **one** `CreateProjectCredential`
call site in the tree (`src/vocky/app_api.py:231`, `POST /app/projects/{id}/credentials`) and it sets
both scopes. Every footgun below is therefore still unreachable.

**Migration `20260728_1200` (`down_revision = "20260716_1600"`).** Applied and downgraded cleanly
against the dev DB and, in a test, against the test DB. `alembic check` reports **no** drift on
`projects` / `project_credentials` — the ORM and the migration agree. (It does report a pre-existing
`remove_index ix_feedback_events_search_trgm`: that trigram index is deliberately unmodelled, dating
from `20260716_1600`. Not caused by, and not fixed by, this slice — but a future `alembic check` gate
would need to whitelist it.)

**Facts S2 must build on:**
- `ProjectCredentialRecord` now carries **`tenant_id` (always set)** and `project_id: UUID | None`.
  S3's resolver gets org identity with **zero extra queries** — it is already on the record the
  middleware resolves by `token_hash`.
- `CreateProjectCredential` requires **both** `tenant_id: UUID` and `project_id: UUID | None` — no
  defaults, deliberately, so an org-level mint has to say `project_id=None` out loud.
- `serialize_credential` (`src/vocky/app_api.py:79-94`) is **still unconditional** `str(record.project_id)`.
  Untouched on purpose (footgun 2) — it is S2's to make NULL-safe, and it is safe today only because
  no NULL row exists. It is reused by `src/vocky/usage_api.py:38,135`; both still pass through.
- `AccountsService.get_or_create_project(tenant_id, name)` exists and is race-safe. **S2's ingest
  project resolution should call it**, with `DEFAULT_PROJECT_NAME` (`= "default"`, in
  `vocky.accounts.service`, also re-exported from `vocky.accounts`) as the fallback for decision 2.
- `AccountsRepository.get_project_by_name` / `AccountsService.get_project_by_name` resolve
  oldest-wins by `(created_at, id)` — the same order the migration's de-dupe picks its survivor by.

**Gotchas found while landing S1:**
- **`get_or_create_project`'s nesting is load-bearing and easy to "tidy" into a bug.** `IntegrityError`
  *is* a `SQLAlchemyError`, so the race handler only ever runs because it is nested **inside** the
  outer `except SQLAlchemyError`. Flattening the two into sibling `except` clauses silently turns
  every duplicate-name race back into a 500. A comment in the code says so; do not remove it.
- **Import-cycle resolved by moving, not duplicating.** `serialize_project` now lives in
  `src/vocky/auth_api.py` (signup returns a project) and `app_api.py` imports it from there, beside
  `serialize_tenant`, which it already did. `app_api → auth_api` is the pre-existing direction; the
  reverse would cycle. Knowledge copy-pasted the serializer instead — vocky does not. **Anything that
  needs `serialize_project` must import it from `auth_api`.**
- **One stale test the plan did not list:** `tests/test_persistence.py:45` pins the alembic head
  string (`"20260716_1600"` → `"20260728_1200"`). **Every future migration in this phase must bump it
  too** — it is the one assertion that hard-codes the revision id.
- **`POST /app/projects` is now idempotent on name** and returns **201** either way; a caller cannot
  distinguish created from already-existed. That is deliberate (no slice boundary carries a known
  500), and S4 must reconcile the three web comments + the `web/tests/vocky-app.test.ts:101-108`
  "keeps duplicate-named projects distinct" test that this falsifies.
- **`/app/usage` now always lists at least the `"default"` project** for any signed-up tenant, so
  "a tenant with no projects" is no longer reachable through signup. `usage_api.py`'s empty-scope
  short-circuit is still correct and still worth keeping (S2's pattern to copy) — it is just no
  longer exercised by the signup path. Two tests were re-pinned accordingly
  (`tests/test_usage_api.py`, `tests/test_app_api.py`).
- **The migration test is deliberately synchronous.** `alembic/env.py` calls `asyncio.run`, so it
  cannot run inside the anyio loop; `tests/test_accounts_provisioning.py::test_org_credentials_migration_round_trip`
  is a plain `def` that takes the session-scoped `test_database_url` fixture, calls
  `asyncio.run(dispose_engine())` first (conftest's `:124` pattern) and drives psycopg synchronously.
  It ends back at head and truncates, so it is self-restoring — but it is **order-independent only
  because it disposes the async pool**; keep that call if the test is ever edited.
- **Footgun 4 is narrowed, not closed.** `create_user` still commits in its own transaction before
  `provision_signup`, so a failure between them still orphans a tenant-less user. Said so in
  `signup`'s docstring; do not claim it fixed.
- Footgun 6's TRUNCATE lists were **verified, not assumed**: no new table, so
  `tests/conftest.py:142-146` and `:151-156` are unchanged.

**Decision 3 is now pinned by a test.**
`tests/test_accounts_provisioning.py::test_signup_provisions_default_project_under_friendly_org`
asserts the org name is `"alice's workspace"`, that `DEFAULT_PROJECT_NAME == "default"`, **and** that
`vocky.accounts.service` has **no** `DEFAULT_ORG_NAME` attribute. A later slice adopting knowledge's
`"default"` org would fail that assertion rather than pass silently.

### P10.S2 landed (2026-07-28) — what S3/S4/S5 inherit

**The gate held: the entire pre-existing suite passes byte-for-byte, 191/191, with *zero* edits to
any existing test or assertion.** `tests/test_project_feedback_api.py:177`'s
`"project_id" not in records[0]` pin is still green. That is the proof the org-key widening is purely
additive, and it is a proof that disappears the moment S3 turns minting on — so do not re-derive it,
cite it.

**The structural decision: the scope is resolved once, in the middleware.**
`ProjectCredentialAuthMiddleware` now stashes a second, sibling ASGI scope key alongside the
credential:

- `vocky.auth.CREDENTIAL_PROJECT_IDS_SCOPE_KEY = "vocky.credential_project_ids"`
- resolved by `vocky.auth.resolve_credential_project_ids(credential) -> tuple[UUID, ...]`:
  project-bound ⇒ `(credential.project_id,)` with **no DB call**; org-level ⇒
  `tuple(p.id for p in list_projects_for_tenant(credential.tenant_id))`.
- read back with **`vocky.auth.get_request_project_ids(request) -> tuple[UUID, ...]`**.

**`get_request_project_ids` is the only correct way to scope a credential-authenticated read or
write. `credential.project_id` is nullable and a `None` project filter reads every project in every
tenant.** The non-`None` return type *is* the enforcement — no handler can accidentally produce an
unfiltered read — and it memoizes the lookup per request (the six `_load_project_feedback` sites in
one handler chain would otherwise re-resolve). There is deliberately **no cross-request cache**
(revocation staleness; the repo has no cache layer to reuse).

Scope resolution **fails closed**: an `AccountsReadError` there answers
`500 {"detail": "credential scope unavailable"}` and never falls through to a handler. This is
deliberately *unlike* the neighbouring best-effort `touch_credential_last_used`, which still swallows
its failure — do not "make them consistent".

**Every credential-derived project filter is now set-based.** Verified by grep, not by memory
(`grep -rn "credential.project_id\|get_request_credential" src/vocky/`). After this slice **zero**
filter sites read `credential.project_id`; the only remaining reads are three deliberate ones:
`auth.py:135-136` (the scope resolver), `capture.py:350-351` (the capture resolver), and
`project_feedback_api.py:105` (a *serializer shape* fork, not a filter). `get_request_credential`
survives only where the handler needs the credential's **shape** (the serializer fork) or passes it
to the capture resolver.

**Facts S3/S4/S5 must build on:**
- **`resolve_capture_project(credential, project_name) -> UUID`** lives in `src/vocky/capture.py`
  (importable by both writers with no cycle; `app_api` is deliberately not reached into). Project-bound
  ⇒ the bound project, **`project_name` ignored entirely** — not compared, not 400'd, which is what
  keeps existing clients byte-for-byte. Org-level ⇒ `get_or_create_project(tenant_id, name or
  DEFAULT_PROJECT_NAME)`. It **never returns `None`**, which matters because
  `capture_queue.py:62,97-100` round-trips `project_id` nullably and `worker.py` never re-derives it:
  **enqueue is the last enforcement point.**
- `RestCaptureFeedbackInput` gained `project: str | None = None`; the MCP `capture_feedback` tool
  gained a `project: str | None = None` argument (placed after `channel`, **`ctx` still last**).
  It is deliberately **not** routed through `McpCaptureFeedbackInput` — the project is stamped onto
  the normalized payload after `normalize_mcp_payload`, outside caller control.
- **`/api/project/feedback` serializes `project_id` only for an org key.** `serialize_record`
  (`tools/query_feedback_common.py`) omits `project_id` on the premise that "the project-scoped caller
  knows its own project from its credential"; an org key breaks that premise, so
  `project_feedback_api._serialize_scoped_record` adds `project_id` **when and only when**
  `credential.project_id is None`. A project-bound response is unchanged. **S4/S5 clients reading
  `/api/project/feedback` must treat `project_id` as present-only-for-org-keys.**
- `serialize_credential` (`app_api.py`) is now NULL-safe (`str(x) if x is not None else None`), so an
  org row renders `project_id: null` rather than the string `"None"`. Footgun 2 is **closed**. It is
  still shared with both `usage_api` surfaces. **S4: `web/src/lib/vocky/types.ts:145` must widen to
  `string | null` for this reason, not merely for the new panel.**
- `_project_usage_response` is now scope-taking (`project_ids: tuple[UUID, ...]`) and both callers pass
  a tuple; the session drill-down passes `(project.id,)`.

**A real pre-existing bug was defused, not refactored.** `usage_api.py`'s
`FeedbackQueryFilters(..., project_ids=project_ids or None)` turned an **empty tuple into no project
filter at all** — a global cross-tenant read. It was safe only because the `if not project_ids`
short-circuit happened to run first. The `or None` is gone; the explicit short-circuit stays. The
convention across the whole phase is now: **an empty scope short-circuits to an empty result; a scope
is never collapsed to `None`.**

**S3 handoff — the one thing S3 must not forget.** `/api/project/usage` aggregates its `credentials`
array by looping `list_project_credentials(project_id)` over the scope. **A per-project listing cannot
return org-level rows (`project_id IS NULL`).** So the moment S3 adds `list_org_credentials`, it must
union those rows into `_project_usage_response` — otherwise **an org key's own usage view omits the
very keys it was minted as.** There is a `NOTE for P10.S3` comment at the exact line in
`src/vocky/usage_api.py`, and `tests/test_org_credential_scope.py` pins the current (incomplete)
behavior so S3's change is a visible test edit rather than a silent one.

**Gotchas found while landing S2:**
- **`FeedbackQueryFilters.project_id` is now dead in `src/`** — nothing sets it anywhere in production
  code (verified by grep); only `_apply_query_filters` still honors it, and `tests/test_persistence.py`
  still constructs it. It is the exact field whose `None`-means-no-filter semantics is footgun 1.
  Deleting it is an **option** for S3 or the review, deliberately not taken here (S2 must change no
  observable behavior).
- **Per-project credential listings concatenate out of order.** Each `list_project_credentials` is
  ordered `(created_at, id)`, but concatenating several is not, so `_project_usage_response` re-sorts
  on the same key. That key is chosen to match the repository's `ORDER BY` exactly, which is why the
  single-project payload stays byte-identical.
- **A capture-supplied `project` name is length-capped at 200** (`MAX_CAPTURE_PROJECT_NAME_LENGTH`),
  mirroring `app_api.CreateProjectInput`, because `projects.name` is an unbounded `Text` column and the
  name becomes a get-or-create key. Over-long ⇒ 400 (REST) / tool error (MCP). Blank/whitespace-only
  normalizes to the `"default"` fallback rather than creating a project named `"  "`.
- **The MCP org branch has no transport-level test.** `tests/test_mcp_transport.py` is the suite's sole
  caller of `mcp.session_manager.run()` on the module-level singleton and is deliberately kept to one
  case; the org path is covered through the shared `resolve_capture_project` on the REST surface
  instead. If S3+ wants MCP org coverage, extend that single test rather than adding a second
  session-manager run.
- **The dark-path tests mint org credentials directly at the service layer**
  (`CreateProjectCredential(tenant_id=…, project_id=None, …)`), because there is no mint route until S3
  and S2 must not add one. **S3 should re-point `tests/test_org_credential_scope.py::_mint_credential`
  at the real mint route** so the tests stop reaching under the API.

### P12 handoff (deploy)

P10's migration lands against an **empty** schema — P6 authored the deploy kit but deployed nothing;
bring-up is **P12** (`intent.md:85-93`). That removes the live-cutover hazards entirely for the first
landing. Two things P12 must carry, and they become **blocking** the moment vocky is live:

- **Migration-before-code ordering is load-bearing.** The new code reads a column the migration adds;
  deploying code first 500s *every* `vk_` request. The only safe overlap is old-code + new-schema — and
  even that has a narrow window where a mint or a duplicate-name create fails.
- **Pre-check prod for duplicate `(tenant_id, name)` projects** with a read-only
  `SELECT tenant_id, name, count(*) … GROUP BY tenant_id, name HAVING count(*) > 1` **before** the
  UNIQUE lands, so the operator knows what the de-dupe will merge.

**If the deploy order ever changes back, re-read both as blocking.**

### Deferred

- **D6 — Org management: additional orgs, member invites, roles** (`works/deferred/open/D6`, sourced
  `P10.DECOMP`). The schema already supports it (`tenant_members.role` exists; only `"owner"` is ever
  written, `src/vocky/accounts/service.py:117`). The UI/API — plus the active-org selector that
  footgun 3 makes necessary — is not this phase.

## Doc impact

_Running list for `P10.REVIEW` to consolidate into doc versions. **No implementation slice runs
`doc-new-version`.** Each slice appends here when it changes durable truth._

Seeded by `P10.DECOMP` from the planned scope — line anchors are from the current tree, re-verify at
review time:

- **`security.md`** — the **trust-boundary change**. A genuine security change, **not** a wording
  update (this is where vocky diverges from knowledge's P18, whose equivalent *was* a wording update).
  `:14`, `:38`, `:56-59` (the `NOT NULL` guarantee sentence at `:58` must be **rewritten**), `:68`,
  `:73`.
- **`api.md`** — `:75` signup response shape (additive `project`), `:107-113` project create is now
  get-or-create, `:125-139` credential shape (`project_id` nullable) + the new `/app/credentials`
  routes, `:154`, `:171` the MCP tool's new `project` argument.
- **`architecture.md`** — `:68`, `:93`, `:207`.
- **`backend.md`** — `:22`, `:44-45`.
- **`product.md`** — `:22`, `:28`, `:116-128`, `:152-156`.
- **`experience.md`** — `:22-32` onboarding (signup now provisions a project), `:56-58`, `:265`,
  `:271`, `:279`, **`:287` — the "names are not unique" guarantee is now false**, `:334-337`.
- **`data.md`** — `projects` UNIQUE(tenant_id, name), `project_credentials.tenant_id` NOT NULL,
  `project_id` nullable + its `IS NULL ⇒ org-level` meaning.
- **`docs/cli.md`** — org-level `keys` usage and the Workspace→Org wording.
- **Naming divergence to record explicitly (decision 3):** signup provisions a `"default"` **project**,
  **not** a `"default"` org — the org keeps `"<localpart>'s workspace"`. The phase objective's own
  wording says otherwise; the docs must follow the code.

Appended by **`P10.S1`** (2026-07-28) — the durable truth this slice actually changed:

- **`data.md`** — `projects` gains `UNIQUE(tenant_id, name)` (`uq_projects_tenant_id`);
  `project_credentials` gains `tenant_id` **NOT NULL** (FK `tenants` CASCADE, `ix_project_credentials_tenant_id`)
  and `project_id` becomes **nullable** with the meaning `IS NULL ⇒ org-level`. Migration
  `20260728_1200`, which also de-dupes pre-existing duplicate `(tenant_id, name)` projects oldest-wins
  and repoints both `project_credentials.project_id` and `feedback_events.project_id` to the survivor.
- **`api.md`** — the signup 201 gains an **additive `project`** object beside `token` / `user` / `tenant`;
  `POST /app/projects` is now **get-or-create, idempotent on name**, returning the existing project with
  the same 201 shape instead of a duplicate-name 500.
- **`experience.md`** — signup now lands every new account with a `"default"` project (onboarding no
  longer starts at zero projects), and **project names are unique per org**, so the current
  "names are not unique" guarantee (`:287`) is false as of this slice.
- **`backend.md`** — three new accounts primitives: `AccountsService.provision_signup(user_id, tenant_name)`
  (tenant + owner membership + `"default"` project in one session/one commit),
  `get_or_create_project(tenant_id, name)` (race-safe against the new UNIQUE), and
  `get_project_by_name(tenant_id, name)` (oldest-wins by `created_at, id`). `serialize_project` moved
  from `app_api` to `auth_api` to keep the single `app_api → auth_api` import direction.
- **`product.md`** — a new account is usable immediately: it arrives with an org **and** a project,
  and re-creating a project by an existing name is a no-op rather than an error.
- **`security.md`** — **schema-level only so far, and it must be said precisely.** The guarantee at
  `:58` ("Because `project_credentials.project_id` is `NOT NULL`, the forced filter can never degrade
  to an unscoped read") is **no longer true as a statement about the schema** — the column is nullable
  as of `20260728_1200`. It is still true as a statement about *behavior*, because S1 writes no NULL
  rows and adds no org-level mint path. The trust boundary itself is widened by S2/S3; the review must
  rewrite `:58` rather than reword it.

Appended by **`P10.S2`** (2026-07-28) — the durable truth this slice actually changed:

- **`security.md`** — **the enforcement half of the trust-boundary change is now real code.** Every
  credential-derived project filter is **set-based and can never be `None`**: the ingest middleware
  resolves the credential's project scope once (`get_request_project_ids`, a `tuple[UUID, ...]` — one
  project for a project-bound key, the org's whole project set for an org-level key) and every
  `/api/*` + `/mcp` handler scopes off that, fails **closed** on a resolution error, and short-circuits
  an empty scope to an empty result rather than an unfiltered read. The guarantee at `:58` must be
  **rewritten** to anchor on this (the enforcement) rather than on `project_credentials.project_id`
  being `NOT NULL` (the schema), which is no longer true. **Behaviorally the boundary is still
  project-bound until S3** — no org key is mintable — but the mechanism that will hold it open is now
  the middleware-resolved scope, not the column's nullability. A pre-existing latent fail-open in
  `/app/usage` (an empty project set collapsing to *no project filter*) was **defused** in the same
  slice.
- **`api.md`** — `POST /api/feedback` accepts an **additive optional `project`** name, honored only for
  an org-level key (get-or-created under its org, defaulting to `"default"`) and **ignored entirely**
  by a project-bound key; `:171` the MCP `capture_feedback` tool gains the same optional `project`
  argument with identical semantics. `GET /api/project/feedback` (list and get-one) includes a
  `project_id` on each record **only** when the caller's key is org-level — a project-bound response is
  unchanged. `GET /api/project/usage` reports the caller's whole scope and aggregates credentials
  across it. `:125-139` credential payloads render `project_id: null` (not `"None"`) for an org-level
  row, on both `/app/*` and usage surfaces.
- **`architecture.md`** — a new request-scoped concept: the ingest middleware resolves and stashes the
  **credential project scope** on the ASGI scope beside the credential, and it is the single chokepoint
  every credential-authenticated read/write scopes off. Ingest project resolution is likewise a single
  shared function (`vocky.capture.resolve_capture_project`) used by both the REST and MCP writers;
  because the capture queue round-trips `project_id` nullably and the worker never re-derives it,
  **enqueue is the last enforcement point** in the write path.
- **`backend.md`** — new primitives: `vocky.auth.resolve_credential_project_ids` /
  `get_request_project_ids` / `CREDENTIAL_PROJECT_IDS_SCOPE_KEY`, and
  `vocky.capture.resolve_capture_project` (+ `MAX_CAPTURE_PROJECT_NAME_LENGTH`).
  `project_feedback_api._load_project_feedback` is now set-membership rather than equality (which also
  excludes legacy NULL-`project_id` rows for free), and `usage_api._project_usage_response` is
  scope-taking rather than single-project.
- **`product.md`** — no user-visible change yet by design: this slice is **dark**. Worth stating that
  the org-key capability is enforced before it is offered.

## Open Questions

- **Distinct org-key token prefix?** (footgun 8) The `vk_` prefix is never validated, so a separate
  prefix would authenticate fine but buys no cheap pre-DB branch. Deliberately left open at DECOMP —
  decide in S3 or leave as-is and record it.
- **`DASHBOARD.projects.empty` / `project.ts:82` empty states** become near-unreachable once signup
  provisions a project. Keep, or simplify? S4's call.
