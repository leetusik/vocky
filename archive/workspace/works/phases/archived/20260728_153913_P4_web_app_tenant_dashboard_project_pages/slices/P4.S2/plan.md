# P4.S2 — Plan: Auth + BFF proxy + authenticated app shell

Orchestrator's native plan for slice **P4.S2** (`implementation`, `high` → executed by **`slice-executor-high`**). The security-sensitive core: the whole server-side data layer + the sealed-cookie session model + the authenticated shell. Builds on the S1 scaffold/design-system; S3–S5 render pages inside the shell this slice creates.

## Context

vocky's API has **no CORS** and issues an opaque 30-day bearer token from `/auth/*`. Per decision **D-P4-2**, the web app is a **BFF (backend-for-frontend)**: the browser only ever talks to the Next.js origin; the Next.js *server* calls vocky server-to-server with `Authorization: Bearer`, and the vocky token lives in a **sealed (encrypted) httpOnly cookie** the app sets for itself — never exposed to browser JS, no web-side DB. This slice implements that end-to-end (signup/login → sealed session → guarded routes → logout) plus the topbar/`[rail | main]` shell, adapting hi2vi_web's proven `auth.ts`/route-handler/guard/fetch-wrapper/console patterns.

## Exact vocky contracts this slice codes against (verified)
- `POST /auth/signup` `{email,password}` → **201** `{token, user{id,email,created_at}, tenant{…}}` — `tenant` **singular**. `409 {detail}` dup email; `400 {detail}` validation.
- `POST /auth/login` `{email,password}` → **200** `{token, user, tenants[…]}` — `tenants` **array**. `401 {detail:"invalid email or password"}` (identical for unknown-email/bad-password; no `WWW-Authenticate`). `400` validation.
- `POST /auth/logout` (bearer) → **204** always, idempotent, never 401 → fire-and-forget.
- `GET /auth/me` (bearer) → **200** `{user, tenants[…]}`; **401** `{detail:"Unauthorized"}` + `WWW-Authenticate: Bearer` (missing/unknown/expired, indistinguishable).
- Token: `secrets.token_urlsafe(32)` — ~43 chars, **no prefix**, 256-bit, 30-day TTL, `Authorization: Bearer` (scheme case-insensitive). **Key off status codes, not 400 detail text.** Normalize the signup(`tenant`)/login(`tenants[0]`) asymmetry — vocky's own `require_user` treats `tenants[0]` as the active tenant.

## Key decisions (operator-approved)
- **Sealing:** hand-rolled **AES-256-GCM** via `node:crypto` (no new crypto/session dep). Cookie value `v1.<iv>.<ct>.<tag>` (base64url); sealed plaintext is JSON `{token, exp}`; open decrypts (GCM tag = integrity), checks embedded `exp`, and **returns the vocky token or null**. 32-byte key = `sha256(SESSION_SECRET)`; fresh 12-byte random IV per seal. Cookie: `httpOnly`, `SameSite=Strict`, `Secure` in prod, `path=/`, `maxAge=30d` (matches the vocky token; a mid-session vocky `401` clears it + redirects to login). Add `zod` (deferred from S1) for request-body validation.
- **BFF via route handlers** (mirrors hi2vi): client forms POST JSON to `web/src/app/api/auth/{login,signup,logout}/route.ts`; each runs the ordered checks then sets/clears the sealed cookie. (Not server actions — keeps the same-origin/rate-limit/JSON gate explicit and portable.)
- **URL structure:** public `(auth)/login` + `(auth)/signup`; authed `(app)/` route group gated by `requireSession()` with the shell, holding `(app)/dashboard` (S3), `(app)/projects/[projectId]` (S4), `(app)/feedback` (S5). S2 ships `(app)/dashboard` as a **placeholder** that proves auth ("Signed in as {email} · {tenant}" from `/auth/me`). Root `/` redirects (authed→`/dashboard`, else→`/login`); P6 later replaces `/` with the landing.

## What S2 builds (all under `web/`)

**1. Env + config** — `web/src/lib/env.ts` (hi2vi `readEnvGroup` pattern: throws naming a missing key, never its value): `VOCKY_API_BASE_URL` (server, e.g. `http://127.0.0.1:8000`) + `SESSION_SECRET` (server). Update `web/.env.example` (both blank, non-`NEXT_PUBLIC_`) + `web/README.md`. Add `zod` to `package.json`.

**2. Session + crypto** — `web/src/lib/session.ts` (`import "server-only"`): AES-256-GCM `sealSession(token)` / `openSession(cookieValue): string|null`; cookie-option helpers (`sessionCookieOptions`/`clearedSessionCookieOptions`, ported from hi2vi); `readSessionCookie(req)` (raw-header parse); `getSession()`/`requireSession()` (server guards: read cookie → open → return token, or `redirect("/login")`); `assertSameOrigin(req)` (ported verbatim). Port `web/src/lib/rate-limit.ts` + `web/src/lib/client-ip.ts` verbatim from hi2vi.

