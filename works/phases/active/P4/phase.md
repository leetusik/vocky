# Phase P4: Web App: Tenant Dashboard & Project Pages

_Intent: see [intent.md](intent.md)._

## Objective

Build the authenticated web app — tenant dashboard and project detail pages — in a new Next.js app (hi2vi_web-style), replacing the packaged operator admin UI.

## Context

P4 is vocky's **first frontend phase** — it builds the authenticated web app (tenant dashboard + project detail pages) as a **new Next.js app**, modeled on `~/projects/personal/hi2vi_web` ("hi2vi_web-style" = stack + patterns + Claude design-gate, not repo topology). `docs/current/frontend.md` is still a bootstrap stub, so this phase authors it fresh.

The app is a **session-token client** of vocky's `/auth/*` + `/app/*` routes only — never the `vk_`-keyed `/api/*` surface (that is the external-service credential path). It surfaces what P2 (accounts/tenancy/projects/credentials) and P3 (feedback API v2, cross-project Korean-safe search, usage monitoring) built.

It **replaces the packaged same-origin operator Admin Web UI** (`src/vocky/admin_ui.py` + `src/vocky/admin_assets/*`) as vocky's browser surface — though the physical removal of that UI is deliberately deferred to P6 (see Open Questions).

Three operator decisions confirmed at decomposition time shape the split — see D-P4-1/2/3 in Findings & Notes: app lives in a repo subdir `web/`, browser↔API goes through a Next.js server-side BFF proxy (sealed httpOnly cookie, no CORS, no web-side DB), and P4 ports the design system + builds functional pages while deferring the intensive operator design session to P6.

## Decomposition

