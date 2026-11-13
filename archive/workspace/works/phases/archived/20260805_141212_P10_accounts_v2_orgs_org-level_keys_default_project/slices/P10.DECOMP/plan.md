# P10.DECOMP — decompose "Accounts v2: orgs, org-level keys & default project"

## Context

P6 closed and committed (`022e9fd`); `workflow.py next` now points at **`P10.DECOMP`**. This plan covers
that one slice: the orchestrator plans it here, and **`slice-executor-high`** executes it — creating
P10's middle slices as **bare folders** and seeding `works/phases/active/P10/phase.md`. It writes no
implementation code and pre-fills no other slice's `plan.md`.

P10 restructures vocky's accounts plane into an explicit **user → org → project** model, following how
the sibling repo `../knowledge` implemented its P18. The confirmed intent is already captured at
`works/phases/active/P10/intent.md` — the executor must read it before cutting slices. The short form:

- No `tenants` → `orgs` rename. The tenant row **is** the org; "org" becomes product-facing naming only.
- Signup auto-provisions a `"default"` **project** (today it creates none at all).
- `projects` gains `UNIQUE(tenant_id, name)` + get-or-create-by-name.
- Credentials become mintable at org level: `project_credentials.tenant_id` NOT NULL, `project_id`
  **nullable**, `project_id IS NULL` ⇒ org-level.

**The one place vocky differs from knowledge, and it is the phase's centre of gravity.** In knowledge,
org-level keys were a *wording* change — its resolver already returned `ctx.tenant_id` and its write path
already authorized by tenant. Vocky is not in that position: `ProjectCredentialAuthMiddleware`
(`src/vocky/auth.py:129-156`) resolves a credential by `token_hash` alone, `ProjectCredentialRecord`
(`src/vocky/accounts/types.py:85-96`) carries **no tenant identity**, and every handler scopes by
`credential.project_id`. So in vocky an org key is a **real trust-boundary widening** and must be
strictly additive — every existing project-bound key keeps its behavior byte-for-byte.

## Operator decisions confirmed at planning (record these verbatim in `phase.md`)

1. **No Claude Design co-work round.** P10 decomposes in a **single pass** — no `co-work` slice, no
   `P10.DECOMP2`. Same call knowledge made for P18. Vocky already has every primitive the org-key surface
   needs (`web/src/components/ui/`: `Card`, `DataTable`, `Badge` incl. an unused `accent` variant,
   `Select`, plus the show-once key panel and revoke-confirm flow in
   `web/src/app/(app)/projects/[projectId]/`), and design round 01 is closed
   (`docs/reference/design/SIGNOFF.md`). The only open question was IA, and knowledge answered it:
   **the org-keys surface is a panel on `/dashboard`** — no new route, no new rail entry.
2. **Ingest under an org key: optional `project` name, get-or-create, defaulting to `"default"`.**
   Mirrors knowledge's `ensure_registry_project`. A project-bound key ignores the field entirely.
3. **The org keeps its friendly auto-name** `"<localpart>'s workspace"` — vocky does **not** adopt
   knowledge's literal `"default"` org name. Nothing resolves an org by name, so the literal buys nothing
   and would regress the dashboard (`web/src/components/app-shell/app-shell.tsx:27,37` renders
   `Workspace <b>{tenant.name}</b>`). **The `"default"` that matters is the project.** This is a
   deliberate, recorded divergence from both the reference implementation and the phase objective's
   wording — the executor must note it in `phase.md`, and `P10.REVIEW` must reflect it in the docs.
4. **P10 = app + CLI parity; P11 = onboarding ergonomics.** In scope: the dashboard org-key panel, the
   nullable `project_id` type widening, Workspace→Org copy in the app and CLI help, and an org-key mint
   path in the CLI. Out of scope, left to P11: `vocky init`, a stored default project, git-root project
   derivation, the env-var quickstart, and **all landing-page marketing copy**
   (`web/src/content/landing.ts:89-109,181-184,230-232` — P11's landing copy depicts the flow P10
   finalizes, per `intent.md`).

