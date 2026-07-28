# Phase P6: Landing Page, Webpage & Production Deploy

_Intent: see [intent.md](intent.md)._

## Objective

Build the public landing page/site in the Next.js app using the hi2vi_web Claude design-gate workflow, and deploy to production at vocky.hi2vi.com — app on the oracle-cloud box, nginx via edge.

## Context

**Reframed to production-deploy-only.** The title still reads "Landing Page, Webpage & Production
Deploy," but the landing/webpage was already built and designed in **P8 (design gate) → P9 (apply)** —
decision **D-P8-1 superseded D-P4-3**, redefining **P6 as production-deploy-only**. So P6 = ship the
missing production deploy for `vocky.hi2vi.com`, close the documented web-app polish gaps, and land the
ancillary P6 cleanups (PyPI publish, Admin-UI removal). The Objective above is kept verbatim per the
DECOMP plan, but the actual scope is the reframed one below.

Deploy pattern = **mirror the sibling `~/projects/personal/knowledge` repo** (`knowledge.hi2vi.com` — same
shape as vocky), with `~/projects/personal/hi2vi_web` for the image-tag rollback model + CI chain.

**Confirmed operator scope (DECOMP session):**
1. Bring-up = **agent drives, operator gates**: author all artifacts AND run the on-box bring-up via
   `ssh oracle-cloud` + `edge`, pausing (`pending`) for operator-only steps (Cloudflare DNS record,
   on-box secret generation, GitHub secrets). **P6 ends with `vocky.hi2vi.com` live and smoke-verified.**
2. **Include CI now** (GitHub Actions production-deploy chain mirroring knowledge/hi2vi).
3. **Also include** PyPI publish of the `vocky` CLI **and** physical removal of the packaged Admin Web UI.

**SECOND REFRAME (2026-07-28) — the bring-up moved out of P6 to P12.** Operator, verbatim: _"mind that deploy
will be done at p12 so p6 doesn't have to mind it."_ So point 1 above no longer holds: **P6 ends with every
deploy artifact authored and validated statically, and nothing deployed.** The live bring-up — Cloudflare DNS
record, on-box `.env` secrets, the three `ORACLE_SSH_*` GitHub secrets, the `/home/opc/vocky` clone,
`up -d --build`, the health gate, the migrate, the edge `scp` + `validate.sh` + `deploy.sh`, and the external
smoke — is now owned by **P12** (`works/phases/active/P12/`). The `P6.S10` row in the table below and every
"Hand-off to S10" note in *Findings & Notes* stay exactly as written: **they are the spec P12 executes**, and
P12's `intent.md` points back here for them.

Rationale for the move: P10 (Accounts v2) adds `UNIQUE(tenant_id, name)` and a three-phase
`project_credentials.tenant_id` backfill. Deploying first would turn that into a live cutover on production data,
with the migration-before-code ordering hazard and a defensive de-dupe of rows that might already exist.
Deploying after P10/P11 makes it a migration against an empty schema. The sequence is **P6 → P10 → P11 → P12**.

## Decomposition

Ten middle slices (P6.S1–P6.S10) + P6.REVIEW (order 9999). Ordering front-loads the low-coupling cleanups
and web changes (S1–S4), then the deploy artifacts that layer on each other (S5 compose → S6 vhost / S7
scripts → S8 CI), with PyPI (S9) parallel and the live operator-gated bring-up last (S10). Every deploy
slice depends on the sibling-repo pattern captured in Findings.

