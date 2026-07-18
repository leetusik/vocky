#!/usr/bin/env bash
#
# deploy.sh — build + release vocky as a Docker Compose stack on the shared OCI box
# for https://vocky.hi2vi.com (P6.S7).
#
# Model: a HYBRID of the two sibling deploy scripts.
#   * from hi2vi_web/deploy/deploy.sh — the simple `git fetch + checkout REF` update
#     and the IMAGE-TAG ROLLBACK (tag :latest -> :previous before a rebuild, flip back
#     on failure). vocky has NO publish-on-write (the api never commits to the repo),
#     so — unlike the sibling `knowledge` — the box clone can be checked out to an exact
#     ref and a bad build can be reverted by an image-tag flip.
#   * from knowledge/deploy/deploy.sh — the MULTI-SERVICE health-gate and the one-off
#     `docker compose run --name` container (knowledge proved compose v2 accepts it on
#     a `container_name:`-pinned service on this box).
#   * vocky-specific — an ALEMBIC MIGRATION run in a one-off container BEFORE the new
#     app code serves. Additive/idempotent schema changes are safe to apply ahead of
#     the new code, and it is first-deploy-safe (the one-off run creates the schema).
#     The ordering (build -> migrate -> up -> gate) is load-bearing: do not reorder.
#
# vocky runs FIVE services from compose.prod.yml over the external
# `changple_shared_network`: vocky-postgres, vocky-redis (datastores), vocky-api
# (FastAPI + in-app /mcp), vocky-worker (the queue consumer, REUSES vocky-api:latest —
# no build of its own), and vocky-web (the Next.js standalone app). The standalone
# `edge` compose project proxies to vocky-api:8000 / vocky-web:3000 by container name.
#
# Lifecycle:
#   1. preflight (git/docker/compose v2; compose file, .git, .env present)
#   2. git fetch --prune + checkout REF (a dirty TRACKED tree fails loudly under set -e)
#   3. tag the currently-live images  vocky-api:latest -> :previous and
#      vocky-web:latest -> :previous  (the rollback points)
#   4. bring up the datastores        docker compose up -d postgres redis  + gate healthy
#   5. build the new images           COMPOSE_BAKE=false docker compose build
#                                      (builds vocky-api:latest + vocky-web:latest)
#   6. MIGRATE BEFORE SERVING          one-off container: alembic upgrade head
#   7. recreate the app               docker compose up -d  (api/worker/web on the new
#                                      images, against the already-migrated schema)
#   8. health-gate                    vocky-api healthy, vocky-web healthy,
#                                      vocky-worker running (no healthcheck by design)
#   9. on any app failure: capture diagnostics; if a :previous exists, flip both images
#      back and re-gate; first deploy (no :previous) => leave running, exit non-zero.
#      NEVER `down` / `down -v` — postgres-data, redis-data, and attachments-data must
#      survive every deploy.
#
# The build-time NEXT_PUBLIC_APP_URL trap is handled UPSTREAM: compose.prod.yml passes
# it as the web build.arg (literal https://vocky.hi2vi.com) and web/Dockerfile asserts
# it non-empty, so the image build fails loudly if it is ever missing — deploy.sh does
# not source or assert it.
#
# Run on the box from /home/opc/vocky (does NOT need root if `opc` is in the docker
# group, as on the changple box):
#   deploy/deploy.sh [git-ref]        # default ref: origin/main
#
# Authored + statically checked off-box (P6.S7): `bash -n`, logic review vs both
# reference scripts. It has ZERO production impact until it actually runs on the box at
# S10 (first deploy) and for every subsequent release — that is the behavioral proof
# (build both images; migrate creates/advances the schema; all five services gate).

set -euo pipefail

# --- config knobs (override via env) ----------------------------------------
# Repo root = parent of this script's dir, so compose.prod.yml + .env resolve
# regardless of the caller's cwd.
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"                    # compose auto-reads ./.env for ${...} (box copies .env.prod.example -> .env)
REF="${1:-origin/main}"                          # git ref to release
HEALTH_TRIES="${HEALTH_TRIES:-24}"               # poll count per service (24*5 = up to 120s each)
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"          # seconds between polls
NETWORK="${NETWORK:-changple_shared_network}"    # external shared net (migrate fallback only)
MIGRATE_CONTAINER="vocky-migrate-$$"             # unique ephemeral name (never clashes with vocky-api)

