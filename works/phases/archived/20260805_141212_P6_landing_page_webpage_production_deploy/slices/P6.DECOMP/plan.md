# P6.DECOMP — plan (decompose the phase)

You are executing the **decomposition** slice for P6. Your job is **only** to (1) create the middle
slices as bare folders with `new-slice`, and (2) seed `works/phases/active/P6/phase.md`. Do **not**
implement anything, do **not** pre-fill any other slice's `plan.md`, do **not** run `doc-new-version`.

## Phase framing (for phase.md)

P6 is titled "Landing Page, Webpage & Production Deploy," but the landing/webpage was already built and
designed in **P8 (design gate) → P9 (apply)** — decision **D-P8-1 superseded D-P4-3**, redefining
"**P6 becomes production-deploy-only**." So P6 = ship the missing production deploy for `vocky.hi2vi.com`,
close the documented web-app polish gaps, and land the ancillary P6 cleanups (PyPI publish, Admin-UI
removal). Deploy pattern = **mirror the sibling `~/projects/personal/knowledge` repo** (`knowledge.hi2vi.com`
— same shape as vocky), with `~/projects/personal/hi2vi_web` for the image-tag rollback model + CI chain.

**Confirmed operator scope (this session):**
1. Bring-up = **agent drives, operator gates**: author all artifacts AND run the on-box bring-up via
   `ssh oracle-cloud` + `edge`, pausing (`pending`) for operator-only steps (Cloudflare DNS record,
   on-box secret generation, GitHub secrets). **P6 ends with `vocky.hi2vi.com` live and smoke-verified.**
2. **Include CI now** (GitHub Actions production-deploy chain mirroring knowledge/hi2vi).
3. **Also include** PyPI publish of the `vocky` CLI **and** physical removal of the packaged Admin Web UI.

## Step 1 — Create the middle slices (bare folders only)

Run exactly these (REVIEW already exists at order 9999):

```
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S1  --name "Admin-UI removal" --kind implementation --risk medium --order 1
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S2  --name "Landing/site metadata & production origin" --kind implementation --risk medium --order 2
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S3  --name "CSP + HSTS security headers" --kind implementation --risk medium --order 3 --depends-on P6.S2
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S4  --name "Web production Dockerfile" --kind implementation --risk medium --order 4
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S5  --name "Production compose + env template" --kind implementation --risk high --order 5 --depends-on P6.S4
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S6  --name "Edge nginx vhost (vocky.conf)" --kind implementation --risk high --order 6 --depends-on P6.S5
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S7  --name "Deploy + rollback scripts" --kind implementation --risk high --order 7 --depends-on P6.S5
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S8  --name "CI production-deploy chain" --kind implementation --risk medium --order 8 --depends-on P6.S7
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S9  --name "PyPI packaging + publish" --kind implementation --risk medium --order 9
python3 scripts/workflow.py new-slice --phase P6 --slice P6.S10 --name "Production bring-up" --kind co-work --risk high --order 10 --depends-on P6.S6
```

Do not create `plan.md`/`result.md` in these folders. After creation, run
`python3 scripts/workflow.py validate` and confirm it passes.

## Step 2 — Seed `works/phases/active/P6/phase.md`

Fill these sections (append; keep the existing intent link + Objective):

### Decomposition (record the table + one-line rationale each)

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

### Findings (deploy pattern — downstream slices depend on these)

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
  `knowledge/deploy/{knowledge.conf,deploy.sh,rollback.sh,README.md,SECRETS.md}`;
  `hi2vi_web/deploy/{deploy.sh,rollback.sh,github-actions-production-deploy.sh,oracle-production-deploy-remote.sh}`,
  `hi2vi_web/.github/workflows/deploy-production.yml`.
- **Stale artifact:** `docker-compose.yml` still sets retired `VOCKY_API_AUTH_TOKEN` — clean it (S5).

### Constraints

- **nginx house rules** (violating any breaks every co-tenant site through the shared edge): never
  `default_server`; no `listen [::]` (IPv6); no `limit_req_zone` and globally-unique zone/location names
  (names are global across the whole `conf.d/` tree — a duplicate fails `nginx -t` for all sites);
  Cloudflare real-IP restore (`set_real_ip_from` + `real_ip_header CF-Connecting-IP`);
  `resolver 127.0.0.11 valid=30s ipv6=off` + variable `proxy_pass` upstreams for Docker DNS re-resolution.
- **Design boundary:** favicon/OG are assembled from the **existing** round-01 brand (the `Mark`
  component, wordmark, brand tokens in `web/src/app/globals.css`) — implementation with the existing
  design system, **not** a new design round. A bespoke OG illustration would be a separate design gate.

## Verdict

Return `done` with a short summary of the slices created. If anything about the breakdown looks wrong
against the repo, note it in `result.md` and `phase.md` rather than silently changing scope.