| Slice | Kind | Risk | Delivers |
|---|---|---|---|
| P6.S1 Admin-UI removal | impl | med | Delete `src/vocky/admin_ui.py`, `admin_assets/*`, the `/admin` + `/admin/api` mounts and wiring in `app.py`, `scripts/check_admin_ui_package.py`, dead `VOCKY_ADMIN_AUTH_TOKEN` refs used only by `/admin`, related tests/docs. First — shrinks route surface before the nginx map. |
| P6.S2 Landing/site metadata & origin | impl | med | `web/public/` + Next file-convention routes: favicon/`icon`/`apple-icon`, `opengraph-image` (from the **existing** brand — `Mark`, wordmark, tokens — not new design), `robots.ts`, `sitemap.ts`, web manifest. Marketing rewrite of `SITE.description`; production origin/`metadataBase` via `NEXT_PUBLIC_APP_URL=https://vocky.hi2vi.com`. Fix landing `not-found.tsx` back-link. |
| P6.S3 CSP + HSTS headers | impl | med | Real-origin CSP in `web/next.config.ts` (+ app security headers); HSTS lands at the edge (S6). |
| P6.S4 Web production Dockerfile | impl | med | `web/Dockerfile` per `knowledge/web/Dockerfile` (multi-stage node:22-slim, pnpm frozen, `ARG NEXT_PUBLIC_APP_URL` asserted, standalone, `USER node`, `EXPOSE 3000`, `node server.js`). Confirm backend `Dockerfile` prod-fit. |
| P6.S5 Production compose + env | impl | **high** | `compose.prod.yml`: api+web+postgres:17+redis+worker, `container_name: vocky-*`, no host ports (expose only), external `changple_shared_network`, container-name upstreams, attachments volume shared api+worker, healthchecks + `depends_on: healthy`, `restart: unless-stopped`, `NEXT_PUBLIC_APP_URL` via web `build.args`, `SESSION_SECRET` to web only. `.env.prod.example`. Drop stale retired `VOCKY_API_AUTH_TOKEN` from dev compose. |
| P6.S6 Edge nginx vhost | impl | **high** | `deploy/vocky.conf` per `knowledge.conf`; routing map + house rules below. |
| P6.S7 Deploy + rollback scripts | impl | **high** | `deploy/deploy.sh` (hi2vi image-tag rollback: tag latest→previous, `COMPOSE_BAKE=false` build, `up -d`, health-gate **all** incl. worker, `docker compose exec vocky-api alembic upgrade head`, auto-rollback on health fail). `deploy/rollback.sh`. |
| P6.S8 CI deploy chain | impl | med | `.github/workflows/deploy-production.yml` (workflow_dispatch, main-guarded, concurrency, `environment: production`, external smoke of `https://vocky.hi2vi.com`), `deploy/github-actions-production-deploy.sh` (runner transport, `ORACLE_SSH_*` secrets), `deploy/oracle-production-deploy-remote.sh` (on-box gate: refuse dirty, fetch origin/main, ancestor-verify `TARGET_SHA`). |
| P6.S9 PyPI packaging + publish | impl | med | `pyproject.toml` publish metadata for the `vocky` dist, build sdist/wheel, verify `uvx vocky` from artifact. `publish` step is operator-authorized (`pending`, PyPI token). |
| P6.S10 Production bring-up | co-work | **high** | Live first deploy — agent-driven, operator-gated (execution model finalized at its plan gate; likely orchestrator-driven). Gates (`pending`): Cloudflare `vocky` DNS record; on-box secrets + `.env`; GH secrets. Agent: clone on box, `COMPOSE_BAKE=false docker compose -f compose.prod.yml up -d --build`, health-gate, migrate, `scp deploy/vocky.conf → /home/opc/edge/conf.d/`, `ssh oracle-cloud 'cd /home/opc/edge && ./validate.sh && ./deploy.sh'`, external smoke `https://vocky.hi2vi.com`. |

## Findings & Notes

_Deploy pattern — downstream slices depend on these._

- **Box:** `ssh oracle-cloud` = `opc@140.245.64.173`. No `edge` ssh alias — `edge` is a compose project.
- **Edge:** standalone compose project `/home/opc/edge`, container `edge-nginx` (`nginx:1.27-alpine`),
  external net `changple_shared_network`; `conf.d/` + `certs/` read-only host bind mounts. Apply a vhost by
  `scp` into `/home/opc/edge/conf.d/` then `./validate.sh` + `./deploy.sh` (nginx -t gate + graceful
  reload; never recreate). Co-tenant vhosts (do not disturb): `00-default.conf`, `changple5.conf`,
  `changple-web.conf`, `hi2vi.conf`, `knowledge.conf`.
- **TLS:** wildcard `/home/opc/edge/certs/hi2vi.crt` (+`.key`), SANs `*.hi2vi.com, hi2vi.com` already
  covers `vocky.hi2vi.com`. Cloudflare Full (Strict). Nothing to provision.
- **DNS:** operator adds a **proxied `vocky`** record on the `hi2vi.com` Cloudflare zone.
- **Serving contract:** container-name upstreams over the shared net, no host ports (`expose:` only),
  `restart: unless-stopped`, container healthchecks, `external: true` network.
- **Env:** `VOCKY_API_BASE_URL=http://vocky-api:8000` (web BFF upstream), `SESSION_SECRET` (web only),
  `NEXT_PUBLIC_APP_URL=https://vocky.hi2vi.com` (web `build.arg`), `DATABASE_URL`/`REDIS_URL` as
  container-name URLs, `POSTGRES_PASSWORD`, `VOCKY_MCP_ALLOWED_HOSTS=vocky.hi2vi.com`.
- **Vocky specifics:** attachments named volume shared by `vocky-api`+`vocky-worker` must persist across
  redeploys; the **worker** must be built + health-considered (stale-worker-image footgun); deploy runs an
  explicit `alembic upgrade head`. Carry `COMPOSE_BAKE=false` (compose v2 bake panic).
- **nginx routing (longest-prefix wins):** `/api/auth/` + `/api/app/` → **web:3000**; `/api/`, `/auth/`,
  `/app/`, `/mcp`, `= /healthz` → **api:8000**; `/` → **web:3000**.
- **Reference files:** `knowledge/compose.prod.yml`, `knowledge/web/Dockerfile`,
  `knowledge/deploy/{knowledge.conf,deploy.sh,README.md,SECRETS.md}` (+ `github-actions-production-deploy.sh`,
  `oracle-production-deploy-remote.sh`); `hi2vi_web/deploy/{deploy.sh,rollback.sh,github-actions-production-deploy.sh,oracle-production-deploy-remote.sh}`,
  `hi2vi_web/.github/workflows/deploy-production.yml`.
