# P10.DECOMP — result

Decomposed "Accounts v2: orgs, org-level keys & default project" into **five middle slices** (S1–S5),
seeded `works/phases/active/P10/phase.md`, and filed the deferred org-management job. **No
implementation code was written**, and no other slice's `plan.md` was pre-filled — every new slice
folder contains only `slice.json`.

## Slices created

| slice | kind | risk | order | depends_on |
|---|---|---|---|---|
| `P10.S1` | implementation | **high** | 1 | — |
| `P10.S2` | implementation | **high** | 2 | `P10.S1` |
| `P10.S3` | implementation | **high** | 3 | `P10.S2` |
| `P10.S4` | implementation | medium | 4 | `P10.S3` |
| `P10.S5` | implementation | medium | 5 | `P10.S3` |

Full names, scope, and rationale live in `phase.md § Decomposition`. Per the plan, **no slice is
`low`** — every one carries schema, hot-path, security-boundary, or cross-surface-parity judgment.
S4 and S5 are parallel-safe with respect to each other (disjoint trees: `web/` vs `src/vocky/cli/`).

## Grounding: what I verified in the tree before cutting slices

The plan's central premise — vocky's org key is a **real trust-boundary widening**, unlike knowledge's
wording-only change — checked out at every anchor I sampled:

- `src/vocky/auth.py:129-156` — the middleware resolves a credential by `sha256_hex(token)` alone; no
  tenant is ever resolved on the ingest path. Confirmed.
- `src/vocky/accounts/types.py:85-96` — `ProjectCredentialRecord` carries `project_id: UUID` and **no
  tenant identity**. Confirmed.
- `src/vocky/feedback/repository.py:562-568` — `_apply_query_filters` applies the project predicate
  only `if filters.project_id is not None`. **`None` really does mean "no filter", not "no rows"** —
  the fail-open leak is real, and it is what makes the ordering invariant non-negotiable.
- `src/vocky/api.py:99`, `:236`; `src/vocky/project_feedback_api.py:64-79`, `:94` — all present and
  shaped as the plan describes.
- `src/vocky/app_api.py:84` — `"project_id": str(record.project_id)`, unconditional. The `"None"`
  footgun is real.
- `src/vocky/app_feedback_api.py:108-123` (set-membership `_load_scoped_feedback`) and `:141-144`
  (empty-scope short-circuit → `{"records": []}`) — the two patterns S2 must copy. Both present.
- `src/vocky/auth_api.py:124-153` — three independent commits (`create_user`,
  `create_tenant_with_owner`, `_mint_token`); tenant named `f"{localpart}'s workspace"`; **no project
  created**. Confirmed.
- `src/vocky/accounts/service.py:62` — an existing `IntegrityError` handler for `get_or_create_project`
  to model on. `repository.py` has `create_project` / `get_project` / `list_projects_for_tenant` but
  **no `get_project_by_name`**, as the plan says.
- `src/vocky/cli/projects.py:35-40` — `_PROJECT_OPTION = typer.Option(..., "--project", …)`; the bare
  `...` makes it mandatory. Confirmed.
- `web/src/lib/vocky/types.ts:145` — `project_id: string`; `web/src/content/app.ts:33` —
  `workspaceLabel: "Workspace"`. Confirmed.

I also read `../knowledge/works/phases/active/P18/phase.md` (read-only; that repo was not modified).
Its five-slice shape and its explicit `phase.md:84-85` "S1 writes NO org-level rows" safety device are
what P10 mirrors. Its `phase.md:95` records the opposite conclusion for knowledge — *"No trust-boundary
change … security doc = wording update"* — which is precisely the sentence vocky **cannot** reuse, and
the clearest confirmation the plan's premise correction is right.

## Deviations from `plan.md`

**One, deliberate.** Everything else follows the recommended breakdown, including the slice count, the
risk assignments, and the S4/S5 split.

**The `POST /app/projects` → `get_or_create_project` fold moves from S3 into S1.** The plan placed it
in S3 while noting: *"If S2 and S3 stay separate, this fix belongs in whichever slice lands first after
S1, not at the end."* I put it one step earlier still — **in S1 itself** — because:

1. **S1 is the slice that creates the hazard.** Its new `UNIQUE(tenant_id, name)` turns a
   duplicate-name `POST /app/projects` into `IntegrityError` → `AccountsPersistenceError` → **500**.
   Knowledge hit exactly this and had to clean it up a slice later (`../knowledge/.../P18/phase.md:97`,
   "Latent dupe-500 killed").