**3. Server-side vocky client** — `web/src/lib/vocky/client.ts`: port hi2vi's `ApiError`/`toError`/`getJson`/`sendJson`, adapted to **server-side** with `VOCKY_API_BASE_URL` + injected `Authorization: Bearer <token>` + `cache: "no-store"`. `web/src/lib/vocky/auth.ts`: typed `signup`/`login`/`logout`/`me` calls that normalize the tenant/tenants asymmetry into `{token, user, tenant}`. (This client is the seam S3–S5 extend with `/app/*` calls.)

**4. BFF route handlers** — `web/src/app/api/auth/{login,signup,logout}/route.ts` (`runtime="nodejs"`, `dynamic="force-dynamic"`), each in hi2vi's strict order: JSON-only (415) → `assertSameOrigin` (403) → per-IP rate limit (429, stricter for login) → parse/zod-validate (400/422) → call vocky `/auth/*` server-side → on success seal the returned token into the cookie (login/signup 200; logout also calls vocky `/auth/logout` with the current bearer then clears the cookie, best-effort). Map vocky 401/409 to the client without leaking detail text; never log passwords.

**5. Auth pages** — `web/src/app/(auth)/layout.tsx` (minimal, `noindex`, no guard) + `login/page.tsx`+`login-form.tsx` and `signup/page.tsx`+`signup-form.tsx` (client forms using S1 `field` primitives → POST the BFF routes → on ok `router.replace("/dashboard"); router.refresh()`; inline error on failure).

**6. Authed shell + gate** — `web/src/app/(app)/layout.tsx`: `await requireSession()` then the shell (server component fetches `/auth/me` for the topbar identity). Shell client island `web/src/components/app-shell/*` (port hi2vi's `console.tsx` skeleton): sticky topbar (brand · tenant/user · `flex-1` spacer · logout) + `grid-cols-1 min-[900px]:grid-cols-[248px_minmax(0,1fr)]` `[Rail | main]` (rail nav placeholders: Dashboard, Feedback) + logout button (POSTs `/api/auth/logout`, then `router.replace("/login")`). `web/src/app/(app)/dashboard/page.tsx` — placeholder proving auth. Repurpose `web/src/app/page.tsx` (S1's DS-preview) to the auth redirect. Add nav/label copy to `web/src/content/`.

**7. Tests** — `web/` unit + integration (keep terse per the repo's small-tests rule; use the Node test runner or Vitest — whichever needs no heavy config):
- Crypto: `sealSession`→`openSession` round-trip returns the token; a tampered cookie (flipped byte / wrong tag) → `null`; an expired payload → `null`.
- Mapping: login `{tenants:[…]}` and signup `{tenant:{…}}` both normalize to the same `{token,user,tenant}`.
- Routes/guards (stubbed vocky `fetch`): login route with a stub `{token,user,tenants}` sets a cookie with the exact attributes + 200; 415/403/429/400/401 paths return the right status; `requireSession` with no/invalid cookie redirects, with a valid sealed cookie yields the token.

## Verification (tiered — the auth slice must be behaviorally proven, robustly)
**A. Mandatory in-sandbox (S2 cannot be `done` without these):** `cd web && pnpm install` (adds zod) → `pnpm typecheck` → `pnpm lint` → `pnpm build` → run the S2 test suite (crypto + mapping + stubbed-route/guard tests) — all green. Then `python3 scripts/workflow.py validate`.

**B. Best-effort live E2E (this environment supports it):** the running `vocky-app` container is a **stale image that 404s on `/auth/*`** — bring up current vocky first, then drive a real round-trip:
- Refresh vocky (reuses the already-migrated Postgres/Redis at 55432/56379): `docker compose up --build -d app` (preferred), or from source `docker stop vocky-app-1 && uv run vocky` (frees port 8000). Confirm `curl -s -o/dev/null -w '%{http_code}' -X POST http://127.0.0.1:8000/auth/signup` is **not 404**.
- Start `web` (`pnpm build && pnpm start`, or `pnpm dev`) with `VOCKY_API_BASE_URL=http://127.0.0.1:8000` + a `SESSION_SECRET`, and script a real flow: `POST /api/auth/signup` (unique email) → assert a sealed `Set-Cookie` → GET an authed page / a guarded `/app/*` through the BFF with that cookie → `POST /api/auth/logout` → assert the guarded route now redirects. Curl-with-cookie-jar is sufficient; no browser needed.
- **This is authorized shared-infra work for verification only:** rebuilding/restarting the vocky *container* or running it from source is allowed; **do NOT modify any `src/vocky/**` source.** Leave vocky running (S3–S5 reuse it).
- **Fallback:** if the live bring-up is genuinely blocked (e.g. the Docker build can't fetch deps), still complete part A, capture the exact failing command + error, and return **`needs_operator`** with the precise commands for the operator to run the live E2E. Do not claim a live pass you didn't run.

## Executor guardrails
- Everything lands under `web/`; **no** edits to `src/vocky/**` (bringing the container up for verification is runtime-only, not a source edit) and **no** `works/**` except `works/phases/active/P4/slices/P4.S2/result.md` + one `phase.md` "Landed changes" note.
- **No** commits, **no** `doc-new-version`, **no** slice/phase status transitions (orchestrator's). Return a structured verdict (`done` with the tiered-verification outcomes; `needs_operator` if only the live E2E is blocked; `escalate`/`blocked` otherwise).
