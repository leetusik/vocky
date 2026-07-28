# P6.REVIEW — plan

Review phase **P6** and return a verdict. Follow `.claude/skills/review-phase/SKILL.md` — it is your checklist.
This plan only records what is unusual about P6, so you judge it against the right target.

## Judge P6 against its *reframed* scope, not its Objective string

P6's `phase.json` objective still reads "Build the public landing page/site … and deploy to production at
vocky.hi2vi.com". **Both halves of that are no longer P6's.** `phase.md` §Context records two reframes; read them
first:

1. **Reframe 1 (DECOMP-era).** The landing/webpage was already built and designed in P8 (design gate) → P9 (apply);
   decision **D-P8-1 superseded D-P4-3**, redefining P6 as *production-deploy-only*.
2. **Reframe 2 (2026-07-28, operator).** The live bring-up moved **out of P6 into P12**. Operator, verbatim:
   _"mind that deploy will be done at p12 so p6 doesn't have to mind it."_ The `P6.S10` stub was removed; its spec
   (the S10 row of the decomposition table, and every "Hand-off to S10" note in *Findings & Notes*) stays in
   `phase.md` deliberately, because **P12 executes it**.

**So the standard P6 must meet is:** every production artifact authored and statically validated, nothing deployed.

Concretely, "shipped" for P6 means: the packaged Admin Web UI physically removed (S1); the web app's metadata /
origin / CSP work landed (S2, S3); and a complete, internally consistent deploy kit authored — `web/Dockerfile`
(S4), `compose.prod.yml` + `.env.prod.example` (S5), `deploy/vocky.conf` (S6), `deploy/deploy.sh` +
`rollback.sh` (S7), the GitHub Actions chain (S8) — plus a publishable CLI distribution (S9).

## Two things that are NOT defects — do not report them as findings

1. **Nothing in P6 ever ran against real infrastructure.** No Docker daemon and no Postgres in the sandbox, so
   `deploy/*.sh`, `compose.prod.yml`, `deploy/vocky.conf` and the CI workflow have never executed, and
   `uv run pytest` leaves 108 DB-backed tests erroring on `psycopg.OperationalError` (79 pass). Every slice
   recorded this and pointed behavioral proof at the bring-up / CI. That is now **P12's** job. Judge the artifacts
   on static correctness and internal consistency (`bash -n`, `docker compose config -q` where possible,
   cross-file agreement on service names, ports, volumes, env vars, upstreams, the `/home/opc/vocky` clone path).
2. **`P6.S9` did not publish to PyPI, and that is now correct.** Its status was `needs_operator`; the operator
   withdrew the gate and **moved the publish to P11**. See the SCOPE CHANGE block at the top of
   `slices/P6.S9/result.md`. S9's deliverable is the packaging work only (lean CLI / `server` extra split, PyPI
   metadata, the ~680 MB → 79 KB sdist fix). Do not flag the unpublished package.

## Do check these specifically

- **The `/admin` story is consistent end to end.** S1 deleted `src/vocky/admin_ui.py` + `admin_assets/`; S6 404s
  `/admin/` at the edge. Confirm the nine `/admin/api/*` routes and `VOCKY_ADMIN_AUTH_TOKEN` are still coherent
  (the token remains a required box secret in `.env.prod.example` guarding a surface unreachable from outside —
  that tension is real but is **routed to P12**, so note it, don't fail on it).
- **Known doc staleness that this review is expected to fix.** `docs/current/product.md` and
  `docs/current/architecture.md` still describe the packaged Admin Web UI as shipping "until P6 removes it" — S1
  already removed it. Also sweep: the root `Makefile` still exports the retired `VOCKY_API_AUTH_TOKEN` in
  `EXPORTED_ENV_VARS`, and `README.md` still carries both that reference and a "PyPI publishing is P6; until
  then…" caveat that is now P11's. Report the `Makefile`/`README` items as findings (they are source, not docs —
  you do not fix them here); fix the doc staleness via consolidation.
- **`docs/current/operations.md` has a "Deferred to P6" list** naming five items. Four are now built (web
  Dockerfile/compose/nginx, CSP+HSTS, Admin-UI removal) and the PyPI publish moved to P11. That list must not
  survive consolidation as written.

## Doc consolidation (pass-only)

`phase.md` §"Doc impact" is a long per-slice running list (S1–S9). On a **passing** verdict, consolidate it into
**one new version per affected doc** — `doc-new-version --doc <doc> --summary "..." --source P6.REVIEW`, edit only
the returned `edit_path`, then `rebuild-docs`. Expected docs, from the running list: `operations.md` (the big
one — production topology, deploy/rollback runbook, CI path, GitHub secrets, edge apply path, CLI distribution
model), `security.md` (the CSP string, edge TLS/HSTS/CF-real-IP, the `/admin` internal-only decision, the
`/auth/*` rate-limit gap), `frontend.md`, `architecture.md`, `api.md`, `product.md`, `experience.md`. Verify
against the running list rather than trusting this sentence.

Two forward-looking facts the consolidated docs must state honestly, because they are true and load-bearing:

- **vocky is not deployed.** The deploy kit exists and is unexecuted; production bring-up is P12.
- **The CLI is not on PyPI.** Distribution is P11's decision (PyPI vs a `curl | bash` installer).

Do not write anything into the docs that presumes either has happened.

## Also validate

- `python3 scripts/workflow.py validate` (state integrity, and it checks `docs/current/*` against
  `docs/index.json` after consolidation).
- Re-run each finished slice's validation commands from its `plan.md` / `result.md` — the orchestrator trusted the
  per-slice `done` verdicts and did not re-run them. Report what could not be run in-sandbox rather than skipping
  silently.
- P6 has one recorded **Open Question** (`/auth/*` has no origin rate limit, accepted for launch behind
  Cloudflare, routed to deferred **D5**). D5 is now folded into P12. Confirm it is still accurately recorded; do
  not reopen the decision.

## Return

The verdict, plus — per the skill — the fixed pointer `explain: not written — run /explain for this phase`.
Form the verdict from the whole picture: finish validation and judgment across every slice before branching, so a
`changes_requested` carries **all** numbered findings and proposed `P6.F<n>` fix slices at once, not one per cycle.
Write `result.md`, append cross-slice notes to `phase.md`. **Do not commit and do not transition any status** —
the orchestrator records the verdict with `review-phase`.
