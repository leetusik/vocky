---
doc_id: frontend
version: v0009
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: recorded_by is a URL-driven feedback filter plus one detail-page row
previous: v0008_p12_the_web_app_is_deployed_and_serving_at_vocky.hi2vi.com_and_the_vestigial_hi2vi_design_tokens_are_renamed_to_role_names
---

# Frontend

## Status

Vocky has **exactly one** frontend: the **authenticated web app + public landing** in `web/` (P4 built the app; P9 applied the design and added the landing). It is a Next.js 16 / React 19 / TypeScript app that talks to vocky's `/auth/*` + `/app/*` surfaces through a **server-side BFF proxy**. It replaced the packaged same-origin operator Admin Web UI — and as of **P6 that old UI is physically deleted** (`src/vocky/admin_ui.py`, `admin_assets/*`, and the `/admin` + `/admin/assets/*` routes are gone). There is no longer a second browser surface anywhere in the product.

P4 delivered signup/login/logout, the app shell, the tenant dashboard, project detail (with credential mint/revoke), and cross-project feedback list/search/detail. **P9 applied the round-01 signed-off vocky design** (`docs/reference/design/rounds/01-brand-app-landing/`) across all of it and added the two net-new surfaces: the public `/` landing and the designed `loading`/`error`/`not-found`/`global-error` states. **P6** finished the site's production-facing edges: the metadata/OG/favicon/robots/sitemap/manifest routes, the marketing description, the real production origin, and a production `Content-Security-Policy` — plus `web/Dockerfile`, the standalone production image.

**P10** added the app's first **org-level** surface: an org-keys panel on the dashboard, `VockyCredential.project_id` widened to `string | null`, a shared show-once key component, and the **Workspace → Org** copy rename. It is the first web change since P4 that adds new mutating surface rather than restyling existing ones — see "The dashboard" and "P10: org keys in the web app" below.

**P11** grew the public landing for the first time since P9, through **design round 02** (`docs/reference/design/rounds/02-onboarding/`, token delta **None**): two net-new sections (`AgentQuickstart` at `#quickstart`, `SkillSection` at `#skill`), two net-new `ui/` primitives (`Snippet`, `Trap`), the landing's **first client islands that render only after hydration**, and the landing's **first request-time filesystem read** (the skill pane reads the served `public/SKILL.md` on every render of `/`). See "P11: the onboarding surfaces on the landing" below. It touched no backend contract, no `globals.css`, and no token.

**The app is deployed and serving (P12, 2026-08-04).** `https://vocky.hi2vi.com` answers: `/` 200, a signup → session round-trip proven live, and the landing's `/install.sh` + `/SKILL.md` both serving. See `operations.md`.

The app is a **session-token client only** (the guarded `(app)` surfaces + the public `(auth)` and landing). It calls `/auth/*` and `/app/*`; it never touches the `vk_`-keyed `/api/*` surface, which is the external-service credential path. There is no web-side database. **No backend/contract change was needed to apply the design** (`build-prompt.md §9`): everything maps to existing serializers, and the only new behavior is web-tier (the `/` landing behind the existing signed-in→dashboard bounce, and a project-detail breadcrumb from already-fetched data).

## App Location and Stack

