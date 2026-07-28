---
doc_id: operations
version: v0005
created_at: 2026-07-29T05:46:37+09:00
source: P11.REVIEW
summary: P11: the hosted install.sh installer, the repo's first push and pull-request CI gate with its two deliberate exclusions, and the CLI capture module
previous: v0004_p6_the_vocky.hi2vi.com_production_deploy_kit_compose_topology_box_secrets_web_image_edge_vhost_deploy_rollback_runbook_ci_chain_lean-cli_split_authored_statically_validated_not_deployed
---

# Operations

## Status

This doc covers running the **web app** (`web/`, the Next.js frontend added in P4), installing/running the **`vocky` CLI** (added in P5), and — as of **P6** — the complete **production deploy kit** for `vocky.hi2vi.com`. It is deliberately scoped: the **backend/service** local operational surface — the Compose-first self-hosted workflow, `make bootstrap` / `verify` / `compose-down`, and the full `DATABASE_URL` / `REDIS_URL` / `VOCKY_*` configuration surface — is documented in **`architecture.md` § Configuration Surface** and is not duplicated here.

**Server console-entry rename (P5).** The server's console script is now **`vocky-server`** (`vocky.main:main`) — the bare `vocky` name is the new user-facing CLI. Every self-host/run reference moved off `vocky` to `vocky-server`: the `Dockerfile` `CMD`, the `docker-compose.yml` app service `command`, and the README "Running The App Directly". (The `Makefile` was untouched — it starts the server via Compose, not a direct `uv run vocky`.) The worker entry (`vocky-worker`) and smoke entry (`vocky-smoke`) are unchanged.

> ### ⚠ vocky is NOT deployed
>
> **P6 authored the entire production deploy kit and deployed none of it.** Every artifact below — `compose.prod.yml`, `.env.prod.example`, `web/Dockerfile`, `deploy/vocky.conf`, `deploy/deploy.sh`, `deploy/rollback.sh`, and the three-file GitHub Actions chain — exists in the repo and was **statically validated only** (compose parser, `bash -n`, YAML parse, `pnpm build`, house-rule greps). **Nothing has ever run against real infrastructure.** There is no `vocky` DNS record, no box clone, no box `.env`, no `ORACLE_SSH_*` GitHub secrets, and no running container. `https://vocky.hi2vi.com` does not answer.
>
> The **live bring-up is P12** — deliberately sequenced after P10 (Accounts v2, which adds a `UNIQUE(tenant_id, name)` constraint and a three-phase `project_credentials.tenant_id` backfill) so those migrations land against an empty schema instead of becoming a live cutover on production data. Sequence: **P6 → P10 → P11 → P12**.
>
> **The `vocky` CLI is also not on PyPI, and will not be.** P6 made the package publishable; **P11 decided the channel is a `curl | bash` installer instead** (`web/public/install.sh`) and published nothing. `uv publish` stays an unexercised, operator-gated action. The hosted install line `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` **404s until P12 deploys** — it is marked "once the site is live" everywhere it appears, and the landing page that shows it ships in the same bring-up.
>
> Read every "production" section below as *the design that will be applied*, not as a description of something running.

## Running the Web App Locally

The app needs a reachable vocky API. Bring the backend up first (see `architecture.md` / the root `Makefile`), then:

```sh
cd web
corepack enable              # pnpm 10.28.2, pinned via packageManager
pnpm install                 # or --frozen-lockfile in CI
cp .env.example .env.local   # then fill in both keys (below)
pnpm dev                     # http://127.0.0.1:3030
```

Requires **node >= 22.13.0** (`.nvmrc` pins `22`). All three server scripts bind `127.0.0.1:3030` — `dev`, `start`, and `build` never listen on a public interface by default.

### The local verification gate

