#!/usr/bin/env bash
#
# status.sh — read-only on-box status snapshot for the vocky.hi2vi.com stack (P12.S5).
#
# The "basic metrics" deliverable for this phase: NOT monitoring infrastructure (no
# collector, no time series, no alerting) — a single, human-run, read-only snapshot an
# operator pastes into a terminal when something looks wrong or before/after a deploy.
# Takes no arguments, changes nothing, and is safe to run at any time (every command
# below is a read: `ps`, `inspect`, `df`, `docker system df`, `logs --tail`).
#
#   deploy/status.sh
#
# Authored + statically checked off-box (P12.S5): `bash -n`. Never executed against the
# live box by this slice.

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.prod.yml}"
SERVICES=(postgres redis api web worker)

section() { printf '\n=== %s ===\n' "$*"; }

cd "$APP_DIR"
dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

section "container states + health ($COMPOSE_FILE)"
dc ps

# Per-container Docker health status where one exists; the worker has none by design
# (compose.prod.yml / deploy.sh gate it on running-state, not health — see there).
section "per-service health detail"
for svc in "${SERVICES[@]}"; do
    cid="$(dc ps -q "$svc" 2>/dev/null || true)"
    if [[ -z "$cid" ]]; then
        printf '%-10s not running\n' "$svc"
        continue
    fi
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}(no healthcheck){{end}}' "$cid" 2>/dev/null || echo 'unknown')"
    status="$(docker inspect --format '{{.State.Status}}' "$cid" 2>/dev/null || echo 'unknown')"
    printf '%-10s status=%-10s health=%s\n' "$svc" "$status" "$health"
done

# The filesystem docker itself lives on (where images/volumes/logs consume disk) — the
# box's real disk-risk surface, per this slice's log-rotation change.
section "disk: filesystem holding /var/lib/docker"
df -h /var/lib/docker 2>/dev/null || df -h /

section "disk: docker system df (images / containers / volumes / build cache)"
docker system df -v

section "disk: named volume sizes (postgres-data / redis-data / attachments-data)"
for vol in vocky_postgres-data vocky_redis-data vocky_attachments-data; do
    if docker volume inspect "$vol" >/dev/null 2>&1; then
        mp="$(docker volume inspect --format '{{.Mountpoint}}' "$vol")"
        size="$(du -sh "$mp" 2>/dev/null | cut -f1 || echo '?')"
        printf '%-28s %s\n' "$vol" "$size"
    else
        printf '%-28s (volume not found)\n' "$vol"
    fi
done

# Last few lines from the two services most likely to show an application-level
# problem (api/worker) — postgres/redis are covered by the health block above.
section "last 20 log lines: api"
dc logs --no-color --tail 20 api 2>&1 || true

section "last 20 log lines: worker"
dc logs --no-color --tail 20 worker 2>&1 || true

printf '\n[status] done — read-only snapshot, nothing changed.\n'