The app is a subdirectory of this repo (**D-P4-1**), versioned and committed by the same workflow engine as the backend. "hi2vi_web-style" (the operator's reference, `~/projects/personal/hi2vi_web`) means **stack, patterns, and the Claude design-gate workflow** — not repo topology; hi2vi_web is a template we port from, not a vendored dependency.

- **Next.js 16** (App Router, Turbopack) / **React 19** / **TypeScript**, package manager **pnpm** (`packageManager: pnpm@10.28.2`, node `>=22.13.0`)
- **Tailwind v4**, CSS-first (`@theme` in `globals.css`); there is no `tailwind.config.*`
- Runtime deps are deliberately few: `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `tw-animate-css`, `server-only`, `zod`. **Pretendard is vendored, not a new dependency** — a single variable woff2 loaded via `next/font/local` (no `@fontsource/*` package added).
- `next.config.ts` sets `output: "standalone"` (build-only; emits `.next/standalone/server.js`, which `web/Dockerfile` copies into its runtime stage), the generic security headers (`nosniff`, `Referrer-Policy`, `Permissions-Policy` — now including `browsing-topics=()`, `X-Frame-Options: DENY`), and a **production-gated CSP** (P6). **HSTS is not set here** — it belongs to the edge vhost, along with an additive `upgrade-insecure-requests` CSP. There is no `middleware.ts` and no nonce, deliberately: a nonce forces dynamic rendering and would cost static generation across the app. Full rationale in `security.md`.
- Scripts: `dev` / `build` / `start` (all bound `127.0.0.1:3030`), `lint`, `typecheck`, `test` (vitest), `format`

## Directory Shape

```
web/
  src/app/
    layout.tsx            root layout (fonts, globals.css, metadata)
    page.tsx              "/" → the PUBLIC LANDING (signed in → /dashboard bounce)
    globals.css           the @theme token system (vocky deep-emerald, applied)
    not-found.tsx         root 404 (404-never-403 copy; backs to "/", not /dashboard)
    global-error.tsx      root-layout crash fallback (own <html><body>)
    icon.svg              favicon (static SVG, Mark geometry)          } P6 metadata
    apple-icon.tsx        180x180 ImageResponse (div-rebuilt Mark)     } file-convention
    opengraph-image.tsx   1200x630 ImageResponse brand card            } routes — all six
    robots.ts / sitemap.ts / manifest.ts   MetadataRoute generators    } static-prerendered
    (auth)/               PUBLIC, unguarded: login, signup (+ auth-card, credentials-form)
    (app)/                GUARDED: layout.tsx awaits requireIdentity()
      loading.tsx         stat-tile + chart skeleton (app-group Suspense fallback)
      error.tsx           danger-mark error boundary ("use client", {error, reset})
      not-found.tsx       in-app 404 (rendered inside the shell)
      dashboard/          page + actions.ts + create-project-form.tsx
      projects/[projectId]/  page + actions.ts + mint-credential-form + revoke-credential-button
      feedback/           page + feedback-fields.tsx + loading.tsx + [feedbackId]/page.tsx
    api/
      auth/{login,signup,logout}/route.ts     the BFF credential routes
      app/feedback/[feedbackId]/attachments/[attachmentId]/route.ts   binary proxy
  src/components/
    ui/                   CVA primitives (the design system; incl. select, chip)
    brand/                mark + wordmark (the vocky brand asset; barrel index.ts)
    app-shell/            app-shell, rail-nav, logout-button
    usage/                stat-tiles, trend-chart (shared by dashboard + project detail)
    landing/              LandingNav/Hero/TrustStrip/HowItWorks/AgentQuickstart/
                          SkillSection/Showcase/Features/Pricing/ClosingCTA/
                          LandingFooter (+ barrel), plus the P11 skill-pane parts
                          (skill-preview, skill-preview-body, skill-copy-button,
                          skill-shared, inline-code)
  src/content/            copy-as-data (site, app, auth, dashboard, project, feedback,
                          landing, states, section-ids)
  src/lib/
    session.ts            AES-256-GCM seal/open + cookie options + guards
    auth-guards.ts        requireIdentity / redirectIfAuthenticated
    bff.ts                the audited BFF credential pipeline
    env.ts, rate-limit.ts, client-ip.ts, fonts.ts, utils.ts (cn)
    clipboard.ts          attemptCopy — the DOM-free copy decision seam (P11)
    use-is-hydrated.ts    useIsHydrated — the mount gate (P11)
    fonts/                PretendardVariable.woff2 (vendored, next/font/local)
    vocky/                client.ts, auth.ts, app.ts, types.ts — the server-side API client
  public/                 install.sh + SKILL.md — real served static files (P11)
  tests/                  vitest (78 tests, 10 files)
```

**Route-group semantics:** `(auth)` is deliberately **unguarded** (otherwise `/login` could not be reached); `(app)` is guarded once in its `layout.tsx`. **`/` (the landing) lives outside `(app)`**, so it renders its own nav/footer with no app shell. Non-route files (forms, field helpers, landing sections) are colocated in the route folder — only `page`/`route`/`layout`/`loading`/`error`/`not-found`/`global-error` files become routes/handlers.

## Design System (applied — the vocky round-01 brand) — D-P4-3 → D-P8-1, applied by P9

P4 ported hi2vi_web's design-system *skeleton* at a placeholder palette; the intensive operator design session that D-P4-3 deferred was **held and closed at P8** (round 01 — `docs/reference/design/rounds/01-brand-app-landing/`) and **applied by P9**. The doc set now describes the **live, applied vocky brand** — the deep-emerald names-kept value swap, Pretendard, the compact scale, the new component vocabulary, the `/` landing, and the loading/error/404 states are all shipped. The **`build-prompt.md`** in that round folder is the read-only implementation contract P9 built from (its §10 is the definition-of-done the review checked against).

- **Tokens** — `src/app/globals.css` keeps the 4-part skeleton: `@theme` tokens → `:root` shadcn aliases → `@theme inline` bridge → `@layer base`. **There is no dark-mode toggle and no `.dark` block** — surfaces are explicit tokens (the closed gate confirmed light-only). Kept: the `[data-reveal]`/`.is-visible` scroll-reveal rules, the focus ring, the reduced-motion block, and `h1–h6 { word-break: keep-all }` (Korean line-breaking).
- **Palette is the applied vocky brand** — a **deep-emerald** green (`--color-green #0C7A52`, hover `--color-green-deep #095E40`, links `--color-green-dark #064A33`) on a **green-cool neutral ramp** (ink `#0E1A16`, forest/surface/hairline families all green-tinted), with `danger #C93B2B` / `caution #C6820E` signals. The swap kept **all 41 hi2vi token *names*** and swapped only values, so the re-theme property (Tailwind utilities compile to `var(--color-*)`) re-themed every surface at once with **zero call-site churn**; the handful of hardcoded literals a value swap can't reach (`button.tsx` primary shadows, `card.tsx` feature/pricing shadows + `pricingFeatured` border) were fixed by hand. `on-primary` stays **`#ffffff`** (the deep-emerald passes AA 5.36:1 with white). One intentional token equality holds (`ink == canvas-dark`); every other placeholder collision is broken.

  **The vestigial hi2vi names are retired as of P12.S2** — a mechanical, **byte-identical-hex, zero-visual-change** rename, deliberately kept out of any design round because it decided nothing visual. Three were renamed to the role their own comments already stated, and **two unused exact duplicates were deleted outright**:

  | Was | Now | Hex |
  | --- | --- | --- |
  | `--color-security-mint` | **`--color-mint`** | `#bee9d5` (mint tint — chip borders, key panel) |
  | `--color-security-teal` | **`--color-teal`** | `#2fa477` (brighter data accent — endpoint label) |
  | `--color-victory-lime` | **`--color-lime`** | `#9ad4a8` (soft positive tint, rare) |
  | `--color-archive-olive` | *deleted* | `#8a968f` — exact duplicate of `--color-muted`, unused |
  | `--color-archive-cream` | *deleted* | `#f1f4f0` — exact duplicate of `--color-surface-soft`, unused |

  All six usage sites were updated in the same pass. The retired names survive **only** as deliberate history in `globals.css`'s header comment — no declaration and no Tailwind utility class references them anywhere in `web/src`. The rest of the token set is unchanged: **do not rename the remaining tokens.**
- **Type / radius / spacing are the compact vocky scale** — all 14 `--text-*` steps retuned to the §3.2 sizes (hero-display 60px … micro 11px), radius base `10px`, `--spacing-hero 120px`, app density via utilities (`space-y-6` page blocks, `p-5` cards, `px-4 py-2` table cells, `p-4` stat tiles). `--breakpoint-xs` (zero consumers) was **dropped** for `--breakpoint-app: 56.25rem` (900px); all 11 `min-[900px]:` literals were migrated to the `app:` variant (zero remain).
- **`cn()`** (`src/lib/utils.ts`) — `clsx` + `extendTailwindMerge`, with the `font-size` group registering the custom `text-*` scale so `text-body-sm`-style tokens merge correctly.
- **Fonts** (`src/lib/fonts.ts`) — **Pretendard** (`--font-sans` and `--font-en`, Korean-capable) loaded via `next/font/local` from the **vendored** `src/lib/fonts/PretendardVariable.woff2` (variable weight `400 800`, CSS var `--font-pretendard`), plus **JetBrains Mono** (`--font-mono`, `next/font/google`, unchanged). The fallback chain retains **Noto Sans KR** as the Korean-capable face (locked floor). `--font-en` is no longer a bare system stack — it points at Pretendard, so buttons (`font-en`) render in the brand face.
- **Primitives** (`src/components/ui/`, CVA + a barrel `index.ts`) — `button`, `card`, `section`, `field` (Label/Input/Textarea/Checkbox/FieldError), `badge`, `grid`, `data-table`, `endpoint-card`, `reveal`, `select`, `chip`, plus the **P11 `snippet` and `trap`** (round 02; see "P11: the onboarding surfaces on the landing"). Round-01 changes: **Button** is `rounded-md` (not pill) with seven variants — `primary`/`secondary`/`ghost`/`destructive`/`destructiveOutline`/`dark`(rename of `secondaryOnDark`)/`link`; **Card** dropped the placeholder `security`/`archive` variants; **Badge** split the overloaded `archive` into rating (`liked`/`disliked`/`unrated`) + status (`active`/`revoked`) + `accent`, with an optional variant-colored leading dot; **Field** compacted; **TrendChart** redesigned (below). **`Select`** wraps a styled native `<select>` (a11y kept) whose `selectVariants` reuses `inputVariants()` so filter controls match form fields — this **removed the `inputVariants()` template-literal `<select>` hack**; **`Chip`** is a mono tag primitive (`default`/`filter`, optional `removable`+`onRemove`).
- **Brand asset** (`src/components/brand/`, new) — `Mark` (inline-SVG three-rising-bars waveform tile, `size` prop 32=chrome / 52=hero, tile fill parameterized via `tileClassName` so the error state re-tints to danger without forking) + `Wordmark` (lowercase "vocky", `tone` light/dark). Imported from `@/components/brand`; reused by the app shell, auth card, landing, and the error/global-error states.
- **`data-table.tsx`** — headless, generically typed `DataTable<T>` (`columns`/`rows`/`rowKey`/`empty`/`actions`), now at compact density (`px-4 py-2` cells, `text-micro` uppercase headers). Purely presentational.
- **Copy-as-data** (`src/content/`) — user-visible strings live in typed modules (`site`, `app`, `auth`, `dashboard`, `project`, `feedback`, plus the new `landing` and `states`) re-exported through `index.ts`, not inline in components. `section-ids.ts` holds the live landing anchors — `features`/`how`/`pricing`, plus **`quickstart` and `skill` from P11**; the dead `content/nav.ts` (`NAV_LINKS`/`SKIP_TO_CONTENT`) and the `overview`/`primitives` ids were **retired** in the P9 sweep. `SectionId` is a typed union, so a new section cannot compile until its id is added here. `landing.ts` likewise gained P11's `snippet` / `heroInstall` / `quickstart` / `skill` blocks.
- **The `web/design/canvas/` mirror stays gone** (deleted in P8). The design workflow reads the real repo directly; the durable design record lives outside `web/`, at `docs/reference/design/`.

## The BFF and the Session Model — D-P4-2

The browser talks **only** to the Next.js origin. The Next.js server talks to vocky server-to-server with `Authorization: Bearer`. **No CORS change to vocky was needed, and there is no web-side DB.**

### The sealed session cookie

The vocky session token is sealed into an httpOnly cookie the Next app sets for itself — it never reaches browser JS.

- Cookie **`vocky_session`** = **`v1.<iv>.<ct>.<tag>`** (each part base64url), **AES-256-GCM**, key = `sha256(SESSION_SECRET)`, a fresh random 12-byte IV per seal. Sealed plaintext is JSON `{token, exp}`.
- Attributes: `httpOnly`, `SameSite=Strict`, `path=/`, `maxAge` **30d** (deliberately matching vocky's own token TTL), and `Secure` **only** when `NODE_ENV === "production"`.
- `openSession` returns the token or **`null` for every failure** — wrong shape/version, GCM tag mismatch (tampering), bad JSON, expired `exp`, rotated/missing secret. It never throws, so callers treat "no session" uniformly.
- The guards (`getSession` / `requireSession`) **return the decrypted vocky token** for bearer injection rather than just gating — the deliberate departure from hi2vi's template (which HMAC-signs a self-minted token and returns void). The landing's signed-in bounce reuses `getSession()`.

> **Dev-vs-prod gotcha (bit S4, cost a wasted run):** because `Secure` is set under `NODE_ENV=production`, a plain-http client on `127.0.0.1` never replays the cookie and **every guarded page silently bounces to `/login`**. Drive local end-to-end runs on **`pnpm dev`**, not `pnpm start`. (Real browsers treat `127.0.0.1` as a secure context and are fine; scripted http cookie jars are not.)

### The BFF credential routes

`src/app/api/auth/{login,signup,logout}/route.ts` (`runtime="nodejs"`, `dynamic="force-dynamic"`) are the app's **only** public unauthenticated POST surface. Their ordered checks are factored into one audited pipeline, `src/lib/bff.ts::handleCredentialRoute`, so the security path has a single copy rather than two near-identical ones:

```
JSON-only 415 → assertSameOrigin 403 → per-IP rate limit 429 → parse 400 / zod 422 → vocky call → seal into cookie, 200
```

- **vocky's `detail` is never echoed** — the response body is only `{ok}` and the client keys off the status. Pass-through statuses: login `[401, 400]`, signup `[409, 400]`; any other upstream error → 502; config/transport → 500.
- **Rate-limit buckets are namespaced** (`auth-login:` / `auth-signup:` + IP) — login is the stricter throttle (5/15min) vs signup (10/15min). hi2vi's template keyed on the bare IP, which would let login attempts drain signup's budget; the namespacing fixes that latent bug and a test locks it.
- **Logout** revokes at vocky best-effort, then **unconditionally** clears the cookie — it never fails open.
- **The identical-login-error mapping (401 → one message) lives here in the form/BFF and is a locked floor** — P9's restyle never touched it.

### Guards and the redirect-loop fix

`src/lib/auth-guards.ts` composes session + vocky, keeping `session.ts` vocky-agnostic:

- **`requireIdentity()`** — gates `(app)`; it is `cache()`d so the layout and the page share **one** `/auth/me` per request. It signals "no session" by `redirect()`, which works **by throwing**.
- **`redirectIfAuthenticated()`** — the `(auth)` bounce. It **verifies against `/auth/me` before redirecting**. This is load-bearing: a cookie can be crypto-valid while its vocky token is dead (revoked out-of-band), and a naive bounce would ping-pong `/login` ↔ `/dashboard` forever, since Next forbids clearing a cookie from a server component. Verifying first means a dead cookie simply renders the login form.
- Only **401** redirects. Non-401 errors (vocky down) are **rethrown**, never silently treated as a logout.

### The server-side vocky client (`src/lib/vocky/`)

- **`client.ts`** — the seam: `ApiError` / `toError` / `getJson` / `sendJson` / `getRaw`, adapted from hi2vi's `content-agent/api.ts` to server-side. Absolute URL from `VOCKY_API_BASE_URL`, `Authorization: Bearer` injection, `cache: "no-store"`, errors carrying vocky's `{detail}`, 204/empty-body tolerant. `getRaw` is the raw/binary GET added for attachments (`getJson`'s `parseBody` would `JSON.parse` a PNG).
- **`auth.ts`** — `signup` / `login` / `logout` / `me`, plus `normalizeAuthResponse` / `activeTenant`, which collapse vocky's **tenant asymmetry** (signup returns `tenant` singular; login/me return `tenants[]`) into one `{token, user, tenant}` with `tenants[0]` active — matching vocky's own `require_user`.
- **`app.ts`** — the `/app/*` functions: `listProjects`, `createProject`, `getUsage`, `getProject`, `createCredential`, `revokeCredential`, `getProjectUsage`, `listFeedback`, `getFeedbackDetail`, plus (P10) `listOrgCredentials` / `createOrgCredential` / `revokeOrgCredential`, plus the `feedbackQueryString` builder. House style: private `Raw*` envelope types, `(token, …pathArgs, signal?)` for reads, `signal`-less writes, `encodeURIComponent`'d ids. The P10 trio follows it exactly: `createOrgCredential` returns the mint envelope **whole** (never unwrapped, same reason as `createCredential`), an absent name sends `{}` rather than `{name: null}`, and errors are enumerated by status in the JSDoc rather than caught.
- **`types.ts`** — the `/app/*` wire shapes. Note `VockyUsageProject` is a **separate** type from `VockyProject` (the usage serializer omits `tenant_id`), and `VockyProjectUsage` is separate from `VockyUsage` (no `projects`, has `credentials`).
  - **`VockyCredential.project_id` is `string | null` as of P10**, and **`null` is the org-key discriminator** — the backend adds no scope field, so this is what a component branches on. The widening broke exactly one site (project detail's `RevokeCredentialButton` cell), which was **narrowed with an explicit guard, not a cast, and not by forking the type**: a credential on the project-detail page is always project-bound because it comes from `/app/projects/{id}/usage`, which never returns org keys. The invariant that narrowing relies on is stated in a comment beside it. `VockyFeedback.project_id` is a different, already-nullable field and was untouched.

## Mutations: server actions vs BFF routes

The split is a rule, not a preference:

- **Authed mutations are server actions** (`actions.ts`, `"use server"`) — create-project, mint-credential, revoke-credential, and (P10) mint-org-credential, revoke-org-credential. Exactly **5** are registered app-wide.
- **BFF route handlers are only the public, rate-limited auth surface** (login/signup/logout) — the one place a caller has no session yet — plus the binary attachment proxy.

Three rules the phase paid for and that any new action must follow:

1. **A `"use server"` file may export ONLY async functions.** Every export is registered as a callable server action; a plain-object export is silently registered as a second action and **500s every submit**. This was a real bug that typecheck, lint, 44 tests, *and* `next build` all passed — caught only by a live run. Form initial-state constants therefore live in the client island.
2. **`requireIdentity()` must be called OUTSIDE an action's `try`.** It redirects **by throwing**; a wrapping `catch` swallows the redirect and renders a bogus "please try again" instead of bouncing to `/login`. The same applies to `notFound()`.
3. **`revalidatePath(pattern, "page")`** on a dynamic route takes the route **pattern** (`"/projects/[projectId]"`), not the resolved href.

Actions map failures **by status** (400/401/404 → copy from `src/content/`), never by echoing vocky's `detail`.

## Page and Component Inventory

| Route | Kind | Notes |
| --- | --- | --- |
| `/` | public landing | signed out → the vocky landing; **signed in → `/dashboard` bounce** (reuses `getSession()`); copy from `content/landing.ts`; **reads `public/SKILL.md` at request time** (P11) |
| `/install.sh`, `/SKILL.md` | static (P11) | plain files in `web/public/`, served by the standalone server through the existing nginx `/` catch-all — no route, no MIME work |
| `/login`, `/signup` | public | `(auth)` group; brand lockup (Mark+Wordmark) + `auth-card` + the shared `credentials-form` client island |
| `/dashboard` | guarded | usage stat tiles + daily-trend area chart + projects `DataTable` + create-project form |
| `/projects/[projectId]` | guarded | breadcrumb + project info + usage + credentials table + mint form + revoke |
| `/feedback` | guarded | cross-project list + `Select` filter form + keyset pagination |
| `/feedback/[feedbackId]` | guarded | read-only detail (message, comments, `Chip` tags, attachments, raw JSON) |
| `loading` / `error` / `not-found` / `global-error` | net-new states | app-group skeleton, danger-mark error boundary, 404-never-403 pages, root crash fallback |
| `/api/auth/{login,signup,logout}` | BFF | the public credential pipeline |
| `/api/app/feedback/[id]/attachments/[id]` | BFF | binary proxy (forced download) |
| `icon.svg`, `apple-icon`, `opengraph-image`, `robots.txt`, `sitemap.xml`, `manifest.webmanifest` | metadata (P6) | all `○ Static` — prerendered at build |

The guarded routes are `ƒ (Dynamic)`; the landing `/` is `ƒ` too (it reads the session cookie); `/_not-found` and the six P6 metadata routes prerender static. `next build` needs no env because env reads are lazy — the one exception is `NEXT_PUBLIC_APP_URL`, which is *optional* (it falls back to the dev origin) but is inlined at build when present.

**The app shell** (`src/components/app-shell/`) is a **server component** — only logout and the pathname-aware rail are client islands, so the server-fetched identity never crosses a client boundary. Its topbar leads with the **brand lockup (Mark 32 + Wordmark)** (no longer `SITE.name` text) · workspace/user · spacer · logout, over an `app:`-breakpoint `[rail | main]` grid (`grid-cols-1 app:grid-cols-[248px_minmax(0,1fr)]`); below 900px the rail collapses to a horizontal strip. **`LogoutButton` is now a `<Button variant="ghost" size="sm">`** (the bespoke chip markup is gone), keeping the pending + best-effort logout logic verbatim.

**`RailNav`** is a client island only because the active item derives from `usePathname()`. An item is active when `pathname === item.href || pathname.startsWith(item.href + "/")` — the prefix rule is what keeps *Feedback* highlighted on `/feedback/[id]`. The active item now carries an **inset green accent bar** (`shadow-[inset_2px_0_0_var(--color-green)]`) on `bg-green-soft`. It also retains a **`soon`** affordance (a muted, non-interactive "Soon" tag). **No item sets `soon` today** — the mechanism is kept for whichever surface lands next.

**Usage components** (`src/components/usage/`) are presentational, props-only server components reused by both the dashboard and project detail (each page renders exactly one of each, since they hardcode DOM ids). `StatTiles` is compact (`Card p-4`) with a per-key leading rating dot. **`TrendChart` is the round-01 dependency-free *area* chart** (§4.14): `viewBox 0 0 100 42`, a green gradient fill + line + hairline baseline, per-point `<circle>`+`<title>` hover, `preserveAspectRatio="none"`, `role="img"` + an `sr-only` peak/total summary, and **both empty shapes** preserved (empty note box for no data; a flat baseline for an all-zero series, `Math.max(1, …)` guarding divide-by-zero). The P8 "adopt a chart library?" question was resolved as **no library** — this is the applied redesign.

### The dashboard

`requireIdentity()` → `Promise.all([listProjects, getUsage, listOrgCredentials])` — the org-keys fetch is a **third leg of the existing `Promise.all`**, so P10 added a panel without adding a sequential round-trip. It renders the project list from **`/app/projects` (canonical)** and deliberately **ignores `usage.projects`** (a narrower serializer with its own type). Rows are keyed by `p.id`, never `name` — **the keying rule survives P10 unchanged, but its old justification does not**: names are now `UNIQUE (tenant_id, name)` server-side, so vocky can no longer produce two same-named projects. Keying on `id` is still correct (ids are the stable identity); the comment saying "names may collide" was corrected rather than the code. The project name is a `<Link>` into `/projects/[id]` (`hover:text-green-dark hover:underline`).

It does **not** call `GET /app/tenant`: the shell's topbar already has the tenant from the `cache()`d `/auth/me`, so a second call buys a round-trip and nothing else.

### P10: org keys in the web app

**The org-keys panel is a fourth `<section aria-labelledby="org-keys">` on `/dashboard`, after the projects section — no new route, no new nav entry.** That IA is deliberate: an org key belongs to no single project, so the org-level page is the only honest home for it, and the design round is closed (no new design work was commissioned; the panel reuses shipped primitives — `Card`, `DataTable`, `Badge`, the mint form, the show-once panel).

- **The show-once key panel is now a shared component**, `web/src/components/show-once-key.tsx` (`ShowOnceKey`, `"use client"`, taking a `copy: ShowOnceKeyCopy` prop), lifted out of the project mint form where it was module-private. **The dismissal logic was preserved verbatim** — keyed on the action state's `ok` stamp, never a boolean — in both consumers. That rule is a locked floor precisely because a missed render there is unrecoverable.
- **A dashboard-local `orgCredentialColumns`** (name / key / created / last-used / status / actions) was defined rather than extracting a shared parameterized column factory. The org table has **no project column** and its actions cell renders a different, non-project-scoped revoke island, so a factory would have been parameterized past the point of paying for itself.
- **The two new server actions live in `dashboard/actions.ts`** and mirror the project actions' shape — `(_prevState, formData) => Promise<State>`, ids as hidden inputs, `requireIdentity()` **outside** the `try`, zod `safeParse` only, failures mapped **by HTTP status** against a status-keyed `ORG_CREDENTIAL_ERRORS` in `content/dashboard.ts`. One error object covers both mint and revoke, because both sit on one panel (unlike `project.ts`'s split pair).
- **Form initial state lives in the client islands** (`mint-org-credential-form.tsx` / `revoke-org-credential-button.tsx`), never in `actions.ts` — rule 1 above, and the rule green CI cannot prove. It was re-verified by re-reading the file after editing.
- **`revalidatePath("/dashboard")` takes no second argument** in both new actions — `/dashboard` is a static route, unlike `/projects/[projectId]`, so rule 3's pattern form does not apply here.

**Workspace → Org is complete in the app.** `content/app.ts`'s `workspaceLabel: "Workspace"` became `orgLabel: "Org"` — **key and value both**, since a `workspaceLabel` key holding `"Org"` would mislead the next reader — along with its one consumer in the app shell and the auth copy ("Access your org, projects, and feedback."; the signup sub now says an org and a default project are created for you). **Only label values changed**: `tenant_id`, `tenants[]`, `VockyTenant`, and every route are untouched. Landing copy (`content/landing.ts`) was deliberately left alone — it belongs to P11.

**Near-unreachable empty states were kept, not deleted.** `DASHBOARD.projects.empty`, `DASHBOARD.trend.empty`, and `FEEDBACK.list.emptyNoProjects` became near-unreachable once signup provisions a project, but they cost nothing, the state is still representable, and nothing guarantees an org keeps a project forever. Only their rationale comments were updated.

### Project detail — and the show-once key

The page now leads with a **breadcrumb** (`<nav>`: a `Dashboard` link + `/ {project.name}`, reusing the already-loaded `project.name` — no extra fetch), above the title. Credentials render from **`usage.credentials`**, which deliberately diverges from the dashboard's "ignore the usage copy" rule — and principled: there the usage copy was a *narrower* serializer, here it is the *identical* `serialize_credential`, bundled by `_project_usage_response` **by design** for this page (the page exists to surface `last_used_at`). Consequently there is **no `listCredentials`** function — it would be dead code, since `revalidatePath` refetches usage and credentials together.

**The plaintext `vk_` key is the app's only handling of a secret**, and its one deliberate exception to "no vocky data crosses a client boundary":

- `createCredential` returns the **whole envelope** (`VockyMintedCredential`) — unwrapping to `VockyCredential` would discard the only copy of the key that will ever exist.
- The key crosses to the client in the **action state**, not the server-rendered tree. That placement is what makes the panel **survive `revalidatePath`'s re-render** yet **vanish on the next submit or navigation**. It is never logged, never in a URL, never persisted.
- The show-once panel is a **green-tinted card** (`border-mint bg-surface-green` — `border-security-mint` before the P12.S2 rename) with the full warning string verbatim (`PROJECT.keyPanel.warning`, a locked floor) and Copy/Dismiss controls.
- Dismissal is keyed by the action state's `ok` stamp, not a boolean flag — a sticky `dismissed` flag would silently swallow the *next* minted key, the one case where a missed render is unrecoverable.
- After a reload only the 12-char `token_prefix` stub remains. Credential status derives from `revoked_at === null` (vocky has no `status` field): Active → **`Badge variant="active"`**, Revoked → **`Badge variant="revoked"`** (was the placeholder `softGreen`/`archive`). **Revoked keys stay listed** (auditable history) — a locked floor. The per-row **Revoke** control is `Button variant="destructiveOutline" size="sm"` behind a two-step confirm.

**404 policy (extends to the feedback surfaces).** Fetches sit in a helper so `notFound()` never sits inside the `try`. `ApiError` **404 or 400** → `notFound()`: a malformed id is effectively not-found, and distinguishing the two leaks the shape of what exists. Everything else rethrows — an outage should surface, not masquerade as a missing project.

### Feedback list, search, and detail

The flagship read surface, and **read + search only** — feedback management lives on the `vk_`-keyed `/api/project/feedback`. Read-only here is **structural, not merely intended**: the detail page has **0 `<form>` elements** and the whole surface adds **0 server actions**.

- **The filter bar is a plain `<form method="GET">` with no client island** — it needs no `useSearchParams`/`router.push`/debounce, and submitting naturally drops `cursor`, which is exactly "a new query resets to page 1". The two filter controls (Project, Rating) are now **`<Select>`** (native `<select>`, a11y kept), which **retired the `inputVariants()` template-literal `<select>` hack**.
- **Blank params are OMITTED, never sent.** This is load-bearing, not tidiness: a GET filter form *necessarily* submits its empty fields, and vocky **400s** on a blank `project_id`/`feedback_value`/`tag`/`cursor`. `getJson`'s bare-concat URL makes a `?` in `path` safe, so `URLSearchParams` builds the query — and never `encodeURIComponent` on top of it (that double-encodes Korean into oblivion).
- **`searchParams` is a `Promise` in Next 16**, and a value is **`string[]`** for a repeated key (`?q=a&q=b`) — a wrinkle `params` never had. Take-first, mirroring vocky's own `query_params.get()`.
- **Pagination is forward-only** (keyset yields no prev-cursor; each page is its own URL, so browser Back *is* Prev). **The cursor does not encode filters** — every page link resends them all. **`next_cursor` is an omitted key, never `null`** → test `!== undefined`; a `!== null` test pages forever.
- The UI exposes `q` + `project_id` + `feedback_value` while the client carries **all 17** query fields (P14 added `recorded_by`); URL-only ones survive as hidden inputs / link params.
- **`recorded_by` is a URL-driven filter only (P14).** `/feedback?recorded_by=agent` narrows the list to agent-recorded feedback and survives a filter submit and pagination, because the key is in `PARAM_KEYS` (the URL allowlist, where blank ⇒ absent is load-bearing) and narrowed in `toQuery` like the other enum params. **`FORM_FIELD_KEYS` was deliberately not touched** — there is no rendered control, and adding a visible agent/human chip or an agent-vs-human split view **is product visual design**: it belongs to Claude Design under the `design-cowork` skill in a design-bearing phase, not to a contract slice. The record interface is **`VockyFeedback`** (`recorded_by: string | null`) and the query type takes the literal union `"agent" | "human"`.
- Adding a fifth name to `toQuery`'s destructure pushed it past one line, so **prettier reformats that block** — CI runs `format:check`, so run `prettier --write` on `web/src/app/(app)/feedback/page.tsx` after touching it.
- **Two distinct empty states** — "no projects yet" is not the same message as "no feedback matches these filters" (a locked floor).
- **Timestamps are pinned to UTC** ("Times are shown in UTC, newest first"). These render *server-side*, so an unpinned zone silently prints the deploy box's clock as if it were local.
- **The detail page's metadata list is the established home for a new record field.** P14 added one `<Field label={FEEDBACK.detail.fields.recordedBy}>` row before the Trigger row — filling an existing pattern, not designing one. `Field` renders `children ?? <Empty />`, so a `null` marker shows the same em-dash the neighbouring nullable fields do and needed **no** null handling of its own; the row's label lives in `web/src/content/feedback.ts` like every other label.
- `feedback-fields.tsx` colocates `formatUtc` / `Timestamp` / `RatingBadge`, shared by list and detail. `RatingBadge` now maps `1`/`2`/`null` → the `liked`/`disliked`/`unrated` **Badge** variants (the old muted-`<span>` null branch is gone; `null` now reads as an explicit `unrated` badge). Detail-page tags render as **`<Chip>`**. Deliberately **not** a `@/components/ui` primitive: both encode vocky's shapes (`1|2|null`, UTC ISO), while the `ui/` kit stays domain-free.
- **Feedback-list active-filter chips were deliberately NOT built** — `build-prompt.md §5/§4.9` marks them **optional**, and a *removable* `Chip` needs a client `onRemove` parent, which would break the page's no-client-island GET-form invariant. This is a spec-sanctioned omission (the page design is preserved), not a dropped element; if ever wanted, do them **link-based** (server-friendly), never with the client `removable` Chip.

### The attachment proxy (`/api/app/feedback/[id]/attachments/[id]`)

The browser has no bearer, so the route relays server-side via `getRaw` and **forces `Content-Disposition: attachment`** (a locked floor: attachments **download, never render inline**). That force is a security control, not a UX choice — see `security.md`. It also sends `X-Content-Type-Options: nosniff` and `cache-control: private, no-store`, and maps vocky's 401 → 401 (a dead session means the same thing; routing it to 500 would blame us), 404 → 404, malformed ids → 400, everything unexpected → 500.

## The public landing (`/`) and the net-new states

**The landing** (`page.tsx` + `content/landing.ts` + `components/landing/*`) is P9's largest net-new surface. `page.tsx` is a server component: `getSession()` → `redirect("/dashboard")` for a live session, else it renders `LandingNav · main#main-content · LandingFooter`. Outside `(app)`, so it renders its own chrome. Copy is a single grounded `LANDING` const (hero with a real `POST /api/feedback` JSON body incl. a Korean `message`, trust strip, how-it-works, showcase, six features, Free-now/paid-later pricing, closing CTA, footer) — no lorem, no fake routes: doc links resolve to the real `github.com/leetusik/vocky` repo (README / GitHub / MIT `LICENSE`), never a fabricated `/docs`. The pricing "coming later" control is **disabled copy — no waitlist endpoint** (§9). `Reveal` is used sparingly on below-the-fold bands only; `break-keep` guards every Korean body example.

**The hero payload was corrected in P11 (`S1`) before anything was designed on top of it.** It had published two falsehoods: a top-level `"source_product"` (the capture *request* nests it as `source.product`) and a `vk_live_9f3c…` auth line implying an environment-tiered key format vocky has never had. Both are gone: the body is `"source": { "product": "checkout-web" }` and the auth line reads `Bearer vk_9f3c…`. `vk_live_` appears nowhere in `web/` or `src/`; the only occurrences in the repo are three **read-only** design-record files under `docs/reference/design/` that document the correction in negation form, and `source_product` survives only as the **read**-path field name (feedback pages, `lib/vocky/types.ts`) — which is correct and must not be "fixed".

## P11: the onboarding surfaces on the landing

**Design round 02** (`docs/reference/design/rounds/02-onboarding/`, gate closed 2026-07-29, SIGNOFF recorded) added three onboarding surfaces to `/` with a **token delta of `None`** — no `globals.css` change, no new or renamed token. The new vocabulary is composition, not tokens: the caution family shipped unused in round 01 and now carries the trap treatment. `output/build-prompt.md` is the read-only implementation contract; the card set stayed in the design project.

**Page composition is now** `LandingNav · Hero · TrustStrip · HowItWorks · AgentQuickstart · SkillSection · Showcase · Features · Pricing · ClosingCTA · LandingFooter`. The nav is a **five-link reorder**, not an insert — `How it works · Get started · Features · Pricing · Docs`; `#skill` deliberately gets **no** nav link, and the landing footer was left alone (the design says nothing about it).

- **The hero install row** is appended *below* the existing two-column grid, inside the hero container. Nothing inside the grid changed. It carries `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` in a `Snippet`, a micro label, and a caption that swaps at `app:` (900px) purely in CSS — both variants ship in the server HTML. `Start free` stays the primary CTA; the install row is never a filled button.
- **`AgentQuickstart`** (`#quickstart`) is a server component: four numbered steps (install → export the two variables → verify → capture), a `Trap` for the Codex `workspace-write` network default, a note recommending `~/.zshenv` over a repo `.env`, a `ReadingList` for the verify step's `400`/`401`/else readings, a peer line into `#skill`, and a sticky contract aside. Two normative content rules: **`400` is the success reading** on the verify step (the token authenticated; a bare `GET` was rejected for a missing filter), and **`401` says stop — never retry, never fall back**, because the published skill says so and the page must not contradict it.
- **`SkillSection`** (`#skill`) is a sticky pitch beside `SkillPreview`, which **reads `public/SKILL.md` at request time** (`fs.readFile(path.join(process.cwd(), "public", "SKILL.md"))`) and computes its own line and byte counts from what it just read. **Hardcoding a count, or pasting an excerpt, is forbidden** — either would fork silently from the `scripts/skill_parity.py` byte gate while CI stayed green. `Copy the skill` copies the pane's `textContent`; `Download SKILL.md` is a plain `<a href="/SKILL.md" download>`.

### Three mechanics the landing did not have before

1. **The mount gate.** Copy buttons are client islands that render **only after hydration**, so a visitor without JS sees *no button at all* — never a present-but-inert control. The gate is `web/src/lib/use-is-hydrated.ts`: `useSyncExternalStore(subscribe, () => true, () => false)` with a module-level stable `subscribe`. **It is deliberately not `useState` + `useEffect`** — `react-hooks/set-state-in-effect` (React Compiler rules, bundled in `eslint-config-next`) rejects a synchronous `setState` in an effect body as an *error*, so the effect form does not pass `pnpm lint`.
2. **The clipboard rule.** The clipboard always gets the **rendered DOM node's `textContent`**, never a separately-typed string — that is why `command` is rendered into a ref'd `<code>`/`<pre>` and read back at click time, and why the block's recoloured comment lines are still copied verbatim. The decision logic lives in the DOM-free `web/src/lib/clipboard.ts::attemptCopy`, so it is testable in the Node-env suite. States are deliberately **asymmetric**: success reverts after exactly **2000ms** (timer cleared on unmount), failure **persists** until the next attempt and instead selects the text programmatically (`Range` + `Selection`) with a hint naming ⌘C/Ctrl+C. One **polite** live region per snippet, success only — **no `role="alert"` and no `aria-live="assertive"` anywhere in round 02**, and `Trap` is an `<aside>`, not an alert.
3. **The request-time `fs` read.** `/` was already `ƒ (Dynamic)` (it reads the session cookie), so the read is safe, and `output: "standalone"` + the Dockerfile's `COPY … /app/public` make `process.cwd()/public/SKILL.md` correct at runtime. **The path must stay statically analyzable at the call site**: building it from a spread array constant made Next trace the whole project into the standalone output ("Encountered unexpected file in NFT list"); literal segments cleared it. `pnpm build` is warning-free — **a new warning there is a regression, not noise.**

### The no-JS floor is a locked floor, and it is regression-tested

`SkillPreview` ships the **whole file** — all 119 lines — in the server HTML in **both** states. "Collapsed" is a *visual* window only (a 300/380px scroller plus a fade; expanded raises the cap to 480/640px and fades the overlay to `opacity-0`) — **the body DOM is identical**. Truncating the server output to the design's 22-line window would pass typecheck, lint, build and every CI check while silently breaking the floor and making the no-JS footer (`<n> lines · scroll to read`) a lie. Three `*-ssr.test.ts` files assert this in CI with `renderToStaticMarkup` and no jsdom: the snippet, the whole quickstart (all four snippets at once), and the skill pane (asserting on the file's **last** section, `not.toContain("<button")`, the computed counts, and the download anchor). Verified against a real `next start` too: the fetched pre-hydration HTML for `/` contains **exactly one** `<button` in the whole document — P9's pre-existing disabled Pricing CTA — and zero inside either new section.

A related trap for anyone editing the pane: HTML drops a newline immediately after a `<pre>` start tag and React's server renderer emits a **compensating extra `\n`**, so the raw HTML carries one more newline than the file while the parsed `textContent` carries exactly the file's. **Do not "clean up" that leading newline** — it is what keeps the copied bytes identical to what `/SKILL.md` serves.

### Design-fidelity decisions worth keeping

- **Both new sections keep `Section`'s shipped padding** (`py-section` / `md:py-section-lg` = 72/104px, gutter `px-5 md:px-14`) rather than the contract's literal `Padding: 84px 28px`. This is a **deliberate, argued departure**, made once and applied to both sections identically: `28px` is not the landing's shared gutter, so honouring it would visibly misalign these two bands' content edge from every neighbour; the identical padding string on two structurally different sections reads as design-tool boilerplate (the same artifact class as the `.eyebrow`/`.note`/`.tag`/`.card` specimen classes that have no repo counterpart); and `Section` is a shared primitive whose whole job is one padding rhythm. The **`container: 1180px`** half *is* honoured exactly (`max-w-page`).
- **The narrow breakpoint is `app:` (900px), never `md:`** — `--breakpoint-app: 56.25rem` is exactly the `< 900px` the design specifies. Arbitrary bracketed values were verified **compiled** in `.next/static/chunks/*.css` rather than merely accepted by `tsc`; Tailwind silently drops a malformed arbitrary value.
- **Composite `--text-*` tokens bundle their own `font-weight`** — never stack a `font-bold` over `text-caption`/`text-micro`; use an explicit `text-[12px] font-bold` instead. A spec'd `border-radius: 6px` is **`rounded-sm`** in this repo (`rounded-md` is 8px here — a repo-specific redefinition).
- The **focus ring and reduced-motion rules are already global** (`globals.css`), so round 02's a11y floor cost one `tabIndex={0}` on the pane scroller and one `aria-expanded` — **no P11 commit touched `globals.css`**.

**RESPECT THE DESIGN** governed every apply slice and held: nothing designed was dropped, simplified or restyled to save effort, and the one departure above is recorded with its argument rather than quietly taken.

## Site Metadata, the Public Origin, and the Production Image (P6)

P6 finished the landing's public-facing edges without opening a new design round — every asset is assembled from the **existing** round-01 brand (the `Mark` geometry, the wordmark, the `globals.css` tokens). A bespoke OG illustration would have been its own design gate; it was deliberately not done.

**The six metadata routes** live under `web/src/app/` as Next 16 file conventions, not in `public/`:

- **`icon.svg`** — a static SVG favicon: the Mark's green tile plus its three rising white bars, at literal colors.
- **`apple-icon.tsx`** (180×180) and **`opengraph-image.tsx`** (1200×630) — `next/og` `ImageResponse` routes. The Mark is **rebuilt with divs** (Satori renders no `<svg>` from a React component tree the way the browser does), and both use the **default ImageResponse font**. Loading the vendored *variable* Pretendard woff2 here is a known Satori failure mode and was deliberately avoided; the OG card's only text is the wordmark and one real line of `LANDING.hero.headline`.
- **`robots.ts`**, **`sitemap.ts`**, **`manifest.ts`** — `MetadataRoute` generators. `robots` allows `/` and disallows the authenticated + BFF surface (`/dashboard`, `/projects/`, `/feedback`, `/api/`); the sitemap contains **only `/`**, because it is the only public page. **Adding a public route means extending `sitemap.ts`** — nothing does it automatically.

`layout.tsx` gained `openGraph` and `twitter` (`summary_large_image`) metadata; Next injects `og:image`/`twitter:image` from the `opengraph-image` route automatically. `SITE.description` was rewritten from an internal "tenant dashboard" line to grounded marketing copy drawn from the landing hero.

**`NEXT_PUBLIC_APP_URL` is the single origin knob**, and it is **build-time, not runtime**. `SITE.url` reads it (blank → `http://127.0.0.1:3030`), and from there it drives `metadataBase`, the canonical + OG URLs, `robots`'s `host` and `sitemap`, and the sitemap `loc`. Because Next inlines `NEXT_PUBLIC_*` at build, a missing value bakes the localhost origin into the image — so `web/Dockerfile` declares `ARG NEXT_PUBLIC_APP_URL` and **asserts it non-empty before `next build`**, and `compose.prod.yml` passes `https://vocky.hi2vi.com` through the web service's `build.args`. **Changing the public origin requires an image rebuild.**

**The production image** (`web/Dockerfile`, P6) is a multi-stage `node:22-slim` build: pnpm frozen install, `pnpm build`, then a runtime stage carrying `.next/standalone` + `.next/static` + `public/`, running `node server.js` as `USER node` on `EXPOSE 3000` with a fetch-based `HEALTHCHECK`. One trap is worth remembering: **the build stage must not set `NODE_ENV=production`** — pnpm would prune `typescript` / `tailwindcss` / `@tailwindcss/postcss` / `eslint-config-next` and the build would fail. `web/public/` used to hold only a `.gitkeep` so the runtime `COPY /app/public ./public` resolves; **as of P11 it holds two real served artifacts** — `install.sh` and `SKILL.md` — which that same `COPY` ships. Every image/metadata asset still comes from the `app/` routes above. Details in `operations.md`.

**The net-new states** (`build-prompt.md §6`) are real designed surfaces, not framework defaults: `(app)/loading.tsx` (a stat-tile + chart skeleton, `feedback/loading.tsx` for the list's different shape), `(app)/error.tsx` (a danger-tinted Mark boundary that **never renders `error.message`** — a security floor), root + in-app `not-found.tsx` (the **404-never-403** subcopy — *"…isn't here — or isn't yours to see"* — single-sourced in `STATES.notFound.body`), and `global-error.tsx` (own `<html><body>`). Copy lives verbatim in `content/states.ts`. Skeletons are static under reduced motion (`animate-pulse motion-reduce:animate-none`, `aria-hidden` with an `sr-only role="status"` sibling).

## Testing

`web/tests/` — **78 vitest tests across 10 files**, kept terse per the repo's small-tests rule: `session.test.ts` (seal/open round-trip, IV/ct/tag tamper → null, expiry, rotated secret, fresh IV, cookie attrs, `assertSameOrigin`), `vocky-auth.test.ts` (the tenant-asymmetry normalization), `auth-routes.test.ts` (415/403/400/422/429, 200 + a cookie that opens back to the exact stub token, 401 without leaking detail, pass-through vs 502, per-route throttle buckets, logout never-fail-open), `session-guards.test.ts`, `vocky-app.test.ts` (envelope unwrapping, outgoing path + bearer, the `daily_counts: []` zero-project shape, the query-string builder). P9's visual apply added no test regressions. **P10 added 5** — three `describe` blocks for the org-credential trio plus a null-`project_id` `ORG_CREDENTIAL` fixture — and **rewrote** the old "keeps duplicate-named projects distinct" case, which asserted a scenario the backend can no longer produce; it now asserts what is still true (the client keys on `id`, not `name`). That test had been passing either way, so the rewrite fixed its name and rationale, not a behavior.

**P11 added 17 across 5 new files**, each aimed at a failure mode that would otherwise ship green: `clipboard.test.ts` (3 — `attemptCopy`'s three outcomes, including a *read* that throws), `landing-copy.test.ts` (3 — the three commands a visitor is invited to **paste**, re-spelled as literals, with the install line additionally checked against `web/public/install.sh` so the landing and the installer cannot drift apart), and the three `*-ssr.test.ts` files (11 — the no-JS floor asserted where it is actually decided, the server HTML). **The suite is `environment: "node"` with no jsdom and no RTL** (`include: ["tests/**/*.test.ts"]` — `.ts` only), so component tests are structurally impossible and testable logic must be extracted into pure `.ts` helpers. `renderToStaticMarkup` from `react-dom/server` is the seam that makes pre-hydration HTML assertable anyway; importing a `"use client"` module from a Node test is fine (the directive is just a string). What it **cannot** reach, and what therefore stays verified by reading rather than by machine: the 2000ms revert, the `Range`+`Selection` failure path, the live-region announcement, hover/focus visuals, and every `< 900px` layout.

`vitest.config.ts` aliases `@` → `src` and stubs `server-only` (the real package throws by design). That alias affects **only** the test run — `next build` resolves the real package, so the client-bundle guarantee stands.

**The gate is `pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build`.** It is necessary but **not sufficient**: the phase's two sharpest bugs (the `"use server"` object export; the `Secure`-cookie dev/prod split) both passed the full gate and were caught only by a live run. Verify user-visible behavior against a running vocky on `pnpm dev` (P9's DoD sweep did exactly that — a broad live-backend smoke across every surface). **Known pre-existing debt:** `pnpm format:check` exits 1 at the repo level, now on **14 files** — the 12 P4-era backend/lib/test ones (`README.md`, `projects/[projectId]/actions.ts`, `apple-icon.tsx`, `opengraph-image.tsx`, `lib/bff.ts`, `lib/env.ts`, `lib/session.ts`, `lib/vocky/auth.ts`, and four test files) plus **two new in P11**: `landing/agent-quickstart.tsx` (net-new) and `landing/hero.tsx` (touched), both solely from `prettier-plugin-tailwindcss` class-list reordering. **`prettier --check` is deliberately not in CI** (see `operations.md`), so this is cosmetic and gates nothing — but it is recorded precisely so a later formatting sweep does not undercount. Reformatting all 14 remains a deferred-job candidate for P12, deliberately not folded into a feature slice.

