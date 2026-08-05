# P6.S4 — Web production Dockerfile · plan

> Slice `P6.S4` (implementation, risk **medium**). First deploy-artifact slice. Adds the production image
> for the Next.js standalone web app, modeled on the proven `knowledge/web/Dockerfile`; confirms the
> existing backend `Dockerfile` is prod-fit. Read `phase.md` (Findings + Constraints).

## Context

The web app sets `output: "standalone"` but has **no Dockerfile** — the last piece before the prod
compose (S5) can build it. `knowledge/web/Dockerfile` is a near-exact model: vocky's web is the same
shape (self-contained pnpm project — its own `package.json`/`pnpm-lock.yaml`, **not** a workspace —
`pnpm@10.28.2`, node 22, **no `next/image`** so no sharp closure, `NEXT_PUBLIC_APP_URL` baked at build by
`src/content/site.ts`). Two vocky-specific wrinkles:

- **No `web/public/` dir** — the standard runtime `COPY /app/public ./public` would fail. Create an empty
  `web/public/.gitkeep` so the directory exists (all real assets are served by `app/` file-convention
  routes; `public/` is just the conventional home + keeps the Dockerfile identical to the reference).
- **No `web/.dockerignore`** — add one (modeled on knowledge's) to lean the build context.

## Create

- **`web/Dockerfile`** — multi-stage, adapted from `knowledge/web/Dockerfile` with a vocky header:
  - `# syntax=docker/dockerfile:1`.
  - **build** (`node:22-slim`): `ENV NEXT_TELEMETRY_DISABLED=1 COREPACK_ENABLE_DOWNLOAD_PROMPT=0`;
    **do NOT set `NODE_ENV=production` in build** (pnpm would skip devDeps → build fails); `corepack
    enable && corepack prepare pnpm@10.28.2 --activate`; `COPY package.json pnpm-lock.yaml ./`;
    `pnpm install --frozen-lockfile`; `COPY . .`; `ARG NEXT_PUBLIC_APP_URL` + assert non-empty
    (`RUN test -n "$NEXT_PUBLIC_APP_URL" || { echo "ERROR: NEXT_PUBLIC_APP_URL build arg required" >&2; exit 1; }`);
    `ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL`; `pnpm build`.
  - **runtime** (`node:22-slim`): `ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1`;
    `COPY --from=build /app/.next/standalone ./`, `/app/.next/static ./.next/static`, `/app/public ./public`;
    `USER node`; `EXPOSE 3000`; `HEALTHCHECK` (node global-fetch probe on `http://127.0.0.1:3000/` — the
    landing returns 200 for a cookieless request); `CMD ["node","server.js"]`.
  - Drop hi2vi's `sharp/@img` block (no `next/image`).
- **`web/.dockerignore`** — `node_modules`, `.next`, `out`, `tests`, `.git`, `.gitignore`, `.env`,
  `.env*.local`, `.DS_Store`, `*.tsbuildinfo`, `*-debug.log*`. (Omit knowledge's `design` line.)
- **`web/public/.gitkeep`** — empty file so `web/public/` exists for the runtime `COPY`.

## Confirm (no change expected) — backend `Dockerfile`

Verify the existing root `Dockerfile` still builds and is prod-usable: it runs as root **on purpose** (it
writes the shared attachments volume — non-root would need volume-ownership plumbing; matches the dev
compose), the migration runs via `uv run --no-sync alembic upgrade head` inside the container, and the
worker reuses the same image with an overridden command in compose (S5). **Leave it unchanged** unless
the build reveals a real problem — if it does, escalate.

## Verification

- **If Docker is available:**
  - `docker build -f web/Dockerfile --build-arg NEXT_PUBLIC_APP_URL=https://vocky.hi2vi.com -t vocky-web:test web/`
    succeeds; `docker run --rm -e PORT=3000 -p 127.0.0.1:3000:3000 vocky-web:test` starts `server.js` and
    `curl -sf http://127.0.0.1:3000/` returns 200. Clean up the test container/image.
  - `docker build -t vocky-api:test .` (backend) succeeds.
  - Confirm the assert fires: a `docker build` **without** `--build-arg NEXT_PUBLIC_APP_URL` fails loudly.
- **If Docker is unavailable:** static review against `knowledge/web/Dockerfile`; confirm
  `cd web && pnpm build` still emits `.next/standalone/server.js` + `.next/static` and that `web/public/`
  now exists. **Note in `result.md`** that the image build is verified at S10/CI — do **not** fake a Docker build.
- `python3 scripts/workflow.py validate` passes (run from repo root — the shell cwd may persist).

## Docs

Append a **Doc impact** note to `phase.md`: web production Dockerfile + `.dockerignore` + `web/public/`
added; backend Dockerfile confirmed prod-fit. REVIEW folds into `docs/current/operations.md` + `frontend.md`.

## Executor notes

Mirror the reference Dockerfile closely — it is proven. The `NODE_ENV` build-stage caveat and the
`NEXT_PUBLIC_APP_URL` non-empty assert are load-bearing; keep both. Do not add the `public/` COPY without
the `.gitkeep`, and do not gold-plate the backend Dockerfile. Write `result.md`; append the Doc-impact
note to `phase.md`. Do not commit; do not transition status.
