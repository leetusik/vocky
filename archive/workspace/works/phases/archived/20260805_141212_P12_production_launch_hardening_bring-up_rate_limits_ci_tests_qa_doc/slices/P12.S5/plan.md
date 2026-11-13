# Plan — P12.S5: Postgres backups, log rotation and basic metrics

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-mid` (risk `medium`).

## Context you must absorb first

Read `phase.md` — especially § *P12.S4 complete — vocky is LIVE* and § *P12.S4 Gate 4 executed*. The
system this slice describes is **running in production right now**: five containers
(`vocky-postgres`, `vocky-redis`, `vocky-api`, `vocky-web`, `vocky-worker`) on the box at
`/home/opc/vocky`, checkout `6c16ac5`, volumes `vocky_postgres-data` / `vocky_redis-data` /
`vocky_attachments-data`, all on `changple_shared_network` behind the shared edge.

**You do not touch the box.** Everything in this slice is authored in the repo and validated locally.
The on-box application (a second `deploy.sh` run to pick up logging caps, the cron install, the restore
drill) is operator-gated and happens **after the operator's next push** — the box deploys from
`origin/main`, the repo is ahead of it, and pushing is an operator action. Your job is to make those
later steps a paste-and-run certainty, not to perform them.

## Scope (from DECOMP's breakdown, order 5)

1. **`deploy/backup.sh`** — a box-side backup script:
   - `pg_dump` of the `vocky` database via `docker exec vocky-postgres pg_dump -U vocky vocky`,
     gzipped, timestamped, into `/home/opc/backups/vocky/db/`.
   - The attachments volume: a tar.gz of `vocky_attachments-data` taken through a one-off container
     (`docker run --rm -v vocky_attachments-data:/data:ro …`), into `/home/opc/backups/vocky/attachments/`.
     Never bind into the live api container for this.
   - Retention: prune both directories to 14 days (`find -mtime`-style). Print what it pruned.
   - Redis is **deliberately not backed up** — it holds the queue and cache, both reconstructible; say
     so in a comment rather than silently omitting it.
   - House style: `set -euo pipefail`, the repo's heavy-comment idiom, no secrets in the script (pg_dump
     via `docker exec` needs none — peer auth inside the container). Must be safe to run while the stack
     serves traffic (pg_dump is online; the attachments tar is read-only).
   - Include (as comments at the top) the one-line cron install the operator will run, e.g. daily at
     04:10 box time, logging to `/home/opc/backups/vocky/backup.log`.
2. **Restore drill — documented, never executed here.** A `deploy/restore.md` (or a section in the
   backup script's header if genuinely short — your call, but it must cover both stores): exact commands
   to restore the DB dump into a scratch database first (verify), then the real cutover order
   (stop api/worker → restore → migrate check → up), and the attachments untar. State plainly it has
   never been rehearsed and that the first rehearsal is an operator action.
3. **Log rotation — the box's real disk risk.** Add a `logging:` block (json-file, `max-size: 10m`,
   `max-file: "3"`) to **all five services** in `compose.prod.yml`. Use a YAML anchor (`x-logging:`) so
   it is stated once — the file already comments heavily; explain that caps apply **on container
   recreate**, i.e. at the next `deploy.sh` run, not retroactively.
4. **Minimal on-box status read** — `deploy/status.sh`: container states + health, `df -h` for the
   filesystem holding docker, `docker system df`, per-volume sizes, and the last few api/worker log
   lines. Read-only, box-side, no arguments needed. This is the "basic metrics" deliverable — do not
   build monitoring infrastructure.

## Boundaries

- Files: `deploy/backup.sh` (new), `deploy/status.sh` (new), `deploy/restore.md` (new, or folded per
  item 2), `compose.prod.yml` (logging anchor + blocks only — touch nothing else in it).
- Do **not** ssh anywhere, do not run anything against the production box, do not install cron, do not
  execute a restore.
- Do not touch `deploy/deploy.sh`, `deploy/rollback.sh`, the GitHub workflow files, dev
  `docker-compose.yml`, or anything under `docs/` (no `doc-new-version` — Doc impact lines only).
- No new test files — validation below is script-level. Do not commit; do not run workflow state
  commands.

## Validation (report actual output)

1. `bash -n deploy/backup.sh && bash -n deploy/status.sh` (and `shellcheck` if available — say whether
   it was).
2. `docker compose -f compose.prod.yml config -q` with the three required env vars set to dummies
   (e.g. `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f
   compose.prod.yml config -q`) — the logging anchor must not break interpolation.
3. `docker compose -f compose.prod.yml config` (same dummies) piped to a grep that proves all five
   services render the `max-size` cap.
4. A dry read of `backup.sh`'s pruning logic — confirm it can never delete outside
   `/home/opc/backups/vocky/`.

## Deliverables

- `result.md`: what landed, every decision (retention length, cron time, restore-drill shape) with its
  reason, verbatim validation output, and a precise **operator runbook** for the on-box application:
  push → `git pull` on box → `deploy.sh` (recreates with caps, creates the first `:previous` rollback
  tags) → install cron line → optional first backup run + `status.sh`.
- `phase.md` § *Findings & Notes*: the backup/restore contract in three or four lines, and the fact
  that log caps wait on the next deploy.
- `phase.md` § *Doc impact*: operations.md gains backups/rotation/status (currently absent — it has no
  backup story at all); the restore drill's never-rehearsed status.