# The two rollback-able images (the worker rides vocky-api:latest, so two names cover
# all three app services). Datastore images (postgres:17 / redis:7-alpine) are never
# rebuilt or rolled back — their DATA is what must survive, not their tags.
IMAGES=(vocky-api vocky-web)

# COMPOSE_BAKE=false avoids the `docker compose build` bake-path panic seen on this
# host's Compose version (P8/hi2vi: compose/build_bake.go slice-bounds — a CLI bug).
# Exported so the docker subprocess inherits it.
export COMPOSE_BAKE=false

log() { printf '[deploy] %s\n' "$*"; }
die() { printf '[deploy] ERROR: %s\n' "$*" >&2; exit 1; }

# `docker compose -f <file>` wrapper (cwd is $APP_DIR, so .env + build context resolve).
dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

# --- health-gate one service on its own healthcheck --------------------------
# Polls `docker inspect --format '{{.State.Health.Status}}'` for the given compose
# service until it reports `healthy`. Returns 0 on healthy, 1 on timeout / an
# `unhealthy` verdict / a service with no healthcheck. $1 = compose service key,
# $2 = friendly container name (for logs). Used for postgres/redis/api/web.
wait_healthy() {
    local svc="$1" name="$2" cid status i
    cid="$(dc ps -q "$svc" 2>/dev/null || true)"
    [[ -n "$cid" ]] || { log "no running $name container to health-check"; return 1; }
    for ((i = 1; i <= HEALTH_TRIES; i++)); do
        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || true)"
        case "$status" in
            healthy)
                log "$name healthy on poll $i"
                return 0
                ;;
            unhealthy)
                log "$name reported UNHEALTHY on poll $i (healthcheck retries exhausted)"
                return 1
                ;;
            none)
                log "$name has no healthcheck — cannot gate (check compose/Dockerfile)"
                return 1
                ;;
            *)
                log "$name poll $i/$HEALTH_TRIES: status=${status:-<none>} — waiting ${HEALTH_INTERVAL}s"
                ;;
        esac
        sleep "$HEALTH_INTERVAL"
    done
    log "$name health-gate TIMED OUT after $((HEALTH_TRIES * HEALTH_INTERVAL))s"
    return 1
}

# --- state-gate the worker (it has NO healthcheck, by design) ----------------
# The worker has no HTTP endpoint, so it can never report a Docker health status. We
# instead gate on `.State.Status`: it must be `running` AND not `.State.Restarting`
# on TWO CONSECUTIVE polls (a single `running` glimpse can precede a crash-loop
# restart — two clean polls in a row rule that out). Fails fast on `exited`/`dead`
# and on timeout. $1 = compose service key, $2 = friendly container name.
wait_running() {
    local svc="$1" name="$2" cid status restarting i stable=0
    cid="$(dc ps -q "$svc" 2>/dev/null || true)"
    [[ -n "$cid" ]] || { log "no running $name container to state-check"; return 1; }
    for ((i = 1; i <= HEALTH_TRIES; i++)); do
        status="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || true)"
        restarting="$(docker inspect --format '{{.State.Restarting}}' "$cid" 2>/dev/null || true)"
        case "$status" in
            running)
                if [[ "$restarting" == "false" ]]; then
                    stable=$((stable + 1))
                    if (( stable >= 2 )); then
                        log "$name running (stable on $stable consecutive polls)"
                        return 0
                    fi
                    log "$name poll $i/$HEALTH_TRIES: running — need one more clean poll ($stable/2)"
                else
                    stable=0
                    log "$name poll $i/$HEALTH_TRIES: running but RESTARTING — waiting ${HEALTH_INTERVAL}s"
                fi
                ;;
            exited|dead)
                log "$name reported $status on poll $i — worker crashed (see logs)"
                return 1
                ;;
            *)
                stable=0
                log "$name poll $i/$HEALTH_TRIES: status=${status:-<none>} — waiting ${HEALTH_INTERVAL}s"
                ;;
        esac
        sleep "$HEALTH_INTERVAL"
    done
    log "$name state-gate TIMED OUT after $((HEALTH_TRIES * HEALTH_INTERVAL))s"
    return 1
}

# --- gate the three app services (api healthy, web healthy, worker running) --
# Runs all three so the logs show every failing service in one pass (|| , not &&).
gate_app() {
    local ok=1
    wait_healthy api vocky-api    || ok=0
    wait_healthy web vocky-web    || ok=0
    wait_running worker vocky-worker || ok=0
    (( ok ))
}