```sh
pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

Expect **56/56 tests** and every real route reported as `ƒ (Dynamic)`. `next build` needs **no env** — env reads are lazy, never at module top level.

> **This gate is necessary but not sufficient.** Two of P4's sharpest bugs passed the *entire* gate and surfaced only in a live run: a `"use server"` file exporting a plain object (registered as a second server action → every submit 500s), and the `Secure`-cookie dev/prod split below. Verify user-visible behavior against a running vocky.

> **Run local end-to-end checks on `pnpm dev`, never `pnpm start`.** The production build marks the session cookie `Secure`, so a plain-http client on `127.0.0.1` never replays it and **every guarded page silently bounces to `/login`** — which looks like an auth bug and is not. (Real browsers treat `127.0.0.1` as a secure context; scripted http cookie jars do not.)

## Web App Configuration

Exactly **two** keys, both **server-only** — neither is `NEXT_PUBLIC_`, and both are read lazily through `src/lib/env.ts` (`import "server-only"`). Exposing either to the browser would defeat the BFF (D-P4-2), whose entire point is that only the Next.js server talks to vocky. `web/.env.example` is the template; `.env.local` is gitignored and must never be committed.

| Key | Meaning |
| --- | --- |
| `VOCKY_API_BASE_URL` | Base URL of the vocky API the Next server calls server-to-server. Local: `http://127.0.0.1:8000`. |
| `SESSION_SECRET` | Secret the AES-256-GCM session key is derived from (`sha256` of this value) to seal vocky's bearer token into the httpOnly cookie. Use a long random string, e.g. `openssl rand -base64 32`. |

**Rotating `SESSION_SECRET` invalidates every live session** — every user is forced to sign in again. That is by design (it is the key that opens existing cookies), but it makes rotation a deliberate, user-visible operation rather than a silent config change.

The app holds **no database** of its own and needs no DB/Redis credentials: it is a stateless BFF client of the vocky API. Its only persistent state is the sealed cookie in the user's browser.

## Build Output

`next.config.ts` sets `output: "standalone"`, so `pnpm build` emits a lean traced server at `.next/standalone/server.js` — this is exactly what `web/Dockerfile` copies into its runtime stage. It is **build-only** — `next dev` and `next start` ignore it, so local dev is unaffected.

The config ships the generic, everywhere-safe security headers (`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-Frame-Options: DENY`) and, as of **P6**, a **production-gated Content-Security-Policy**. **HSTS is not set by the app** — it lives at the edge vhost, together with an *additive* `upgrade-insecure-requests` CSP. See `security.md` for the directive string and the app/edge split.

### `NEXT_PUBLIC_APP_URL` — the single origin knob (P6)

`src/content/site.ts` reads `process.env.NEXT_PUBLIC_APP_URL` (blank → `http://127.0.0.1:3030`). That one value drives `metadataBase`, the canonical/OpenGraph URLs, `robots.txt`'s `host` + `sitemap`, and the sitemap `loc`.

It is **inlined at build time, not read at runtime** — a build that forgets it bakes the localhost origin into the image. Three places therefore have to agree:

- `web/.env.example` documents it (blank locally).
- `web/Dockerfile` declares `ARG NEXT_PUBLIC_APP_URL` and **asserts it is non-empty before `next build`**, so a mis-invoked image build fails loudly rather than shipping a wrong origin.
- `compose.prod.yml` passes it through the web service's `build.args` as the literal `https://vocky.hi2vi.com`.

Changing the public origin therefore requires an **image rebuild**, not an env edit.

### The metadata file-convention routes (P6)

`web/src/app/` ships the Next 16 metadata routes, all built from the existing round-01 brand (no new design round): `icon.svg` (static SVG favicon), `apple-icon.tsx` and `opengraph-image.tsx` (`next/og` `ImageResponse`, div-rebuilt Mark, **default ImageResponse font** — the variable Pretendard woff2 is deliberately *not* loaded, avoiding the Satori variable-font failure mode), `robots.ts`, `sitemap.ts`, and `manifest.ts`. `pnpm build` static-prerenders all six (`○` in the route summary); a Satori failure would fail the build, so the build *is* the check.

`robots.txt` disallows the authenticated + BFF surface (`/dashboard`, `/projects/`, `/feedback`, `/api/`); only `/` is in the sitemap. **Adding a public route means extending `sitemap.ts`.**

## Local Worker Gotcha

If captures accept (`202`) and the worker logs "Persisted" but records surface in **neither** `/app/usage` nor `/app/feedback`, the local docker `worker` is running a **stale image** — rebuilding only `app` is easy to do by accident. Fix:

```sh
docker compose up --build -d worker
```

Usage and feedback read empty locally until the worker image is current.

## The `vocky` CLI (P5)

The `vocky` CLI is the same Python package as the service, exposed through the `vocky = "vocky.cli:main"` console script. It talks to a running vocky API over HTTP; it needs no database, Redis, or service env of its own.