- **Stale artifact:** `docker-compose.yml` still sets retired `VOCKY_API_AUTH_TOKEN` (line 45) — clean it (S5).
- **S1 done — `/admin` route surface shrunk (relevant to S6 nginx map):** after removing the Web UI, the
  **only** routes under the `/admin` prefix are `/admin/api/*` (9 routes, admin-bearer-guarded). Bare
  `/admin`, `/admin/`, and `/admin/assets/*` no longer exist in the app. The nginx routing map need not
  (and should not) expose any `/admin` Web-UI path; only `/admin/api/` if the admin REST API is to be
  reachable through the edge. `VOCKY_ADMIN_AUTH_TOKEN` still guards `/admin/api`.
- **Repo-state check (DECOMP):** all S1/S3/S5 targets present (`src/vocky/admin_ui.py`,
  `src/vocky/admin_assets/`, `scripts/check_admin_ui_package.py`, `web/next.config.ts`, the stale token in
  `docker-compose.yml`) and both sibling repos present with the referenced deploy artifacts. **One minor
  correction to the plan's reference list:** `knowledge/deploy/` has **no** `rollback.sh` — the rollback
  reference for S7 lives in `hi2vi_web/deploy/rollback.sh` (knowledge folds rollback into `deploy.sh`).
  Corrected in the reference list above. No scope change.
- **S2 done — metadata routes live; relevant to S3 (CSP), S4 (Dockerfile), S5 (compose):**
  - The web toolchain is fully runnable in-sandbox (node v24.3.0, pnpm 10.28.2); `pnpm build` compiles
    the `ImageResponse` routes and static-prerenders them — no deferral needed. `next/og` (Satori) was
    already present; div-based Mark rebuilds render cleanly with the **default** ImageResponse font (the
    variable Pretendard woff2 was deliberately NOT loaded — avoids the Satori-variable-font footgun).
  - **`NEXT_PUBLIC_APP_URL` is now a live build-time input.** `SITE.url` reads it (blank →
    `http://127.0.0.1:3030`). It drives `metadataBase`, canonical/OG, robots `host`+`sitemap`, and the
    sitemap `loc`. **S4 must declare `ARG NEXT_PUBLIC_APP_URL` and export it before `next build`** (it is
    inlined at build, not runtime — a missing/blank value bakes the localhost origin into the image), and
    **S5 must pass it via the web service `build.args` = `https://vocky.hi2vi.com`.** This is the single
    origin knob for the whole site's metadata.
  - **S3 (CSP) note:** `opengraph-image`/`apple-icon` are same-origin server-rendered PNGs and the
    favicon is a same-origin SVG, so `img-src 'self'` covers them; no external image/font origin was
    introduced (no third-party font fetch — self-host philosophy preserved).
  - `robots.txt` disallows `/dashboard`, `/projects/`, `/feedback`, `/api/` (the authenticated + BFF
    surface); only `/` is in the sitemap. If S3/later slices add public routes, extend `sitemap.ts`.
