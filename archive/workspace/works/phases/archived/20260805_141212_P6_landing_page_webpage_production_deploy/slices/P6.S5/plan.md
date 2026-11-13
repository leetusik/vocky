# P6.S5 — Production compose + env template · plan

> Slice `P6.S5` (implementation, risk **HIGH**). The deploy-topology slice — load-bearing. Creates
> `compose.prod.yml` (the box compose project) + `.env.prod.example`, mirroring `knowledge/compose.prod.yml`
> adapted to vocky's **5-service** shape. Read `phase.md` (Findings + Constraints).

## Context

The dev `docker-compose.yml` publishes host ports and is not a prod stack. The prod compose mirrors
`knowledge/compose.prod.yml`'s serving contract: fixed `container_name`s reached by the edge over the
**external** `changple_shared_network`, **no host ports** (`expose:` only), container-name upstreams,
healthchecks + `depends_on: healthy`, `restart: unless-stopped`, secrets interpolated from the box's
gitignored `.env` (never committed). Vocky differs from knowledge:
- **Two extra services**: `redis` + `worker` (queue + capture-persistence consumer).
- **Shared attachments volume**: `attachments-data` on **both** `vocky-api` and `vocky-worker` — must
  persist across redeploys.
- **`/mcp` is in-app** (Starlette `Mount("/mcp")` inside vocky-api) — **no separate mcp container**; the
  edge routes `/mcp` → `vocky-api:8000` (S6).

## Create — `compose.prod.yml` (repo root), five services

All: `networks: [changple_shared_network]`, `restart: unless-stopped`, **no `ports:`**. Reference peers by
**container_name** (collision-safe on the shared external net — never the bare service alias).

- **`postgres`** — `postgres:17`, `container_name: vocky-postgres`; `POSTGRES_DB: vocky`,
  `POSTGRES_USER: vocky`, `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}` (**no `:-` default**); volume
  `postgres-data:/var/lib/postgresql/data`; `pg_isready` healthcheck.
- **`redis`** — `redis:7-alpine`, `container_name: vocky-redis`,
  `command: ["redis-server","--appendonly","yes"]`; volume `redis-data:/data`; `redis-cli ping` healthcheck.
- **`api`** — `build: .`, `container_name: vocky-api`, `expose: ["8000"]`; `depends_on:` postgres+redis
  `service_healthy`; volume `attachments-data:/var/lib/vocky/attachments`; python-urllib `/healthz`
  healthcheck (`start_period: 60s`). `environment:`
  - `DATABASE_URL: postgresql+psycopg://vocky:${POSTGRES_PASSWORD}@vocky-postgres:5432/vocky`
  - `REDIS_URL: redis://vocky-redis:6379/0`
  - `VOCKY_HOST: 0.0.0.0`, `VOCKY_PORT: 8000`, `VOCKY_LOG_LEVEL: INFO`
  - `VOCKY_ADMIN_AUTH_TOKEN: ${VOCKY_ADMIN_AUTH_TOKEN}` (guards the surviving `/admin/api`)
  - `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com` (public `/mcp` DNS-rebinding allowlist — `config.py`)
  - `VOCKY_ATTACHMENTS_DIR: /var/lib/vocky/attachments`, `_MAX_BYTES: 5242880`, `_MAX_COUNT: 10`,
    `_ALLOWED_MIME_TYPES: image/jpeg,image/png,image/gif,image/webp`
  - **Omit `VOCKY_API_AUTH_TOKEN`** (retired). Default command (`vocky-server`).
- **`worker`** — `build: .`, `container_name: vocky-worker`,
  `command: ["uv","run","--no-sync","vocky-worker"]`; `depends_on:` postgres+redis `service_healthy`;
  volume `attachments-data:/var/lib/vocky/attachments` (**shared with api**); env `DATABASE_URL`,
  `REDIS_URL`, `VOCKY_LOG_LEVEL: INFO`, `VOCKY_ATTACHMENTS_DIR: /var/lib/vocky/attachments`.
  **No healthcheck** (a queue consumer has no HTTP endpoint) — a comment should note S7 gates it `running`
  and must rebuild it (stale-worker footgun).
