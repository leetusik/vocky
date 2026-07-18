# P6.S7 — Deploy + rollback scripts · plan

> Slice `P6.S7` (implementation, risk **HIGH**). Production deploy automation — hybrid of
> `hi2vi_web/deploy/deploy.sh` (image-tag rollback) + `knowledge/deploy/deploy.sh` (multi-service
> health-gate) plus a migration step. Authored here; behaviorally proven on the box at S10. Read
> `phase.md` (Findings + Constraints).

## Context

Vocky has **no publish-on-write** (the api never commits to the repo), so it takes hi2vi's simple
`git fetch + checkout REF` + **image-tag rollback** model (not knowledge's reconcile/fix-forward). But it
has knowledge's shape: **5 services** to gate + an **Alembic migration**. The migration runs **before the
new app code serves** (correct for additive schema changes; first-deploy-safe), via a **one-off container**
using the `docker compose run --name` idiom (knowledge proved it works on this box's compose v2).

## Edit — `compose.prod.yml` (enable image-tag rollback + kill the stale-worker footgun)

- `api`: add `image: vocky-api:latest` (keep `build: .`).
- `web`: add `image: vocky-web:latest` (keep its `build:`).
- `worker`: **replace `build: .` with `image: vocky-api:latest`** (no build) — reuses the api image with its
  `vocky-worker` command, so the worker always runs the same freshly-built image as the api (stale-worker
  footgun closed) and `deploy.sh` has two predictable image names to tag/roll back.
- Short comment on each `image:` explaining the rollback + worker-reuse rationale. Re-verify
  `docker compose -f compose.prod.yml config -q` passes.

## Create — `deploy/deploy.sh` (`set -euo pipefail`, `export COMPOSE_BAKE=false`)

Knobs (env-overridable): `APP_DIR` (script's `..`), `COMPOSE_FILE=compose.prod.yml`, `ENV_FILE=.env`
(compose auto-reads `./.env` for `${...}`; the box copies `.env.prod.example` → `.env`), `REF=${1:-origin/main}`,
`IMAGES=(vocky-api vocky-web)`, `HEALTH_TRIES=24`, `HEALTH_INTERVAL=5`. Helpers: `log`/`die`,
`dc() { docker compose -f "$COMPOSE_FILE" "$@"; }`, `wait_healthy <svc> <name>` (poll
`.State.Health.Status`; from knowledge), `wait_running <svc> <name>` (worker has no healthcheck: poll
`.State.Status`; pass when `running` AND `.State.Restarting=false` on **2 consecutive** polls; fail on
`exited`/`dead`/timeout — catches a crash-loop), `capture_artifacts` (→ `$REMOTE_ARTIFACT_DIR` if set, else inline).

**Lifecycle:**
1. Preflight: `git`/`docker`/`docker compose`; `$COMPOSE_FILE`, `.git`, `$ENV_FILE` exist.
2. Checkout: `git fetch --prune`; `git checkout "$REF"` (dirty tracked tree fails under `set -e`).
3. Tag rollback point: for each `img`, if `img:latest` exists → `docker tag img:latest img:previous`, set `have_previous=1`; else log first-deploy.
4. Datastores: `dc up -d postgres redis`; `wait_healthy postgres vocky-postgres`; `wait_healthy redis vocky-redis`.
5. Build: `dc build` (builds `vocky-api:latest` + `vocky-web:latest`).
6. Migrate (before serving): `dc run --rm --no-deps --name "vocky-migrate-$$" vocky-api uv run --no-sync alembic upgrade head`. Fallback if `compose run` is refused: `docker run --rm --network changple_shared_network --env-file .env vocky-api:latest …`.
7. App up: `dc up -d` (recreates api/worker/web against the migrated schema).
8. Gate: `wait_healthy api vocky-api`; `wait_healthy web vocky-web`; `wait_running worker vocky-worker`.
9. On failure: `capture_artifacts`; if `have_previous` → rollback (for each `img`: `docker tag img:previous img:latest`; `dc up -d --no-build`; re-gate; `die` distinguishing rolled-back-healthy vs rollback-also-unhealthy). First deploy → leave running, `die` non-zero. **Never `down`/`down -v`** (preserve `postgres-data` + `attachments-data`).

## Create — `deploy/rollback.sh`

Mirrors hi2vi's `rollback.sh` for **two** images + the 5-service gate: preflight (docker, compose, env, and
both `vocky-*:previous` exist); for each `img` `docker tag img:previous img:latest`; `dc up -d --no-build`;
`wait_healthy api/web` + `wait_running worker`; `die` on failure. **Does not re-migrate** (additive-migration
assumption; deeper revert = a git-ref redeploy). Never `down`.

## Hand-off notes (append to `phase.md`)

- **S8**: CI remote script wraps `deploy.sh` — refuse dirty, fetch, ancestor-verify `TARGET_SHA`, set
  `REMOTE_ARTIFACT_DIR`, call `deploy.sh` (model `hi2vi_web/deploy/oracle-production-deploy-remote.sh`).
- **S10**: on the box, run `deploy/deploy.sh` from the clone after `.env` exists. First deploy hits the
  no-`:previous` branch (expected); the one-off migrate creates the schema.

## Verification

- `bash -n deploy/deploy.sh` + `bash -n deploy/rollback.sh` pass; `shellcheck` if available (fix real
  findings). `chmod +x` both.
- `docker compose -f compose.prod.yml config -q` (dummy `POSTGRES_PASSWORD=x SESSION_SECRET=x
  VOCKY_ADMIN_AUTH_TOKEN=x`) passes; rendered config shows `image: vocky-api:latest` / `vocky-web:latest`
  and the **worker has `image: vocky-api:latest`, no `build:`**.
- Static review of the lifecycle vs both reference scripts. **The scripts don't run in the sandbox** (no
  daemon/box) — behavioral proof is S10; note this in `result.md`.
- `python3 scripts/workflow.py validate` passes (repo root — cwd may persist).

## Docs

Append a **Doc impact** note to `phase.md`: `deploy/deploy.sh` + `rollback.sh` added; `compose.prod.yml`
gained `image:` tags + worker reuses the api image. REVIEW → `docs/current/operations.md` (deploy/rollback runbook).

## Executor notes (high tier)

Mirror the reference scripts' structure + comments. Get the ordering right: build → migrate (one-off) → up →
gate. Keep the two-image tag/rollback loop and the never-`down` rule exact. If `docker compose config`
rejects the worker image-reuse, escalate rather than reverting to `build: .`. Write `result.md`; append the
hand-off + Doc-impact notes to `phase.md`. Do not commit; do not transition status.
