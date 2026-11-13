---
doc_id: operations
version: v0008
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: the recorded_by migration needs no operational change, and a local compose MCP env gap
previous: v0007_p13_feedback_email_alerts_are_live_on_the_box_vocky_smtp_password_is_the_fourth_fail-loud_box_secret_the_smtp_block_is_worker-only_and_the_changple5_smtp_account_is_reused_via_a_django-to-vocky_var_mapping
---

# Operations

## Status

This doc covers running the **web app** (`web/`, the Next.js frontend added in P4), installing/running the **`vocky` CLI** (added in P5), and — authored in **P6**, **executed and extended in P12** — the **production deployment** at `vocky.hi2vi.com`, which is **live**. P12 added the proven CI gate, the `/auth/*` rate-limit tunables, and the backup/log-cap/status artifacts. It is deliberately scoped: the **backend/service** local operational surface — the Compose-first self-hosted workflow, `make bootstrap` / `verify` / `compose-down`, and the full `DATABASE_URL` / `REDIS_URL` / `VOCKY_*` configuration surface — is documented in **`architecture.md` § Configuration Surface** and is not duplicated here.

**Server console-entry rename (P5).** The server's console script is now **`vocky-server`** (`vocky.main:main`) — the bare `vocky` name is the new user-facing CLI. Every self-host/run reference moved off `vocky` to `vocky-server`: the `Dockerfile` `CMD`, the `docker-compose.yml` app service `command`, and the README "Running The App Directly". (The `Makefile` was untouched — it starts the server via Compose, not a direct `uv run vocky`.) The worker entry (`vocky-worker`) and smoke entry (`vocky-smoke`) are unchanged.

> ### ✅ vocky is LIVE — `https://vocky.hi2vi.com`, since 2026-08-04 (P12)
>
> **P12 executed the bring-up P6 authored and never ran.** The entire deploy chain ran for the first time on 2026-08-04 and was **green end to end**: both images built on the box, **P10's 11-revision accounts-v2 migration chain applied cleanly on its first execution anywhere**, and the five-service health gate passed (`vocky-api` on poll 1, `vocky-web` on poll 8, `vocky-worker` stable-running). First deployed commit: **`6c16ac5`**.
>
> Verified live at bring-up: `/healthz` and `/` both 200; a **signup → session round-trip** (not just the two health probes); `/install.sh` and `/SKILL.md` both 200 with the served `SKILL.md` **byte-identical** (`cmp` clean) to `skills/vocky-feedback/SKILL.md`; a clean-container `curl … | bash` install delivering **vocky 0.2.0** from the real `git+https://` target; and every co-tenant vhost (`hi2vi.com`, `knowledge.hi2vi.com`, `changple.ai`, `miracle.changple.ai`) still 200 after the edge reload.
>
> The ordering **P6 → P10 → P11 → P12** paid off exactly as designed: P10's `UNIQUE(tenant_id, name)` constraint and three-phase `project_credentials.tenant_id` backfill landed against an **empty schema**, never as a live cutover on production data.
>
> **The `vocky` CLI is still not on PyPI, and will not be.** P6 made the package publishable; **P11 decided the channel is a `curl | bash` installer** (`web/public/install.sh`) and published nothing. `uv publish` stays an unexercised, operator-gated action. The hosted line `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` **now works** — it was proven end to end into a clean container at the bring-up.
>
> Read the "production" sections below as a description of something **running**. Two things below are still authored-not-applied and say so in place: the **backup/log/status artifacts** (`P12.S5` — authored and committed, not yet installed on the box) and the **restore drill** (documented, never rehearsed).

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

Expect **78/78 tests across 10 files** (the count as of P12; it was 56 at P4) and every real route reported as `ƒ (Dynamic)`. `next build` needs **no env** — env reads are lazy, never at module top level. As of **P12.S6** `pnpm format:check` is part of the CI gate too, so run it before pushing.

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

`typer` is a **direct** dependency (promoted from transitive in P5). **The package is not published anywhere** — the install source is this repo, and the supported end-user path is the hosted installer below, **live since P12** (see also "CLI Distribution Model").

### The hosted installer — `web/public/install.sh` (P11)

P11 settled distribution as a **`curl | bash` installer**, at zero infra cost: `output: "standalone"` plus `web/Dockerfile`'s `COPY … /app/public ./public` plus the edge's bare `location / { proxy_pass … }` already serve `web/public/*`, and no `location` block shadows a root-level static path — so the file serves at `/install.sh` with **no route, MIME or vhost work**. `web/Dockerfile`, `web/next.config.ts` and the edge vhost were all left untouched. **P12's bring-up confirmed this empirically** — the file served 200 on the first deploy with zero serving work.