- **`web`** — `build: { context: ./web, args: { NEXT_PUBLIC_APP_URL: "https://vocky.hi2vi.com" } }`,
  `container_name: vocky-web`, `expose: ["3000"]`; `depends_on: api service_healthy`; node-fetch `/`
  healthcheck. `environment:` `VOCKY_API_BASE_URL: http://vocky-api:8000` and
  `SESSION_SECRET: ${SESSION_SECRET}` (interpolated — **not** `env_file`, so api secrets never enter web).

`volumes: postgres-data: redis-data: attachments-data:` (named). `networks: changple_shared_network: { external: true }`.

**No `env_file:` anywhere** — the three secrets are `${...}` interpolations compose reads from the box's
project `.env`; containers receive only the vars listed in `environment:`.

## Create — `.env.prod.example` (repo root)

Template for the box's gitignored `.env`: the three secrets to generate **on the box**
(`openssl rand -base64 32`) — `POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`. Note
`DATABASE_URL`/`REDIS_URL`/`VOCKY_API_BASE_URL` are literal container-name URLs in compose (not here);
`NEXT_PUBLIC_APP_URL` is a compose build arg (not here); rotating `SESSION_SECRET` logs everyone out.

## Edit

- **`docker-compose.yml`** (dev) — drop the stale `VOCKY_API_AUTH_TOKEN: ${VOCKY_API_AUTH_TOKEN:-}` line
  (~45). Leave the rest of the dev stack intact.
- **`.dockerignore`** (root) — add `web`, `works`, `docs`, `tests`, `dist`, `attachments`, `.env.prod`,
  `node_modules`, `.next` (backend build context = `.`; the Dockerfile only copies
  `pyproject.toml`/`uv.lock`/`README.md`/`alembic*`/`src`). Keep existing entries.

## Hand-off notes (append to `phase.md`)

- **S6**: `/mcp` → `vocky-api:8000` (in-app MCP, no mcp container); upstreams `vocky-api:8000` / `vocky-web:3000`.
- **S7** `deploy.sh`: `COMPOSE_BAKE=false`; rebuild **all** incl. `worker`; gate api/web/postgres/redis on
  `healthy` + worker on `running`; `docker compose -f compose.prod.yml exec vocky-api uv run --no-sync alembic upgrade head`
  after `up -d`; **never `down -v`** (preserve `attachments-data` + `postgres-data`).
- **S10**: box `.env` needs `POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`.

## Verification

- **Syntax + interpolation (no daemon needed):**
  `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml config -q`
  succeeds. Inspect the rendered `config` and assert: **no `ports:`**; `external: true`; `attachments-data`
  on both `vocky-api` and `vocky-worker`; container-name upstreams; **no `VOCKY_API_AUTH_TOKEN`**.
- Edited dev compose still parses: `docker compose -f docker-compose.yml config -q`. If the CLI is entirely
  unavailable, fall back to `python3 -c "import yaml; yaml.safe_load(open('compose.prod.yml'))"` + a static
  diff against `knowledge/compose.prod.yml`, and note full `config` validation defers to S10.
- `grep -n "VOCKY_API_AUTH_TOKEN" docker-compose.yml compose.prod.yml` → empty.
- `python3 scripts/workflow.py validate` passes (repo root — cwd may persist).

## Executor notes (high tier)

The topology contract every later slice builds on — precision matters. Mirror knowledge's serving contract
exactly. Do **not** invent an `env_file`, a host port, or a bare-service-name upstream. Keep the worker
healthcheck decision as specified (none; S7 gates `running`) unless you have a clean, dependency-free
liveness check using only what the uv image already has. If `docker compose config` surfaces a real schema
problem you can't resolve against the reference, escalate. Write `result.md`; append the hand-off +
Doc-impact notes to `phase.md`. Do not commit; do not transition status.
