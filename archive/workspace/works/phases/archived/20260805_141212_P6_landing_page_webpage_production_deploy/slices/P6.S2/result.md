# P6.S2 — Landing/site metadata & production origin · result

Implemented the Next 16 metadata file-convention routes, marketing description,
production-origin wiring, and the public-404 back-link fix. All from the existing
round-01 brand (Mark geometry + brand tokens) — no new design round.

## Created (all under `web/src/app/`)

- **`icon.svg`** — static SVG favicon: the Mark geometry with literal colors
  (`#0c7a52` tile `rx=9`, three white bars at the same 32-unit coordinates).
- **`apple-icon.tsx`** — `ImageResponse` 180×180. Rebuilt the Mark with divs
  (green rounded tile + three bottom-aligned white rounded bars, literal colors).
  No custom font (no text). Exports `size` + `contentType`.
- **`opengraph-image.tsx`** — `ImageResponse` 1200×630 brand card: forest
  (`#14231e`) background, the Mark (div rebuild) + "vocky" wordmark + one line of
  real landing copy (`LANDING.hero.headline`, imported from `@/content`). Exports
  `alt`, `size`, `contentType`. Default ImageResponse font (no Pretendard load) —
  robust build. Next auto-injects `og:image` + `twitter:image` from this file.
- **`robots.ts`** — `MetadataRoute.Robots`: `allow: "/"`, disallow the
  authenticated/BFF routes (`/dashboard`, `/projects/`, `/feedback`, `/api/`);
  `sitemap` + `host` derived from `SITE.url`.
- **`sitemap.ts`** — `MetadataRoute.Sitemap`: the landing `/` (only public page).
- **`manifest.ts`** — `MetadataRoute.Manifest`: name/short_name "vocky", the
  marketing `SITE.description`, `start_url: "/"`, `display: "standalone"`,
  `background_color: "#ffffff"`, `theme_color: "#0c7a52"`, icons → `/icon.svg` +
  `/apple-icon`.

## Edited

- **`web/src/content/site.ts`** — rewrote `SITE.description` to grounded marketing
  copy drawn from `LANDING.hero` ("Capture the feedback your product is already
  getting. vocky turns explicit user reactions — likes, dislikes, comments — into
  structured signal you can search across every project."), replacing the internal
  "tenant dashboard" line. Kept the env-driven `url`
  (`process.env.NEXT_PUBLIC_APP_URL ?? "http://127.0.0.1:3030"`) — no hardcoded
  prod origin. Updated the stale "production origin is a P6 deploy concern" comment
  to say it is now wired via the `NEXT_PUBLIC_APP_URL` build arg (P6.S4/S5).
- **`web/src/app/layout.tsx`** — extended `metadata` with `openGraph`
  (title/description/`siteName`/`url`/`type: website`/`locale: en_US`) and
  `twitter` (`card: summary_large_image`, title, description). Kept `metadataBase`.
  Updated the stale lines-7-9 comment now that the routes exist.
- **`web/src/content/states.ts`** — added `notFound.backHome: "Back to home"`.
  Left `back: "Back to dashboard"` (in-app 404) and the locked `body` untouched.
- **`web/src/app/not-found.tsx`** (public 404) — changed `href="/dashboard"` → `/`
  and label `STATES.notFound.back` → `STATES.notFound.backHome`. Did **not** touch
  `(app)/not-found.tsx`.
- **`web/.env.example`** — added `NEXT_PUBLIC_APP_URL=` with a comment (build-time
  public var for `metadataBase`/OG; blank in dev → `http://127.0.0.1:3030`
  fallback; prod sets `https://vocky.hi2vi.com` via Docker `build.args` in S4/S5).
  Adjusted the header note so the "server-only" claim now scopes the two server
  keys only.

## Preserved

`Mark`/`Wordmark` components (geometry mirrored, not restyled); `metadataBase`
wiring; `(app)/not-found.tsx`; the locked 404 body; env-driven `SITE.url`.

## Verification

The node/pnpm toolchain **was** available in the sandbox (node v24.3.0, pnpm
10.28.2, `next/og` present), so the primary build verification ran fully — no
deferral to S4/REVIEW needed.

- **`cd web && pnpm build`** — PASSED. Compiled + typechecked cleanly. All six
  metadata routes emitted in the route summary:
  `/icon.svg`, `/apple-icon`, `/opengraph-image` (○ Static),
  `/robots.txt`, `/sitemap.xml`, `/manifest.webmanifest` (○ Static). The two
  `ImageResponse` routes static-prerendered without Satori/JSX errors (a Satori
  failure would have failed the build).
- **`cd web && pnpm lint`** — PASSED (no findings).
- **`cd web && pnpm test`** (vitest) — PASSED, 56/56 across 5 files (green,
  unchanged by this slice).
- **Eyeballed the prerendered OG** (`.next/server/app/opengraph-image.body`, a
  valid 1200×630 RGBA PNG): forest background, green Mark tile with three white
  rising bars (round-01 geometry), white "vocky" wordmark, and the one landing
  headline line. Brand-faithful, no invented illustration. Generated
  `robots.txt` / `manifest.webmanifest` / `sitemap.xml` bodies verified correct;
  the origin resolved to the local-dev fallback (`http://127.0.0.1:3030`) here
  since `NEXT_PUBLIC_APP_URL` is blank in `.env.local` — production flows the real
  origin through `SITE.url` unchanged.
- **`python3 scripts/workflow.py validate`** — PASSED ("Workflow validation
  passed.").

## Deviations from plan

None. The plan mentioned `web/public/` in the DECOMP table, but the plan's own
Create section specifies the Next `app/` file-convention routes (favicon via
`icon.svg`, etc.) rather than a `public/` folder — followed the Create section as
written; Next 16 serves these from `src/app/`, so no `public/` dir is needed.

## Doc impact

Appended one line to `phase.md` (see the Doc impact running list): the metadata/
OG/favicon/robots/sitemap/manifest routes were added, `SITE.description` rewritten
to marketing copy, and the production origin wired via `NEXT_PUBLIC_APP_URL` (build
arg) — REVIEW folds this into `docs/current/frontend.md` (+ an `operations.md` note
on the build arg).