### Install / run

```sh
uv tool install .            # installs the `vocky` command on your PATH from this repo
uvx --from . vocky --help     # one-off run without installing
uv run vocky --help           # in-repo (development), no install
```

`typer` is a **direct** dependency (promoted from transitive in P5). **The package is not published anywhere** — today the install source is this repo; once the site is live the supported path is the hosted installer below (see also "CLI Distribution Model").

### The hosted installer — `web/public/install.sh` (P11)

P11 settled distribution as a **`curl | bash` installer**, at zero infra cost: `output: "standalone"` plus `web/Dockerfile`'s `COPY … /app/public ./public` plus the edge's bare `location / { proxy_pass … }` already serve `web/public/*`, and no `location` block shadows a root-level static path — so the file serves at `/install.sh` with **no route, MIME or vhost work**. `web/Dockerfile`, `web/next.config.ts` and `deploy/vocky.conf` were all left untouched.

```sh
curl -fsSL https://vocky.hi2vi.com/install.sh | bash    # once the site is live
```

The script is 61 lines and its shape is the contract, not a style choice:

- **`set -euo pipefail`, and every executable statement inside `main()`, with `main "$@"` as the literal last line.** `curl | bash` streams, so bash executes what it has received while the rest is still downloading; a flat script would run whatever prefix arrived. Wrapped in `main()`, a truncated download defines a function and hits EOF. **Verified at two cut points**: a mid-function truncation is a bash *parse error* (exit 2, no output — a truncated function body cannot finish parsing), and a truncation after the closing `}` but before the final line parses clean and exits **0 with no output**.
- **`uv` is bootstrapped via the official Astral installer only when absent**, and the script says so before doing it. The branch was genuinely exercised in validation (`env -i` with a minimal PATH), not skipped.
- **`uv tool install --reinstall "$INSTALL_TARGET"`**, so re-running the same line is the upgrade path. **No sudo, nothing system-wide** — everything lands under `$HOME/.local`. vocky's CLI is at the repo root, so there is **no `#subdirectory=` fragment**.
- Verification is **PATH-tolerant**: it re-exports `$HOME/.local/bin` and *warns* rather than dying if `vocky` is not yet on the current shell's PATH — the tool is installed either way. It closes by printing the next command and the two-export agent line.
- `VOCKY_INSTALL_TARGET` overrides the install source (used to verify against a local checkout). It is not a new attack surface: anyone who can set your environment before running the script can already run arbitrary commands.

**Two things it does not yet prove, both P12's.** The live `404 → 200` flip (`curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh` reads `404` today and must read `200` after the first deploy), and the real `git+https://` target: the installer resolves **GitHub `main`**, which is many commits behind local, so installing from it today would silently deliver a pre-P10 CLI with no org keys and no `vocky capture`. **P12 owns the `git push` and must install-and-check, not assert** — run the installer into a clean environment and assert `vocky --version` reads `0.2.0` or newer and `vocky capture --help` renders, which is exactly what P11 proved against the local target.

### `.github/workflows/ci.yml` — the repo's first push/PR gate (P11)

Before P11 the repo had exactly one workflow, `deploy-production.yml`, which is `workflow_dispatch`-only and has never run. `ci.yml` runs on **`push` to `main` and on every `pull_request`**, `permissions: contents: read`, with three jobs:

| Job | What it runs |
| --- | --- |
| **Skill Parity** | `python3 scripts/skill_parity.py` — the canonical/served `SKILL.md` byte gate |
| **Installer Syntax** | `bash -n web/public/install.sh` |
| **Web** | `pnpm install --frozen-lockfile` then `pnpm lint`, `pnpm typecheck`, `pnpm test` (Node 22, pnpm via corepack) |

**Two exclusions are deliberate and documented in the file itself:**

- **No `prettier --check`.** There are 14 pre-existing failures in files this workflow has no business rewriting (12 P4-era, plus two P11 files that differ only by `prettier-plugin-tailwindcss` class ordering). Gating on it would make the workflow red on its very first run for reasons unrelated to any change under review. Fixing them is a separate, deliberate sweep.
- **No `pytest`.** The suite needs a live Postgres and a bare GitHub runner has none. **P12 adds a Postgres-service job to this same file** — it was shaped so P12 appends a job rather than starting from nothing.