## Frontend Constraints

- **Session-token client only** — `/auth/*` + `/app/*`. Never the `vk_`-keyed `/api/*` surface. (`web/src/app/api/**` are the app's *own* BFF routes on the Next origin; do not confuse them with vocky's `/api/*`.)
- The vocky token **never** reaches browser JS; the browser talks only to the Next origin. No CORS change to vocky; no web-side DB.
- Both env keys are **server-only** — `VOCKY_API_BASE_URL` and `SESSION_SECRET`, neither `NEXT_PUBLIC_`, both read lazily through `src/lib/env.ts` (`import "server-only"`).
- The `vk_` plaintext key is shown **exactly once**, never re-rendered, never logged; revoked keys stay listed. This holds at **both** scopes and is enforced by one shared `ShowOnceKey` component — do not re-privatize it or fork the dismissal logic.
- **`VockyCredential.project_id === null` means "org key"**, and it is the only signal the backend gives. Narrow it at the consumer with an explicit guard; never cast, and never fork the shared credential type to dodge the null.
- **Org keys belong on the dashboard, project keys on project detail**, and the two never cross: `/app/projects/{id}/usage` does not return org keys, and `/app/credentials` does not return project keys. A panel that shows both would be showing something the API deliberately keeps disjoint.
- **404-never-403** on foreign/cross-tenant ids, mirroring the backend; the not-found copy never confirms existence.
- Cross-project feedback is **read + search only**; `?q` must stay Korean-safe (substring, never tokenized).
- **No dark-mode toggle** (light-only, confirmed). **The token *names* stay stable** — the vocky brand is a names-kept value swap; a future rebrand swaps values, and any name-retirement pass is its own mechanical slice (`build-prompt.md §2.4`), never mixed into a visual change.
- **RESPECT THE DESIGN** — rounds 01 and 02 are applied as designed (layout, density, tokens, interactions, states, no-JS behaviour); each round's `build-prompt.md` acceptance checklist is the definition-of-done. Don't drop, simplify, or "improve" a designed element to save effort; where an exact value is unspecified, pick the option closest to the designed intent, never a plainer fallback.
- **The no-JS floor on the landing is a locked floor.** Copy buttons must be *absent* pre-hydration, never inert; the skill pane must ship the **whole** file in the server HTML (collapsing is visual only); `Download SKILL.md` stays a plain `<a download>`. The three `*-ssr.test.ts` files are the CI proof — do not weaken them.
- **The skill pane's counts are computed from the served file, never hardcoded, and it never renders a pasted excerpt.** Either would fork silently from the `scripts/skill_parity.py` byte gate while CI stayed green.
- **`web/public/` now holds real served artifacts** (`install.sh`, `SKILL.md`), not just a `.gitkeep`. `web/.prettierignore` excludes `public/` — **do not undo it**; a prettier markdown reflow would break the skill's byte parity on the first `pnpm format`.
- Attachments **download, never render inline**; the identical-login-error mapping lives in the form/BFF and must not change; `FieldError` keeps its empty `min-h-[1.25rem]` `aria-live="polite"` region; `word-break: keep-all` and a Korean-capable `--font-sans` are preserved.
- Copy belongs in `src/content/`, not inline in components.
- **`NEXT_PUBLIC_APP_URL` is build-time.** Never treat it as a runtime setting; changing the public origin means rebuilding the web image. It is the only `NEXT_PUBLIC_` var the app has, and it carries no secret.
- **The production CSP is all-`'self'`.** Introducing any third-party script, font, image, or fetch origin requires editing the directive string in `next.config.ts` — and self-hosting remains the default answer. Never set HSTS in the app; that is the edge's.
- **Adding a public route means updating `robots.ts` and `sitemap.ts`.** Neither is generated from the route table.
- **The app is deployed.** The image + compose + vhost (P6) all ran for real at **P12**; `vocky-web` is healthy in production behind the shared edge.