2. **S1 already builds the primitive the fix needs** — `get_or_create_project` is in S1's scope per the
   plan. The fold is a two-line change at `src/vocky/app_api.py:177-191`.
3. **The orchestrator commits at every slice boundary.** Leaving a known 500 in the tree across a
   commit is avoidable here at zero cost, and avoiding it is strictly stronger than the plan's stated
   constraint ("not at the end"), never weaker.

**S2 and S3 were kept separate, not merged** (the plan permitted merging, since knowledge merged).
Knowledge merged because it had *no* enforcement work; vocky has seven call sites. Keeping them apart
buys a checkpoint worth more than the extra dispatch: **S2 is a pure no-observable-behavior-change
slice** — no org key exists yet, so its validation is "the existing suite passes byte-for-byte", which
is the cleanest available proof that the widening is additive. That proof is unavailable once minting
is on. The `depends_on` chain S1←S2←S3 encodes the order the invariant requires.

## Binding constraint recorded

`phase.md § Constraints` opens with the headline, as the plan required:

> **No slice may make an org key mintable until every credential-derived project filter is org-aware.**

with the fail-open mechanism spelled out, the "S1 writes NO org-level rows" safety device, and the
explicit rule that a future re-planner **may merge S2 and S3 but may not reverse them**.

## Deferred job filed

**`D6` — "Org management: additional orgs, member invites, roles"**, source `P10.DECOMP`
(`works/deferred/open/D6`). Reason records that the schema already supports it
(`tenant_members.role`, only `"owner"` ever written, `src/vocky/accounts/service.py:117`) and that the
missing piece is the UI/API **plus the active-org selector** that footgun 3 (`require_user` silently
picks `tenants[0]`, `src/vocky/accounts/auth.py:89-93`) makes necessary. Trigger: a user needing a
second org, a second person sharing an org, or per-seat pricing.

## Doc impact

**No `doc-new-version` was run** — durable docs are versioned once, at `P10.REVIEW`. I seeded the
running **`## Doc impact`** list in `phase.md` for the review to consolidate:

`security.md` (the trust-boundary change — a genuine security change, **not** a wording update; the
`NOT NULL` guarantee sentence at `:58` must be **rewritten**), `api.md`, `architecture.md`,
`backend.md`, `product.md`, `experience.md` (incl. `:287`, where the "names are not unique" guarantee
becomes false), `data.md`, and `docs/cli.md` — each with the specific line anchors from the plan.

Plus one entry the review must not miss: **decision 3's naming divergence.** Signup provisions a
`"default"` **project**, **not** a `"default"` org — the org keeps `"<localpart>'s workspace"`. The
phase objective's own wording (in `phase.json` and at the top of `phase.md`) still says "a `default`
org and a `default` project". Only the project half is true. The docs must follow the code, and I
flagged this in `phase.md` twice (Context and Doc impact) so it cannot be quietly inherited.

## Validation

| command | outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **pass** — "Workflow validation passed." (exit 0) |
| `python3 scripts/workflow.py next` | **pass** — `current_phase=P10`, `current_slice=P10.DECOMP`, **`next_slice=P10.S1`** |
| `python3 scripts/workflow.py deferred` | **pass** — `open=6`; `D6` present in `works/deferred.md` sourced `P10.DECOMP` |
| `python3 scripts/workflow.py rebuild` | **pass** — dashboards regenerated |
| `ls -A` on every `P10` slice folder | **pass** — S1–S5 each contain **only** `slice.json` |
| `works/backlog.md` P10 table | **pass** — all seven slices listed (DECOMP, S1–S5, REVIEW) with kind + status |
| `git status --porcelain` | **pass** — only `works/**` changed; **no source file touched**, no commit made |

Behavioral validation for the phase happens once, at `P10.REVIEW` (`make verify` = smoke + pytest, plus
`web` typecheck/lint/vitest/build and the CLI suite). `P10.DECOMP` produces no behavior, so its
validation is structural by design.

## Notes for the orchestrator

- `P10.S1` is next and is `high` risk → `slice-executor-high`. S2 and S3 likewise. S4/S5 are `medium`.
- Nothing in this slice was committed and no slice or phase status was transitioned.
- `phase.md § Open Questions` carries two items left deliberately undecided at DECOMP: whether org keys
  get a distinct token prefix (footgun 8 — the `vk_` prefix is never validated, so it buys no cheap
  pre-DB branch), and whether the now near-unreachable empty states in `web/src/content/dashboard.ts:69`
  and `web/src/content/project.ts:82` should be simplified.