`scripts/skill_parity.py` is stdlib-only and **exit-code-is-the-contract** (matching `scripts/wait_for_health.py`), with a `make check-skill-parity` target; the gate was proven **red then green** (append a byte to the served copy → exit 1; restore → exit 0). `web/.prettierignore` excludes `public/` — required, since prettier's markdown reflow would otherwise silently break byte parity the first time anyone runs `pnpm format`. **The workflow has never executed on a GitHub runner** (the commits are unpushed); every job's command was verified locally instead.

### CLI Distribution Model (P6) — lean core + a `server` extra

P6 made `vocky` publishable and split its dependency surface so a CLI user does not install a database driver:

| Install | Gets |
| --- | --- |
| `pip install vocky` / `uvx vocky` | **lean CLI only** — `httpx` + `typer` (≈15 packages resolved) |
| `pip install "vocky[server]"` | the full self-hosted stack — adds alembic, greenlet, `mcp[cli]`, pydantic-settings, `psycopg[binary]`, redis, sqlalchemy, starlette, `uvicorn[standard]`, python-multipart, argon2-cffi |

The split works only because the CLI is **import-isolated**: `vocky/__init__.py` is trivial and `vocky.cli.*` imports nothing beyond typer / httpx / stdlib / the httpx-only `vocky.smoke`. Adding a server-side import to a CLI module silently breaks the lean install — a `uvx --from dist/*.whl vocky --version` check is the cheap guard.

**The CLI command modules are** `app.py`, `auth.py`, `client.py`, `config_store.py`, `context.py`, `feedback.py`, `projects.py`, and — new in **P11** — **`capture.py`**. `capture.py` respects the isolation rule the hard way: it **hand-builds the `/api/feedback` request body as a plain `dict`** rather than importing `vocky.capture`'s pydantic models, which would pull the server dependency set into the lean install. The isolation was re-verified for P11 by building a wheel and resolving it fresh: **15 packages**, no pydantic/sqlalchemy/uvicorn/psycopg.

Three packaging facts worth keeping:

- **`[tool.uv] default-extras` does not exist in uv 0.8.x** (it is rejected as an unknown `[tool.uv]` field). The idiom used instead is a **self-referencing dev group**: `"vocky[server]"` inside `[dependency-groups] dev` (a default group), so a plain `uv sync` still installs core + server + dev and the suite stays green. Dependency groups never enter built distribution metadata, so the wheel/sdist stay lean (`server` appears only as an `; extra == "server"` gate).
- **The sdist include-list is load-bearing — do not remove it.** Hatchling's default sdist selection ignores the nested `web/.gitignore`, so an unconstrained `uv build` sweeps in `web/node_modules` + the `.next` cache and produces a **~680 MB sdist** (unpublishable — PyPI's limit is 100 MB). `[tool.hatch.build.targets.sdist] include = ["/src/vocky", "/README.md", "/LICENSE"]` brings it to **79 KB**. The leading `/` anchoring matters: bare `README.md` / `LICENSE` globs otherwise match thousands of nested `node_modules` files.
- **The backend `Dockerfile` passes `--extra server` on both `uv sync` layers**, deterministically, rather than relying on any default-extras behavior. The server image's dependency set is unchanged from before the split.

`dist/` still holds P6's `vocky-0.1.0-py3-none-any.whl` (95 KB) + `vocky-0.1.0.tar.gz` (79 KB), with SPDX `License-Expression: MIT`, keywords, classifiers, and `[project.urls]` in the wheel `METADATA`. **Those artifacts are stale** — `pyproject.toml` is **`0.2.0`** as of P11 — and **nothing has been uploaded**; the PyPI name `vocky` was free (404) when P6 checked. **P11 chose the `curl | bash` installer over PyPI**, so the publish hand-off stays unexercised; if PyPI is ever revisited, rebuild first.

### Session store and config

The CLI keeps its state in a small JSON file, **not** in env only:

- **Location**: `~/.config/vocky/config.json` — XDG-aware (`$XDG_CONFIG_HOME/vocky` when set), overridable with the **`VOCKY_CONFIG_DIR`** env var (used for isolated / throwaway sessions, e.g. an agent running per-task).
- **Contents**: the account **session token** (opaque, 30-day TTL — the same token `/auth/*`/`/app/*` mint; *not* a `vk_` key) plus an optional stored **base URL**.
- **Permissions**: the directory is created `0700` and the file `0600`, so the on-disk session token is owner-only readable (see `security.md`).

