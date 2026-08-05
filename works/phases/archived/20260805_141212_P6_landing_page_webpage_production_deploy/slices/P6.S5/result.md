# P6.S5 — Production compose + env template · result

**Status: done.** The load-bearing deploy-topology artifacts are in place and validate through
the real `docker compose config` parser (daemon not required for `config`).

## Created

- **`compose.prod.yml`** (repo root) — the OCI-box compose project, five services, mirroring
  `~/projects/personal/knowledge/compose.prod.yml`'s serving contract, adapted to vocky's shape:
  - **postgres** (`postgres:17`, `vocky-postgres`) — `POSTGRES_DB/USER: vocky`,
    `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` (no `:-` default), `postgres-data` volume, `pg_isready`
    healthcheck.
  - **redis** (`redis:7-alpine`, `vocky-redis`) — `redis-server --appendonly yes`, `redis-data`
    volume, `redis-cli ping` healthcheck.
  - **api** (`build: .`, `vocky-api`) — `expose: ["8000"]`, `depends_on` postgres+redis
    `service_healthy`, shared `attachments-data` volume, python-urllib `/healthz` healthcheck
    (`start_period: 60s`), default image CMD (`vocky-server`). Env: container-name `DATABASE_URL` +
    `REDIS_URL`, `VOCKY_HOST/PORT/LOG_LEVEL`, `VOCKY_ADMIN_AUTH_TOKEN: ${...}`,
    `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com`, the four `VOCKY_ATTACHMENTS_*`. Retired legacy API
    token deliberately omitted.
  - **worker** (`build: .`, `vocky-worker`) — `command: uv run --no-sync vocky-worker`,
    `depends_on` postgres+redis `service_healthy`, the SAME `attachments-data` volume as api, env
    `DATABASE_URL`/`REDIS_URL`/`VOCKY_LOG_LEVEL`/`VOCKY_ATTACHMENTS_DIR`. NO healthcheck — an inline
    comment flags the stale-worker footgun and that S7 gates it on `running` + must rebuild it.
  - **web** (`build.context: ./web`, `build.args.NEXT_PUBLIC_APP_URL: https://vocky.hi2vi.com`,
    `vocky-web`) — `expose: ["3000"]`, `depends_on` api `service_healthy`, node-fetch `/`
    healthcheck, env `VOCKY_API_BASE_URL: http://vocky-api:8000` + `SESSION_SECRET: ${...}`
    (interpolated, NOT `env_file`).
  - Named volumes `postgres-data` / `redis-data` / `attachments-data`; network
    `changple_shared_network: { external: true }`. No `env_file:` anywhere; the three secrets are
    `${...}` interpolations only.
- **`.env.prod.example`** (repo root) — template for the box's gitignored `.env`: the three secrets
  to generate on the box (`openssl rand -base64 32`) — `POSTGRES_PASSWORD`, `SESSION_SECRET`,
  `VOCKY_ADMIN_AUTH_TOKEN` — plus notes that `DATABASE_URL`/`REDIS_URL`/`VOCKY_API_BASE_URL` are
  literal container-name URLs in the compose and `NEXT_PUBLIC_APP_URL` is a build arg (neither
  belongs in `.env`), and that rotating `SESSION_SECRET` logs everyone out.

## Edited

- **`docker-compose.yml`** (dev) — dropped the stale retired `VOCKY_API_AUTH_TOKEN: ${...:-}` line
  (was line 45). Rest of the dev stack intact; still parses.
- **`.dockerignore`** (root) — kept existing entries; added `.env.prod`, `works`, `docs`, `tests`,
  `dist`, `attachments`, `web`, `node_modules`, `.next` (backend build context is `.`, but the
  Dockerfile only copies `pyproject.toml`/`uv.lock`/`README.md`/`alembic*`/`src`).

## Verification (actual output)

The Docker daemon is unreachable in this sandbox, but the `docker compose config` PARSER runs
without it (`docker compose` CLI **is** available — v2.37.1). All commands run from the repo root.

| Check | Command | Result |
|---|---|---|
| Prod compose syntax + interpolation | `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml config -q` | **exit 0** |
| Dev compose still parses | `POSTGRES_PASSWORD=x docker compose -f docker-compose.yml config -q` | **exit 0** |
| Token grep (expect empty) | `grep -n "VOCKY_API_AUTH_TOKEN" docker-compose.yml compose.prod.yml` | **empty (PASS)** |
| Workflow state integrity | `python3 scripts/workflow.py validate` | **passed, exit 0** |

Assertions inspected against the rendered `docker compose ... config` (all confirmed):
- **No `ports:` / `published:`** anywhere — every service is `expose:`-only (`8000` api, `3000` web).
- **`external: true`** on `changple_shared_network`.
- **`attachments-data`** mounted at `/var/lib/vocky/attachments` on **both** `vocky-api` and
  `vocky-worker` (rendered named volume `vocky_attachments-data`).
- **Container-name upstreams**: `DATABASE_URL → vocky-postgres:5432`, `REDIS_URL → vocky-redis:6379`,
  `VOCKY_API_BASE_URL → http://vocky-api:8000` — no bare service aliases.
- **No `VOCKY_API_AUTH_TOKEN`** in the rendered environment.
- `depends_on: service_healthy` gates on api (postgres+redis), worker (postgres+redis), web (api);
  `restart: unless-stopped` on all five.

Full `config` validation (schema + build + runtime health) still ultimately exercises on the box /
CI at S10 — this slice verified everything the parser can reach in-sandbox, which is the whole
compose schema + interpolation + topology.

## Deviations from plan

- One wording deviation: my first draft of `compose.prod.yml` carried an inline comment that named
  the retired legacy API token literally, which tripped the plan's `grep "VOCKY_API_AUTH_TOKEN" ...
  → empty` assertion (a comment, not a setting — the rendered config already had the var absent). I
  reworded the comment so the literal string appears nowhere in either compose file, and the grep is
  now empty as the plan specifies. No functional change.
- Otherwise none — mirrors the plan and the knowledge serving contract exactly (no `env_file`, no
  host ports, no bare-service-name upstreams; worker healthcheck omitted as specified).
