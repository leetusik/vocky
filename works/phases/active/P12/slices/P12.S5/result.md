# Result — P12.S5: Postgres backups, log rotation and basic metrics

## What landed

- **`deploy/backup.sh`** (new, executable) — box-side nightly backup script.
  - Postgres: online `docker exec vocky-postgres pg_dump -U vocky vocky | gzip -9`, timestamped
    (`vocky-db-<UTC-YYYYMMDD-HHMMSS>.sql.gz`) into `/home/opc/backups/vocky/db/`. No secrets read or
    echoed — peer auth inside the container needs no password.
  - Attachments: `docker run --rm -v vocky_attachments-data:/data:ro -v <backup-dir>:/backup alpine tar
    -C /data -czf /backup/<name> .` into `/home/opc/backups/vocky/attachments/` — a throwaway container,
    read-only mount, never binds into the live `vocky-api`/`vocky-worker` containers.
  - Redis: explicitly skipped, with a comment explaining why (queue/cache only, fully reconstructible).
  - Retention: both directories pruned to 14 days on every run (`find -maxdepth 1 -mtime +13`, i.e.
    delete anything ≥14 days old), printing every file it removes and a per-directory summary count.
  - Header comments carry the exact one-line cron install for the operator.
- **`deploy/status.sh`** (new, executable) — read-only on-box snapshot: `docker compose ps` + per-service
  health/state, `df -h` on the docker filesystem, `docker system df -v`, per-named-volume sizes
  (`postgres-data` / `redis-data` / `attachments-data`), and the last 20 log lines each for `api` and
  `worker`. Takes no arguments, changes nothing. Explicitly scoped as "basic metrics", not monitoring
  infrastructure — no collector, no time series, no alerting.
- **`deploy/restore.md`** (new) — the documented, never-executed restore drill. Covers both stores: (1)
  verify a chosen dump by restoring into a scratch `vocky_restore_check` database first; (2) the real
  cutover order for the database (`stop api worker` → drop/recreate `vocky` → load dump → `alembic
  current` + `alembic upgrade head` as a migrate-check → `up -d` → re-gate); (3) the attachments untar
  into the live volume via a throwaway read-write container. Closes with an explicit "what this does not
  protect against" section (box loss, >14 days back, <24h of loss window, Redis) and states plainly it
  has never been rehearsed.
- **`compose.prod.yml`** — added a top-level `x-logging: &default-logging` anchor (`json-file`, `max-size:
  "10m"`, `max-file: "3"`) plus `logging: *default-logging` on all five services (`postgres`, `redis`,
  `api`, `worker`, `web`), each placed after that service's `restart: unless-stopped` line. A new comment
  block explains the cap applies **on container recreate**, not retroactively, and calls out specifically
  that `postgres`/`redis` (never recreated by an ordinary `deploy.sh` app deploy) only pick up the cap on
  a deliberate `docker compose up -d postgres redis` or full stack bounce — not the next ordinary deploy.
  Nothing else in the file was touched.

## Decisions and reasoning

- **Retention: 14 days**, per the plan's instruction — a cheap box-local default that survives "I broke
  something last week" without unbounded growth; recorded in `restore.md` as not surviving box loss.
- **Cron time: daily at 04:10 box time** (`10 4 * * *`), per the plan — matches the plan's suggested slot,
  low-traffic hour, offset from the top of the hour to avoid colliding with any other cron minute-0 jobs.
  Logs to `/home/opc/backups/vocky/backup.log` via `>>` + `2>&1` in the cron line itself (not inside the
  script), so a cron-level failure (e.g. the script not found) is also captured.
- **Restore drill shape: a standalone `deploy/restore.md`**, not folded into the script header — it needed
  three distinct, multi-step procedures (verify / DB cutover / attachments cutover) plus a "what this does
  not protect against" section; that is not "genuinely short" per the plan's own carve-out, so a separate
  file was the right call.
