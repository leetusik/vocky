# P6.S4 — Web production Dockerfile · result

Status: **done**. Added the web production image and its build-context trim; confirmed the backend
`Dockerfile` is prod-fit and left it unchanged.

## Created

- **`web/Dockerfile`** — multi-stage `node:22-slim` image, mirrored closely on
  `knowledge/web/Dockerfile` (proven, same-shape app) with a vocky-specific header:
  - **build stage:** `ENV NEXT_TELEMETRY_DISABLED=1 COREPACK_ENABLE_DOWNLOAD_PROMPT=0`; **no
    `NODE_ENV=production` in build** (load-bearing — pnpm would prune devDeps `typescript` /
    `tailwindcss` / `@tailwindcss/postcss` / `eslint-config-next` and the build would fail);
    `corepack prepare pnpm@10.28.2 --activate`; `COPY package.json pnpm-lock.yaml ./`;
    `pnpm install --frozen-lockfile`; `COPY . .`; `ARG NEXT_PUBLIC_APP_URL` + the non-empty assert
    (`RUN test -n "$NEXT_PUBLIC_APP_URL" || { echo "ERROR: NEXT_PUBLIC_APP_URL build arg required" >&2; exit 1; }`);
    `ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL`; `pnpm build`. Both caveats kept per the plan.
  - **runtime stage:** `ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1`;
    `COPY --from=build` of `/app/.next/standalone → ./`, `/app/.next/static → ./.next/static`,
    `/app/public → ./public`; `USER node`; `EXPOSE 3000`; fetch-based `HEALTHCHECK` on
    `http://127.0.0.1:3000/`; `CMD ["node","server.js"]`.
  - No `sharp`/`@img` block (the app has no `next/image`, so no native codec closure to stage) —
    matches the knowledge reference, which already dropped it.
- **`web/.dockerignore`** — modeled on knowledge's, minus its `design` line (vocky has no design-round
  record dir): `node_modules`, `.next`, `out`, `tests`, `.git`, `.gitignore`, `.env`, `.env*.local`,
  `.DS_Store`, `*.tsbuildinfo`, `*-debug.log*`.
- **`web/public/.gitkeep`** — empty file so `web/public/` exists for the runtime `COPY /app/public
  ./public` (all real assets are served by Next `app/` file-convention routes; `public/` is just the
  conventional home and keeps the Dockerfile byte-identical to the reference). `web/.gitignore` does
  not cover `public/`, so the `.gitkeep` is tracked.

## Backend `Dockerfile` — confirmed prod-fit, unchanged

Static review only (Docker unavailable — see below). The root `Dockerfile` is a standard uv two-layer
build: `COPY pyproject.toml uv.lock README.md` → `uv sync --frozen --no-dev --no-install-project`,
then `COPY alembic.ini alembic src` → `uv sync --frozen --no-dev`, `CMD ["uv","run","--no-sync","vocky-server"]`.
Verified all COPY targets exist (`pyproject.toml`, `uv.lock`, `README.md`, `alembic.ini`, `alembic/`,
`src/`) and the `vocky-server = "vocky.main:main"` entrypoint is defined in `[project.scripts]`. It runs
as root **on purpose** (writes the shared attachments volume — non-root would need volume-ownership
plumbing; matches the dev compose); the migration runs via `uv run --no-sync alembic upgrade head`
inside the container (S7); the worker reuses this same image with an overridden command in compose (S5).
No problem found → left unchanged, as the plan directs.

## Verification

**Docker is unavailable in this sandbox.** `docker version` shows the client (28.2.2) but the daemon is
unreachable (`Cannot connect to the Docker daemon at unix:///Users/sugang/.docker/run/docker.sock`). So
the plan's **Docker-unavailable fallback** was taken; the actual image builds (web + backend), the
`NEXT_PUBLIC_APP_URL`-missing assert firing, the container run, and the `curl /` 200 probe are deferred
to **S10 / CI**, where a real Docker build runs. No Docker build was faked.

Fallback checks performed:

- **Static review** of `web/Dockerfile` against `knowledge/web/Dockerfile`: structurally identical
  aside from the vocky header, the dropped `design` `.dockerignore` line, and comment wording. Both
  load-bearing caveats (no build-stage `NODE_ENV`, the `NEXT_PUBLIC_APP_URL` non-empty assert) are
  present.
- **`cd web && pnpm build`** (fresh) → `✓ Compiled successfully`, 13 routes generated, and it still
  emits the standalone server + static assets:
  - `web/.next/standalone/server.js` — present.
  - `web/.next/static` — present.
- **`web/public/`** now exists (contains `.gitkeep`), so the runtime `COPY /app/public ./public` will
  resolve.
- **`python3 scripts/workflow.py validate`** (from repo root) → `Workflow validation passed.`

## Deviations from plan

None.

## Doc impact

Appended to `phase.md` (Doc impact list) — REVIEW consolidates into `docs/current/operations.md` +
`frontend.md`:

> **P6.S4** (Web production Dockerfile): `web/Dockerfile` (multi-stage `node:22-slim`, pnpm frozen,
> standalone, `ARG NEXT_PUBLIC_APP_URL` asserted non-empty, `USER node`, `EXPOSE 3000`, `node server.js`)
> + `web/.dockerignore` + `web/public/.gitkeep` added; backend root `Dockerfile` confirmed prod-fit and
> left unchanged. REVIEW folds the deploy-artifact addition into `docs/current/operations.md` (build/run
> contract, `NEXT_PUBLIC_APP_URL` build arg) and `docs/current/frontend.md` (standalone image note).