- **S3 done — app owns the CSP + security headers; HSTS + additive CSP are the edge's job (S6 hand-off):**
  - `web/next.config.ts` now ships a **production-gated** all-`'self'` CSP (verified present under
    `pnpm start`, absent under `pnpm dev`); `Permissions-Policy` tightened to add `browsing-topics=()`.
    No HSTS in Next, no nonce, no `middleware.ts` (deliberate — a nonce forces dynamic rendering / loses
    static generation). The app CSP directive string is:
    `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'`.
  - **S6 (nginx `vocky.conf`) MUST add, on the `:443` server (mirroring the sibling house style):**
    `add_header Strict-Transport-Security "max-age=300" always;` (**`max-age=300`, no `includeSubDomains`,
    no `preload`**) and the **additive** `add_header Content-Security-Policy "upgrade-insecure-requests"
    always;` — this composes with, does **not** replace, the app CSP. nginx otherwise passes the app's
    headers through untouched (do not re-declare or strip the app's CSP / the four security headers).

- **S4 done — web + backend prod images ready; relevant to S5 (compose), S7 (deploy), S10 (bring-up):**
  - **`web/Dockerfile`** mirrors `knowledge/web/Dockerfile`. Runtime stage sets `PORT=3000
    HOSTNAME=0.0.0.0` and `EXPOSE 3000`, so the compose upstream is `vocky-web:3000` over the shared
    net (matches the serving contract). It has a built-in fetch `HEALTHCHECK` on
    `http://127.0.0.1:3000/`; S5 can rely on the image healthcheck or restate it. **S5 MUST pass
    `NEXT_PUBLIC_APP_URL=https://vocky.hi2vi.com` via the web service `build.args`** — it is asserted
    non-empty in the build stage, so a compose build that forgets it fails loud (by design). `web/public/`
    now exists (`.gitkeep`) purely so the runtime `COPY /app/public ./public` resolves; nothing needs to
    mount into it.
  - **Backend root `Dockerfile` confirmed prod-fit, unchanged.** uv two-layer build, `CMD
    ["uv","run","--no-sync","vocky-server"]`, runs as **root on purpose** (writes the shared attachments
    volume). It carries **no** migration and **no** worker command — S7 runs `alembic upgrade head`
    externally (`uv run --no-sync alembic upgrade head` in the container) and S5's `vocky-worker` reuses
    this same image with an overridden command. Do not bake migration/worker into the image.
  - **Docker daemon is unavailable in this sandbox** (client present, daemon unreachable). S4 verified
    via the plan's fallback (static review + `pnpm build` emits `.next/standalone/server.js` + `.next/static`).
    The actual `docker build` of both images, the `NEXT_PUBLIC_APP_URL`-missing assert firing, and the
    `curl /` 200 probe are **verified at S10 / CI** — do not expect an in-sandbox Docker build to work.

- **S5 done — `compose.prod.yml` + `.env.prod.example` are the box's deploy topology; relevant to
  S6 (vhost), S7 (deploy scripts), S10 (bring-up):**
  - The `docker compose` CLI **is** available in-sandbox (v2.37.1); the daemon is not, but
    `docker compose -f compose.prod.yml config -q` (the PARSER) runs without it. Prod + dev compose
    both parse (exit 0); the rendered config was inspected and passes every topology assertion (no
    host ports / `expose:` only, `external: true`, `attachments-data` on api+worker, container-name
    upstreams, no retired token). Full build/health validation still lands at S10 / CI.
  - **Five services, fixed `container_name`s** reached over `changple_shared_network`:
    `vocky-postgres:5432`, `vocky-redis:6379`, `vocky-api:8000`, `vocky-worker` (no port), `vocky-web:3000`.
    The edge (S6) addresses **api/web by container name**, never bare service alias.
  - **In-app `/mcp`**: there is NO mcp service — `/mcp` is a Starlette Mount inside `vocky-api`. The
    edge routes `/mcp → vocky-api:8000` (S6). `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com` is set on api.
  - **Secrets contract**: NO `env_file:` anywhere. Exactly three `${...}` interpolations, supplied by
    the box's gitignored `.env` (template = `.env.prod.example`): `POSTGRES_PASSWORD` (postgres + baked
    into api/worker `DATABASE_URL`), `SESSION_SECRET` (web only), `VOCKY_ADMIN_AUTH_TOKEN` (api only).
    `DATABASE_URL`/`REDIS_URL`/`VOCKY_API_BASE_URL` are committed literal container-name URLs;
    `NEXT_PUBLIC_APP_URL=https://vocky.hi2vi.com` is a web `build.args` value (build-time, not `.env`).
  - **Retired legacy API token** dropped from the dev `docker-compose.yml` and never introduced in
    prod; `.dockerignore` leaned (added `.env.prod`, `works`, `docs`, `tests`, `dist`, `attachments`,
    `web`, `node_modules`, `.next`; kept existing entries).

- **Hand-off to S6 (edge `deploy/vocky.conf`):** upstreams are `vocky-api:8000` and `vocky-web:3000`
  by container name. `/mcp → vocky-api:8000` (in-app MCP, no mcp container). Combine with the S1/S3
  routing + HSTS/CSP hand-offs already recorded above.
- **Hand-off to S7 (`deploy/deploy.sh`):** carry `COMPOSE_BAKE=false`; rebuild **all** services incl.
  `worker` (it rides the api image — an un-rebuilt worker runs stale code); health-gate
  api/web/postgres/redis on `healthy` and **worker on `running`** (it has no healthcheck by design);
  run `docker compose -f compose.prod.yml exec vocky-api uv run --no-sync alembic upgrade head` after
  `up -d`; **never `down -v`** (preserve `attachments-data` + `postgres-data` + `redis-data`).
- **Hand-off to S10 (bring-up):** the box `.env` must define `POSTGRES_PASSWORD`, `SESSION_SECRET`,
  `VOCKY_ADMIN_AUTH_TOKEN` (generate on the box, `openssl rand -base64 32`); template is
  `.env.prod.example`. `.env` is gitignored + `.dockerignore`d — never committed.

