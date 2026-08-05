# P6.S7 — Deploy + rollback scripts · result

Authored the production deploy automation for `vocky.hi2vi.com`: an image-tag-rollback
`deploy.sh` with a migrate-before-serve step, a matching manual `rollback.sh`, and the
`compose.prod.yml` edits that make image-tag rollback possible and close the
stale-worker footgun. **The scripts do not run in this sandbox** (no docker daemon, no
box) — behavioral proof is S10 / CI. Static verification below.

## What changed

- **`compose.prod.yml`** (edited)
  - `api`: added `image: vocky-api:latest` (kept `build: .`) — gives deploy.sh a
    predictable tag to move `:latest -> :previous` and flip back.
  - `web`: added `image: vocky-web:latest` (kept its `build:`).
  - `worker`: **replaced `build: .` with `image: vocky-api:latest`** (no build of its
    own). The worker now runs the exact image `docker compose build` builds for the api,
    with its `command: [uv run --no-sync vocky-worker]` override — so it can never lag
    behind a fresh api build. Rewrote the worker's header comment to record that the
    stale-worker footgun is now CLOSED (was: "MUST rebuild the worker on every deploy").
- **`deploy/deploy.sh`** (new, `chmod +x`) — hybrid of the two sibling scripts:
  hi2vi's `git fetch + checkout REF` + two-image tag rollback, knowledge's
  multi-service gate + one-off `docker compose run --name` container, plus vocky's
  alembic migration. Lifecycle, in order (load-bearing — not reordered):
  preflight -> `git fetch --prune` + `checkout REF` -> tag both `:latest -> :previous`
  (`have_previous`) -> `up -d postgres redis` + gate healthy -> `docker compose build`
  (builds vocky-api + vocky-web) -> **migrate in a one-off container**
  (`alembic upgrade head`) -> `up -d` (recreate app on the migrated schema) -> gate
  api/web healthy + worker running -> on migrate OR gate failure: `capture_artifacts`,
  then if `have_previous` flip both images back + `up -d --no-build` + re-gate (die
  distinguishing rolled-back-healthy vs rollback-also-unhealthy); first deploy leaves it
  running and dies non-zero. **Never `down`/`down -v`** — postgres-data / redis-data /
  attachments-data survive every path.
- **`deploy/rollback.sh`** (new, `chmod +x`) — manual counterpart: preflight (docker,
  compose, `.env`, and BOTH `vocky-*:previous` exist), retag both `:previous -> :latest`,
  `up -d --no-build`, re-gate (api/web healthy, worker running), die on failure. Does
  **not** re-migrate (additive-migration assumption; a deeper revert is a git-ref
  redeploy via `deploy.sh <sha>`). Never `down`.

## Key design points (vs the plan)

- **Worker gate = `wait_running`** (two consecutive `running` + `.State.Restarting=false`
  polls; fail on `exited`/`dead`/timeout) because the worker has no healthcheck by
  design. api/web use `wait_healthy` (Docker health status). postgres+redis are gated
  healthy in the datastore step. That is the "gate all 5" the plan calls for, split
  across the two up-steps.
- **Migrate primary path** = `docker compose run --rm -T --no-deps --name
  vocky-migrate-$$ api uv run --no-sync alembic upgrade head`. The one-off container
  inherits the api service's full `environment:` block — so it gets the interpolated
  `DATABASE_URL` (config.py reads `DATABASE_URL` directly; it is a required field) and
  the shared network to reach `vocky-postgres:5432`. `--no-deps` because postgres+redis
  are already up+healthy; `--name` sidesteps the pinned `container_name: vocky-api`
  (knowledge proved compose v2 accepts this on this box). A `MIGRATE_VIA_DOCKER_RUN=1`
  fallback builds `DATABASE_URL` from `POSTGRES_PASSWORD` in `.env` and uses plain
  `docker run --network changple_shared_network` if a Compose ever refuses `run` on the
  container_name-pinned service.
- **Migrate-failure path reuses the rollback logic** (`rollback_or_die`): on a
  subsequent deploy the old app is still on the old image+schema (we haven't `up`ed the
  new code yet), alembic runs each revision transactionally so the schema is left at the
  last-good revision, and flipping both images back + `up -d --no-build` re-serves the
  known-good release. First deploy dies non-zero with the app left for inspection.

## Deviation from `plan.md`

- **Plan step 6 wrote the `docker compose run` service arg as `vocky-api`** (the
  container_name). `docker compose run` takes the **service key**, which is `api` — the
  container_name `vocky-api` is not a valid `run` target and would fail with "no such
  service: vocky-api". I used **`api`** (matching the knowledge reference, which uses its
  `api` service key). The `:latest` **image** name `vocky-api:latest` is still correct in
  the `docker run` fallback (that takes an image, not a service). No scope change; the
  migrate-before-serve ordering is unchanged.
- The `worker` header comment in `compose.prod.yml` was rewritten (it still said "MUST
  rebuild the worker on every deploy … an un-rebuilt worker runs stale code") to reflect
  that the footgun is now closed by image-reuse. This is a doc-in-file correction, not a
  behavior change.

## Verification (all run from the repo root)

| Command | Result |
|---|---|
| `bash -n deploy/deploy.sh` | syntax OK |
| `bash -n deploy/rollback.sh` | syntax OK |
| `chmod +x deploy/deploy.sh deploy/rollback.sh` | both `-rwxr-xr-x` |
| `shellcheck …` | **not installed in sandbox** — skipped (plan says "if available"); did a manual review for common findings (quoting, SC2155 split declare/assign, array quoting, `local` scoping) — clean |
| `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml config -q` | exit 0 |
| rendered config (same env) | `api` -> `build:` + `image: vocky-api:latest`; `web` -> `build:` + `image: vocky-web:latest`; **`worker` -> `image: vocky-api:latest`, its `vocky-worker` command, and NO `build:` key** |
| `python3 scripts/workflow.py validate` | Workflow validation passed |

**Not verifiable in-sandbox (proven at S10 / CI):** the actual `docker compose build` of
both images, the one-off migrate creating/advancing the schema, `docker compose run
--name` being accepted on the pinned api service, and all five services gating. The
docker CLI is present (v2.37.1) but the daemon is not — the compose *parser* (`config`)
runs without it; nothing that needs the daemon was executed.
