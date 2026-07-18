---
doc_id: operations
version: v0003
created_at: 2026-07-18T11:15:51+09:00
source: P5.REVIEW
summary: P5: the vocky-server server-entry rename and vocky CLI install (uv tool install / uvx / in-repo uv run vocky; PyPI publish is P6) with its ~/.config/vocky/config.json (0700/0600, VOCKY_CONFIG_DIR) session store
previous: v0002_p4_web_app_build_run_pnpm_dev_on_3030_output_standalone_and_its_two_server-only_env_keys_production_deploy_remains_p6
---

# Operations

## Status

This doc covers running the **web app** (`web/`, the Next.js frontend added in P4) and installing/running the **`vocky` CLI** (added in P5). It is deliberately scoped: the **backend/service** operational surface — the Compose-first self-hosted workflow, `make bootstrap` / `verify` / `compose-down`, and the full `DATABASE_URL` / `REDIS_URL` / `VOCKY_*` configuration surface — is documented in **`architecture.md` § Configuration Surface** and is not duplicated here.

**Server console-entry rename (P5).** The server's console script is now **`vocky-server`** (`vocky.main:main`) — the bare `vocky` name is the new user-facing CLI. Every self-host/run reference moved off `vocky` to `vocky-server`: the `Dockerfile` `CMD`, the `docker-compose.yml` app service `command`, and the README "Running The App Directly". (The `Makefile` was untouched — it starts the server via Compose, not a direct `uv run vocky`.) The worker entry (`vocky-worker`) and smoke entry (`vocky-smoke`) are unchanged.

**Production deploy is P6.** P4 targets **local-dev-runnable only**: no Dockerfile, no compose service, no nginx config, no `vocky.hi2vi.com`. The app is deploy-*ready* (`output: "standalone"`) but not deploy-*ed*.

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

`next.config.ts` sets `output: "standalone"`, so `pnpm build` emits a lean traced server at `.next/standalone/server.js` for a container to run in P6. It is **build-only** — `next dev` and `next start` ignore it, so local dev is unaffected.

The config also ships generic, everywhere-safe security headers (`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-Frame-Options: DENY`). A full **CSP**, **HSTS**, and the edge/nginx wiring are deliberately deferred to the P6 deploy, where the real origin is known.

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

`typer` is a **direct** dependency (promoted from transitive in P5). A **PyPI publish** (so `uv tool install vocky` / `uvx vocky` work from the index rather than a local checkout) is deferred to **P6** — today the install source is this repo.

### Session store and config

The CLI keeps its state in a small JSON file, **not** in env only:

- **Location**: `~/.config/vocky/config.json` — XDG-aware (`$XDG_CONFIG_HOME/vocky` when set), overridable with the **`VOCKY_CONFIG_DIR`** env var (used for isolated / throwaway sessions, e.g. an agent running per-task).
- **Contents**: the account **session token** (opaque, 30-day TTL — the same token `/auth/*`/`/app/*` mint; *not* a `vk_` key) plus an optional stored **base URL**.
- **Permissions**: the directory is created `0700` and the file `0600`, so the on-disk session token is owner-only readable (see `security.md`).

### Base-URL resolution

The API base URL resolves in this precedence: `--base-url` flag → `VOCKY_BASE_URL` env → stored `base_url` in the config → `http://127.0.0.1:8000` (local default). A `--password-stdin` flag on `signup`/`login` reads the password from one line of stdin so it never lands on argv — the headless-agent path.

## Deferred to P6

- Production Dockerfile / compose service / nginx (edge) config for the web app
- **PyPI publish of the `vocky` CLI** (so `uv tool install vocky` / `uvx vocky` resolve from the index rather than a local checkout)
- The `vocky.hi2vi.com` domain on the `oracle-cloud` box, fronted by the `edge` nginx
- CSP + HSTS (they need the real origin)
- Physical removal of the packaged Admin Web UI (`src/vocky/admin_ui.py`, `admin_assets/*`, the `/admin` mount). P4 built the replacement browser surface; the old UI stays mounted until the new app is actually deployed, so no browser surface disappears in the interim.
