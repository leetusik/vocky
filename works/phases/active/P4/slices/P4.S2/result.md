# P4.S2 — Result: Auth + BFF proxy + authenticated app shell

Implemented the BFF end-to-end (D-P4-2): signup/login → **AES-256-GCM sealed
httpOnly cookie** → `requireSession`-gated `(app)` route group + topbar/`[rail |
main]` shell → logout. The browser never sees the vocky token and never talks to
vocky; no web-side DB. Everything landed under `web/`; **no `src/vocky/**` source
was touched** (the container rebuild was runtime-only, for verification).

Verified **both** tiers: the full in-sandbox gate is green **and** the live E2E
ran against a freshly-rebuilt vocky — real signup → sealed cookie → guarded page →
logout, including the revoked-token replay.

## What was built (all under `web/`)

**Session + crypto** — `src/lib/session.ts` (`import "server-only"`, `node:crypto`)
- `sealSession(token, now?)` / `openSession(value, now?) → string | null`,
  `sessionCookieOptions()` / `clearedSessionCookieOptions()`,
  `readSessionCookie(req)` (raw-header parse), `getSession()` / `requireSession()`
  (guards that **return the decrypted vocky token** for bearer injection, or
  `redirect("/login")`), `assertSameOrigin(req)` (ported verbatim from hi2vi).
- Ported verbatim: `src/lib/rate-limit.ts` + `src/lib/client-ip.ts`.

**Env** — `src/lib/env.ts`: hi2vi's `readEnvGroup` pattern (throws naming missing
keys, never values), grouped per consumer: `readVockyApiEnv()` /
`readSessionEnv()`. Reads are **lazy** (never module top-level) → `next build`
needs no env. `.env.example` + README env/auth-model sections added.

**Server-side vocky client** — `src/lib/vocky/`
- `client.ts` — `ApiError` / `toError` / `getJson` / `sendJson` adapted from
  hi2vi's `content-agent/api.ts` to server-side: absolute URL from
  `VOCKY_API_BASE_URL`, `Authorization: Bearer` injection, `cache: "no-store"`,
  errors carry vocky's `{detail}` (not hi2vi's `{error, field}`), 204/empty-body
  tolerant. This is the seam S3–S5 extend with `/app/*`.
