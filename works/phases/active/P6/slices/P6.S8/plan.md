# P6.S8 — CI production-deploy chain · plan

> Slice `P6.S8` (implementation, risk **medium**). Adds the GitHub Actions deploy chain that drives the S7
> `deploy.sh` on the box. Faithful port of hi2vi's proven three-file chain (vocky has **no `.github/`** yet
> — net-new). Read `phase.md` (Findings + Constraints).

## Context

The operator wants one-click redeploys matching the sibling repos. hi2vi's chain is the model: a manual
`workflow_dispatch` workflow → a runner transport script (SSH to the box) → an on-box gate script (refuse
dirty tree, fetch, ancestor-verify `TARGET_SHA`) that hands off to the repo's own `deploy.sh` (checkout +
build + gate + rollback). Vocky reuses S7's `deploy.sh` **unchanged**.

## Create (port `~/projects/personal/hi2vi_web/deploy/*` + its workflow, with the vocky deltas)

- **`.github/workflows/deploy-production.yml`** — from `hi2vi_web/.github/workflows/deploy-production.yml`:
  `on: workflow_dispatch`; `permissions: contents: read`; **preflight** job (guard `main`, output
  `target_sha=GITHUB_SHA`); **deploy** job (`needs: preflight`, `environment: { name: production, url:
  https://vocky.hi2vi.com }`, `concurrency: { group: vocky-deploy, cancel-in-progress: false }`,
  `timeout-minutes: 90`): checkout target SHA → `bash -n` the two helpers → run
  `deploy/github-actions-production-deploy.sh` (env `TARGET_SHA`, `ORACLE_SSH_PRIVATE_KEY`,
  `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE`, `ARTIFACT_DIR`) → **external smoke** → upload artifacts
  (`if: always()`).
  - **Smoke (vocky delta):** check **both** (retry ~5×6s, expect 200): `https://vocky.hi2vi.com/healthz`
    (api via edge) and `https://vocky.hi2vi.com/` (web via edge). Fail if either never returns 200.
- **`deploy/github-actions-production-deploy.sh`** (`+x`) — hi2vi's, verbatim except: `ORACLE_REPO_PATH`
  default **`/home/opc/vocky`**; temp names `/tmp/vocky-gha-deploy-*` / `/tmp/vocky-gha-artifacts-*`; log
  prefix `[vocky-deploy]`. Keep the SSH prep, `TARGET_SHA` 40-hex assert, artifact scp-back, cleanup as-is.
  Same box: `ORACLE_SSH_HOST` default `140.245.64.173`, user `opc`.
- **`deploy/oracle-production-deploy-remote.sh`** (`+x`) — hi2vi's, verbatim except: `REPO_PATH` default
  **`/home/opc/vocky`**; `PROJECT_NAME` → **`vocky`**; `COMPOSE_ENV_FILE` → **`.env`** (vocky's compose
  auto-reads `./.env`). Keep the dirty-tree refusal, `git fetch --prune origin main`, the `TARGET_SHA`
  ancestor-verify, and the handoff `deploy/deploy.sh "${TARGET_SHA}"` as-is. `collect_status` uses
  `docker compose -f compose.prod.yml ps` (matches deploy.sh's `dc()` — no `-p`, `.env` auto-read; the
  script `cd`s to `REPO_PATH` first).

## Consistency note (record in `phase.md` for S10)

vocky's `deploy.sh` `dc()` uses `docker compose -f compose.prod.yml` with **no `-p` pin**, so the project
name derives from the clone **directory basename**. **S10 must clone to `/home/opc/vocky`** (→ project
`vocky`) so named volumes (`vocky_postgres-data`, `vocky_attachments-data`) stay stable across redeploys.
Container names are pinned + image tags explicit, so only the clone dir name matters.

## Hand-off notes (append to `phase.md`)

- **S10 (operator co-work):** add three GH repo secrets to `leetusik/vocky` — `ORACLE_SSH_PRIVATE_KEY`,
  `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE` (same box as hi2vi/knowledge — reuse the existing key
  material). Clone the box to `/home/opc/vocky`. First deploy: manual `deploy/deploy.sh` OR dispatch this
  workflow once secrets + clone + `.env` + DNS exist.

## Verification

- `bash -n` both `deploy/*.sh` new scripts; `shellcheck` if available; `chmod +x` both.
- Workflow YAML parses: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-production.yml'))"`;
  `actionlint` if available. Confirm the `bash -n` step references the existing S7 `deploy/deploy.sh`.
- **The workflow only runs on operator dispatch** (needs GH secrets + live box) — no CI run in this slice;
  note in `result.md`.
- `python3 scripts/workflow.py validate` passes (repo root — cwd may persist).

## Docs

Append a **Doc impact** note to `phase.md`: CI deploy chain added (manual, main-only, ancestor-verified,
drives S7 `deploy.sh`, external smoke of `/healthz` + `/`); requires the `ORACLE_SSH_*` GH secrets (S10).
REVIEW → `docs/current/operations.md` (CI deploy path).

## Executor notes

Port hi2vi's three files faithfully — change only the documented vocky deltas. Do **not** modify S7's
`deploy.sh`. Keep the SSH key handling and the ancestor-verify gate exactly. If a delta forces a real change
to `deploy.sh`'s contract, escalate rather than editing S7's script. Write `result.md`; append the
consistency + hand-off + Doc-impact notes to `phase.md`. Do not commit; do not transition status.