### Base-URL resolution, and the `vk_` key (P11)

The API base URL resolves in this precedence: `--base-url` flag → `VOCKY_BASE_URL` env → stored `base_url` in the config → `http://127.0.0.1:8000` (local default). A `--password-stdin` flag on `signup`/`login` reads the password from one line of stdin so it never lands on argv — the headless-agent path.

**`VOCKY_API_TOKEN` (P11) resolves in exactly one tier: the env var, or nothing.** It carries the `vk_` ingest key that `vocky capture` sends, and its shape is deliberately unlike the base URL's:

- **No `--token` flag.** argv is world-readable via `ps` and lands in shell history — the same reasoning behind `--password-stdin`.
- **No config-store persistence.** `config_store` holds only the session `token` and `base_url`, and `clear_token()` pops only `"token"` — a persisted `vk_` key would silently survive `vocky logout`.
- Unset or blank fails before any HTTP call, with a message naming the variable and pointing at `vocky keys mint`.
- `capture` builds its client as `make_client(token=…, use_stored_token=False)`, so the session token and the `vk_` key **cannot cross**. `ApiClient.request` grew an `unauthorized_message` override for the same reason: a `401` from a `vk_`-keyed call must not tell the user to run `vocky login`.

## Production Deploy Kit (P6) — `vocky.hi2vi.com`

Everything in this section is **authored and unexecuted**. It mirrors the two sibling deployments on the same box: `~/projects/personal/knowledge` (`knowledge.hi2vi.com`, the same app shape) for the serving contract and edge vhost, and `~/projects/personal/hi2vi_web` for the image-tag rollback model and the CI chain.

### The box and the shared edge

- **Box:** `ssh oracle-cloud` = `opc@140.245.64.173`. vocky is a **co-tenant**, not the only thing on it.
- **Edge:** a standalone Compose project at `/home/opc/edge` (container `edge-nginx`, `nginx:1.27-alpine`) on the external `changple_shared_network`, with `conf.d/` and `certs/` bound read-only from the host. Co-tenant vhosts that must never be disturbed: `00-default.conf`, `changple5.conf`, `changple-web.conf`, `hi2vi.conf`, `knowledge.conf`.
- **Apply path for a vhost:** `scp deploy/vocky.conf` into `/home/opc/edge/conf.d/`, then `cd /home/opc/edge && ./validate.sh && ./deploy.sh` — an `nginx -t` gate plus a **graceful reload**. Never recreate the edge container.
- **TLS:** the wildcard `/home/opc/edge/certs/hi2vi.crt` (+ `.key`) already carries SANs `*.hi2vi.com, hi2vi.com`, so `vocky.hi2vi.com` needs **nothing provisioned**. Cloudflare is Full (Strict).
- **DNS:** an operator-added **proxied `vocky`** record on the `hi2vi.com` Cloudflare zone. Not yet created.

### Serving contract

The whole topology follows one rule: **no host ports.** Every service is `expose:`-only and is reached **by container name** over the pre-existing external `changple_shared_network`. Nothing about vocky is directly reachable from the internet except through the edge.

`compose.prod.yml` (repo root — **not** the local dev `docker-compose.yml`, which does publish host ports) defines five services with fixed `container_name`s:

| Service key | Container | Reached as | Notes |
| --- | --- | --- | --- |
| `postgres` | `vocky-postgres` | `vocky-postgres:5432` | `postgres:17`, `postgres-data` volume, `pg_isready` healthcheck |
| `redis` | `vocky-redis` | `vocky-redis:6379` | `redis:7-alpine`, `--appendonly yes`, `redis-data` volume |
| `api` | `vocky-api` | `vocky-api:8000` | root `Dockerfile`; `image: vocky-api:latest`; python-urllib `/healthz` healthcheck (`start_period: 60s`) |
| `worker` | `vocky-worker` | — (no port) | **reuses `image: vocky-api:latest` with no `build:`**, command `uv run --no-sync vocky-worker` |
| `web` | `vocky-web` | `vocky-web:3000` | `web/Dockerfile`; `image: vocky-web:latest`; node-fetch `/` healthcheck |

