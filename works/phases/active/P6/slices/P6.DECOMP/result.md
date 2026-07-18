# P6.DECOMP — result

Decomposed P6 (production-deploy-only, per D-P8-1 superseding D-P4-3) into ten middle slices as bare
folders and seeded `phase.md`. No code implemented, no `plan.md`/`result.md` pre-filled in the new
folders, no `doc-new-version` run.

## Slices created (bare folders, `slice.json` only)

| Slice | Order | Kind | Risk | depends_on |
|---|---|---|---|---|
| P6.S1 Admin-UI removal | 1 | implementation | medium | — |
| P6.S2 Landing/site metadata & production origin | 2 | implementation | medium | — |
| P6.S3 CSP + HSTS security headers | 3 | implementation | medium | P6.S2 |
| P6.S4 Web production Dockerfile | 4 | implementation | medium | — |
| P6.S5 Production compose + env template | 5 | implementation | high | P6.S4 |
| P6.S6 Edge nginx vhost (vocky.conf) | 6 | implementation | high | P6.S5 |
| P6.S7 Deploy + rollback scripts | 7 | implementation | high | P6.S5 |
| P6.S8 CI production-deploy chain | 8 | implementation | medium | P6.S7 |
| P6.S9 PyPI packaging + publish | 9 | implementation | medium | — |
| P6.S10 Production bring-up | 10 | co-work | high | P6.S6 |

P6.REVIEW already existed at order 9999. Each new folder contains only `slice.json`.

Commands run: the exact ten `new-slice` invocations from the plan's Step 1 — all reported `created
slice ...`.

## Validation

- `python3 scripts/workflow.py validate` → **PASSED** (`Workflow validation passed.`)
- Confirmed each `works/phases/active/P6/slices/P6.S{1..10}/` holds only `slice.json` (no `plan.md`/`result.md`).

## phase.md seeded

Filled Context (reframing note + confirmed operator scope), Decomposition (table + ordering rationale),
Findings & Notes (the deploy pattern block every downstream slice depends on), and Constraints (nginx
house rules + design boundary). Kept the existing intent link and Objective verbatim.

## Repo-state check vs plan assumptions

Sanity-checked the plan's referenced targets against the real repo before creating slices. All present:
- S1: `src/vocky/admin_ui.py`, `src/vocky/admin_assets/`, `scripts/check_admin_ui_package.py` — exist.
- S3: `web/next.config.ts` — exists.
- S5: stale `VOCKY_API_AUTH_TOKEN` in `docker-compose.yml` (line 45) — present, confirming the cleanup.
- Sibling repos present: `~/projects/personal/knowledge/{compose.prod.yml,web/Dockerfile}` and its
  `deploy/`; `~/projects/personal/hi2vi_web/deploy/` and `.github/workflows/deploy-production.yml`.

## Deviations

- **One reference-list correction (no scope change):** the plan's Findings listed
  `knowledge/deploy/{...,rollback.sh,...}`, but `knowledge/deploy/` has **no** `rollback.sh` — knowledge
  folds rollback into its `deploy.sh`, and the standalone `rollback.sh` reference lives in
  `hi2vi_web/deploy/rollback.sh`. I recorded the corrected reference list in `phase.md` Findings so S7
  points at a real file. Everything else matched the plan; slices created exactly as specified.