```sh
curl -fsSL https://vocky.hi2vi.com/install.sh | bash    # live since 2026-08-04
```

The script is 61 lines and its shape is the contract, not a style choice:

- **`set -euo pipefail`, and every executable statement inside `main()`, with `main "$@"` as the literal last line.** `curl | bash` streams, so bash executes what it has received while the rest is still downloading; a flat script would run whatever prefix arrived. Wrapped in `main()`, a truncated download defines a function and hits EOF. **Verified at two cut points**: a mid-function truncation is a bash *parse error* (exit 2, no output — a truncated function body cannot finish parsing), and a truncation after the closing `}` but before the final line parses clean and exits **0 with no output**.
- **`uv` is bootstrapped via the official Astral installer only when absent**, and the script says so before doing it. The branch was genuinely exercised in validation (`env -i` with a minimal PATH), not skipped.
- **`uv tool install --reinstall "$INSTALL_TARGET"`**, so re-running the same line is the upgrade path. **No sudo, nothing system-wide** — everything lands under `$HOME/.local`. vocky's CLI is at the repo root, so there is **no `#subdirectory=` fragment**.
- Verification is **PATH-tolerant**: it re-exports `$HOME/.local/bin` and *warns* rather than dying if `vocky` is not yet on the current shell's PATH — the tool is installed either way. It closes by printing the next command and the two-export agent line.
- `VOCKY_INSTALL_TARGET` overrides the install source (used to verify against a local checkout). It is not a new attack surface: anyone who can set your environment before running the script can already run arbitrary commands.

**Both things P11 could not prove are now proven (P12).** `/install.sh` flipped `404 → 200` on the first deploy, and the real `git+https://` target was exercised **install-and-check, not asserted**: in a clean `buildpack-deps:bookworm-scm` container, `curl -fsSL … | bash` bootstrapped uv, built **vocky 0.2.0** from `git+https://github.com/leetusik/vocky@6c16ac5` (exactly `origin/main`), installed 4 executables, and both `vocky --version` and `vocky capture --help` rendered.

**The installer resolves GitHub `main`, so the pushed SHA is the product.** A local commit that has not been pushed is not installable — the pre-launch hazard (installing a pre-P10 CLI with no org keys and no `vocky capture`) recurs any time `main` is ahead of `origin/main`. Push before telling anyone to install.

### `.github/workflows/ci.yml` — the push/PR gate (P11, completed by P12.S6)

Before P11 the repo had exactly one workflow, `deploy-production.yml`, which is `workflow_dispatch`-only. `ci.yml` runs on **`push` to `main` and on every `pull_request`**, `permissions: contents: read`. **P12.S6 closed both of P11's deliberate exclusions by extending this same file** (never a second workflow), so it now has **four** jobs:

| Job | What it runs |
| --- | --- |
| **Skill Parity** | `python3 scripts/skill_parity.py` — the canonical/served `SKILL.md` byte gate |
| **Installer Syntax** | `bash -n web/public/install.sh` |
| **Web** | `pnpm install --frozen-lockfile` then `pnpm lint`, `pnpm typecheck`, `pnpm test`, and — new in P12 — **`pnpm format:check`** (Node 22, pnpm via corepack). Appended as a step to the existing job, so there is no second install. |
| **Python Tests (Postgres)** *(new in P12)* | a `postgres:17` **service container** (`POSTGRES_DB`/`USER`/`PASSWORD` all `vocky`), health-gated on `pg_isready` (`10s`/`5s`/`5`); `uv sync --frozen` via `astral-sh/setup-uv@v7`, then `uv run --no-sync pytest`; `timeout-minutes: 20` |

**The pytest job's env contract is explicit, not derived** — get it wrong and it fails as a pydantic `ValidationError` at import, not as a clean test failure (`config.py` gives `DATABASE_URL` no default):

```yaml
DATABASE_URL:      postgresql+psycopg://vocky:vocky@localhost:5432/vocky
TEST_DATABASE_URL: postgresql+psycopg://vocky:vocky@localhost:5432/vocky_test
```