## What the executor does

1. Read `intent.md`, `phase.md`, and `AGENTS.md`. Read the knowledge reference material named in
   `intent.md:94-106` (read-only; **never edit `../knowledge`**).
2. Create the middle slices with `python3 scripts/workflow.py new-slice --phase P10 --slice P10.S<n>
   --name "..." --kind implementation --risk <r> --order <n> [--depends-on ...]` — **bare folders only**.
3. Seed `phase.md`: the breakdown table + rationale, the four operator decisions above, the findings and
   footguns below, and a **"Doc impact"** list for `P10.REVIEW` to consolidate.
4. File the deferred job: `python3 scripts/workflow.py defer-job --title "Org management: additional
   orgs, member invites, roles" --reason "..." --trigger "..." --source P10.DECOMP`. The schema already
   supports it (`tenant_members.role` exists, only `"owner"` is ever written,
   `src/vocky/accounts/service.py:117`); the UI/API is not this phase.
5. Run `python3 scripts/workflow.py validate` and write `result.md`.

## Recommended breakdown

Strong guidance, not a straitjacket — the executor finalizes it, but **the invariant in §"Non-negotiable
ordering" below is binding**. Backend first, then the two client surfaces (parallel-safe, both depend
only on the backend). **No slice is `low`** — every one carries schema, hot-path, security-boundary, or
cross-surface-parity judgment. `risk` selects the executor tier, so it is the phase's cost lever.

| slice | kind | risk | depends | scope |
|---|---|---|---|---|
| `P10.S1` | implementation | high | — | Schema migration + ORM/types + provisioning |
| `P10.S2` | implementation | high | S1 | Org-scoped enforcement (dark — nothing mintable yet) |
| `P10.S3` | implementation | high | S2 | Org-key mint surface (turns it on) + `POST /app/projects` get-or-create |
| `P10.S4` | implementation | medium | S3 | Web app: org-keys panel, nullable type, Workspace→Org copy |
| `P10.S5` | implementation | medium | S3 | CLI parity: org-key mint/list/revoke + wording |

S4 and S5 are parallel-safe with respect to each other. The executor may merge S2+S3 into one slice —
knowledge did — but **must not** split them the other way round (see below).

### S1 — Schema + provisioning
- Migration on head `20260716_1600`, following `../knowledge/alembic/versions/0003_org_level_credentials.py`
  step for step: **de-dupe → UNIQUE → add-nullable/backfill/SET-NOT-NULL → relax `project_id`**. The order
  is load-bearing: the `tenant_id` backfill joins through `project_id`, so it only works while `project_id`
  is still NOT NULL.
- De-dupe oldest-wins by `first_value(id) OVER (PARTITION BY tenant_id, name ORDER BY created_at, id)` —
  deliberately the same order the new `get_project_by_name` resolves. **vocky must repoint
  `feedback_events.project_id` as well as `project_credentials.project_id`** before deleting dead rows
  (knowledge repointed `usage_events`; vocky's analogue is `feedback_events`,
  `alembic/versions/20260716_1500_add_feedback_project_id.py`).
- `src/vocky/persistence/models.py`: `ProjectModel` gains `UniqueConstraint("tenant_id","name")`;
  `ProjectCredentialModel` gains `tenant_id` (NOT NULL, FK CASCADE, indexed) and `project_id` → nullable.
- `src/vocky/accounts/types.py`: `CreateProjectCredential` / `ProjectCredentialRecord` gain `tenant_id`;
  `project_id` → `UUID | None`.