- **S7 done — deploy/rollback scripts authored; `compose.prod.yml` now supports image-tag rollback.
  Relevant to S8 (CI wrapper) and S10 (first bring-up):**
  - **`compose.prod.yml` changed:** `api` gained `image: vocky-api:latest` (kept `build: .`), `web`
    gained `image: vocky-web:latest` (kept its build), and **`worker` now `image: vocky-api:latest`
    with NO `build:`** (reuses the api image + its `vocky-worker` command override). The
    **stale-worker footgun is CLOSED**: one `docker compose build` freshens api + worker together;
    the worker can no longer run stale code behind a fresh api. Verified via
    `docker compose config` (rendered worker block has `image: vocky-api:latest`, no `build:`).
  - **`deploy/deploy.sh`** (executable): `git fetch --prune` + `checkout REF` (default `origin/main`)
    -> tag both `vocky-{api,web}:latest -> :previous` -> `up -d postgres redis` + gate healthy ->
    `docker compose build` -> **migrate in a one-off container BEFORE serving** -> `up -d` -> gate
    api/web healthy + worker running -> image-tag rollback (flip both `:previous -> :latest`,
    `up -d --no-build`, re-gate) on any failure. **Ordering build -> migrate -> up -> gate is
    load-bearing.** Carries `COMPOSE_BAKE=false`. **Never `down`/`down -v`** (datastores +
    attachments volume persist).
  - **Migrate idiom (correction to the S7 plan):** `docker compose run` takes the **service key
    `api`**, NOT the container_name `vocky-api` (the plan's step-6 snippet wrote `vocky-api`, which
    would fail "no such service"). Full primary command:
    `docker compose -f compose.prod.yml run --rm -T --no-deps --name vocky-migrate-$$ api uv run
    --no-sync alembic upgrade head`. The one-off container inherits the api service's `environment:`
    block (interpolated `DATABASE_URL`, which config.py reads directly) + the shared net. A
    `MIGRATE_VIA_DOCKER_RUN=1` env toggle switches to a plain `docker run --network
    changple_shared_network` fallback (builds `DATABASE_URL` from `POSTGRES_PASSWORD` in `.env`) if a
    Compose ever refuses `run` on the pinned service.
  - **`deploy/rollback.sh`** (executable): manual counterpart — retag both `:previous -> :latest`,
    `up -d --no-build`, re-gate (api/web healthy, worker running). **Does NOT re-migrate** (additive
    migrations only; a schema-incompatible revert is a git-ref redeploy `deploy/deploy.sh <sha>`).
    Never `down`.
  - **The scripts did NOT run in-sandbox** (no docker daemon / box). Static proof only
    (`bash -n` both, compose `config -q`, workflow `validate`); behavioral proof is S10 / CI.
    `shellcheck` is not installed in the sandbox — skipped (manual review done instead).

- **Hand-off to S8 (CI deploy chain):** the on-box remote gate script wraps `deploy/deploy.sh`
  (model `hi2vi_web/deploy/oracle-production-deploy-remote.sh`): refuse a dirty tree, `git fetch`,
  ancestor-verify `TARGET_SHA` against `origin/main`, export `REMOTE_ARTIFACT_DIR` (deploy.sh writes
  compose ps + per-service logs there on failure for scp-back), then call `deploy/deploy.sh`.
  `deploy.sh` reads `REF="${1:-origin/main}"`, `APP_DIR`/`COMPOSE_FILE`/`ENV_FILE`/`HEALTH_TRIES`/
  `HEALTH_INTERVAL` are env-overridable knobs.
- **Hand-off to S10 (first bring-up):** run `deploy/deploy.sh` from the box clone once `.env` exists.
  First deploy hits the no-`:previous` branch for both images (expected — no rollback point), and the
  one-off migrate creates the schema. Confirm the box's compose v2 accepts `docker compose run --name`
  on the container_name-pinned api service (knowledge proved it there); if not, set
  `MIGRATE_VIA_DOCKER_RUN=1`.

- **S8 done — CI production-deploy chain authored (`.github/` was net-new). Relevant to S10 (first
  bring-up + operator secrets) and REVIEW (operations doc):**
  - Three files ported from hi2vi_web's proven chain, changing only the documented vocky deltas:
    - `.github/workflows/deploy-production.yml` — manual `workflow_dispatch`, main-guarded
      (`preflight` outputs `target_sha=GITHUB_SHA`), `deploy` job with `environment: {production,
      url: https://vocky.hi2vi.com}`, `concurrency: {group: vocky-deploy, cancel-in-progress:
      false}`, `timeout-minutes: 90`. `bash -n`s the two helpers **plus the existing S7
      `deploy/deploy.sh`**, runs `deploy/github-actions-production-deploy.sh` with the `ORACLE_SSH_*`
      + `TARGET_SHA` + `ARTIFACT_DIR` env, then a **two-endpoint external smoke** of
      `https://vocky.hi2vi.com/healthz` (api) **and** `https://vocky.hi2vi.com/` (web), each 5×6s,
      fail-if-either-≠200, then uploads artifacts `if: always()`.
    - `deploy/github-actions-production-deploy.sh` (`+x`) — runner transport: SSH to
      `opc@140.245.64.173`, scp+run the on-box gate against `/home/opc/vocky`, scp artifacts back.
      SSH/key/passphrase handling + `TARGET_SHA` 40-hex assert kept verbatim; log prefix
      `[vocky-deploy]`, temp names `/tmp/vocky-gha-*`.
    - `deploy/oracle-production-deploy-remote.sh` (`+x`) — on-box gate: refuse dirty tracked tree,
      `git fetch --prune origin main`, **ancestor-verify `TARGET_SHA` against fetched origin/main**
      (`git merge-base --is-ancestor`), then hand off `deploy/deploy.sh "${TARGET_SHA}"` (S7's script,
      untouched). `REPO_PATH=/home/opc/vocky`, `collect_status` = `docker compose -f compose.prod.yml
      ps` (no `-p`, `.env` auto-read — mirrors deploy.sh's `dc()`).
  - **S7's `deploy/deploy.sh` was NOT modified** — the chain reuses it as-is (verified: `git status`
    clean for it). No delta forced any `deploy.sh` contract change.
  - **The chain never ran here.** No `.github/` existed before; the workflow only fires on operator
    `workflow_dispatch` and needs the three `ORACLE_SSH_*` GH secrets + a live box + `.env` + DNS.
    Static proof only: `bash -n` all three scripts (PASS), `chmod +x` both new ones, YAML `safe_load`
    (PASS, via `uv run --with pyyaml` — system python3 lacks yaml), `workflow.py validate` (PASS).
    `shellcheck`/`actionlint` not installed — skipped (manual review). Behavioral proof = S10 / first
    dispatch.