Port **5432**, not this workspace's local `55432` publish port — a GitHub-hosted service container maps differently. The job sets **no `working-directory`**: `conftest.py` runs `alembic upgrade head` through a relative `alembic.ini` and must start from the repo root. Redis is **not** needed (`fakeredis` is a dev dependency), and a plain `uv sync` gives the full server dependency set because the dev group self-references `vocky[server]` — no `--extra server` flag.

**Neither exclusion survives.** The 14 pre-existing `prettier --check` failures were swept to zero by **P12.S2** *before* the gate was turned on, which is the only order that works. `web/.prettierignore` still excludes `public/` — required, since prettier's markdown reflow would otherwise silently break the served `SKILL.md` byte parity the first time anyone runs `pnpm format`.

**This gate has actually executed.** Its first-ever runner run (push `6c16ac5`, run `30873072664`, triggered by P12's production push) went **green in 53 seconds** — including the new Postgres-backed suite and the format check — with zero iteration needed. `scripts/skill_parity.py` is stdlib-only and **exit-code-is-the-contract** (matching `scripts/wait_for_health.py`), with a `make check-skill-parity` target; the gate was proven **red then green** (append a byte to the served copy → exit 1; restore → exit 0).

**No Python lint step runs in CI.** `ruff check` is clean on the files recent slices touched, but ~34 pre-existing findings in unrelated files mean it is not gated — turning it on needs its own sweep first, exactly as prettier did.

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

## Production Deploy Kit (P6, executed by P12) — `vocky.hi2vi.com`

Everything in this section **has now run in production** (first deploy `6c16ac5`, 2026-08-04). It mirrors the two sibling deployments on the same box: `~/projects/personal/knowledge` (`knowledge.hi2vi.com`, the same app shape) for the serving contract and edge vhost, and `~/projects/personal/hi2vi_web` for the image-tag rollback model and the CI chain.

> **The box was not empty when P12 arrived, and that nearly cost data.** An abandoned **dev**-compose vocky stack from May was still running at `/home/opc/vocky` — same directory basename, therefore the **same Compose project name and the same `vocky_postgres-data` / `vocky_redis-data` volume names** the prod file would use. A naive first deploy would have run P10's accounts-v2 migration against that May database instead of an empty schema. The operator chose dump-then-wipe: `pg_dump` → `/home/opc/vocky-preP12-db-2026-08-04.sql` (4 feedback rows), the old env → `…-env-2026-08-04.bak`, `docker compose down` (**never `down -v`**), then an explicit `docker volume rm` of both volumes, and the stray `docker-compose.override.yml` moved aside so no stray `docker compose up` can resurrect a dev stack under the prod project name. **Check what is already running under that project name before any first deploy on a shared box.**

### The box and the shared edge

- **Box:** `ssh oracle-cloud` = `opc@140.245.64.173`. vocky is a **co-tenant**, not the only thing on it.
- **Edge:** a standalone Compose project at `/home/opc/edge` (container `edge-nginx`, `nginx:1.27-alpine`) on the external `changple_shared_network`, with `conf.d/` and `certs/` bound read-only from the host. Co-tenant vhosts that must never be disturbed: `00-default.conf`, `changple5.conf`, `changple-web.conf`, `hi2vi.conf`, `knowledge.conf`. (The changple vhosts serve **`changple.ai` / `miracle.changple.ai`** — not `changple5.com`, which is not a served hostname.)
- **Apply path for a vhost — dispatch the edge repo's `edge-deploy` workflow. Never `scp`.** `/home/opc/edge/` is a plain rsync target, **not** the source of truth: the **`leetusik/edge` repo** is (`~/projects/personal/edge`), and it tracks the whole `conf.d/` tree plus `compose.yml`, `validate.sh`, `stage.sh`, `deploy.sh`, `cutover.sh`. Its workflow runs validate (dummy certs + `compose config -q` + a throwaway-container `nginx -t` over the **whole tree**) → stage (rsync, deliberately **without `--delete`**) → deploy (graceful reload). Copying a file onto the box by hand bypasses that repo and leaves an untracked vhost on the VM. **Never recreate the edge container.**
- **TLS:** the wildcard `/home/opc/edge/certs/hi2vi.crt` (+ `.key`) already carries SANs `*.hi2vi.com, hi2vi.com`, so `vocky.hi2vi.com` needed **nothing provisioned**. Cloudflare is Full (Strict).
- **DNS:** a **proxied `vocky`** record on the `hi2vi.com` Cloudflare zone — **created at the P12 bring-up**. Useful intermediate state to recognise: before the vhost existed, `https://vocky.hi2vi.com` returned **526** (Cloudflare reached the origin, but `00-default.conf` presents no `*.hi2vi.com` cert). That is the correct pre-vhost reading, not a DNS fault.

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

**There is no MCP container.** `/mcp` is a Starlette `Mount` **inside `vocky-api`**, so the edge routes `/mcp → vocky-api:8000` like any other api path. `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com` is set on the api service so the transport's DNS-rebinding allowlist accepts the public host — **verified live at P14**: a full authenticated MCP session from that `Host` succeeds, and without the variable the identical request answers `421 Invalid Host header` (not `401` — the key is never examined). `VOCKY_MCP_ALLOWED_ORIGINS` is deliberately **unset and should stay unset**: the transport only checks `Origin` when the header is present, and non-browser MCP clients send none.

> **Local-stack gap (P14, not a production issue).** The local `docker-compose.yml` does **not** forward `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS` to the `app` service even when `.env` sets them, so `/mcp` reached over a local stack's external hostname `421`s while REST is unaffected (the allowlist guards `/mcp` only). Production is fine. Testing a public-host MCP session locally therefore needs the variables passed to the process directly; the compose gap is a candidate for a local-dev-parity follow-up.

> **The worker used to be the sharpest footgun here, and it is now closed by construction.** When the worker had its own `build: .`, a partial rebuild could leave it running stale code behind a fresh api. It now runs the *exact* tag `docker compose build` produces for the api, so one build freshens both. It has **no healthcheck by design** (no HTTP endpoint), so the deploy script gates it on container **state**, not health.

> **Clone the box to `/home/opc/vocky` — the path is load-bearing.** `deploy.sh`'s `dc()` pins **no `-p`**, so the Compose project name derives from the clone directory's basename. `/home/opc/vocky` → project `vocky` → volumes `vocky_postgres-data` / `vocky_redis-data` / `vocky_attachments-data`. A clone at any other path would silently orphan the datastore volumes on the next deploy. Container names are pinned and image tags explicit, so *only the directory name* matters for identity.

### Box secrets

`.env.prod.example` is the template for the box's gitignored `.env`. There is deliberately **no `env_file:` anywhere** in `compose.prod.yml`: each container receives only the vars listed under its own `environment:`, so the api's secrets are never injected into the web container and vice versa. **Four** secrets are `${...}` interpolated; the first three are generated on the box (`openssl rand -base64 32`), the fourth is copied from an existing SMTP account:

| Secret | Consumed by |
| --- | --- |
| `POSTGRES_PASSWORD` | the postgres service, and baked into the api/worker `DATABASE_URL` |
| `SESSION_SECRET` | **web only** — rotating it logs every user out |
| `VOCKY_ADMIN_AUTH_TOKEN` | **api only** — guards `/admin/api/*`, and **still mandatory** (P12.S1 kept `/admin/api/*`, fail-closed) |
| `VOCKY_SMTP_PASSWORD` (P13) | **worker only** — the SMTP account password used to send feedback alert email |

**All four now fail loudly, and only since P12.S1** (P13 for the fourth) — every interpolation site uses the `${VAR:?message}` form (`POSTGRES_PASSWORD` at all three sites: the postgres service plus the `DATABASE_URL` built in both api and worker), so `docker compose` **aborts** with an actionable message rather than substituting a blank. Before P12 this doc's "a missing value must fail loudly" claim was aspirational: a plain `${VAR}` makes Compose substitute an **empty string with a warning**. `POSTGRES_PASSWORD` failed only by the `postgres:17` image's own refusal to initialize blank, and **a blank `SESSION_SECRET` passed `deploy.sh`'s health gate entirely** — the web healthcheck fetches `/`, the static landing, which never reads it — surfacing only when a real user tried to log in.

> **Testing the fail-loud behaviour: `env -u VAR` proves nothing.** `docker compose` auto-reads the project directory's `.env`, so unsetting a shell variable silently false-passes (exit 0) while the file supplies the value. This trap bit twice in P12 — once locally, once on the box. Test with an explicit `--env-file` pointing at a partial or empty file instead: `docker compose --env-file /tmp/partial.env -f compose.prod.yml config -q` → **exit 1**, *"POSTGRES_PASSWORD is required — set it in the box .env"*. The same trap applies to P13's `VOCKY_SMTP_*` guards; an `env -u` test of those only proves anything while the project `.env` happens to carry no `VOCKY_SMTP_*` line at all (`grep -c VOCKY_SMTP .env` → `0`).

`DATABASE_URL`, `REDIS_URL`, and `VOCKY_API_BASE_URL` are **committed literal container-name URLs**, not secrets, and do not belong in `.env`; `NEXT_PUBLIC_APP_URL` is a build arg, not an env var.

### SMTP feedback alerts (P13) — the box block

Since **P13** the worker emails the owning org's owner one plain-text alert per persisted feedback event. This is **live on the box** (verified 2026-08-04 with a real capture and a received email). The mechanism is in `architecture.md` / `backend.md`; what follows is the operations surface.

**The five vars, and their interpolation forms.** All five live on the **`worker` service's `environment:` block only**, in both compose files — `api` and `web` never receive them, matching the per-service isolation invariant above (the worker is the sole sender).

| Var | `compose.prod.yml` | `docker-compose.yml` (dev) | Meaning |
| --- | --- | --- | --- |
| `VOCKY_SMTP_HOST` | `${VAR:?…}` — required | `${VAR:-}` | SMTP server hostname. Required but **not secret** |
| `VOCKY_SMTP_USER` | `${VAR:?…}` — required | `${VAR:-}` | SMTP account username. Required but **not secret** |
| `VOCKY_SMTP_PASSWORD` | `${VAR:?…}` — required | `${VAR:-}` | the **secret** (see the box-secrets table above) |
| `VOCKY_SMTP_PORT` | `${VAR:-587}` | `${VAR:-587}` | `465` selects implicit SSL; anything else uses STARTTLS |
| `VOCKY_SMTP_FROM` | `${VAR:-}` | `${VAR:-}` | From address; **blank falls back to `VOCKY_SMTP_USER`** |

**Why prod is `:?` and dev is `:-`.** Production *intends* alerts on, so a missing host/user/password **aborts `docker compose` itself** rather than silently shipping a stack whose alerts are quietly off — the same fail-loud pattern as the other three secrets. Dev mirrors all five in the empty-default form so a local stack with no SMTP configured still starts and simply runs with alerts disabled (`Settings.smtp_configured` is false). **Env-first, deploy-second on the box**: once S4's guards are on `origin/main`, `deploy/deploy.sh` will abort at interpolation until the three required vars are in `.env`.

**`deploy/deploy.sh` needed no change and must not gain one.** It only asserts that `.env` exists; compose's `${VAR:?}` interpolation is the **single** enforcement point for every box secret. Do not add a second one.

**Bring-up: reusing changple5's SMTP account.** vocky borrows the SMTP account changple5 already sends with on the same box. changple5 is Django, so its env speaks Django's names:

| Django name (changple5) | vocky name (`/home/opc/vocky/.env`) |
| --- | --- |
| `EMAIL_HOST` | `VOCKY_SMTP_HOST` (required) |
| `EMAIL_PORT` | `VOCKY_SMTP_PORT` (optional, default 587) |
| `EMAIL_HOST_USER` | `VOCKY_SMTP_USER` (required) |
| `EMAIL_HOST_PASSWORD` | `VOCKY_SMTP_PASSWORD` (required, the secret) |
| `DEFAULT_FROM_EMAIL` | `VOCKY_SMTP_FROM` (optional, falls back to the user) |

Discovery on the box, most robust first: **read the running container's actual environment** — `docker ps --format 'table {{.Names}}\t{{.Image}}' | grep -i changple`, then `docker exec <changple5-container> env | grep -iE 'email|smtp'`. This is what worked in practice (the values were read off `changple5-celery_beat-1`); grepping a source `.env` or `settings*.py` under the changple5 checkout is a fallback that depends on where the clone lives. Then edit the five keys **in place** in `/home/opc/vocky/.env` — `grep -c VOCKY_SMTP /home/opc/vocky/.env` first, since a duplicate key in a `.env` is read inconsistently by different tools — sanity-check with `docker compose -f compose.prod.yml config --quiet`, and run `deploy/deploy.sh` (it recreates the worker unconditionally, so no separate restart is needed).

**The live endpoint (non-secret, as deployed):** host `mail.privateemail.com`, port `587` (STARTTLS), user `hi@hi2vi.com`, From `창플 <hi@hi2vi.com>`. The password lives **only** in the box's gitignored `.env` and in changple5's own env — never in this repo.

**Verifying an alert live.** Capture one real feedback event (`VOCKY_EXTERNAL_BASE_URL=https://vocky.hi2vi.com make external-smoke` is the easiest full round trip, but it creates a throwaway account — so its alert goes to *that* throwaway owner; use a real project of your own if you want the mail in your own inbox). Then check both:

1. `docker logs vocky-worker --since 5m` — the job persisted, and **no** `Feedback alert failed` line (that string is the worker's `logger.exception` message and the only in-band signal that a send failed).
2. The **org owner's** account inbox — one plain-text mail, `From:` the configured `VOCKY_SMTP_FROM` (or the user fallback).

**Triage, by failure shape:**

- **`docker compose` / `deploy.sh` aborts with a `:?` message** → one of host/user/password is missing or blank in `.env`. Watch for a stray duplicate key further down the file shadowing the one you edited.
- **Worker logs `Feedback alert failed`** → credentials or TLS mismatch. Most common fix is the other port: `465` (implicit SSL) vs `587` (STARTTLS), then recreate just the worker (`docker compose -f compose.prod.yml up -d worker`).
- **No error in the log, but no email** → check spam first; then check that the effective From is an identity the SMTP account is authorized to send *as* — some providers accept the SMTP transaction and drop the message.
- **`No owner email for project …` warning** → the project's tenant has no `role='owner'` member. The alert is skipped by design; the feedback row is unaffected.

**A failed alert is lost, by design** — there is no retry and no notify DLQ, so the worker log is the only record. The feedback itself is always durably stored and readable in the app; alerting is strictly best-effort. See `architecture.md` for the reasoning.

### Optional non-secret tunables (P12.S3)

The `/auth/*` rate limiter reads two settings, both with safe defaults, both documented (commented out) in `.env.example` and **deliberately not in `.env.prod.example`** — the box `.env` needs no entry for either:

| Var | Default | Meaning |
| --- | --- | --- |
| `VOCKY_AUTH_RATE_LIMIT` | `20` | requests per window, per `(client IP, route)`. **`<= 0` disables the limiter entirely.** |
| `VOCKY_AUTH_RATE_WINDOW_S` | `900` | window length in seconds (15 min) |

**Operational invariant: `vocky-api` must stay a single uvicorn worker.** The limiter's state is a module-global dict in one process. `vocky.main` runs a single uvicorn process today (no `workers=N`, no gunicorn, and `compose.prod.yml` sets no `command:` or `deploy.replicas` override for `api`); adding a second worker would silently **divide** the effective rate limit and give each process its own buckets. Setting `VOCKY_AUTH_RATE_LIMIT=0` temporarily is the supported escape hatch for a deliberate stress or smoke pass — restore it afterwards.

### The images

- **`web/Dockerfile`** — multi-stage `node:22-slim`. Build stage: `corepack prepare pnpm@10.28.2`, `pnpm install --frozen-lockfile`, the `NEXT_PUBLIC_APP_URL` assert, `pnpm build`. **It deliberately does not set `NODE_ENV=production` in the build stage** — pnpm would prune `typescript` / `tailwindcss` / `@tailwindcss/postcss` / `eslint-config-next` and the build would fail. Runtime stage: `NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0`, copies `.next/standalone` + `.next/static` + `public/`, `USER node`, `EXPOSE 3000`, a fetch-based `HEALTHCHECK`, `CMD ["node","server.js"]`. `web/public/` exists (holding only `.gitkeep`) purely so the runtime `COPY /app/public ./public` resolves — real assets are served by the `app/` file-convention routes. There is no `sharp` closure because the app uses no `next/image`.
- **Backend root `Dockerfile`** — unchanged by P6 apart from `--extra server`. Standard uv two-layer build, `CMD ["uv","run","--no-sync","vocky-server"]`. It runs as **root on purpose** (it writes the shared attachments volume; non-root would need volume-ownership plumbing). It bakes **no migration and no worker command** — the migration is run externally by `deploy.sh`, and the worker overrides the command in compose. Do not bake either into the image.

### Edge vhost — `edge/conf.d/vocky.conf`, **in the `leetusik/edge` repo**

> **The vhost no longer lives in this repo (P12.S4).** `deploy/vocky.conf` is retired; this repo keeps **`deploy/vocky.conf.md`** as a pointer. The canonical file is `edge/conf.d/vocky.conf` in the **`leetusik/edge`** repo, which owns the whole shared-edge tree and reached the box through its own `edge-deploy` workflow (first run green, 2026-08-04). **Vhost changes are made there, not here** — and the behaviour described below is unchanged, only the file's home moved.

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

**That first-deploy branch has now been exercised** (2026-08-04): with no prior `vocky-api:latest` / `vocky-web:latest` on the box, the script took the no-`:previous` path exactly as designed and completed green. **Every deploy from here on has real `:previous` rollback points**, so `deploy/rollback.sh` is armed for the first time.

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

**Step 6-before-step-7 is what makes an additive schema change need no operational work at all.** P14's `recorded_by` migration (`20260805_1200`) is the worked example: migrate **before** deploying code that reads the column — old-code + new-schema is safe (the old code never selects it), new-code + old-schema `500`s. Because the column is nullable with no backfill and its index is a btree over an all-`NULL` column, the migration is **instant and non-blocking**, so there is **no lock window to schedule** and no maintenance announcement to make. `deploy.sh` already runs migrate-then-recreate, so **P14 required no change to any deploy artifact**, and `rollback.sh`'s deliberate no-re-migrate stance is safe for it: reverting to pre-P14 images over the P14 schema simply leaves the column unread. Treat that as the template for additive migrations; a *non*-additive one is the case where the rollback script stops being a valid path.

Env-overridable knobs on both scripts: `APP_DIR`, `COMPOSE_FILE`, `ENV_FILE`, `HEALTH_TRIES` (default 24), `HEALTH_INTERVAL` (default 5s).

### CI deploy path

`.github/workflows/deploy-production.yml` is **manual only** (`workflow_dispatch`), **main-guarded**, and **ancestor-verified** — it can only ever ship a commit that is already on `origin/main`. It runs `environment: production` (url `https://vocky.hi2vi.com`), `concurrency: {group: vocky-deploy, cancel-in-progress: false}`, `timeout-minutes: 90`, `permissions: contents: read`.

Three files, ported from hi2vi_web's proven chain:

1. **the workflow** — preflight guards `refs/heads/main` and emits `target_sha`; the deploy job `bash -n`s all three helper scripts (including `deploy/deploy.sh`), runs the transport, then smokes, then uploads artifacts `if: always()`.
2. **`deploy/github-actions-production-deploy.sh`** — runner transport: SSH to `opc@140.245.64.173` (temp key file at `umask 077`, `StrictHostKeyChecking=yes` with `UserKnownHostsFile`, optional passphrase via ssh-agent + askpass), a `TARGET_SHA` 40-hex assert, ship+run the on-box gate against `/home/opc/vocky`, scp artifacts back.
3. **`deploy/oracle-production-deploy-remote.sh`** — the on-box gate: refuse a dirty tracked tree, `git fetch --prune origin main`, `git merge-base --is-ancestor` the target against **fetched** origin/main, then hand off to `deploy/deploy.sh "$TARGET_SHA"` (which owns checkout, build, migrate, gate, and rollback — the CI adds no second copy of that logic).

**External smoke:** two endpoints through the edge, `https://vocky.hi2vi.com/healthz` (proves the api) **and** `https://vocky.hi2vi.com/` (proves the web), each retried 5×6s; the step fails if **either** never returns 200.

**GitHub repo secrets** on `leetusik/vocky` — `ORACLE_SSH_PRIVATE_KEY` and `ORACLE_SSH_KNOWN_HOSTS` are **set** (P12, reusing the hi2vi/knowledge key material for the same box). **`ORACLE_SSH_PASSPHRASE` was deliberately not created** — the key is unencrypted and the transport script does not require it.

**`deploy-production.yml` itself has still never run.** P12's first deploy was executed manually on the box (`deploy/deploy.sh`), which exercises the same underlying script the workflow hands off to, but not the runner transport. Its first `workflow_dispatch` is a natural follow-up, not a P12 requirement.

### The bring-up probes — all flipped (P11 armed them, P12 ran them)

P11 could verify nothing against a live origin, so it left falsifiable probes instead of assertions. Every one of them flipped on the first deploy, and they remain the standing liveness check:

```sh
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/healthz     # 200
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/            # 200
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh  # 404 -> 200
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/SKILL.md    # 404 -> 200
```

The served `/SKILL.md` is **byte-identical** (`cmp` clean) to `skills/vocky-feedback/SKILL.md`, re-verified at this review.

- **Cloudflare is not a barrier — proven live, three ways in one pass**: it served a shell script to `curl` with the correct `application/x-sh` and no challenge, passed a non-browser JSON POST to the auth surface, and did not interfere with `uv`'s git fetches. The same empirical result the sibling `knowledge` got. Stop designing around it.
- **Cache policy for `/install.sh` and `/SKILL.md`: answered — deliberately uncached.** Measured live: `cache-control: public, max-age=0`, `cf-cache-status: DYNAMIC`. Every install gets fresh bytes, so there is no stale-installer window after a push. That is the right default at current traffic; revisit only if these paths ever see real volume.
- **The BFF origin gate is a trap for every future probe.** Origin-less non-browser POSTs to `/api/auth/*` return **403 by design** — `web/src/lib/session.ts`'s CSRF second layer rejects a request with no `Origin`/`Sec-Fetch-Site`. Real browsers always send them. When curling that surface, pass `Origin: https://vocky.hi2vi.com` explicitly or you will read a false failure.

### Backups, log caps and on-box status (P12.S5)

> **Authored and committed, not yet applied on the box.** The artifacts below landed in the repo *after* the deployed commit `6c16ac5`. Until the box pulls a newer commit and the runbook below is run, production has **no scheduled backup and uncapped container logs**. This is the phase's one deliberate authored-not-applied item.

- **`deploy/backup.sh`** — nightly `pg_dump` + gzip of the `vocky` database into `/home/opc/backups/vocky/db/`, plus an `alpine`-throwaway-container tar of the `vocky_attachments-data` volume into `/home/opc/backups/vocky/attachments/`. **Redis is deliberately not backed up** (it is a queue, not a source of truth). **14-day retention** on both directories, and it prints what it pruned; the prune paths are hard-coded under `$BACKUP_ROOT` and cannot delete outside `/home/opc/backups/vocky/`.
- **Cron line** (daily 04:10 box time):
  ```
  10 4 * * * /home/opc/vocky/deploy/backup.sh >> /home/opc/backups/vocky/backup.log 2>&1
  ```
- **`deploy/restore.md`** — the restore drill: verify a `.sql.gz` in a **scratch database first**, then the real database cutover (stop `api`/`worker`, drop/recreate, restore, `alembic upgrade head` sanity check, bring the stack back and re-gate), then the attachments-volume cutover, which is independent of the database restore. It also states what it does **not** protect against. **It has never been rehearsed** and says so in its own header — treat it as a starting draft to be corrected by the first real run, ideally in a quiet window rather than during an incident.
- **`deploy/status.sh`** — the basic on-box read: `compose ps` + health + `df -h` + `docker system df -v` + per-volume sizes + the last 20 api/worker log lines. Read-only, and explicitly *basic metrics*, not monitoring infrastructure.
- **Log caps** — `compose.prod.yml` carries an `x-logging: &default-logging` anchor (`json-file`, `max-size: 10m`, `max-file: 3`) referenced by **all five** services; unbounded `json-file` logs were the box's real disk risk.

> **The log-cap gotcha, worth reading twice.** App services (`api`, `web`, `worker`) pick the cap up on the next ordinary `deploy.sh` run, because that recreates them. **The datastores (`postgres`, `redis`) are NOT recreated by an ordinary app deploy**, so they keep running uncapped until someone deliberately runs `docker compose -f compose.prod.yml up -d postgres redis --force-recreate`. "The caps apply at the next deploy" is false for exactly the two containers that run longest.

**Applying it (operator, on the box):** push → `cd /home/opc/vocky && git pull` → `./deploy/deploy.sh` → the datastore `--force-recreate` above → install the cron line → optionally run `deploy/backup.sh` once by hand and check `deploy/status.sh`.

### Remaining operational gaps (post-P12)

- **The restore drill is unrehearsed** (above) — the single largest remaining operational risk, and it is an operator action.
- **Backups do not survive box loss.** They are on-box dated files with 14-day retention. Off-box (object-storage) replication needs a credential the operator must provision, and was deliberately not decided in P12.
- **The `/auth/*` limiter is in-process only.** It is versioned and tested (P12.S3), but it is per-process memory: it resets on restart and depends on the single-worker invariant above. A Cloudflare rate-limiting rule as an outer, unversioned layer remains available at operator discretion — nothing depends on it.
- **No metrics or log export off the box.** `deploy/status.sh` is a manual read, not monitoring; nothing alerts.
- **`deploy-production.yml` has never been dispatched** (above).
- **P12 loose ends the operator may clear at leisure**: the throwaway production account `p12-smoke-20260804@example.com` created by the launch smoke, and the Gate-4 keepsakes `/home/opc/vocky-preP12-*.{sql,bak}` plus the quarantined `docker-compose.override.yml.bak`.