- `src/vocky/accounts/repository.py`: `get_project_by_name(tenant_id, name)` ordered `created_at, id`.
- `src/vocky/accounts/service.py`: `provision_signup(user_id)` (tenant + owner membership + `"default"`
  project in **one session, one commit** — vocky has no session-injection seam, so atomicity comes from
  the shared session exactly as knowledge's does) and `get_or_create_project(tenant_id, name)`
  (read-first → insert → catch `IntegrityError` → rollback → re-read). Constant `DEFAULT_PROJECT_NAME =
  "default"`; **no `DEFAULT_ORG_NAME`** — the org keeps `f"{email.split('@')[0]}'s workspace"`
  (`src/vocky/auth_api.py:142`).
- `src/vocky/auth_api.py` signup switches to `provision_signup`; the response gains an **additive**
  `project` field. Existing tenants are never renamed and gain `"default"` lazily via get-or-create.
- **S1 writes NO org-level (NULL `project_id`) rows.** That is what keeps the serialization footgun below
  unreachable until the slice that fixes it.

### S2 — Org-scoped enforcement, landed dark
Make every consumer of `credential.project_id` org-aware **before any org key exists**. The complete call
list (verified):

| site | today | must become |
|---|---|---|
| `src/vocky/api.py:99` | stamps `project_id` on REST capture | resolve from request `project` name → get-or-create → else the org's `"default"` |
| `src/vocky/tools/capture_feedback.py:103` | same for the MCP tool | tool gains an optional `project` argument, same resolution |
| `src/vocky/api.py:236` | `filters.project_id = credential.project_id` (self-read) | org's project id set — **never `None`** |
| `src/vocky/project_feedback_api.py:94` | `filters.project_id = credential.project_id` | `filters.project_ids = <org's project ids>` |
| `src/vocky/project_feedback_api.py:121,189,218,274,302,335` | `_load_project_feedback(id, credential.project_id)` (`:64-79` equality check) | set-membership, mirroring `src/vocky/app_feedback_api.py:108-123` |
| `src/vocky/usage_api.py:202` | `_project_usage_response(credential.project_id, …)` | org-wide mode via `filters.project_ids` (template already exists at `usage_api.py:149-172`) |

**Why this is the phase's sharpest edge:** `FeedbackQueryFilters.project_id = None` means *"no filter"*,
not *"no rows"* (`src/vocky/feedback/repository.py:562-568`). A credential that resolves with a NULL
project therefore **fails open to a global, cross-tenant read**. `docs/current/security.md:58` publishes
the current guarantee and anchors it on exactly the column this phase relaxes: *"Because
`project_credentials.project_id` is `NOT NULL`, the forced filter can never degrade to an unscoped
read."* That sentence must not survive this phase intact.

Also here: `src/vocky/app_feedback_api.py:143-144`'s empty-scope short-circuit is the pattern to copy — an
empty project set must return an empty page, never an unfiltered `IN ()` query. `serialize_credential`
(`src/vocky/app_api.py:84`) becomes NULL-safe (`str(x) if x is not None else None`) — unfixed, an org row
serializes `project_id` as the literal string `"None"`, and the serializer is reused by
`src/vocky/usage_api.py:38,135`.

Adding an optional `project` field to `RestCaptureFeedbackInput` (`src/vocky/capture.py:66`) is additive
and safe: pydantic's default is `extra="ignore"`, so no existing client is affected.

### S3 — Mint surface
- `POST /app/credentials`, `GET /app/credentials`, `DELETE /app/credentials/{credential_id}` — org-level,
  additive beside the per-project routes, `project_id=None` on mint, list filtered
  `tenant_id = … AND project_id IS NULL`, delete 404-never-403 against the caller's **org-level** list only
  (so a project-bound credential id can neither be revoked nor probed through it).
- Middleware/resolver: `ProjectCredentialRecord` now carries `tenant_id`, so an org key authorizes from it
  with **zero extra queries**. Keep the "vanished project ⇒ unresolvable" guard, but **only where
  `project_id` is set** — see `../knowledge/server/api_auth.py:133-187`.
- Fold `POST /app/projects` (`src/vocky/app_api.py:177`) into `get_or_create_project`, returning the
  existing row with the same 201 shape. **This closes a 500 that S1's new UNIQUE constraint introduces** —
  knowledge hit exactly this (`phase.md:97`). If S2 and S3 stay separate, this fix belongs in whichever
  slice lands first after S1, not at the end.
- `src/vocky/app_api.py:284-285` scopes credential delete by listing and scanning in Python; the org
  variant should not inherit that shape blindly.

### S4 — Web app (`web/`)
- `web/src/lib/vocky/types.ts:145` `project_id: string` → `string | null` with the P10 doc comment. This
  produces **exactly one** hard TS error today: `web/src/app/(app)/projects/[projectId]/page.tsx:109`
  (`projectId={credential.project_id}` into `RevokeCredentialButton`'s `projectId: string`). Narrow it —
  a project-detail credential is always project-bound — do not fork the type
  (`../knowledge/web/src/lib/knowledge/types.ts:158-176` records why the shared type was widened).
- Org-keys panel on `/dashboard`, reusing `Card`, `DataTable`, `Badge`, the mint form and show-once key
  panel from `web/src/app/(app)/projects/[projectId]/`. New BFF client fns in `web/src/lib/vocky/app.ts`
  (`listOrgCredentials` / `createOrgCredential` / `revokeOrgCredential`) and server actions appended to
  `web/src/app/(app)/dashboard/actions.ts`. Note the hard constraint documented at
  `web/src/app/(app)/projects/[projectId]/actions.ts:16-23`: a `"use server"` file may export only async
  functions, so form initial state lives in the client island.
- Workspace → Org: `web/src/content/app.ts:33` `workspaceLabel` and the other copy tokens under
  `web/src/content/`. **Label values only** — `tenant_id`, `tenants[]`, `VockyTenant` and every route stay
  as they are.
- UNIQUE(tenant_id, name) falsifies three comments and one passing test: `web/src/lib/vocky/types.ts:56-58`,
  `web/src/lib/vocky/app.ts:62-63`, `web/src/app/(app)/dashboard/page.tsx:116-117`, and
  `web/tests/vocky-app.test.ts:101-108` ("keeps duplicate-named projects distinct"). All four must change.
- `web/src/content/dashboard.ts:69` (`DASHBOARD.projects.empty`) and `web/src/content/project.ts:82`
  become near-unreachable states once signup provisions a project — worth a note, not necessarily a change.
- **Landing copy is out of scope** (decision 4).

### S5 — CLI (`src/vocky/cli/`)
- `keys mint/list/revoke` currently require `--project` (`src/vocky/cli/projects.py:35-40` — the `...`
  makes it mandatory). Add an org-level path.
- Workspace → Org wording in help/output: `projects.py:27,55,201,210`; `feedback.py:29,38`;
  `auth.py:67,92,143,157`; and `docs/cli.md`.
- **Lean-CLI invariant** (`docs/current/experience.md:320-324`): `vocky/cli/*` must not import server
  code, or `pip install vocky` breaks silently. `src/vocky/cli/client.py:27` already imports
  `make_http_user_agent` from `vocky.smoke` — keep that module server-free.
- `vocky init`, a stored default project, and git-root derivation are **P11's**, not this slice's.

## Non-negotiable ordering

**No slice may make an org key mintable until every credential-derived project filter is org-aware.** An
org key that reaches today's handlers reads *every project in every tenant* — a cross-tenant data leak,
not a bug. So: enforcement (S2) lands before or in the same slice as the mint surface (S3); never after.
The executor may merge them; it may not reverse them. Record this in `phase.md` as the slice's headline
constraint.

Knowledge's equivalent safety device was sequencing: S1 shipped a schema that *permits* NULL while writing
*no* NULL rows, so the footguns stayed unreachable until the slice that fixed them
(`../knowledge/works/phases/active/P18/phase.md:84-85`). Mirror it.

## Footguns to carry into `phase.md`

1. **Fail-open project filters** — the §S2 table above. The single most dangerous consequence of relaxing
   the column, and the reason `docs/current/security.md:58` must be rewritten rather than reworded.
2. **`str(None) == "None"`** — `src/vocky/app_api.py:84`, reused by `src/vocky/usage_api.py:38,135`.
3. **`require_user` silently picks `tenants[0]`** (`src/vocky/accounts/auth.py:89-93`) — oldest-first, no
   active-org selection. Fine while a user has one org; it is why multi-org is deferred.
4. **Signup's three independent transactions** (`src/vocky/auth_api.py:124-153`) — a failure after
   `create_user` currently orphans a tenant-less user who can never authenticate. `provision_signup`
   narrows but does not close this; note it.
5. **Behavior change breaks existing tests, and that is in scope, not scope creep.** Signup provisioning a
   project makes exact project-set assertions stale: `tests/test_auth_api.py:36`,
   `tests/test_app_api.py:41`, `tests/test_usage_api.py:126`, `tests/test_credentials_api.py:28-36`.
   `tests/test_project_feedback_api.py:176` pins that `/api/project/*` never leaks `project_id`.
6. **`tests/conftest.py:113-119` builds the test schema with `alembic upgrade head`, not `create_all`** —
   so unlike knowledge, **vocky's suite does exercise the real migration**. What it does *not* exercise is
   `downgrade`, or the de-dupe branch (a clean DB has no duplicates). Add a small round-trip smoke that
   seeds duplicate `(tenant_id, name)` projects with dependent `project_credentials` **and**
   `feedback_events` rows, upgrades, and asserts one survivor with children repointed. Keep it terse —
   `AGENTS.md` wants minimal high-value tests.
   `tests/conftest.py:142-156` lists TRUNCATE tables by name **twice**; any new table must go in both.
7. **`src/vocky/smoke.py:28-79`** hard-codes signup → create project → mint key → capture and is what the
   deploy smoke runs. Signup's additive `project` field and the get-or-create'd `POST /app/projects` must
   keep it green.
8. **The `vk_` prefix is never validated** — auth resolves purely by `sha256_hex` (`src/vocky/auth.py:130-133`).
   A distinct org-key prefix would authenticate fine but buys no cheap pre-DB branch. Note the option;
   don't decide it here.
9. **P12 handoff.** P10's migration lands against an **empty** schema (P6 authored the deploy kit but
   deployed nothing; bring-up is P12), which removes the live-cutover hazards
   (`intent.md:90-93`). Leave a `phase.md` note for P12: migration-before-code ordering, and a read-only
   `GROUP BY tenant_id, name HAVING count(*) > 1` pre-check before the UNIQUE lands. **If the deploy order
   ever changes back, those become blocking.**

## Doc impact to seed (consolidated by `P10.REVIEW`, not by any implementation slice)

`security.md` (the trust-boundary change — a genuine security change, **not** a wording update; `:14`,
`:38`, `:56-59`, `:68`, `:73`), `api.md` (`:75` signup shape, `:107-113` project create,
`:125-139` credential shape + the new `/app/credentials` routes, `:154`, `:171` the MCP `project`
argument), `architecture.md` (`:68`, `:93`, `:207`), `backend.md` (`:22`, `:44-45`), `product.md`
(`:22`, `:28`, `:116-128`, `:152-156`), `experience.md` (`:22-32` onboarding, `:56-58`, `:265`, `:271`,
`:279`, `:287` — the "names are not unique" guarantee is now false, `:334-337`), `data.md` (the
`projects` UNIQUE, `project_credentials.tenant_id`, nullable `project_id`), and `docs/cli.md`.

## Verification

`P10.DECOMP` produces no behavior, so its validation is structural:

```bash
python3 scripts/workflow.py validate      # state integrity
python3 scripts/workflow.py next          # should point at P10.S1
python3 scripts/workflow.py deferred      # the org-management job is filed
```

Plus a read of `works/backlog.md` (the P10 table lists every middle slice with its kind/risk) and of
`phase.md` (breakdown, the four operator decisions, footguns, doc-impact list). Every new slice folder
must contain **only** `slice.json`.

Behavioral validation for the phase happens once, at `P10.REVIEW` (`make verify` = smoke + pytest, plus
`web` typecheck/lint/vitest/build and the CLI suite).