All five carry `restart: unless-stopped`; `depends_on: service_healthy` gates api and worker on postgres+redis and web on api. Named volumes: `postgres-data`, `redis-data`, and `attachments-data` — the last **shared by api and worker** (the worker writes uploaded attachment bytes, the api serves them) and it must survive every redeploy.

**There is no MCP container.** `/mcp` is a Starlette `Mount` **inside `vocky-api`**, so the edge routes `/mcp → vocky-api:8000` like any other api path. `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com` is set on the api service so the transport's DNS-rebinding allowlist accepts the public host.

> **The worker used to be the sharpest footgun here, and it is now closed by construction.** When the worker had its own `build: .`, a partial rebuild could leave it running stale code behind a fresh api. It now runs the *exact* tag `docker compose build` produces for the api, so one build freshens both. It has **no healthcheck by design** (no HTTP endpoint), so the deploy script gates it on container **state**, not health.

> **Clone the box to `/home/opc/vocky` — the path is load-bearing.** `deploy.sh`'s `dc()` pins **no `-p`**, so the Compose project name derives from the clone directory's basename. `/home/opc/vocky` → project `vocky` → volumes `vocky_postgres-data` / `vocky_redis-data` / `vocky_attachments-data`. A clone at any other path would silently orphan the datastore volumes on the next deploy. Container names are pinned and image tags explicit, so *only the directory name* matters for identity.

### Box secrets

`.env.prod.example` is the template for the box's gitignored `.env`. There is deliberately **no `env_file:` anywhere** in `compose.prod.yml`: each container receives only the vars listed under its own `environment:`, so the api's secrets are never injected into the web container and vice versa. Exactly **three** `${...}` interpolations exist, all generated on the box (`openssl rand -base64 32`):

| Secret | Consumed by |
| --- | --- |
| `POSTGRES_PASSWORD` | the postgres service, and baked into the api/worker `DATABASE_URL` |
| `SESSION_SECRET` | **web only** — rotating it logs every user out |
| `VOCKY_ADMIN_AUTH_TOKEN` | **api only** — guards `/admin/api/*` |

None has a `:-` default: a missing value must fail loudly on the box rather than silently fall back to something weak. `DATABASE_URL`, `REDIS_URL`, and `VOCKY_API_BASE_URL` are **committed literal container-name URLs**, not secrets, and do not belong in `.env`; `NEXT_PUBLIC_APP_URL` is a build arg, not an env var.

### The images

- **`web/Dockerfile`** — multi-stage `node:22-slim`. Build stage: `corepack prepare pnpm@10.28.2`, `pnpm install --frozen-lockfile`, the `NEXT_PUBLIC_APP_URL` assert, `pnpm build`. **It deliberately does not set `NODE_ENV=production` in the build stage** — pnpm would prune `typescript` / `tailwindcss` / `@tailwindcss/postcss` / `eslint-config-next` and the build would fail. Runtime stage: `NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0`, copies `.next/standalone` + `.next/static` + `public/`, `USER node`, `EXPOSE 3000`, a fetch-based `HEALTHCHECK`, `CMD ["node","server.js"]`. `web/public/` exists (holding only `.gitkeep`) purely so the runtime `COPY /app/public ./public` resolves — real assets are served by the `app/` file-convention routes. There is no `sharp` closure because the app uses no `next/image`.
- **Backend root `Dockerfile`** — unchanged by P6 apart from `--extra server`. Standard uv two-layer build, `CMD ["uv","run","--no-sync","vocky-server"]`. It runs as **root on purpose** (it writes the shared attachments volume; non-root would need volume-ownership plumbing). It bakes **no migration and no worker command** — the migration is run externally by `deploy.sh`, and the worker overrides the command in compose. Do not bake either into the image.

### Edge vhost — `deploy/vocky.conf`

The routing map, longest-prefix over the two container-name upstreams:

| Location | → | Notes |
| --- | --- | --- |
| `/api/auth/`, `/api/app/` | `vocky-web:3000` | the Next BFF (credential routes + the binary attachment proxy) — these beat `/api/` |
| `/api/` | `vocky-api:8000` | `vk_`-keyed capture + project read/manage (`/api/project/*` correctly falls here) |
| `/auth/`, `/app/` | `vocky-api:8000` | account auth + the session-authed control plane |
| `= /healthz` | `vocky-api:8000` | exact match; the CI smoke target |
| `/mcp` | `vocky-api:8000` | **SSE-safe**: `proxy_buffering off`, 3600s read/send timeouts |
| `/admin/` | **`return 404`** | not exposed at the edge — see `security.md` |
| `/` | `vocky-web:3000` | catch-all: the landing and every app page |

