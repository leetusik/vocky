# P6.S2 — Landing/site metadata & production origin · plan

> Slice `P6.S2` (implementation, risk **medium**). Closes the documented web-app production-readiness
> gaps: no `public/`/favicon/OG/robots/sitemap/manifest, generic dashboard metadata, unwired production
> origin. Read `phase.md` (Findings + Constraints) for accumulated context.

## Context

The landing/webpage is built (P8/P9), but the app ships with **no metadata file-convention routes**
(`web/src/app/layout.tsx:7-9` and `web/src/content/site.ts:5` explicitly defer icons/OG/robots/sitemap
and the production origin to "a P6 deploy concern"). Implement those using the **existing** round-01
brand — the `Mark` geometry (`web/src/components/brand/mark.tsx`: 32×32 rounded tile `rx=9` + three white
rising bars) and brand tokens (`--color-green #0c7a52`, `--color-forest #14231e`, white) — **not** a new
design.

**Design boundary (`phase.md` Constraints):** favicon/OG are assembled from the existing brand. Keep the
OG card minimal and brand-faithful (Mark + "vocky" wordmark + one line of existing landing copy on a
brand background). **No invented illustration** — that would be a separate design gate.

Implementation gotchas found in research:
- **Literal colors only** in icon/OG assets: `Mark` uses Tailwind classes (`fill-green`) that resolve via
  CSS vars — those don't exist inside a static SVG or `ImageResponse`. Inline the same geometry with
  literal `#0c7a52` / `#ffffff`.
- **Font in `ImageResponse`:** Pretendard is a *variable* woff2 (`web/src/lib/fonts/PretendardVariable.woff2`)
  which Satori (next/og) may reject. Prefer the default ImageResponse font over a fragile build; do **not**
  block the build trying to load the variable font.

## Create (all under `web/src/app/`, Next 16 file conventions; `next/og` confirmed present)

- **`icon.svg`** — static favicon: the Mark geometry, literal `#0c7a52` tile + white bars.
- **`apple-icon.tsx`** — `ImageResponse` 180×180: green rounded tile + three white bars (divs/inline SVG, literal colors).
- **`opengraph-image.tsx`** — `ImageResponse` 1200×630 brand card: forest (`#14231e`) background, the Mark + "vocky" wordmark + a one-line tagline reused from `LANDING.hero` (import `LANDING` from `@/content` — do not duplicate copy). Export `alt`, `size`, `contentType`. Next auto-injects `og:image` (and `twitter:image`) from this file.
- **`robots.ts`** — `MetadataRoute.Robots`: `allow: "/"`, `disallow` the authenticated/BFF routes (`/dashboard`, `/projects/`, `/feedback`, `/api/`); `sitemap` + `host` from `SITE.url`.
- **`sitemap.ts`** — `MetadataRoute.Sitemap`: the landing `/` (the only public page).
- **`manifest.ts`** — `MetadataRoute.Manifest`: `name`/`short_name` "vocky", marketing `description`, `start_url: "/"`, `display: "standalone"`, `background_color: "#ffffff"`, `theme_color: "#0c7a52"`, icons referencing `icon.svg` (+ apple-icon).

## Edit

- **`web/src/content/site.ts`** — rewrite `SITE.description` to grounded **marketing** copy (source from `LANDING.hero`, e.g. the headline "Capture the feedback your product is already getting." + a clause from the sub), replacing the generic "tenant dashboard" line. Keep the env-driven `url` pattern (`process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3030"`) — **do not hardcode** the prod URL (injected at build via the `NEXT_PUBLIC_APP_URL` build arg in S4/S5). Update the stale "production origin is a P6 deploy concern" comment to say it is now wired.
- **`web/src/app/layout.tsx`** — extend `metadata`: add `openGraph` (title, description, `siteName: "vocky"`, `url: SITE.url`, `type: "website"`, `locale: "en_US"`) and `twitter` (`card: "summary_large_image"`, title, description). Keep `metadataBase`. Update the stale comment (lines 7-9) now that these routes exist.
- **`web/src/content/states.ts`** — add `notFound.backHome: "Back to home"` (the shared `back: "Back to dashboard"` stays for `(app)/not-found.tsx`; do not repurpose it). Leave `notFound.body` untouched (locked 404-never-403 floor).
- **`web/src/app/not-found.tsx`** — this is the **public** 404 (unmatched URLs outside `(app)`). Change `href="/dashboard"` → `href="/"` and label `STATES.notFound.back` → `STATES.notFound.backHome`. Do not touch `(app)/not-found.tsx`.
- **`web/.env.example`** — add `NEXT_PUBLIC_APP_URL=` with a comment: build-time **public** var for `metadataBase`/OG; local dev blank → `http://127.0.0.1:3030` fallback; production sets `https://vocky.hi2vi.com` via the Docker `build.args` (S4/S5).

## Preserve

`Mark`/`Wordmark` components (mirror geometry, don't restyle); `metadataBase` wiring;
`(app)/not-found.tsx`; the locked 404 body copy; the env-driven `SITE.url` (no hardcoded origin).

## Docs

Append a **Doc impact** note to `phase.md`: metadata/OG/favicon/robots/sitemap/manifest added,
`SITE.description` rewritten, production origin wired via `NEXT_PUBLIC_APP_URL` (build arg) — REVIEW folds
into `docs/current/frontend.md` (+ an `operations.md` note on the build arg).

## Verification

- **Primary:** `cd web && pnpm build` succeeds — typechecks and compiles every `ImageResponse`/metadata
  route (a Satori/JSX error fails the build). If node/pnpm is unavailable in the sandbox, run `pnpm lint`
  + `pnpm test` and note that full build verification defers to S4 (Dockerfile build) / REVIEW — do
  **not** fake a pass.
- Confirm routes emitted (from the `next build` route summary): `/icon.svg`, `/apple-icon`,
  `/opengraph-image`, `/robots.txt`, `/sitemap.xml`, `/manifest.webmanifest`.
- `pnpm test` (vitest) stays green.
- Eyeball the OG output for brand fidelity (Mark + wordmark + one existing line, brand colors, no invented art).
- `python3 scripts/workflow.py validate` passes.

## Executor notes

Reuse existing copy (`LANDING`, `SITE`) — never hardcode strings inline (the `@/content` convention). If
`ImageResponse` fights the variable font or the Mark geometry, use the robust fallback (default font /
inline literal-color SVG) rather than escalating — brand-faithful-enough beats a broken build. Escalate
only if a metadata convention can't be satisfied without a design decision. Write `result.md`; append the
Doc-impact note to `phase.md`. Do not commit; do not transition status.
