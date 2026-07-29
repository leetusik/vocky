# Plan — P12.DECOMP (decompose phase P12)

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-high`.

## What this slice is

Cut P12 — "Production launch & hardening: bring-up, rate limits, CI tests, QA doc" — into middle slices.
Create **bare** slice folders with `python3 scripts/workflow.py new-slice` and record the breakdown,
findings, constraints and open questions in `works/phases/active/P12/phase.md`.

**Do not** pre-fill any slice's `plan.md`, do not write implementation code, do not run `doc-new-version`,
do not commit, do not transition slice/phase status.

## Read first (this is the spec, not background)

1. `works/phases/active/P12/intent.md` — the confirmed operator intent. Every scoped item, the ordering
   constraints, the "include or explicitly route, don't silently drop" list, and the out-of-scope line
   (feature work; D3 attachment GC) come from here. **Treat its "Notes" section as binding decomposition
   guidance.**
2. `works/phases/active/P6/phase.md` — **the bring-up spec**: the `P6.S10` row of its decomposition table
   plus every "Hand-off to S10" note in *Findings & Notes*, and the box/edge facts at the top of that
   section (`ssh oracle-cloud`, the `/home/opc/edge` compose project, the `scp` → `validate.sh` →
   `deploy.sh` apply path, co-tenant vhosts that must not be disturbed, and the CONSISTENCY NOTE that the
   box clone **must** live at `/home/opc/vocky` or the compose project name orphans the named volumes).
3. `docs/current/operations.md`, `docs/current/security.md`, `docs/current/architecture.md`,
   `docs/current/qa.md` — the consolidated durable truth (P6's doc impact already landed at `P6.REVIEW`;
   read the consolidated versions, not P6's running list). `qa.md` is still the bootstrap placeholder.
4. The artifacts that have never executed: `compose.prod.yml`, `.env.prod.example`, `deploy/deploy.sh`,
   `deploy/rollback.sh`, `deploy/vocky.conf`, `deploy/github-actions-production-deploy.sh`,
   `deploy/oracle-production-deploy-remote.sh`, `.github/workflows/deploy-production.yml`.
5. `.github/workflows/ci.yml` — **note this exists**: P11.S4 already added the repo's first push/PR gate
   (skill parity, web lint/typecheck/vitest, installer syntax). Its header explicitly says P12 is expected
   to **add a job to this same file, not start a new one**, and names the two things it deliberately
   excluded (`prettier --check`, `uv run pytest` needing Postgres). The intent's "CI has never existed"
   wording predates this file — reconcile and scope the CI slice to *extending* `ci.yml`.
6. `works/deferred/open/D5/` (in scope, must land before/with the bring-up), and `D2`, `D4`, `D6`
   (each must be explicitly routed — promoted into a slice or left deferred with a stated reason).

## Constraints on the decomposition

- **Ordering is prescribed by intent.** The bring-up is **not** first and **not** a single trailing step:
  - Pre-launch: D5 `/auth/*` rate limiting must be in place **before or with** go-live.
  - Independent of the launch (may go early): the `/admin/api/*` fate decision + its
    `VOCKY_ADMIN_AUTH_TOKEN` box-secret consequence, `qa.md`, and the mechanical stale-artifact sweep.
  - Post-launch (statements about a *running* system): Postgres backups, log/metrics, and the CI test
    workflow extension.
- **The bring-up slice is operator/infra co-work, not design.** Create it as `--kind co-work --risk high`
  so the orchestrator runs it inline on the main thread with the operator in the loop (P6.S10 already
  anticipated "likely orchestrator-driven"). Record explicitly in `phase.md` that this `co-work` slice is
  an **infra/operator gate, not a `design-cowork` round** — no `handoff.md`, no `DesignSync`, no Claude
  Design. Its operator gates (`pending`) are: the proxied Cloudflare `vocky` DNS record on the `hi2vi.com`
  zone; on-box `.env` secret generation (`POSTGRES_PASSWORD`, `SESSION_SECRET`,
  `VOCKY_ADMIN_AUTH_TOKEN` — subject to the `/admin` decision); the three `ORACLE_SSH_*` GitHub repo
  secrets on `leetusik/vocky`.
- **Because that co-work is not design, this phase decomposes in ONE pass** — no `P12.DECOMP2`, no build
  inventory. There is no product visual design in P12. (The token-rename sweep below is a mechanical
  rename with zero visual change; it is explicitly *not* to be folded into a visual slice.)
- **Plan the bring-up to iterate, not to succeed first time.** Nothing in the deploy chain has ever run;
  it is simultaneously the first behavioral test of P6.S4–S8, of P10's accounts-v2 migration, and of
  P11's install path. Expect defects in all three and say in `phase.md` how they get absorbed
  (in-slice iteration vs. a follow-on `fix` slice) — but do **not** create `fix` slices now.
- **Risk selects the executor tier and is the phase's main cost lever.** `low` → `slice-executor-low`, a
  literal plan-follower (use only for fully mechanical work: the Makefile/README token sweep is the clear
  candidate); `medium` → `slice-executor-mid`; anything else → `slice-executor-high`. Rate deliberately
  and justify each rating in one clause.
- **Durable docs are versioned once, at `P12.REVIEW`.** No middle slice may hand-edit `docs/current/*.md`
  or run `doc-new-version`. For `qa.md` — which needs a whole new body, not a one-line note — plan the QA
  slice to author the **full intended `qa.md` body inside its own `result.md`** plus a "Doc impact" line
  in `phase.md` pointing at it, so `P12.REVIEW` can consolidate it verbatim into a new doc version. State
  this convention in `phase.md` so the QA slice's later plan inherits it.
- Slice IDs `P12.S1..P12.Sn`, `--order 1..n` (DECOMP is 0, REVIEW is last). Use `--depends-on` where a
  real ordering dependency exists (advisory, existence-checked only).
- Keep the slice count proportionate: this is a hardening phase with ~7 distinct deliverables. Prefer
  cohesive slices over many tiny ones, but never bundle the live bring-up with anything else.

## Must be explicitly included or explicitly routed (never silently dropped)

Each of these gets a row in `phase.md` with the decision (own slice / folded into slice X / stays deferred
+ reason):

- **D5** — `/auth/*` rate limiting (in scope, pre-launch). Decide the mechanism (Cloudflare rule vs.
  in-process per-IP limiter in `src/vocky/auth_api.py`) or leave the choice to the slice's plan, but say
  which and why. Remember: a `limit_req_zone` at the shared edge is **forbidden**.
- **`/admin/api/*` fate** — keep / retire / re-expose deliberately; whichever way, it decides whether
  `VOCKY_ADMIN_AUTH_TOKEN` remains a required box secret, which the bring-up slice depends on. Resolves an
  open question already carried in `docs/current/architecture.md`.
- **`docs/current/qa.md`** — still the bootstrap `v0001` placeholder; the repo has 27 pytest files (108
  needing Postgres), 56 vitest tests, a `qa-agent` subagent and a `/qa-check` skill whose project-defined
  QA driver does not exist. Decide whether the slice also defines that driver or only documents QA.
- **CI test workflow** — extend `.github/workflows/ci.yml` with a Postgres-service pytest job (and decide
  the `prettier --check` question below).
- **Postgres backups + basic log/metrics** — post-launch.
- **Stale-artifact sweep** (cheap, mechanical): root `Makefile` still exports the retired
  `VOCKY_API_AUTH_TOKEN` in `EXPORTED_ENV_VARS`; `README.md:161` still references it; check whether P11
  already dropped the "PyPI publishing is P6; until then…" caveat in `README.md` / `docs/cli.md` before
  touching it.
- **`pnpm format:check` debt** — the 12–13 pre-existing P4-era prettier failures. A CI gate will surface
  them; decide **before** the gate can go red: fix, scope the check, or defer with a reason.
- **Design token-rename pass** — retiring vestigial hi2vi names (`victory-lime`, `archive-*`,
  `security-*`), costed in the P8 gate's `build-prompt.md §2.4` as its own mechanical slice. Include as a
  standalone mechanical slice or defer it — explicitly **not** folded into a visual slice.
- **D4** (project-scope the end-user attachment download endpoint) and **D2** (public-safe field
  projection) — its trigger is "next time the `/api/*` attachment surface is touched"; P12 likely does not
  touch it. Route explicitly.
- **D6** (org management) and **D3** (attachment GC) — both out of scope per intent; note that they stay
  deferred.

## Deliverables

1. Middle slices created via `new-slice` (bare folders — `slice.json` only).
2. `works/phases/active/P12/phase.md` filled in:
   - **Decomposition**: a table (Slice | Kind | Risk | Delivers) + the ordering rationale, mirroring the
     P6 phase.md style, plus the routing decisions for every item in the section above.
   - **Findings & Notes**: the durable facts later slices need without re-deriving them — the box/edge
     access model, the `/home/opc/vocky` clone-path constraint and *why*, the never-executed status of the
     deploy chain, the `ci.yml`-already-exists reconciliation, the qa.md-via-result.md doc convention, and
     the `/admin` decision's dependency on the bring-up's secret list.
   - **Constraints** and **Open Questions**: anything the operator must decide at a later slice's gate.
3. A concise `result.md` for this slice (free-form): what was created, the risk-rating rationale, and any
   surprises found while reading the P6 spec.

## Validation

- `python3 scripts/workflow.py validate` passes.
- `python3 scripts/workflow.py next` resolves to the first new middle slice.
- Every created slice folder contains `slice.json` and **no** `plan.md`.