Other load-bearing properties: `:80` returns a server-level `301` to https; TLS terminates on the hi2vi wildcard cert; **Cloudflare real-IP restore** (the full v4+v6 `set_real_ip_from` list, byte-identical to `knowledge.conf`, plus `real_ip_header CF-Connecting-IP`); `client_max_body_size 12m`; and **Docker DNS re-resolution** — `resolver 127.0.0.11 valid=30s ipv6=off` with **variable** `proxy_pass` upstreams (`set $vocky_api vocky-api;`), so a recreated container's new IP is picked up without an nginx reload.

> **The `proxy_set_header` inheritance footgun.** nginx inherits a server-level `proxy_set_header` set into a `location` **only if that location sets none of its own** — the first per-location `proxy_set_header` drops the *entire* inherited set. `vocky.conf` therefore hoists `Host` / `X-Real-IP` / `X-Forwarded-For` / `X-Forwarded-Proto` / `proxy_http_version 1.1` / `Connection ""` to the server level and **every location sets none**. Adding a single per-location header would silently strip the rest for that route.

**Shared-edge house rules** (violating any breaks *every* co-tenant site): never `default_server`; no `listen [::]` (IPv6); **no `limit_req_zone`** — zone and location names are global across the whole `conf.d/` tree, so a duplicate fails `nginx -t` for all sites; always restore Cloudflare real IPs; always use the resolver + variable upstreams.

### Deploy and rollback runbook

`deploy/deploy.sh [git-ref]` (default `origin/main`), run from the box clone. **The ordering is load-bearing — do not reorder:**

1. Preflight (git / docker / compose v2; `compose.prod.yml`, `.git`, `.env` all present).
2. `git fetch --prune` + `git checkout REF` (a dirty **tracked** tree fails loudly under `set -e`).
3. Tag the live images `vocky-api:latest → :previous` and `vocky-web:latest → :previous` — the rollback points.
4. `up -d postgres redis`, gate both **healthy**.
5. `docker compose build` (freshens api **and** worker, since the worker reuses the api tag).
6. **Migrate before serving** — `alembic upgrade head` in a one-off container.
7. `up -d` — recreate api/worker/web on the new images against the already-migrated schema.
8. Health-gate: **api and web on `healthy`, worker on `running`** (two consecutive clean polls plus `.State.Restarting == false`, so a single `running` glimpse before a crash-loop cannot pass).

On a migration or gate failure it captures diagnostics and, if a `:previous` exists, flips both image tags back, `up -d --no-build`, and re-gates — distinguishing "rolled back and healthy" from "the rollback is also unhealthy". The **first** deploy has no `:previous`, leaves the stack up for inspection, and exits non-zero.

Two absolutes:

- **`COMPOSE_BAKE=false` is exported** — this host's Compose version panics on the bake build path (a CLI bug).
- **It never runs `down` or `down -v`** on any path. `postgres-data`, `redis-data`, and `attachments-data` survive every deploy and every rollback.

The migrate command takes the **service key `api`**, not the container name:

```sh
docker compose -f compose.prod.yml run --rm -T --no-deps --name vocky-migrate-$$ api \
  uv run --no-sync alembic upgrade head
```

`docker compose run` does not accept a `container_name` as a target ("no such service: vocky-api"). The one-off container inherits the api service's `environment:` block — including the interpolated `DATABASE_URL`, which `config.py` reads directly — and the shared network. `--name` sidesteps the pinned `container_name: vocky-api`. If a Compose version ever refuses `run` on a name-pinned service, `MIGRATE_VIA_DOCKER_RUN=1` switches to a plain `docker run --network changple_shared_network` fallback that rebuilds `DATABASE_URL` from `POSTGRES_PASSWORD`.

`deploy/rollback.sh` is the manual counterpart: verify both `vocky-*:previous` exist, retag `:previous → :latest`, `up -d --no-build`, re-gate. **It does not re-migrate** — that assumes additive migrations. A schema-incompatible revert is a git-ref redeploy (`deploy/deploy.sh <sha>`), not a rollback.

