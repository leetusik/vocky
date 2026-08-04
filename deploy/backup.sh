#!/usr/bin/env bash
#
# backup.sh — nightly Postgres + attachments backup for the vocky.hi2vi.com box (P12.S5).
#
# Backs up the TWO durable datastores compose.prod.yml's health-gate never protects
# against loss: the `vocky_postgres-data` volume (via a live `pg_dump`, NOT a raw volume
# copy — a raw copy of a running Postgres data dir can capture a torn write) and the
# `vocky_attachments-data` volume (a straight tar, since attachments are inert files with
# no in-flight writer state to tear).
#
# REDIS IS DELIBERATELY NOT BACKED UP. `vocky_redis-data` holds only the capture queue
# (RQ) and cache state — every entry is reconstructible from Postgres or re-enqueued by
# the producing request; there is no durable data in Redis that a restore needs. Backing
# it up would only add a third artifact nothing ever restores.
#
# Safe to run while the stack serves live traffic:
#   - `pg_dump` takes Postgres's own internal MVCC snapshot — it is the ONLINE, supported
#     way to back up a live database (unlike `docker cp`-ing the data directory, which can
#     capture a file mid-write). No downtime, no lock that blocks reads/writes.
#   - The attachments tar is taken through a ONE-OFF throwaway container that mounts the
#     named volume `:ro` — it NEVER binds into the live `vocky-api` / `vocky-worker`
#     containers, so it cannot disturb what they have open. `tar` reading files that the
#     worker concurrently appends to can only ever produce a slightly-stale (never
#     corrupt) copy of the file being written at that instant — attachments are written
#     once and not mutated after, so in practice this window does not occur.
#
# Retention: BOTH backup directories are pruned to the last 14 days on every run (`find
# -mtime +13`, i.e. anything strictly older than 14*24h — see the prune function below).
# 14 days was picked as a cheap, box-local default that survives "I broke something last
# week" without unbounded disk growth; it does NOT survive loss of the box itself (see
# deploy/restore.md's "what this does not protect against" section).
#
# House rules: `set -euo pipefail`, no secrets in this script — `docker exec` into
# vocky-postgres for pg_dump uses the container's own local Postgres peer-auth trust (the
# `vocky` role connecting from `localhost` inside its own container needs no password),
# so nothing from the box `.env` is read or echoed here.
#
# ---------------------------------------------------------------------------------------
# CRON INSTALL (operator action, run ON THE BOX — this script does not install itself):
#   crontab -e
#   # add this line — daily at 04:10 box time, output appended to its own log:
#   10 4 * * * /home/opc/vocky/deploy/backup.sh >> /home/opc/backups/vocky/backup.log 2>&1
# ---------------------------------------------------------------------------------------
#
# Manual run:
#   deploy/backup.sh
#
# Restore: see deploy/restore.md — NEVER rehearsed as of this writing; the first
# rehearsal is an operator action.
#
# Authored + statically checked off-box (P12.S5): `bash -n`, a dry read of the prune
# logic against the boundary rule below. It has never executed against the live box.

set -euo pipefail

# --- config knobs (override via env) ------------------------------------------------
BACKUP_ROOT="${BACKUP_ROOT:-/home/opc/backups/vocky}"
DB_DIR="$BACKUP_ROOT/db"
ATTACH_DIR="$BACKUP_ROOT/attachments"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-vocky-postgres}"
POSTGRES_DB="${POSTGRES_DB:-vocky}"
POSTGRES_USER="${POSTGRES_USER:-vocky}"
ATTACHMENTS_VOLUME="${ATTACHMENTS_VOLUME:-vocky_attachments-data}"
TS="$(date -u +%Y%m%d-%H%M%S)"

log() { printf '[backup] %s\n' "$*"; }
die() { printf '[backup] ERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "docker not found"

mkdir -p "$DB_DIR" "$ATTACH_DIR"

# --- 1. Postgres: online pg_dump, gzipped, timestamped ------------------------------
# `docker exec` into the running container, not a host-side `pg_dump` (the box has no
# Postgres client installed, and the container already has the matching server-version
# `pg_dump`). Peer auth inside the container needs no password — no secret touches this
# script or its log.
DB_OUT="$DB_DIR/vocky-db-$TS.sql.gz"
log "dumping database '$POSTGRES_DB' from container '$POSTGRES_CONTAINER' -> $DB_OUT"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip -9 > "$DB_OUT"
log "db dump complete: $(du -h "$DB_OUT" | cut -f1)"

# --- 2. Attachments: tar the named volume through a throwaway :ro container ---------
# `--rm` = no leftover container; `-v volume:/data:ro` = read-only mount, never touches
# the live api/worker containers or their open file handles. `alpine` is the smallest
# image with `tar` already on it — no build, no dependency beyond a cached/pullable
# base image.
ATTACH_OUT="$ATTACH_DIR/vocky-attachments-$TS.tar.gz"
log "archiving volume '$ATTACHMENTS_VOLUME' -> $ATTACH_OUT"
docker run --rm \
    -v "$ATTACHMENTS_VOLUME:/data:ro" \
    -v "$ATTACH_DIR:/backup" \
    alpine \
    tar -C /data -czf "/backup/$(basename "$ATTACH_OUT")" .
log "attachments archive complete: $(du -h "$ATTACH_OUT" | cut -f1)"

# --- 3. Redis: deliberately skipped -------------------------------------------------
log "skipping redis (vocky_redis-data) — queue/cache only, fully reconstructible, not backed up by design"

# --- 4. Prune both directories to RETENTION_DAYS ------------------------------------
# `find "$dir" -maxdepth 1 -type f -mtime +N` — `+N` means "more than N*24h old", so
# `+13` with a 14-day retention keeps everything through day 14 and deletes day 15+.
# `-maxdepth 1` + a fixed directory argument keeps this scoped to exactly $DB_DIR /
# $ATTACH_DIR and nothing below/above them — it can never walk outside
# $BACKUP_ROOT because the two prune calls are hard-coded to $DB_DIR and $ATTACH_DIR,
# never to a variable or glob that could expand elsewhere.
prune() {
    local dir="$1" label="$2" f pruned=0
    while IFS= read -r -d '' f; do
        log "pruning $label backup older than ${RETENTION_DAYS}d: $f"
        rm -f -- "$f"
        pruned=$((pruned + 1))
    done < <(find "$dir" -maxdepth 1 -type f -mtime "+$((RETENTION_DAYS - 1))" -print0)
    log "$label prune complete: $pruned file(s) removed"
}
prune "$DB_DIR" "db"
prune "$ATTACH_DIR" "attachments"

log "DONE — db: $DB_OUT   attachments: $ATTACH_OUT   retention: ${RETENTION_DAYS}d"
