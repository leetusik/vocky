# Restore drill — vocky.hi2vi.com (P12.S5)

**Status: documented, never rehearsed.** Every command below is written from reading
`deploy/backup.sh`, `compose.prod.yml`, and `deploy/deploy.sh` — none has been executed,
on the box or anywhere else. **The first rehearsal is an operator action**, ideally on a
quiet window rather than during an incident. Treat this file as a starting draft to be
corrected by that first real run, not as a proven procedure.

This covers both backed-up stores. Redis is not backed up (see `backup.sh`'s header) and
has no restore procedure — it repopulates itself from Postgres/incoming traffic.

## 1. Verify a dump first, in a scratch database — never restore straight into `vocky`

Before touching the live database, prove a given `.sql.gz` actually restores cleanly, in
a throwaway database on the same Postgres instance:

```sh
# on the box, from /home/opc/vocky
LATEST_DUMP="$(ls -t /home/opc/backups/vocky/db/*.sql.gz | head -1)"

docker exec vocky-postgres psql -U vocky -d vocky -c \
  "CREATE DATABASE vocky_restore_check;"

gunzip -c "$LATEST_DUMP" | docker exec -i vocky-postgres psql -U vocky -d vocky_restore_check

# sanity: table list + a row count against something recognizable, e.g.:
docker exec vocky-postgres psql -U vocky -d vocky_restore_check -c '\dt'
docker exec vocky-postgres psql -U vocky -d vocky_restore_check -c \
  'SELECT count(*) FROM alembic_version;'

# clean up the scratch database once satisfied
docker exec vocky-postgres psql -U vocky -d vocky -c \
  "DROP DATABASE vocky_restore_check;"
```

If this step fails, the dump is bad or incompatible — stop here. Do not proceed to a
real cutover on a dump that has not passed this check.

## 2. Real cutover — database

Only after step 1 has passed on the dump you intend to use. This is a real outage
window: `api`/`worker` are stopped so nothing writes to the database mid-restore, and
users see the app down for the duration.

```sh
cd /home/opc/vocky

# a. stop the two services that touch the database (leaves postgres + redis up)
docker compose -f compose.prod.yml stop api worker

# b. drop and recreate the live database, then load the dump
docker exec vocky-postgres psql -U vocky -d postgres -c \
  "DROP DATABASE vocky;"
docker exec vocky-postgres psql -U vocky -d postgres -c \
  "CREATE DATABASE vocky;"
gunzip -c "$LATEST_DUMP" | docker exec -i vocky-postgres psql -U vocky -d vocky

# c. migrate-check — confirm the restored schema is at the head alembic expects for the
#    CURRENTLY DEPLOYED code (a dump taken before a later migration landed will need
#    `alembic upgrade head` to catch up; a dump taken after a migration that has since
#    been rolled back is the harder case and needs a judgment call, not a script)
docker compose -f compose.prod.yml run --rm --no-deps api \
  uv run --no-sync alembic current
docker compose -f compose.prod.yml run --rm --no-deps api \
  uv run --no-sync alembic upgrade head

# d. bring the app back up and re-gate (same health checks deploy.sh uses)
docker compose -f compose.prod.yml up -d
docker compose -f compose.prod.yml ps
```

If step (c)'s `alembic upgrade head` fails, do not bring `api`/`worker` back up against a
schema alembic itself does not trust — that is an incident, not a scripted next step.

## 3. Real cutover — attachments

Independent of the database restore; can be done before, after, or skipped if only the
database needs recovery.

```sh
LATEST_ATTACH="$(ls -t /home/opc/backups/vocky/attachments/*.tar.gz | head -1)"

# stop api/worker first if not already stopped (they hold the volume open for writes)
docker compose -f compose.prod.yml stop api worker

# untar INTO the named volume via a throwaway container, mounted read-write this time.
# --strip and re-untar rather than a docker cp: the volume mountpoint is root-owned on
# the host and not reliably reachable outside a container.
docker run --rm \
  -v vocky_attachments-data:/data \
  -v /home/opc/backups/vocky/attachments:/backup:ro \
  alpine \
  sh -c "rm -rf /data/* && tar -C /data -xzf /backup/$(basename "$LATEST_ATTACH")"

docker compose -f compose.prod.yml up -d
```

The `rm -rf /data/*` is destructive on purpose — this is a full replace of the live
attachments tree with the tar's contents, appropriate for "the volume itself is gone or
corrupt". If instead only some files are missing, extracting to a scratch location and
copying back the missing ones by hand is safer and is not scripted here.

## What this does not protect against

- **Box loss.** Both backup trees live on the same box's filesystem as the data they
  back up (`/home/opc/backups/vocky/`, separate from the `postgres-data`/
  `attachments-data` volumes but the same physical disk). A destroyed box loses backups
  and live data together. Off-box (object storage) replication was raised as an open
  question at `P12.DECOMP` and deliberately deferred — it needs a credential the
  operator has not yet provisioned.
- **More than 14 days back.** Retention prunes anything older; see `backup.sh`.
- **Anything written after the last nightly `pg_dump`** (up to ~24h of loss in the worst
  case, since the cron runs once daily at 04:10).
- **Redis.** Not backed up; see `backup.sh`'s header for why that is intentional.