# --- diagnostics on failure --------------------------------------------------
# Dumps compose ps + per-service logs into $REMOTE_ARTIFACT_DIR when set (the remote
# gate, S8, scps this dir back), else prints compose ps inline. Never fails the deploy.
capture_artifacts() {
    log "capturing diagnostics (a gate failed)"
    if [[ -n "${REMOTE_ARTIFACT_DIR:-}" ]]; then
        mkdir -p "$REMOTE_ARTIFACT_DIR" 2>/dev/null || true
        dc ps                                 > "$REMOTE_ARTIFACT_DIR/deploy-compose-ps.txt"     2>&1 || true
        dc logs --no-color --tail 300 api     > "$REMOTE_ARTIFACT_DIR/deploy-api-logs.txt"       2>&1 || true
        dc logs --no-color --tail 300 web     > "$REMOTE_ARTIFACT_DIR/deploy-web-logs.txt"       2>&1 || true
        dc logs --no-color --tail 300 worker  > "$REMOTE_ARTIFACT_DIR/deploy-worker-logs.txt"    2>&1 || true
        dc logs --no-color --tail 100 postgres > "$REMOTE_ARTIFACT_DIR/deploy-postgres-logs.txt" 2>&1 || true
        dc logs --no-color --tail 100 redis   > "$REMOTE_ARTIFACT_DIR/deploy-redis-logs.txt"     2>&1 || true
        log "diagnostics written to $REMOTE_ARTIFACT_DIR"
    else
        log "REMOTE_ARTIFACT_DIR unset — printing compose ps inline"
        dc ps || true
    fi
}

# --- image-tag rollback ------------------------------------------------------
# Flips both app images back to their :previous tag, recreates the app (NO rebuild),
# and re-gates. Called on a migration or health-gate failure when a :previous exists.
# NEVER `down` — the datastores + attachments volume stay up throughout. $1 = a human
# reason for the die messages.
rollback_or_die() {
    local reason="$1" img
    capture_artifacts
    if (( have_previous )); then
        log "rolling back: flip both images to :previous and recreate (no rebuild)"
        for img in "${IMAGES[@]}"; do
            docker tag "$img:previous" "$img:latest"
        done
        dc up -d --no-build
        if gate_app; then
            die "$reason — ROLLED BACK to the :previous images (now healthy). Inspect 'docker compose -f $COMPOSE_FILE logs api web worker'."
        fi
        die "$reason — AND the rollback to the :previous images is ALSO unhealthy — manual intervention required. Inspect 'docker compose -f $COMPOSE_FILE logs api web worker' (datastores were left up; nothing was 'down'ed)."
    fi
    die "$reason — first deploy, no :previous images to roll back to. Left running for inspection; check 'docker compose -f $COMPOSE_FILE logs api web worker' and $ENV_FILE. NOTHING was 'down'ed."
}

# --- run the alembic migration in a one-off container ------------------------
# Runs `alembic upgrade head` BEFORE the new app serves. Primary path: `docker compose
# run` a one-off container off the api service — it inherits the api service's full
# `environment:` block (the interpolated DATABASE_URL) and the shared network, so it
# reaches vocky-postgres:5432. `--no-deps` skips re-starting postgres/redis (already up
# + healthy from step 4); `-T` disables the TTY (non-interactive SSH/CI); `--name`
# sidesteps the api service's pinned `container_name: vocky-api`. Returns non-zero if
# the migration fails (caller rolls back). If a given Compose refuses `run` on a
# container_name-pinned service, set MIGRATE_VIA_DOCKER_RUN=1 to use the plain
# `docker run` fallback (knowledge proved `compose run --name` works on this box, so
# the fallback is a safety net, not the default).
run_migration() {
    if [[ -n "${MIGRATE_VIA_DOCKER_RUN:-}" ]]; then
        log "migrating via the docker-run fallback (MIGRATE_VIA_DOCKER_RUN set)"
        local pw
        pw="$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)"
        [[ -n "$pw" ]] || { log "could not read POSTGRES_PASSWORD from $ENV_FILE for the fallback DATABASE_URL"; return 1; }
        docker run --rm --network "$NETWORK" \
            --env-file "$ENV_FILE" \
            -e "DATABASE_URL=postgresql+psycopg://vocky:${pw}@vocky-postgres:5432/vocky" \
            "vocky-api:latest" \
            uv run --no-sync alembic upgrade head
        return
    fi
    dc run --rm -T --no-deps --name "$MIGRATE_CONTAINER" api \
        uv run --no-sync alembic upgrade head
}