Five middle slices: a foundation **chain P4.S1 → P4.S2**, then a **fan-out** of three page surfaces (**P4.S3, P4.S4, P4.S5**) that each need only the S2 app shell + authed client and are otherwise independent of one another (any order after S2). One slice is `high` (P4.S2, the auth/BFF boundary); the rest are `medium`; none is `low` (nothing is fully mechanical). Mirrors the house pattern (P3's foundation-then-fan-out with one security-sensitive slice at the top tier).

- **P4.S1 — App scaffold + design-system foundation** · `medium` · order 1
  Touches: new `web/` app (Next.js 16 / React 19 / TS, pnpm, ESLint/Prettier, `next.config.ts` `output: "standalone"`, `pnpm dev`-runnable); Tailwind v4 CSS-first `@theme` token system ported from hi2vi_web (colors/fonts/type scale/radius; **no dark-mode toggle** — explicit surface tokens); `cn()` (`clsx` + extended `tailwind-merge`); self-hosted `next/font`; the CVA primitive set (`button`, `card`, `section`, `field`, `badge`, `grid`) **plus a NEW `data-table`/`data-list` primitive** (hi2vi_web has none; projects/credentials/feedback lists need it); the copy-as-data `src/content/` convention; scaffold `web/design/canvas/` (tokens mirror + a couple of section cards + `_ds_manifest.json`) for the deferred-to-P6 design session. Purely presentational — no vocky calls yet.
  _Rationale:_ the load-bearing foundation every page builds on; templated from hi2vi_web but needs adaptation + a net-new primitive, so `medium`, not `low`.

- **P4.S2 — Auth + BFF proxy + authenticated app shell** · `high` · order 2 · depends P4.S1
  Touches: typed **server-side vocky API client** (base-URL env, `getJson`/`sendJson`, `ApiError`, bearer injection — extends hi2vi_web's `content-agent/api.ts` shape); **BFF auth flow** (signup + login pages → Next.js server calls vocky `/auth/signup|login` → seal returned token into a **sealed/encrypted httpOnly `SameSite` cookie** the Next.js app sets for itself, never exposed to browser JS → server guards `requireUser` analog + same-origin check gating `/app` routes → logout clears cookie + calls vocky `/auth/logout` → redirect-to-login on vocky 401/expiry); **authenticated app shell/layout** (sticky topbar/nav + `[rail | main]` skeleton that S3–S5 render inside). No web-side DB.
  _Rationale:_ auth boundary + session-cookie sealing + novel multi-tenant BFF token wiring = the riskiest slice → top tier (cf. P2.S2, P7.S2).

- **P4.S3 — Tenant dashboard: projects + create + tenant usage** · `medium` · order 3 · depends P4.S2
  Touches: post-login home — tenant header (`GET /app/tenant`), projects list + create-project (`GET|POST /app/projects`), tenant usage summary (`GET /app/usage`: totals + zero-filled daily trend + project list, 30-day default window). Renders with S1 primitives via S2's authed client (server components).
  _Rationale:_ read + one create + derived-metrics rendering (cf. P3.S4) → `medium`.

- **P4.S4 — Project detail: info + credentials + project usage** · `medium` · order 4 · depends P4.S2
  Touches: per-project page — project info (`GET /app/projects/{id}`), **credentials management** (`POST` mint with a **show-once `vk_` key** modal — never re-render/log; `GET` list metadata; `DELETE` revoke — `/app/projects/{id}/credentials[/{cid}]`), project usage (`GET /app/projects/{id}/usage`, surfacing each key's `last_used_at`). 404-never-403 on foreign ids.
  _Rationale:_ CRUD + credential mint/revoke UX; boundary is backend-enforced → `medium` (may bump to `high` at this slice's own planning turn if credential handling proves riskier).

- **P4.S5 — Cross-project feedback list + Korean-safe search + detail** · `medium` · order 5 · depends P4.S2
  Touches: flagship read surface — cross-project feedback list (`GET /app/feedback`, newest-first, keyset-paged, each record carries `project_id`), **Korean-safe substring search** (`?q=`) with standard filters + optional `?project_id=` narrowing, feedback detail (`GET /app/feedback/{id}` with `comments[]` + `attachments[]`, attachments streamed via the BFF). **Read + search only** — feedback management (PATCH/DELETE/comments) is the `vk_`-keyed `/api/project/feedback` surface and is **out of scope for this app**.
  _Rationale:_ read + search rendering over a backend already tested for Korean search (P3) → `medium`.

**Why 5, not 4:** S1/S2 differ in both risk and concern (design system vs auth security), so splitting lets the auth work take the `high` tier while the scaffold stays `medium`. S3/S4/S5 are three distinct surfaces (tenant home / one project + credentials / cross-project search) with distinct API sets; merging project-detail into the dashboard would make one oversized slice. Five is at the top of the house range but justified for standing up a whole app. (DECOMP considered collapsing S3+S4 to a 4-slice shape but kept them split — project-detail carries its own distinct API set plus the security-sensitive show-once credential-mint UX, so it is not small enough to fold into the dashboard.)

## Findings & Notes

### Decisions

- **D-P4-1 — App location.** The app is a **subdirectory `web/` in this repo**, versioned and committed by the existing workflow engine. "hi2vi_web-style" means stack / patterns / design-gate, not repo topology (hi2vi_web is a separate repo we template from, not vendor).
- **D-P4-2 — Browser↔API boundary.** A **Next.js server-side proxy (BFF)**. The Next.js server calls vocky server-to-server with `Authorization: Bearer`; the browser only ever talks to the Next.js origin. The vocky session token lives in a **sealed/encrypted httpOnly cookie** the Next.js app sets for itself — never exposed to browser JS, no web-side DB. **No vocky backend change** (no CORS) is required.
- **D-P4-3 — Design gate.** P4 **ports** hi2vi_web's Tailwind-v4 `@theme` token system + CVA primitives (and adds a `data-table`/`data-list` primitive) and builds **functional** dashboard/project pages; it scaffolds `web/design/canvas/` + the DesignSync/`SIGNOFF` convention but **defers the intensive operator design session to P6** (landing page). Brand palette is a placeholder (reused hi2vi_web tokens) until the P6 design gate.

### Implementation anchors (so downstream slice plans start grounded)

- **vocky API (session `/app/*` + `/auth/*`; all Starlette `Route` lists, not FastAPI routers):**
  - `src/vocky/auth_api.py` — `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` (routes at ~line 211).
  - `src/vocky/app_api.py` — `GET /app/tenant`, `GET|POST /app/projects`, `GET /app/projects/{id}`, `POST|GET /app/projects/{id}/credentials`, `DELETE /app/projects/{id}/credentials/{cid}` (routes at ~line 292).
  - `src/vocky/app_feedback_api.py` — `GET /app/feedback` (cross-project list/search), `GET /app/feedback/{id}` (+comments+attachments), `GET /app/feedback/{id}/attachments/{aid}` (download) (routes at ~line 258).
  - `src/vocky/usage_api.py` — `GET /app/usage`, `GET /app/projects/{id}/usage` (routes at ~line 206); the `/api/project/usage` route there is the `vk_` surface — **out of scope for this app**.
  - Session guard: `src/vocky/accounts/auth.py::require_user` (~line 61) — the `/app/*` handlers use it; the BFF's `requireUser` analog mirrors its semantics (401 → redirect-to-login).
- **Retiring admin UI (do NOT touch in P4; removal deferred to P6):** `src/vocky/admin_ui.py`, `src/vocky/admin_assets/*` (`index.html`, `app.css`, `app.js`, `docs.json`), mounted in `src/vocky/app.py`.
- **hi2vi_web template (`~/projects/personal/hi2vi_web`, verified present):**
  - `src/app/globals.css` — the `@theme` token system to port.
  - `src/components/ui/*` — CVA primitives (`button`, `card`, `section`, `field`, `badge`, `grid` + `endpoint-card`, `reveal`, `index.ts`); no data-table yet (S1 adds it).
  - `src/lib/utils.ts` — `cn()`.
  - `src/lib/agent/auth.ts` — the cookie/guard shape to adapt for the sealed session cookie.
  - `src/app/operator/(console)/content-agent/{console.tsx,api.ts,hooks.ts}` — dashboard skeleton + fetch wrapper to extend.
  - `design/canvas/` — palette + `_ds_manifest.json` + `SIGNOFF` convention (P4 scaffolds a vocky mirror; heavy session = P6).
  - `next.config.ts` / `Dockerfile` / `deploy/` / `compose.prod.yml` — **P6** deploy reference (P4 sets up only local-dev + `output: "standalone"`).

## Constraints

- **Session-token client only:** talk to `/auth/*` + `/app/*` (session token via the sealed cookie) — **never** the `vk_`-keyed `/api/*` surface.
- **BFF boundary (D-P4-2):** browser talks only to the Next.js origin; the vocky token lives in a sealed httpOnly cookie, never in browser JS; no CORS change to vocky; no web-side DB.
- **Cross-project feedback is read + search only** (management stays on the `/api/project/feedback` `vk_` surface); **404-never-403** on foreign/cross-tenant ids (mirrors the backend); **Korean-safe `?q`** substring search (backend already trigram-indexed in P3).
- **Usage is derived / 30-day default window** (no billing, no metering — honors D-P3-5).
- **Credential plaintext (`vk_`) shown exactly once** at mint — never re-rendered, never logged.
- **Design system:** Tailwind-v4 CSS-first `@theme`, **no dark-mode toggle** (explicit surface tokens); copy-as-data `src/content/`; scaffold `design/canvas/` + DesignSync/`SIGNOFF` convention but defer the heavy operator design session to P6.
- **Deploy is P6:** S1 sets up a local-dev-runnable scaffold + `output: "standalone"` only; production Dockerfile/compose/nginx (`vocky.hi2vi.com` on the oracle-cloud box, edge nginx) is P6.
- **DECOMP itself writes no application code** — bare middle-slice folders only; each middle slice plans + implements at its own turn.

## Open Questions

- **Admin-UI retirement timing (P4 vs P6 — leaning P6).** P4 **builds** the replacement browser surface but **defers physical removal** of `src/vocky/admin_ui.py` / `src/vocky/admin_assets/*` / the `/admin/api/*` mount to **P6** (when the new app is actually deployed), so no browser surface disappears in the interim. Recorded here, **not** as a P4 slice; the P4.REVIEW should resolve the `architecture.md` "admin-UI convergence" note accordingly.
- **vocky brand palette vs. reused hi2vi_web tokens.** P4 uses hi2vi_web's tokens as a placeholder; the real vocky palette is finalized at the **P6** design gate. S1 should keep tokens cleanly swappable.
- **Deployed domain vs. local dev for P4.** Does P4 need a live `vocky.hi2vi.com` deploy, or just local dev? Deploy is **P6**; P4 targets local-dev-runnable only. Confirm at the P6 planning turn.
- **Deferred-job D2 intersection.** **D2** ("scope end-user feedback read to a public-safe field subset") **stays deferred** — the P4 dashboard is owner/session-scoped, so full-field feedback exposure is appropriate. Revisit D2 only if a non-owner / end-user feedback view is ever added. **D1 / D3 / D4** are unrelated to P4.

## Doc impact

Running list the phase REVIEW consolidates into new durable-doc versions (one version per doc, covering the whole phase):

- `frontend.md` — **authored fresh (v0002)**: the ported design system (`@theme` tokens, `cn`, CVA primitives + the new data-table/data-list), the `web/` app structure, the BFF + auth/session model, and the component/page inventory (dashboard, project detail, feedback surfaces).
- `architecture.md` — a **separate-origin Next.js web app + server-side BFF proxy** as vocky's browser surface (sealed httpOnly session cookie, no CORS, no web-side DB); **resolve the "admin-UI convergence" open question** (replacement built in P4, physical removal deferred to P6).
- `experience.md` — the tenant-dashboard / project-page / feedback-search UX (how a signed-in owner navigates projects, mints/revokes credentials, reads+searches feedback).
- `decisions.md` — **D-P4-1** (subdir `web/`), **D-P4-2** (BFF proxy + sealed httpOnly cookie, no CORS/DB), **D-P4-3** (port design system, build functional, defer heavy design gate to P6).
- `operations.md` — web app **build/run stub** (`pnpm dev`, `output: "standalone"`); full production deploy = **P6**.
- `product.md` (possibly) — the authenticated web app as the primary **user surface**, replacing the operator admin UI.

_Landed changes (each middle slice appends its own one-line note here as it finishes; the review consolidates them):_

- **P4.S2** — Built the **BFF auth boundary** end-to-end: AES-256-GCM **sealed httpOnly cookie** (`vocky_session` = `v1.<iv>.<ct>.<tag>`, key `sha256(SESSION_SECRET)`, JSON `{token,exp}`, `SameSite=Strict`, 30d = vocky's token TTL, `Secure` in prod) in `web/src/lib/session.ts` whose guards **return the decrypted vocky token** for bearer injection; server-side vocky client (`web/src/lib/vocky/{client,auth,types}.ts`, `no-store` + `Bearer`, normalizing the signup-`tenant`/login-`tenants[]` asymmetry to `tenants[0]`); BFF routes `api/auth/{login,signup,logout}` via one audited pipeline (`lib/bff.ts`: 415→403→429→400/422→vocky→seal; vocky `detail` never echoed, body only `{ok}`, login throttle 5/15min stricter than signup 10/15min, namespaced buckets); public `(auth)/{login,signup}`; `requireSession`-gated `(app)/` + topbar/`[rail | main]` shell + `dashboard` placeholder proving auth; `/` → auth redirect (replaced S1's DS preview). Env `VOCKY_API_BASE_URL` + `SESSION_SECRET` (server-only, lazy-read → build needs no env). **Decision:** the `(auth)` bounce **verifies against `/auth/me`** before redirecting — a crypto-valid-but-revoked cookie would otherwise ping-pong `/login`↔`/dashboard` forever (Next forbids clearing cookies from a server component); `requireIdentity` is `cache()`d so layout+page share one `/auth/me`. Verified: install/typecheck/lint/build + **36/36 vitest** green, all routes `ƒ (Dynamic)`; **live E2E ran** against a rebuilt vocky (stale image 404'd `/auth/*`) — real signup→sealed cookie→guarded page→logout, incl. revoked-cookie replay and no token leak into HTML. **vocky left running on :8000 (healthy) for S3–S5.** → feeds `frontend.md` (BFF + session model, `(auth)`/`(app)` structure, shell, client seam), `architecture.md` (sealed-cookie BFF, no CORS, no web-side DB), `experience.md` (signup/login/logout + shell nav), `decisions.md` (D-P4-2 as built), `operations.md` (the two server-only env keys + `.env.example`).
- **P4.S1** — Stood up the `web/` Next.js 16 app + ported design system (Tailwind-v4 `@theme` tokens, `cn()`, CVA primitives + the **new `data-table` primitive**, `src/content/` copy-as-data, `next/font/google` Noto Sans KR + JetBrains Mono, `design/canvas/` mirror). **Neutral placeholder palette** (slate surfaces + one indigo accent + red/amber signals) keeping hi2vi's token *names* — real vocky brand is P6. Purely presentational; `output: "standalone"` set for the P6 deploy. Verified: install / typecheck / lint / build all green, no backend calls. → feeds `frontend.md` (design system + `web/` structure + primitive/data-table inventory), `operations.md` (`pnpm dev` / standalone build stub), `decisions.md` (D-P4-1/-3), `architecture.md` (the new `web/` browser surface).