- **Attachments backup via a throwaway `alpine` container**, matching the plan's exact prescription and
  `backup.sh`'s own `:ro` volume-mount idiom already used elsewhere in this repo's deploy scripts (e.g.
  `deploy.sh`'s one-off migration container) — no bind into `vocky-api`.
- **`docker system df -v`** (verbose) rather than the plain form in `status.sh`, so the per-image/
  container/volume breakdown is visible in one read rather than only the summary table — still a single
  read-only command, in keeping with "basic metrics, not monitoring infrastructure".

## Validation (verbatim output)

1. `bash -n deploy/backup.sh && bash -n deploy/status.sh`
   ```
   backup.sh: bash -n OK
   status.sh: bash -n OK
   ```
   `shellcheck` is **not installed** in this sandbox (`which shellcheck` → not found) — confirmed, matching
   the phase notebook's existing note that shellcheck/actionlint are absent here.

2. `docker compose -f compose.prod.yml config -q` with dummy secrets, run two ways to cross-check against
   the known "repo's real dev `.env` auto-loads and can mask a missing var" trap `P12.S1` documented:
   - `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose --env-file /dev/null -f
     compose.prod.yml config -q` → **exit 0**
   - `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml
     config -q` (repo's real `.env` present and auto-loaded) → **exit 0**
   Both pass — the `x-logging` anchor does not break interpolation either way.

3. Proving all five services render the cap. Two checks:
   - `... docker compose --env-file /dev/null -f compose.prod.yml config | grep -c 'max-size: 10m'` →
     **6** (5 services + the preserved top-level `x-logging` extension block itself).
   - A precise per-service check via `docker compose config --format json` parsed with stdlib `json`
     (no `pyyaml` available in this sandbox):
     ```
     api       json-file 10m 3
     postgres  json-file 10m 3
     redis     json-file 10m 3
     web       json-file 10m 3
     worker    json-file 10m 3
     total services: 5
     ```
     Confirms all five, not just some, carry `driver=json-file`, `max-size=10m`, `max-file=3`.

4. Dry read of `backup.sh`'s pruning logic: `prune()` is invoked exactly twice, hard-coded —
   `prune "$DB_DIR" "db"` and `prune "$ATTACH_DIR" "attachments"` — and both `$DB_DIR` / `$ATTACH_DIR` are
   derived only from `$BACKUP_ROOT` (default `/home/opc/backups/vocky`), never from external input, a
   glob, or a `find` result. Inside `prune()`, the only deletion is `rm -f -- "$f"` where `$f` comes from
   `find "$dir" -maxdepth 1 -type f -mtime "+$((RETENTION_DAYS - 1))" -print0` — scoped to `$dir` itself
   with `-maxdepth 1` (no recursion into subdirectories, no following out of `$dir`). Confirmed: the
   script can never delete outside `/home/opc/backups/vocky/` (unless `BACKUP_ROOT` itself is overridden
   to point elsewhere at invocation time — the same trust boundary every other config knob in this repo's
   deploy scripts has; not a defect specific to this script).

## What was NOT done (by design, per plan boundaries)

- No ssh to the box, no execution against production, no cron installed, no restore executed. Everything
  above is authored-and-validated-locally only.
- `deploy/deploy.sh`, `deploy/rollback.sh`, the GitHub workflow files, dev `docker-compose.yml`, and
  `docs/` were not touched.
- **Note on a phase.md forward-note**: the § *P12.S4 complete* section of `phase.md` says "For S5: box
  access from this environment is proven; S5 can install its backup artifacts itself." This slice's own
  `plan.md`, written after that note, is explicit and unambiguous that this slice authors-only and the
  box application is operator-gated post-push — and the orchestrator's own dispatch instructions to this
  executor separately forbade any ssh/box contact. Followed `plan.md`'s literal scope rather than the
  earlier forward-note; flagging the discrepancy here rather than silently resolving it, in case the
  orchestrator intended to update the plan and didn't.

## Operator runbook — on-box application (do this after the operator's next push)

1. **Push** the commit(s) landing this slice (and any later P12 slices) to `origin/main` — an explicit
   operator action per `CLAUDE.md`.
2. **On the box** (`ssh oracle-cloud`, then `cd /home/opc/vocky`):
   ```sh
   git pull --ff-only
   ```
3. **Re-deploy to pick up the logging caps** (recreates `api`/`web`/`worker` on the same code if nothing
   else changed, or applies whatever else the push carries):
   ```sh
   deploy/deploy.sh
   ```
   This is `deploy.sh`'s **second-ever run** on this box — the first `:previous` rollback tags for
   `vocky-api` and `vocky-web` get created here (the first deploy, P12.S4, had none). The app services
   (`api`/`web`/`worker`) pick up the `max-size`/`max-file` cap immediately since they're recreated. The
   **datastores (`postgres`/`redis`) do not** — they're never recreated by an ordinary app deploy (see
   `deploy.sh`'s step 3: `dc up -d postgres redis` only starts them if not already running, it doesn't
   force-recreate a running container). To cap the datastore containers' logs too, run, on the box, once,
   whenever convenient (short blip, not a rebuild):
   ```sh
   docker compose -f compose.prod.yml up -d postgres redis --force-recreate
   ```
   (Verify health returns green afterward — `deploy/status.sh` below — before moving on; this is optional
   and can be deferred if the operator would rather not touch a live datastore container right now.)
4. **Install the cron line** (see `deploy/backup.sh`'s header comment for the exact line):
   ```sh
   crontab -e
   # add:
   10 4 * * * /home/opc/vocky/deploy/backup.sh >> /home/opc/backups/vocky/backup.log 2>&1
   ```
5. **Optional: run a first backup by hand** to prove the script works before waiting for 04:10, and check
   the stack's live status:
   ```sh
   deploy/backup.sh
   ls -la /home/opc/backups/vocky/db/ /home/opc/backups/vocky/attachments/
   deploy/status.sh
   ```
6. **The restore drill remains unrehearsed.** `deploy/restore.md` is ready to use, but its first real
   rehearsal (ideally against the scratch-database verify step only, step 1 of that file, not a real
   cutover) is a separate operator-scheduled action, not part of this runbook.

## Doc impact

Appended to `phase.md` § *Doc impact* (see below) — `operations.md` currently has **no backup story at
all**; it needs a new section covering: the backup script + its cron install line, the 14-day retention,
what is and isn't backed up (DB + attachments, not Redis), the log-rotation cap and its "applies on
recreate, datastores need a deliberate action" caveat, `deploy/status.sh`'s existence and scope, and a
pointer to `deploy/restore.md` with its never-rehearsed status stated plainly.

## Deviations from plan.md

None in scope or file boundaries. One judgment call flagged above (followed `plan.md`'s literal "author
only" scope over an earlier, looser forward-note in `phase.md`) — documented rather than silently resolved.
