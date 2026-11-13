---
doc_id: frontend
version: v0002
created_at: 2026-07-16T23:25:16+09:00
source: P4.REVIEW
summary: "P4: the vocky web app — Next.js 16 app in web/, ported Tailwind-v4 design system, server-side BFF + sealed-cookie session, and the dashboard/project/feedback page inventory"
previous: v0001_bootstrap
---

# Frontend

## Status

Vocky has one frontend: the **authenticated web app** in `web/` (P4). It is a Next.js 16 / React 19 / TypeScript app that talks to vocky's `/auth/*` + `/app/*` surfaces through a **server-side BFF proxy**, and it is the browser surface that replaces the packaged same-origin operator Admin Web UI (`src/vocky/admin_ui.py` + `admin_assets/*`). The replacement is **built** as of P4; the physical removal of the old admin UI is deferred to **P6**, so no browser surface disappears in the interim.

P4 delivered signup/login/logout, the app shell, the tenant dashboard, project detail (with credential mint/revoke), and cross-project feedback list/search/detail. What is **not** here yet: the vocky brand palette (P4 ships a neutral placeholder — see "Design System"), the landing page, and the production deploy — all **P6**.

The app is a **session-token client only**. It calls `/auth/*` and `/app/*`; it never touches the `vk_`-keyed `/api/*` surface, which is the external-service credential path. There is no web-side database.

## App Location and Stack

The app is a subdirectory of this repo (**D-P4-1**), versioned and committed by the same workflow engine as the backend. "hi2vi_web-style" (the operator's reference, `~/projects/personal/hi2vi_web`) means **stack, patterns, and the Claude design-gate workflow** — not repo topology; hi2vi_web is a template we port from, not a vendored dependency.

- **Next.js 16** (App Router, Turbopack) / **React 19** / **TypeScript**, package manager **pnpm** (`packageManager: pnpm@10.28.2`, node `>=22.13.0`)
- **Tailwind v4**, CSS-first (`@theme` in `globals.css`); there is no `tailwind.config.*`
- Runtime deps are deliberately few: `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `tw-animate-css`, `server-only`, `zod`
- `next.config.ts` sets `output: "standalone"` (build-only; emits `.next/standalone/server.js` for the P6 deploy) plus generic security headers (`nosniff`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options: DENY`). A full CSP/HSTS and the edge/nginx wiring are P6.
- Scripts: `dev` / `build` / `start` (all bound `127.0.0.1:3030`), `lint`, `typecheck`, `test` (vitest), `format`

## Directory Shape

```
web/
  src/app/
    layout.tsx            root layout (fonts, globals.css, metadata)
    page.tsx              "/" → auth redirect (signed in → /dashboard, else → /login)
    globals.css           the @theme token system
    (auth)/               PUBLIC, unguarded: login, signup (+ auth-card, credentials-form)
    (app)/                GUARDED: layout.tsx awaits requireIdentity()
      dashboard/          page + actions.ts + create-project-form.tsx
      projects/[projectId]/  page + actions.ts + mint-credential-form + revoke-credential-button
      feedback/           page + feedback-fields.tsx + [feedbackId]/page.tsx
    api/
      auth/{login,signup,logout}/route.ts     the BFF credential routes
      app/feedback/[feedbackId]/attachments/[attachmentId]/route.ts   binary proxy
  src/components/
    ui/                   CVA primitives (the design system)
    app-shell/            app-shell, rail-nav, logout-button
    usage/                stat-tiles, trend-chart (shared by dashboard + project detail)
  src/content/            copy-as-data
  src/lib/
    session.ts            AES-256-GCM seal/open + cookie options + guards
    auth-guards.ts        requireIdentity / redirectIfAuthenticated
    bff.ts                the audited BFF credential pipeline
    env.ts, rate-limit.ts, client-ip.ts, fonts.ts, utils.ts (cn)
    vocky/                client.ts, auth.ts, app.ts, types.ts — the server-side API client
  design/canvas/          design-gate mirror (tokens.css, _ds_manifest.json, cards)
  tests/                  vitest (56 tests, 5 files)
```