- `auth.ts` — typed `signup` / `login` / `logout` (fire-and-forget) / `me`, plus
  `normalizeAuthResponse` / `activeTenant` collapsing the **tenant asymmetry**
  (signup `tenant` singular vs login/me `tenants[]`) into one `{token, user,
  tenant}`, with `tenants[0]` as active (matches vocky's `require_user`).
- `types.ts` — `VockyUser` / `VockyTenant` / `VockySession` / `VockyIdentity`.

**BFF routes** — `src/app/api/auth/{login,signup,logout}/route.ts`
(`runtime="nodejs"`, `dynamic="force-dynamic"`), with the ordered checks factored
into `src/lib/bff.ts` (`handleCredentialRoute`) so the pipeline is audited **once**
rather than duplicated across two near-identical routes:
`JSON-only 415 → assertSameOrigin 403 → per-IP rate limit 429 → parse 400 / zod 422
→ vocky call → seal into cookie, 200`. Login is the stricter throttle (5/15min) vs
signup (10/15min). vocky's `detail` is **never** echoed — body is only `{ok}`, the
client keys off status; pass-through statuses are login `[401,400]` / signup
`[409,400]`, any other upstream error → 502, config/transport → 500. Logout
revokes at vocky best-effort then **unconditionally** clears the cookie (never
fails open).

**Auth pages** — `(auth)/` layout (minimal, `noindex`, **unguarded** so /login stays
reachable) + `login/{page,login-form}.tsx`, `signup/{page,signup-form}.tsx`, sharing
`auth-card.tsx` + a `credentials-form.tsx` client island; S1 `field` primitives,
status→copy in `src/content/auth.ts`.

**Shell + gate** — `(app)/layout.tsx` awaits `requireIdentity()`; `AppShell`
(`src/components/app-shell/`) = sticky topbar (brand · workspace/user · `flex-1`
spacer · logout) + `grid-cols-1 min-[900px]:grid-cols-[248px_minmax(0,1fr)]`
`[rail | main]`; `(app)/dashboard/page.tsx` placeholder proves auth; root
`page.tsx` repurposed to the auth redirect. Nav/labels in `src/content/app.ts`.

## Crypto / cookie design as implemented

- Cookie `vocky_session` = **`v1.<iv>.<ct>.<tag>`**, each part base64url. Sealed
  plaintext is JSON `{token, exp}`; key = `sha256(SESSION_SECRET)` (32 B); a fresh
  **random 12-byte IV per seal** (verified: same token → different ciphertext).
- `openSession` returns the token or **null for every failure** — wrong
  shape/version, GCM tag mismatch (tampering), bad JSON, expired `exp`, rotated or
  missing secret. It never throws, so callers treat "no session" uniformly.
- Attributes: `httpOnly`, `SameSite=Strict`, `path=/`, `maxAge` 30d (matches
  vocky's token TTL exactly), `Secure` **only** in prod — both branches proven live
  (Secure present under `NODE_ENV=production`, absent on dev http/127.0.0.1).
- **Guards return the token**, they don't just gate — that is the deliberate
  departure from hi2vi (which HMAC-signs a self-minted token and returns void).

**One design decision worth flagging (not in plan.md, resolved during
implementation):** a naive mid-session-401 handling creates an infinite redirect
loop. A cookie can be crypto-valid while its vocky token is dead (revoked
out-of-band); `/dashboard` would 401 → `/login`, whose "already signed in" bounce
sees a valid cookie → `/dashboard` → … forever. Next also forbids clearing a
cookie from a server component, so the layout cannot self-heal. Fix:
`redirectIfAuthenticated()` (in `src/lib/auth-guards.ts`) **verifies against
`/auth/me` before bouncing**, so a dead cookie simply renders the login form.
`requireIdentity()` is `cache()`d → layout + page share **one** `/auth/me` per
request. Both behaviors are proven live (E2E #14) and unit-tested. Non-401 errors
(vocky down) are **rethrown**, not silently treated as a logout.

## Verification

### A. In-sandbox floor — all green (re-run clean at the end)

| Command | Outcome |
| --- | --- |
| `pnpm install --frozen-lockfile` | **pass** (adds `zod` 4.4.3, `server-only` 0.0.1, dev `vitest` 4.1.10) |
| `pnpm typecheck` | **pass** — clean |
| `pnpm lint` | **pass** — clean |
| `pnpm test` (vitest) | **pass** — **36/36**, 4 files |
| `pnpm build` | **pass** — `/`, `/login`, `/signup`, `/dashboard`, `/api/auth/*` all **`ƒ (Dynamic)`** (nothing per-user prerendered/cached; build needs no env) |
| `python3 scripts/workflow.py validate` (repo root) | **pass** |

Tests (`web/tests/`, terse per the small-tests rule): `session.test.ts` (round-trip;
tamper of IV/ct/tag → null; expiry → null; rotated/missing secret → null; fresh IV;
cookie attrs; `readSessionCookie`; `assertSameOrigin`), `vocky-auth.test.ts`
(signup `tenant` ≡ login `tenants[]` normalization), `auth-routes.test.ts`
(415/403/400/422/429, 200 + cookie that **opens back to the exact stub token**, 401
without leaking detail, 400 pass-through vs 502, signup 409, per-route throttle
buckets, logout revoke/clear/never-fail-open/403), `session-guards.test.ts`
(`getSession`/`requireSession` with mocked `next/headers`).

`vitest.config.ts` aliases `@`→`src` and `server-only`→an inert test stub (the real
package throws by design). This affects **only** the test run — `next build` still
resolves the real package, so the client-bundle guarantee stands.

### B. Live E2E — **RAN** (not deferred)

The running `vocky-app` was the predicted stale image (`POST /auth/signup` → 404).
Rebuilt with `docker compose up --build -d app` (reused the already-migrated
Postgres/Redis at 55432/56379); after rebuild `/auth/signup` → **400** (not 404),
`/auth/me` → 401, `/healthz` → 200. Drove the flow with curl + a cookie jar against
`pnpm dev` (`VOCKY_API_BASE_URL=http://127.0.0.1:8000` + a `SESSION_SECRET`):

| # | Check | Result |
| --- | --- | --- |
| 1 | `/dashboard` unauthenticated | **307 → /login** |
| 2 | `POST /api/auth/signup` (unique email) | **200** + `vocky_session=v1.…; Path=/; Max-Age=2592000; HttpOnly; SameSite=strict` |
| 3 | `/dashboard` with sealed cookie | **200**, renders real identity from `/auth/me` (`…@example.com` · `…'s workspace` — proves **both** tenant normalizations) |
| 4 | Token leak into HTML | **none** (0 occurrences of `Bearer`/cookie/`v1.`) |
| 5–6 | Login wrong password / unknown email | **401 / 401** — identical, no enumeration, no cookie |
| 7 | Login correct password | **200** + fresh sealed cookie; `/dashboard` → 200 |
| 8 | `/login` while signed in | **307 → /dashboard** (verified bounce) |
| 9 | `/` signed out / signed in | **307 → /login** / **307 → /dashboard** |
| 10–11 | Cross-site POST / non-JSON content-type | **403 / 415** |
| 12 | `POST /api/auth/logout` | **200** + `vocky_session=; Max-Age=0` |
| 13 | `/dashboard` after logout | **307 → /login** |
| 14 | **Replay pre-logout cookie** (crypto-valid, token revoked) | `/dashboard` **307 → /login**; `/login` **200 renders form** (no ping-pong) |
| 15 | vocky rejects a garbage bearer directly | **401** |
| 16 | Logout with no cookie (idempotent) | **200** |

Also confirmed `Secure` **is** set when run under `NODE_ENV=production` (`pnpm
start`); the jar-based flow used `pnpm dev` because curl refuses to return `Secure`
cookies over plain http — which is exactly why the code gates `secure` on
`NODE_ENV`. **vocky was left running** (healthy, `:8000`) for S3–S5; the web server
was stopped; no `.env.local` was written (env passed inline).

## Deviations from plan.md

- **Added files beyond the plan's list, all in its spirit:** `src/lib/bff.ts` (the
  ordered pipeline factored out of the two credential routes — one auditable copy
  instead of duplicating a security pipeline), `src/lib/auth-guards.ts`
  (`requireIdentity` / `redirectIfAuthenticated` — composes session+vocky, keeping
  `session.ts` vocky-agnostic), `src/lib/vocky/types.ts`, `(auth)/auth-card.tsx` +
  `(auth)/credentials-form.tsx` (shared by the two forms; the plan's
  `login-form.tsx` / `signup-form.tsx` remain as the thin per-page wrappers it
  names). Added `server-only` as a dependency (plan named only `zod`, but it
  specifies `import "server-only"`; S1 had dropped the package).
- **`AppShell` is a server component**, not the "client island" the plan wrote —
  only logout + the pathname-aware rail are client islands, so the server-fetched
  identity never crosses a client boundary. hi2vi's one-big-island console was a
  poor fit here.
- **Rate-limit buckets are namespaced** (`auth-login:` / `auth-signup:` + IP) rather
  than hi2vi's bare-IP key, which would let login attempts drain signup's budget
  (latent bug in the template; test #`keeps its own throttle bucket` locks it).
- **`/feedback` rail item renders as a muted "Soon"** item rather than a link that
  would 404 until S5 ships the route.
- Root `/` DS-preview replaced by the redirect **as instructed** — the S1 preview
  page is gone (its primitives are now exercised by the real auth/shell surfaces;
  `design/canvas/` remains the design-gate artifact).
- vitest chosen over `node --test` (TS + `@/*` aliases + the `server-only` stub need
  a resolver); config is 2 aliases + `environment: "node"`.
