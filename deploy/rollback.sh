#!/usr/bin/env bash
#
# rollback.sh — roll vocky back to the previous container images (P6.S7).
#
# Retags BOTH app images vocky-api:previous -> vocky-api:latest and
# vocky-web:previous -> vocky-web:latest, recreates the app containers WITHOUT a
# rebuild, and re-gates them (api + web healthy, worker running). This is the manual
# counterpart to deploy.sh's automatic rollback: use it for a release that PASSED its
# post-deploy gate but misbehaves later. deploy.sh writes both :previous tags at the
# start of every deploy (the images that were live before), so this reverts to exactly
# that release.
#
# The worker rides vocky-api:latest (no image of its own), so flipping the two app
# image tags rolls back all three app services in lockstep. Datastore images
# (postgres:17 / redis:7-alpine) are never rolled back — their DATA persists.
#
# NO RE-MIGRATION. deploy.sh applies only additive/idempotent schema changes ahead of
# the new code, so the previous code stays compatible with the current (already-
# migrated) schema — flipping images back does not require reverting the schema. A
# deeper revert (a schema-incompatible change) is a GIT-REF redeploy, not this script:
#   deploy/deploy.sh <prior-good-sha>     # rebuilds that older ref into :latest
#
# NEVER `down` / `down -v` — postgres-data, redis-data, and attachments-data stay up.
#
#   deploy/rollback.sh
#
# If a :previous image is gone (e.g. pruned, or you must go back more than one
# release), use the git-ref redeploy above instead.
#
# Authored + statically checked off-box (P6.S7); behaviorally rehearsed against the
# live origin at S10.

set -euo pipefail

# --- config knobs (override via env; keep in sync with deploy.sh) ------------
APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env}"
HEALTH_TRIES="${HEALTH_TRIES:-24}"
HEALTH_INTERVAL="${HEALTH_INTERVAL:-5}"

# Both app images (the worker rides vocky-api:latest). Both :previous tags must exist.
IMAGES=(vocky-api vocky-web)

export COMPOSE_BAKE=false

log() { printf '[rollback] %s\n' "$*"; }
die() { printf '[rollback] ERROR: %s\n' "$*" >&2; exit 1; }

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

# --- health-gate one service on its own healthcheck (same contract as deploy) -
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
                log "$name has no healthcheck — cannot gate"
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

# --- state-gate the worker (no healthcheck, by design; same contract as deploy) -
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

# --- preflight ---------------------------------------------------------------
command -v docker >/dev/null || die "docker not found"
docker compose version >/dev/null 2>&1 || die "'docker compose' (v2 plugin) not found"

cd "$APP_DIR"
[[ -f "$COMPOSE_FILE" ]] || die "compose file not found: $APP_DIR/$COMPOSE_FILE"
[[ -f "$ENV_FILE" ]] || die "env file not found: $APP_DIR/$ENV_FILE (compose needs it to recreate the containers)"
for img in "${IMAGES[@]}"; do
    docker image inspect "$img:previous" >/dev/null 2>&1 \
        || die "no $img:previous image to roll back to. Use a git-ref redeploy instead: deploy/deploy.sh <prior-good-sha>"
done

# --- retag both previous -> latest, recreate, re-gate ------------------------
for img in "${IMAGES[@]}"; do
    log "rolling back: retag $img:previous -> $img:latest"
    docker tag "$img:previous" "$img:latest"
done

log "recreating app services from the rolled-back images (no rebuild, no down)"
dc up -d --no-build

gate_ok=1
wait_healthy api vocky-api       || gate_ok=0
wait_healthy web vocky-web       || gate_ok=0
wait_running worker vocky-worker || gate_ok=0

if (( gate_ok )); then
    log "DONE — rolled back to the :previous images; vocky-api + vocky-web healthy, vocky-worker running."
else
    die "rolled back to the :previous images but the app is NOT healthy — manual intervention required (check 'docker compose -f $COMPOSE_FILE logs api web worker'). NOTHING was 'down'ed."
fi