Env-overridable knobs on both scripts: `APP_DIR`, `COMPOSE_FILE`, `ENV_FILE`, `HEALTH_TRIES` (default 24), `HEALTH_INTERVAL` (default 5s).

### CI deploy path

`.github/workflows/deploy-production.yml` is **manual only** (`workflow_dispatch`), **main-guarded**, and **ancestor-verified** — it can only ever ship a commit that is already on `origin/main`. It runs `environment: production` (url `https://vocky.hi2vi.com`), `concurrency: {group: vocky-deploy, cancel-in-progress: false}`, `timeout-minutes: 90`, `permissions: contents: read`.

Three files, ported from hi2vi_web's proven chain:

1. **the workflow** — preflight guards `refs/heads/main` and emits `target_sha`; the deploy job `bash -n`s all three helper scripts (including `deploy/deploy.sh`), runs the transport, then smokes, then uploads artifacts `if: always()`.
2. **`deploy/github-actions-production-deploy.sh`** — runner transport: SSH to `opc@140.245.64.173` (temp key file at `umask 077`, `StrictHostKeyChecking=yes` with `UserKnownHostsFile`, optional passphrase via ssh-agent + askpass), a `TARGET_SHA` 40-hex assert, ship+run the on-box gate against `/home/opc/vocky`, scp artifacts back.
3. **`deploy/oracle-production-deploy-remote.sh`** — the on-box gate: refuse a dirty tracked tree, `git fetch --prune origin main`, `git merge-base --is-ancestor` the target against **fetched** origin/main, then hand off to `deploy/deploy.sh "$TARGET_SHA"` (which owns checkout, build, migrate, gate, and rollback — the CI adds no second copy of that logic).

**External smoke:** two endpoints through the edge, `https://vocky.hi2vi.com/healthz` (proves the api) **and** `https://vocky.hi2vi.com/` (proves the web), each retried 5×6s; the step fails if **either** never returns 200.

**Required GitHub repo secrets** on `leetusik/vocky` — `ORACLE_SSH_PRIVATE_KEY`, `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE`. It is the **same box** as hi2vi/knowledge, so the existing key material is reused. **None of the three is set yet.**

### Armed flip probes for P12's bring-up smoke (P11)

P11 could verify nothing against a live origin, so it left P12 falsifiable probes instead of assertions. All three flip on the first deploy:

```sh
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh   # 404 today -> must be 200
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/SKILL.md     # 404 today -> must be 200
```

plus the landing page carrying the install line. After `/SKILL.md` flips, the **served bytes must `cmp` clean** against `skills/vocky-feedback/SKILL.md`. Separately, P12 must run the **Cloudflare-not-a-barrier probe** live (it is unrunnable while the site is down — do not design around an unverified blocker), and must **install from the real `git+https://` target into a clean environment after pushing** rather than asserting the installer works.

### Known operational gaps carried into P12

- **`/auth/*` has no origin rate limit.** The public account-auth surface (`/auth/login`, `/auth/signup` — an unauthenticated password grant plus open signup) reaches `vocky-api` through the edge, but vocky has no server-side per-IP limiter (the sibling `knowledge` does), and the shared edge **forbids** `limit_req_zone`. At launch it relies on Cloudflare in front. Tracked as deferred job **D5**: add a Cloudflare rate rule and/or an in-process limiter in `src/vocky/auth_api.py`. Accepted for launch behind Cloudflare.
- **`VOCKY_ADMIN_AUTH_TOKEN` is a required box secret for a surface that is unreachable from outside.** The edge 404s `/admin/`, so `/admin/api/*` is internal-only, yet the api still requires the token to be configured. That is intentional defense in depth (a co-tenant on the shared network could otherwise reach `vocky-api:8000` directly), but whether the token stays mandatory is a P12 question.
- The **first** `deploy.sh` run hits the no-`:previous` branch for both images (expected — there is no rollback point yet), and the one-off migrate creates the schema from empty.
- **`.github/workflows/ci.yml` has never executed on a GitHub runner** (the commits are unpushed). Its first real run happens on P12's push, alongside the two exclusions it must close: the Postgres-backed `pytest` job, and a decision about the 14 `prettier --check` failures.
- **A cache policy for `/install.sh` and `/SKILL.md` was deliberately not decided** — round 02 explicitly left it as a bring-up question. Both are served straight off `web/public/` through the edge's `/` catch-all today.