- **CONSISTENCY NOTE for S10 (project-name / volume stability):** vocky's `deploy/deploy.sh` `dc()`
  runs `docker compose -f compose.prod.yml` with **no `-p` pin**, so the Compose **project name derives
  from the clone directory basename**. The S8 chain follows the same convention (the on-box gate's
  `collect_status` also pins no `-p`). **S10 MUST clone the box to `/home/opc/vocky`** → project name
  `vocky` → named volumes `vocky_postgres-data`, `vocky_redis-data`, `vocky_attachments-data` stay
  stable across every redeploy. A clone at any other path would silently orphan the datastore volumes
  on the next deploy. (Container names are pinned + image tags explicit, so *only the clone dir name*
  matters for identity.)

- **Hand-off to S10 (operator co-work — GH secrets + box clone):** add three repo secrets to
  `leetusik/vocky` — `ORACLE_SSH_PRIVATE_KEY`, `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE`
  (**same box as hi2vi/knowledge — reuse the existing key material**). Clone the box to
  `/home/opc/vocky` (per the consistency note). **First deploy:** either run `deploy/deploy.sh`
  manually on the box, OR dispatch this workflow once secrets + clone + `.env` + the `vocky` DNS
  record all exist. The workflow is main-only and ancestor-verified, so a dispatch can only ship a
  commit that is already on `origin/main`.

- **S9 done — PyPI packaging complete (built + verified), publish is operator-gated. Relevant to S10
  (operator publish) and REVIEW:**
  - **Lean-CLI split works and stays test-green.** Core = `httpx` + `typer`; everything else is the
    `server` optional extra. The CLI is import-isolated (`vocky/__init__.py` trivial; `vocky.cli.*` import
    only typer/httpx/stdlib + the httpx-only `vocky.smoke`), so the wheel runs with core deps alone —
    proven by `uvx --from dist/vocky-0.1.0-*.whl vocky --version` → `0.1.0` (15 pkgs, no server deps).
  - **`[tool.uv] default-extras` is UNSUPPORTED in uv 0.8.14** (rejected as an unknown `[tool.uv]` field).
    The plan's approach was replaced with the standard uv 0.8.x idiom: the dev dependency group
    self-references the project's own extra — `"vocky[server]"` in `[dependency-groups] dev` (a default
    group) — so a plain `uv sync` installs core + server + dev. Dependency groups never enter built dist
    metadata, so the wheel/sdist stay lean (server only as a `; extra == "server"` gate). If uv is later
    upgraded past the version that adds `default-extras`, either mechanism works; keep the self-ref.
  - **sdist bloat footgun (fixed):** an unconstrained `uv build` yields a **~680 MB** sdist because
    hatchling's default sdist selection ignores the nested `web/.gitignore` and pulls in
    `web/node_modules` + `.next`. Fixed with `[tool.hatch.build.targets.sdist] include = ["/src/vocky",
    "/README.md", "/LICENSE"]` (root-anchored — bare globs match nested node_modules READMEs/LICENSEs).
    sdist is now 79 KB. **Do not remove this include-list.**
  - **Backend `Dockerfile`** now passes `--extra server` on both `uv sync` layers (deterministic — does not
    rely on default-extras reaching `--no-dev`). The server image's dep set is unchanged from before the
    split (verified `uv sync --extra server` resolves cleanly).
  - **In-sandbox test caveat:** `uv run pytest` = 79 passed / 108 `psycopg.OperationalError` (no Postgres,
    Docker daemon unavailable). A stash→baseline run on pre-split HEAD gave the *identical* 79/108, proving
    the split changed nothing behaviorally. Full DB validation is S10 / CI, as with the other deploy slices.
  - **Publish is the operator's step:** `dist/` holds the wheel + sdist; PyPI name `vocky` is free (404);
    run `uv publish` with a PyPI token. Orchestrator sets S9 `pending` for the operator.

## Constraints

- **nginx house rules** (violating any breaks every co-tenant site through the shared edge): never
  `default_server`; no `listen [::]` (IPv6); no `limit_req_zone` and globally-unique zone/location names
  (names are global across the whole `conf.d/` tree — a duplicate fails `nginx -t` for all sites);
  Cloudflare real-IP restore (`set_real_ip_from` + `real_ip_header CF-Connecting-IP`);
  `resolver 127.0.0.11 valid=30s ipv6=off` + variable `proxy_pass` upstreams for Docker DNS re-resolution.