**Route-group semantics:** `(auth)` is deliberately **unguarded** (otherwise `/login` could not be reached); `(app)` is guarded once in its `layout.tsx`. Non-route files (forms, field helpers) are colocated in the route folder — only `page`/`route`/`layout` files become routes.

## Design System (ported, P6-swappable) — D-P4-3

P4 **ports** hi2vi_web's design system and builds functional pages; the intensive operator design session is deferred to **P6** (with the landing page).

- **Tokens** — `src/app/globals.css` keeps hi2vi's 4-part skeleton: `@theme` tokens → `:root` shadcn aliases → `@theme inline` bridge → `@layer base`. **There is no dark-mode toggle and no `.dark` block** — surfaces are explicit tokens. Kept from the template: the `[data-reveal]`/`.is-visible` scroll-reveal rules, the focus ring, the reduced-motion block, and `h1–h6 { word-break: keep-all }` (Korean line-breaking).
- **Palette is a neutral PLACEHOLDER**, not vocky's brand: a slate surface ramp + one indigo accent (`green #6366f1`) + red/amber signals. It deliberately **keeps hi2vi's token *names*** (`green*`, `ink`, `forest*`, `charcoal`, `slate`, `steel`, `muted`, `danger`, `caution`) so the P6 design gate swaps **values only**, never call sites. One semantic flip was required: `on-primary` went `#061512` → `#ffffff` (hi2vi's bright-green CTA took dark text; the indigo accent needs white).
- **`cn()`** (`src/lib/utils.ts`) — `clsx` + `extendTailwindMerge`, with the `font-size` group registering the custom `text-*` scale so `text-body-sm`-style tokens merge correctly.
- **Fonts** (`src/lib/fonts.ts`) — `next/font/google`, build-time self-hosted: **Noto Sans KR** (`--font-sans`, chosen because feedback content is Korean) + **JetBrains Mono** (`--font-mono`). The `--font-en` token name is retained but points at a system stack; hi2vi's 8 self-hosted faces and Korean-clip micro-subsets were not copied.
- **Primitives** (`src/components/ui/`, CVA + a barrel `index.ts`) — `button`, `card`, `section`, `field` (Label/Input/Textarea/Checkbox/FieldError), `badge`, `grid`, plus ported `endpoint-card` and `reveal`.
- **`data-table.tsx` is net-new** (hi2vi has no table; projects/credentials/feedback all need one). Headless and generically typed `DataTable<T>`: `columns` (header + `cell` renderer, optional `align`/`actions`), `rows` + `rowKey`, an `overflow-x-auto` wrapper, `text-caption` headers, hover rows, and an `empty` slot. Purely presentational — data arrives as props, never fetched.
- **Copy-as-data** (`src/content/`) — user-visible strings live in typed modules (`site`, `nav`, `app`, `auth`, `dashboard`, `project`, `feedback`) re-exported through `index.ts`, not inline in components.
- **`design/canvas/`** — the design-gate mirror: `tokens.css` (a 1:1 `:root` mirror of the `@theme` values), `_ds_manifest.json` (namespace + 125 mirrored tokens + fonts + 10 cards), and `foundations/`, `components/`, `sections/` HTML cards each carrying the `<!-- @dsCard … -->` first-line marker. The DesignSync/`SIGNOFF` convention is scaffolded; the heavy session is P6.

## The BFF and the Session Model — D-P4-2

The browser talks **only** to the Next.js origin. The Next.js server talks to vocky server-to-server with `Authorization: Bearer`. **No CORS change to vocky was needed, and there is no web-side DB.**

### The sealed session cookie

The vocky session token is sealed into an httpOnly cookie the Next app sets for itself — it never reaches browser JS.

- Cookie **`vocky_session`** = **`v1.<iv>.<ct>.<tag>`** (each part base64url), **AES-256-GCM**, key = `sha256(SESSION_SECRET)`, a fresh random 12-byte IV per seal. Sealed plaintext is JSON `{token, exp}`.
- Attributes: `httpOnly`, `SameSite=Strict`, `path=/`, `maxAge` **30d** (deliberately matching vocky's own token TTL), and `Secure` **only** when `NODE_ENV === "production"`.
- `openSession` returns the token or **`null` for every failure** — wrong shape/version, GCM tag mismatch (tampering), bad JSON, expired `exp`, rotated/missing secret. It never throws, so callers treat "no session" uniformly.
- The guards (`getSession` / `requireSession`) **return the decrypted vocky token** for bearer injection rather than just gating — the deliberate departure from hi2vi's template (which HMAC-signs a self-minted token and returns void).

> **Dev-vs-prod gotcha (bit S4, cost a wasted run):** because `Secure` is set under `NODE_ENV=production`, a plain-http client on `127.0.0.1` never replays the cookie and **every guarded page silently bounces to `/login`**. Drive local end-to-end runs on **`pnpm dev`**, not `pnpm start`. (Real browsers treat `127.0.0.1` as a secure context and are fine; scripted http cookie jars are not.)

### The BFF credential routes

`src/app/api/auth/{login,signup,logout}/route.ts` (`runtime="nodejs"`, `dynamic="force-dynamic"`) are the app's **only** public unauthenticated POST surface. Their ordered checks are factored into one audited pipeline, `src/lib/bff.ts::handleCredentialRoute`, so the security path has a single copy rather than two near-identical ones:

```
JSON-only 415 → assertSameOrigin 403 → per-IP rate limit 429 → parse 400 / zod 422 → vocky call → seal into cookie, 200
```

- **vocky's `detail` is never echoed** — the response body is only `{ok}` and the client keys off the status. Pass-through statuses: login `[401, 400]`, signup `[409, 400]`; any other upstream error → 502; config/transport → 500.
- **Rate-limit buckets are namespaced** (`auth-login:` / `auth-signup:` + IP) — login is the stricter throttle (5/15min) vs signup (10/15min). hi2vi's template keyed on the bare IP, which would let login attempts drain signup's budget; the namespacing fixes that latent bug and a test locks it.
- **Logout** revokes at vocky best-effort, then **unconditionally** clears the cookie — it never fails open.

### Guards and the redirect-loop fix

`src/lib/auth-guards.ts` composes session + vocky, keeping `session.ts` vocky-agnostic:

- **`requireIdentity()`** — gates `(app)`; it is `cache()`d so the layout and the page share **one** `/auth/me` per request. It signals "no session" by `redirect()`, which works **by throwing**.
- **`redirectIfAuthenticated()`** — the `(auth)` bounce. It **verifies against `/auth/me` before redirecting**. This is load-bearing: a cookie can be crypto-valid while its vocky token is dead (revoked out-of-band), and a naive bounce would ping-pong `/login` ↔ `/dashboard` forever, since Next forbids clearing a cookie from a server component. Verifying first means a dead cookie simply renders the login form.
- Only **401** redirects. Non-401 errors (vocky down) are **rethrown**, never silently treated as a logout.

### The server-side vocky client (`src/lib/vocky/`)

- **`client.ts`** — the seam: `ApiError` / `toError` / `getJson` / `sendJson` / `getRaw`, adapted from hi2vi's `content-agent/api.ts` to server-side. Absolute URL from `VOCKY_API_BASE_URL`, `Authorization: Bearer` injection, `cache: "no-store"`, errors carrying vocky's `{detail}`, 204/empty-body tolerant. `getRaw` is the raw/binary GET added for attachments (`getJson`'s `parseBody` would `JSON.parse` a PNG).
- **`auth.ts`** — `signup` / `login` / `logout` / `me`, plus `normalizeAuthResponse` / `activeTenant`, which collapse vocky's **tenant asymmetry** (signup returns `tenant` singular; login/me return `tenants[]`) into one `{token, user, tenant}` with `tenants[0]` active — matching vocky's own `require_user`.
- **`app.ts`** — the `/app/*` functions: `listProjects`, `createProject`, `getUsage`, `getProject`, `createCredential`, `revokeCredential`, `getProjectUsage`, `listFeedback`, `getFeedbackDetail`, plus the `feedbackQueryString` builder. House style: private `Raw*` envelope types, `(token, …pathArgs, signal?)` for reads, `signal`-less writes, `encodeURIComponent`'d ids.
- **`types.ts`** — the `/app/*` wire shapes. Note `VockyUsageProject` is a **separate** type from `VockyProject` (the usage serializer omits `tenant_id`), and `VockyProjectUsage` is separate from `VockyUsage` (no `projects`, has `credentials`).

## Mutations: server actions vs BFF routes

The split is a rule, not a preference:

- **Authed mutations are server actions** (`actions.ts`, `"use server"`) — create-project, mint-credential, revoke-credential. Exactly **3** are registered app-wide.
- **BFF route handlers are only the public, rate-limited auth surface** (login/signup/logout) — the one place a caller has no session yet — plus the binary attachment proxy.

Three rules the phase paid for and that any new action must follow:

1. **A `"use server"` file may export ONLY async functions.** Every export is registered as a callable server action; a plain-object export is silently registered as a second action and **500s every submit**. This was a real bug that typecheck, lint, 44 tests, *and* `next build` all passed — caught only by a live run. Form initial-state constants therefore live in the client island.
2. **`requireIdentity()` must be called OUTSIDE an action's `try`.** It redirects **by throwing**; a wrapping `catch` swallows the redirect and renders a bogus "please try again" instead of bouncing to `/login`. The same applies to `notFound()`.
3. **`revalidatePath(pattern, "page")`** on a dynamic route takes the route **pattern** (`"/projects/[projectId]"`), not the resolved href.

Actions map failures **by status** (400/401/404 → copy from `src/content/`), never by echoing vocky's `detail`.

## Page and Component Inventory

| Route | Kind | Notes |
| --- | --- | --- |
| `/` | redirect | signed in → `/dashboard`, else → `/login` |
| `/login`, `/signup` | public | `(auth)` group; `auth-card` + the shared `credentials-form` client island |
| `/dashboard` | guarded | usage stat tiles + daily-trend chart + projects `DataTable` + create-project form |
| `/projects/[projectId]` | guarded | project info + usage + credentials table + mint form + revoke |
| `/feedback` | guarded | cross-project list + filter form + keyset pagination |
| `/feedback/[feedbackId]` | guarded | read-only detail (message, comments, attachments, raw JSON) |
| `/api/auth/{login,signup,logout}` | BFF | the public credential pipeline |
| `/api/app/feedback/[id]/attachments/[id]` | BFF | binary proxy (forced download) |

Every route is `ƒ (Dynamic)` — nothing per-user is prerendered or cached; `next build` needs no env because env reads are lazy.

**The app shell** (`src/components/app-shell/`) is a **server component** — only logout and the pathname-aware rail are client islands, so the server-fetched identity never crosses a client boundary (hi2vi's one-big-island console was a poor fit). It is a sticky topbar (brand · workspace/user · spacer · logout) over a `grid-cols-1 min-[900px]:grid-cols-[248px_minmax(0,1fr)]` `[rail | main]`; below 900px the rail collapses to a horizontal strip.

**`RailNav`** is a client island only because the active item derives from `usePathname()`. An item is active when `pathname === item.href || pathname.startsWith(item.href + "/")` — the prefix rule is what keeps *Feedback* highlighted on `/feedback/[id]`. It also retains a **`soon`** affordance (renders a muted, non-interactive "Soon" tag instead of a link that would 404). **No item sets `soon` today** — `/feedback` was the last, and S5 shipped it — but the mechanism is kept deliberately for P6's new surfaces. Note `/projects/[id]` is not a rail item, so no rail entry is marked current there.

**Usage components** (`src/components/usage/`) are presentational, props-only server components generic over `VockyMetricCounts` / `VockyDailyMetricCount[]`, and are **reused as-is** by both the dashboard (`/app/usage`) and project detail (`/app/projects/{id}/usage`). Because `StatTiles`/`TrendChart` hardcode their `usage-totals` / `usage-trend` DOM ids, a page may render **exactly one** of each. `TrendChart` is ~60 lines of dependency-free inline SVG (`preserveAspectRatio="none"`, `role="img"` + `aria-label` + an `sr-only` peak/total summary, a `<title>` per bar, an explicit `[]` empty state, `maxTotal` floored at 1 so an all-zero series cannot divide by zero) — a real chart library is a P6 design-gate question.

### The dashboard

`requireIdentity()` → `Promise.all([listProjects, getUsage])`. It renders the project list from **`/app/projects` (canonical)** and deliberately **ignores `usage.projects`** (a narrower serializer with its own type). Rows are keyed by `p.id`, never `name` — two projects may share a name and do render as distinct rows. The project name is a `<Link>` into `/projects/[id]`.

It does **not** call `GET /app/tenant`: the shell's topbar already has the tenant from the `cache()`d `/auth/me`, so a second call buys a round-trip and nothing else.

### Project detail — and the show-once key

Credentials render from **`usage.credentials`**, which deliberately diverges from the dashboard's "ignore the usage copy" rule — and principled: there the usage copy was a *narrower* serializer, here it is the *identical* `serialize_credential`, bundled by `_project_usage_response` **by design** for this page (the page exists to surface `last_used_at`). Consequently there is **no `listCredentials`** function — it would be dead code, since `revalidatePath` refetches usage and credentials together.

**The plaintext `vk_` key is the app's only handling of a secret**, and its one deliberate exception to "no vocky data crosses a client boundary":

- `createCredential` returns the **whole envelope** (`VockyMintedCredential`) — unwrapping to `VockyCredential` would discard the only copy of the key that will ever exist.
- The key crosses to the client in the **action state**, not the server-rendered tree. That placement is what makes the panel **survive `revalidatePath`'s re-render** yet **vanish on the next submit or navigation**. It is never logged, never in a URL, never persisted.
- Dismissal is keyed by the action state's `ok` stamp, not a boolean flag — a sticky `dismissed` flag would silently swallow the *next* minted key, the one case where a missed render is unrecoverable.
- After a reload only the 12-char `token_prefix` stub remains. Badges derive from `revoked_at === null` (vocky has no `status` field): Active → `softGreen`, Revoked → `archive`.

**404 policy (extends to the feedback surfaces).** Fetches sit in a helper so `notFound()` never sits inside the `try`. `ApiError` **404 or 400** → `notFound()`: a malformed id is effectively not-found, and distinguishing the two leaks the shape of what exists. Everything else rethrows — an outage should surface, not masquerade as a missing project.

### Feedback list, search, and detail

The flagship read surface, and **read + search only** — feedback management lives on the `vk_`-keyed `/api/project/feedback`. Read-only here is **structural, not merely intended**: the detail page has **0 `<form>` elements** and the whole surface adds **0 server actions**.

- **The filter bar is a plain `<form method="GET">` with no client island** — it needs no `useSearchParams`/`router.push`/debounce, and submitting naturally drops `cursor`, which is exactly "a new query resets to page 1".
- **Blank params are OMITTED, never sent.** This is load-bearing, not tidiness: a GET filter form *necessarily* submits its empty fields, and vocky **400s** on a blank `project_id`/`feedback_value`/`tag`/`cursor`. `getJson`'s bare-concat URL makes a `?` in `path` safe, so `URLSearchParams` builds the query — and never `encodeURIComponent` on top of it (that double-encodes Korean into oblivion).
- **`searchParams` is a `Promise` in Next 16**, and a value is **`string[]`** for a repeated key (`?q=a&q=b`) — a wrinkle `params` never had. Take-first, mirroring vocky's own `query_params.get()`.
- **Pagination is forward-only** (keyset yields no prev-cursor; each page is its own URL, so browser Back *is* Prev). **The cursor does not encode filters** — every page link resends them all. **`next_cursor` is an omitted key, never `null`** → test `!== undefined`; a `!== null` test pages forever.
- The UI exposes `q` + `project_id` + `feedback_value` while the client carries **all 16** query fields; URL-only ones survive as hidden inputs / link params.
- **Timestamps are pinned to UTC** ("Times are shown in UTC, newest first"). These render *server-side*, so an unpinned zone silently prints the deploy box's clock as if it were local.
- `feedback-fields.tsx` colocates `formatUtc` / `Timestamp` / `RatingBadge`, shared by list and detail. Deliberately **not** a `@/components/ui` primitive: both encode vocky's shapes (`1|2|null`, UTC ISO), while the `ui/` kit stays domain-free and P6-swappable.

### The attachment proxy (`/api/app/feedback/[id]/attachments/[id]`)

The browser has no bearer, so the route relays server-side via `getRaw` and **forces `Content-Disposition: attachment`**. That force is a security control, not a UX choice — see `security.md`. It also sends `X-Content-Type-Options: nosniff` and `cache-control: private, no-store`, and maps vocky's 401 → 401 (a dead session means the same thing; routing it to 500 would blame us), 404 → 404, malformed ids → 400, everything unexpected → 500.

## Testing

`web/tests/` — **56 vitest tests across 5 files**, kept terse per the repo's small-tests rule: `session.test.ts` (seal/open round-trip, IV/ct/tag tamper → null, expiry, rotated secret, fresh IV, cookie attrs, `assertSameOrigin`), `vocky-auth.test.ts` (the tenant-asymmetry normalization), `auth-routes.test.ts` (415/403/400/422/429, 200 + a cookie that opens back to the exact stub token, 401 without leaking detail, pass-through vs 502, per-route throttle buckets, logout never-fail-open), `session-guards.test.ts`, `vocky-app.test.ts` (envelope unwrapping, outgoing path + bearer, the `daily_counts: []` zero-project shape, the query-string builder).

`vitest.config.ts` aliases `@` → `src` and stubs `server-only` (the real package throws by design). That alias affects **only** the test run — `next build` resolves the real package, so the client-bundle guarantee stands.

**The gate is `pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build`.** It is necessary but **not sufficient**: the phase's two sharpest bugs (the `"use server"` object export; the `Secure`-cookie dev/prod split) both passed the full gate and were caught only by a live run. Verify user-visible behavior against a running vocky on `pnpm dev`.

## Frontend Constraints

- **Session-token client only** — `/auth/*` + `/app/*`. Never the `vk_`-keyed `/api/*` surface. (`web/src/app/api/**` are the app's *own* BFF routes on the Next origin; do not confuse them with vocky's `/api/*`.)
- The vocky token **never** reaches browser JS; the browser talks only to the Next origin. No CORS change to vocky; no web-side DB.
- Both env keys are **server-only** — `VOCKY_API_BASE_URL` and `SESSION_SECRET`, neither `NEXT_PUBLIC_`, both read lazily through `src/lib/env.ts` (`import "server-only"`).
- The `vk_` plaintext key is shown **exactly once**, never re-rendered, never logged.
- **404-never-403** on foreign/cross-tenant ids, mirroring the backend.
- Cross-project feedback is **read + search only**; `?q` must stay Korean-safe (substring, never tokenized).
- **No dark-mode toggle**; keep the placeholder palette's token *names* stable so the P6 gate swaps values only.
- Copy belongs in `src/content/`, not inline in components.
- Deploy is **P6**: local-dev-runnable + `output: "standalone"` only.
