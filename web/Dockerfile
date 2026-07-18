# syntax=docker/dockerfile:1
# vocky-web — multi-stage image for the Next.js standalone app behind the OCI
# box's shared edge (P6.S4). Built on the box; reached by the edge over
# `changple_shared_network` as `vocky-web:3000` — NO public host port. Serves the
# landing/site (`/`) and the BFF auth/app proxy (`/api/auth/`, `/api/app/`); the
# Python API answers the rest. Modeled on knowledge/web/Dockerfile (same shape:
# self-contained pnpm project, node 22, no next/image → no sharp closure). See
# compose.prod.yml (P6.S5) + deploy/vocky.conf (P6.S6) + works/phases/active/P6/phase.md.
#
# ---------- build ----------
FROM node:22-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1 COREPACK_ENABLE_DOWNLOAD_PROMPT=0
# Do NOT set NODE_ENV=production here — pnpm would skip devDependencies
# (typescript, tailwindcss, @tailwindcss/postcss, eslint-config-next) and the
# build fails. NODE_ENV=production is set only in the runtime stage below.
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@10.28.2 --activate
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# Public app origin, baked at build time: src/content/site.ts reads
# NEXT_PUBLIC_APP_URL for metadataBase / canonical / OG / sitemap / robots. It is
# inlined at build, not read at runtime. Required — assert non-empty so a
# mis-invoked build fails loud instead of shipping the http://127.0.0.1:3030 dev
# fallback origin. Passed via the web service build.args in compose.prod.yml (P6.S5).
ARG NEXT_PUBLIC_APP_URL
RUN test -n "$NEXT_PUBLIC_APP_URL" || { echo "ERROR: NEXT_PUBLIC_APP_URL build arg required" >&2; exit 1; }
ENV NEXT_PUBLIC_APP_URL=$NEXT_PUBLIC_APP_URL
RUN pnpm build          # next.config.ts sets output:'standalone'

# ---------- runtime ----------
FROM node:22-slim AS runtime
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0 NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
# The lean traced standalone server + its node_modules closure, the static assets,
# and public/. server.js lands at the app root (web/ is a self-contained project,
# not a workspace, so there is no nested standalone path).
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
# Run unprivileged; the copied tree is world-readable and the app writes nothing to
# disk at runtime (no next/image cache, no uploads — it is a stateless BFF + SSR).
USER node
EXPOSE 3000
# Same fetch-based probe compose uses; node 22 has global fetch. HOSTNAME=0.0.0.0
# above makes server.js bind all interfaces so the edge (and this probe) can reach
# it. The landing returns 200 for a cookieless request.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node","server.js"]