# --- preflight ---------------------------------------------------------------
command -v git >/dev/null || die "git not found"
command -v docker >/dev/null || die "docker not found"
docker compose version >/dev/null 2>&1 || die "'docker compose' (v2 plugin) not found"

cd "$APP_DIR"
[[ -f "$COMPOSE_FILE" ]] || die "compose file not found: $APP_DIR/$COMPOSE_FILE"
[[ -d .git ]] || die "not a git checkout: $APP_DIR (clone the repo here first — see deploy/README / phase.md S10)"
[[ -f "$ENV_FILE" ]] || die "env file not found: $APP_DIR/$ENV_FILE (create it from .env.prod.example — see .env.prod.example)"

log "repo: $APP_DIR   compose: $COMPOSE_FILE   ref: $REF"

# --- 1. update the checkout --------------------------------------------------
# .env is gitignored (survives the checkout); build artifacts are gitignored too. A
# dirty TRACKED tree makes `git checkout` fail loudly (set -e) — the deploy box carries
# no local tracked edits.
log "fetching + checking out $REF"
git fetch --prune
git checkout "$REF"

# --- 2. tag the currently-live images as the rollback points -----------------
# Retag each app image live BEFORE this deploy as :previous. First-ever deploy has no
# :latest yet => no rollback target for that image; have_previous stays 0 only if
# NEITHER exists (they are always built together, so they move in lockstep).
have_previous=0
for img in "${IMAGES[@]}"; do
    if docker image inspect "$img:latest" >/dev/null 2>&1; then
        log "tagging current $img:latest -> $img:previous (rollback point)"
        docker tag "$img:latest" "$img:previous"
        have_previous=1
    else
        log "no existing $img:latest — first deploy for this image, no rollback point"
    fi
done

# --- 3. bring up the datastores + gate them healthy --------------------------
# Postgres + redis come up FIRST so the migration (step 5) has a live schema target and
# the app (step 6) has its dependencies. `up -d postgres redis` never touches
# api/worker/web (any prior-deploy app containers keep running old code until step 6).
log "bringing up datastores (postgres + redis)"
dc up -d postgres redis
wait_healthy postgres vocky-postgres || die "postgres did not become healthy — aborting before any build/migrate. NOTHING was 'down'ed."
wait_healthy redis vocky-redis       || die "redis did not become healthy — aborting before any build/migrate. NOTHING was 'down'ed."

# --- 4. build the new app images ---------------------------------------------
# Builds vocky-api:latest (api) + vocky-web:latest (web). The worker has no build of
# its own — it reuses vocky-api:latest, so this one build freshens api + worker code.
log "building app images (COMPOSE_BAKE=false docker compose build)"
dc build

# --- 5. MIGRATE BEFORE SERVING (one-off container) ---------------------------
# Additive/idempotent schema, applied ahead of the new code (and first-deploy-safe: the
# one-off run creates the schema). The old app (if any) is still on the old code+schema
# at this point; alembic runs each revision in its own transaction, so a failure leaves
# the schema at the last good revision — the old code stays compatible and we roll back.
log "running alembic migration in a one-off container (before serving new code)"
if ! run_migration; then
    rollback_or_die "database migration (alembic upgrade head) FAILED before serving new code (also try MIGRATE_VIA_DOCKER_RUN=1 if 'docker compose run' was refused on the container_name-pinned api service)"
fi

# --- 6. recreate the app services against the migrated schema ----------------
# Recreates api/worker/web on the freshly-built images (worker rides vocky-api:latest).
# postgres/redis already up (unchanged). No `--build` here — the images are already
# built (step 4) so a rollback's `up -d --no-build` and this share one image set.
log "recreating app services (docker compose up -d)"
dc up -d

# --- 7. health-gate the app (api + web healthy, worker running) --------------
if gate_app; then
    log "all app services up — vocky-api + vocky-web healthy, vocky-worker running"
else
    rollback_or_die "health-gate FAILED for vocky-api and/or vocky-web and/or vocky-worker"
fi

log "DONE — ref $REF live (edge proxies to vocky-api:8000 / vocky-web:3000; worker consuming the queue)."