- **Design boundary:** favicon/OG are assembled from the **existing** round-01 brand (the `Mark`
  component, wordmark, brand tokens in `web/src/app/globals.css`) — implementation with the existing
  design system, **not** a new design round. A bespoke OG illustration would be a separate design gate.

## Doc impact

_Running list — the REVIEW slice consolidates these into durable-doc versions._

- **P6.S1** (Admin Web UI removal): stale `/admin` Web-UI mentions to drop/correct — `README.md`
  (token-into-UI instructions), `docs/current/architecture.md` (route-group "/admin packaged Admin Web
  UI" + the P4-open-question "superseded but still mounted / removal deferred to P6" resolution notes),
  `docs/current/api.md`, `docs/current/operations.md` (its "Deferred to P6" Admin-UI removal line). The
  `/admin/api/*` REST surface and `VOCKY_ADMIN_AUTH_TOKEN` are unchanged.
- **P6.S2** (Landing/site metadata & origin): web app now ships the Next 16 metadata file-convention
  routes (`icon.svg`, `apple-icon`, `opengraph-image`, `robots.txt`, `sitemap.xml`, `manifest.webmanifest`
  under `web/src/app/`) built from the existing round-01 brand; `SITE.description` rewritten to grounded
  marketing copy; `layout.tsx` gained `openGraph`/`twitter` metadata; production origin/`metadataBase`
  wired via the build-time public var `NEXT_PUBLIC_APP_URL` (blank→`http://127.0.0.1:3030` dev fallback,
  `https://vocky.hi2vi.com` via Docker `build.args` in S4/S5). REVIEW folds this into
  `docs/current/frontend.md` (+ an `operations.md` note on the `NEXT_PUBLIC_APP_URL` build arg).
- **P6.S3** (CSP + production security headers): `web/next.config.ts` now ships a **production-only**
  Content-Security-Policy (all `'self'`; `'unsafe-inline'` for `script-src`/`style-src` to cover Next's
  nonce-less inline hydration + `next/font`/React inline styles; no nonce, no `middleware.ts`), and
  `Permissions-Policy` was tightened to `camera=(), microphone=(), geolocation=(), browsing-topics=()`.
  HSTS and the additive `upgrade-insecure-requests` CSP are deferred to the edge nginx vhost (S6), not
  the app. REVIEW folds this into `docs/current/security.md` (the CSP directive string + prod-only /
  no-nonce rationale + the edge/app split) and `docs/current/frontend.md` (the shipped security-header set).
- **P6.S4** (Web production Dockerfile): `web/Dockerfile` (multi-stage `node:22-slim`, pnpm frozen,
  `output:'standalone'`, `ARG NEXT_PUBLIC_APP_URL` asserted non-empty, `USER node`, `EXPOSE 3000`,
  `node server.js`) + `web/.dockerignore` + `web/public/.gitkeep` added; backend root `Dockerfile`
  confirmed prod-fit and left unchanged. REVIEW folds this into `docs/current/operations.md` (the web
  build/run image contract + the `NEXT_PUBLIC_APP_URL` build arg) and `docs/current/frontend.md` (the
  standalone production image note).
- **P6.S5** (Production compose + env template): new repo-root `compose.prod.yml` (the OCI-box deploy
  topology — five services `vocky-postgres`/`vocky-redis`/`vocky-api`/`vocky-worker`/`vocky-web`, fixed
  container names over the external `changple_shared_network`, no host ports/`expose:`-only,
  container-name upstreams, healthchecks + `depends_on: service_healthy`, `restart: unless-stopped`,
  `attachments-data` shared api+worker, in-app `/mcp` on vocky-api with no mcp container, three
  `${...}` secrets from the box `.env` and NO `env_file:`) + `.env.prod.example` (the box-`.env`
  secrets template: `POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`). Retired legacy
  API auth-token env var dropped from the dev `docker-compose.yml`; root `.dockerignore` leaned. REVIEW
  folds this into `docs/current/operations.md` (the production deploy topology / serving contract / box
  secrets model) and, if the doc set carries a deployment/architecture view, the container topology in
  `docs/current/architecture.md`.
- **P6.S6** (Edge nginx vhost): new `deploy/vocky.conf` — the `vocky.hi2vi.com` edge vhost dropped into
  `/home/opc/edge/conf.d/` (scp + `./validate.sh` + `./deploy.sh`, hard `nginx -t` gate, applied at S10).
  Records the durable **edge routing map** (longest-prefix over two container-name upstreams
  `vocky-api:8000` / `vocky-web:3000`: `/api/auth/` + `/api/app/` → web; `/api/`, `/auth/`, `/app/`,
  `/mcp`, `= /healthz` → api; `/admin/` → **404, not exposed**; `/` → web), TLS termination on the hi2vi
  wildcard cert, **HSTS `max-age=300`** + **additive `upgrade-insecure-requests` CSP** (composes with the
  S3 app CSP), **Cloudflare real-IP restore** (verbatim CF v4+v6 ranges + `CF-Connecting-IP`), **Docker
  DNS re-resolution** (`resolver 127.0.0.11` + variable `proxy_pass`), `client_max_body_size 12m`,
  in-app `/mcp` (SSE-safe, no mcp container), and **shared-edge house-rule compliance** (no
  `default_server` / IPv6 `listen` / rate-limit zone / duplicate global name). REVIEW folds this into
  `docs/current/operations.md` (edge/serving topology + apply path) and `docs/current/security.md` (edge
  TLS / HSTS / additive CSP / CF real-IP + the `/admin` internal-only decision).

- **P6.S7** (Deploy + rollback scripts): new `deploy/deploy.sh` + `deploy/rollback.sh` (executable) —
  the production release + rollback runbook for `vocky.hi2vi.com`. `deploy.sh` = git-checkout-REF +
  two-image (`vocky-api`/`vocky-web`) tag rollback, `COMPOSE_BAKE=false` build, **alembic migration in
  a one-off `docker compose run` container BEFORE serving**, five-service gate (api/web on health,
  worker on `running`, postgres/redis on health), auto image-tag rollback on failure, **never
  `down`** (postgres-data/redis-data/attachments-data persist). `rollback.sh` = manual retag
  `:previous -> :latest` + `up -d --no-build` + re-gate, no re-migration. `compose.prod.yml` gained
  `image:` tags on api (`vocky-api:latest`) + web (`vocky-web:latest`) and the **worker now reuses
  `image: vocky-api:latest` with no `build:`** (stale-worker footgun closed). REVIEW folds this into
  `docs/current/operations.md` (the deploy/rollback runbook: lifecycle order, image-tag rollback
  model, migrate-before-serve, worker-state gate, never-`down` rule, `MIGRATE_VIA_DOCKER_RUN`
  fallback) and the container-topology note in `docs/current/architecture.md` (worker reuses the api
  image).

- **P6.S8** (CI production-deploy chain): new `.github/workflows/deploy-production.yml` +
  `deploy/github-actions-production-deploy.sh` + `deploy/oracle-production-deploy-remote.sh` (both
  `+x`) — a **manual** (`workflow_dispatch`), **main-only**, **ancestor-verified** GitHub Actions
  deploy path ported from hi2vi_web. Flow: preflight guards `main` → runner SSHes to the box
  (`opc@140.245.64.173`) and ships the on-box gate → the gate refuses a dirty tree, fetches
  `origin/main`, verifies `TARGET_SHA` is an ancestor of fetched origin/main, then hands off to the
  S7 `deploy/deploy.sh` (unchanged — owns checkout/build/migrate/health-gate/rollback) → **external
  two-endpoint smoke** of `https://vocky.hi2vi.com/healthz` (api) + `/` (web) → artifact upload.
  Requires three `ORACLE_SSH_*` GitHub repo secrets (added by the operator in S10). REVIEW folds this
  into `docs/current/operations.md` (the CI deploy path: manual/main-only/ancestor-verified dispatch,
  the three-file chain driving `deploy.sh`, the required GH secrets, and the external smoke).

- **P6.S9** (PyPI packaging): `pyproject.toml` split into a **lean CLI core** (`[project.dependencies]` =
  `httpx` + `typer` only) plus a `[project.optional-dependencies] server` extra carrying the 11 heavy deps
  (alembic, greenlet, mcp[cli], pydantic-settings, psycopg[binary], redis, sqlalchemy, starlette,
  uvicorn[standard], python-multipart, argon2-cffi) — so `pip install vocky` / `uvx vocky` install only the
  CLI and self-hosting uses `pip install "vocky[server]"`. PyPI metadata enriched (CLI `description`,
  keywords, classifiers, `[project.urls]`, SPDX `license = "MIT"` + `license-files`). Backend `Dockerfile`
  now `uv sync … --extra server` on both layers. `uv.lock` regenerated. Built + verified (wheel 95 KB,
  sdist 79 KB, `uvx --from` wheel runs the lean CLI); **not yet published** (operator-gated, PyPI token).
  REVIEW folds this into `docs/current/operations.md` (the CLI distribution/install model + lean-CLI-vs-
  `[server]` split + the `--extra server` Docker build) and `docs/current/experience.md` / `product.md`
  (the published `pip install vocky` / `uvx vocky` install path). Add "`vocky` published to PyPI" once the
  operator runs `uv publish`.

## Open Questions

- **`/auth/*` has no origin rate limit (P6.S6).** The public account-auth surface (`/auth/login`,
  `/auth/signup` — an unauthenticated password grant + open signup) routes to `vocky-api` through the
  edge, but vocky has **no** server-side per-IP limiter (unlike the sibling `knowledge`, which throttles
  its `/auth/*` in-process), and the shared edge **forbids** a `limit_req_zone` (global zone name across
  the whole `conf.d/` tree — a house-rule violation). So at launch `/auth/*` is unthrottled at the origin
  and relies on Cloudflare in front. **Resolution:** the orchestrator opens a **deferred job** — add a
  Cloudflare rate rule and/or an in-process `/auth` limiter — and REVIEW records the gap in
  `operations.md` / `security.md`. Accepted for launch behind Cloudflare.
-
