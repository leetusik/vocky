# P4.DECOMP — Plan (decompose the Web App phase)

Orchestrator's native plan for the **`P4.DECOMP`** slice, executed by **`slice-executor-high`**. The executor's only job is to create P4's middle slices as **bare folders** and seed the phase notebook — **no app code, no slice `plan.md`, no `doc-new-version`, no commits.** The implementation plans for S1–S5 are written later, one at a time, at each slice's own turn.

## Context

P4 builds vocky's authenticated web app — **tenant dashboard + project detail pages** — as a new Next.js app modeled on `~/projects/personal/hi2vi_web`. It is the first phase to touch frontend (`docs/current/frontend.md` is still a bootstrap stub) and it replaces the packaged same-origin Admin Web UI (`src/vocky/admin_ui.py` + `src/vocky/admin_assets/*`) as the browser surface. The dashboard is a **session-token** client of vocky's `/auth/*` and `/app/*` routes (never the `vk_`-keyed `/api/*`).

Three operator decisions (confirmed at decomposition time) shape the split:

- **D-P4-1 — App location:** the app is a **subdirectory `web/` in this repo**, versioned and committed by the existing workflow engine. "hi2vi_web-style" means stack/patterns/design-gate, not repo topology.
- **D-P4-2 — Browser↔API:** a **Next.js server-side proxy (BFF)**. The Next.js server calls vocky server-to-server with `Authorization: Bearer`; the browser only talks to the Next.js origin. The vocky session token lives in a **sealed, httpOnly cookie** the Next.js app sets for itself — never exposed to browser JS. **No vocky backend change** (no CORS) is required.
- **D-P4-3 — Design gate:** P4 **ports** hi2vi_web's Tailwind-v4 `@theme` token system + CVA primitives (and adds a data-table primitive) and builds **functional** dashboard/project pages; it scaffolds `web/design/canvas/` but **defers the intensive operator design session to P6** (landing page).

The DECOMP slice's output is: 5 bare middle-slice folders + a fully seeded `works/phases/active/P4/phase.md`.

## What the DECOMP executor does (scope + guardrails)

1. Verify this plan's research against the current tree (endpoints, hi2vi_web template paths) — adjust the breakdown only if reality has drifted; otherwise keep the 5-slice shape below.
2. Run the five `new-slice` commands (bare folders only — **never** pre-fill any slice's `plan.md`).
3. Seed `phase.md`: fill **Context**, **Decomposition**, **Findings & Notes**, **Constraints**, **Open Questions**, and start the **Doc impact** running list.
4. Run `python3 scripts/workflow.py validate`.
5. Write `result.md` (terse: slices-created table, phase.md sections seeded, validation, deviations) and append cross-slice notes to `phase.md`. Return a verdict.
   - **No** `web/` code, **no** slice `plan.md`, **no** `doc-new-version`, **no** commits (the orchestrator commits).

## Proposed slice breakdown (5 middle slices)

Foundation chain **S1 → S2**, then fan-out **S3, S4, S5** (each needs only the S2 shell). One `high` (the auth boundary); the rest `medium`; no `low` (nothing is fully mechanical). Mirrors the house pattern (P3's foundation-then-fan-out; one security-sensitive slice at `high`, the rest `medium`).

- **P4.S1 — App scaffold + design-system foundation** · `medium` · order 1
  Stand up the Next.js 16 / React 19 / TS app in `web/` (pnpm, Tailwind v4 CSS-first `@theme`, ESLint/Prettier, `next.config.ts` `output: "standalone"`, runnable via `pnpm dev`). Port from hi2vi_web: the `@theme` token system (colors/fonts/type scale/radius; no dark-mode toggle — explicit surface tokens), `cn()` (`clsx` + extended `tailwind-merge`), self-hosted `next/font`, the CVA primitive set (`button`, `card`, `section`, `field`, `badge`, `grid`) **plus a NEW `data-table`/`data-list` primitive** (hi2vi_web has none; projects/credentials/feedback lists need it), and the copy-as-data `src/content/` convention. Scaffold `web/design/canvas/` (tokens mirror + a couple of section cards + `_ds_manifest.json`) for the deferred-to-P6 design session. Purely presentational — no vocky calls yet.
  _Rationale:_ the load-bearing foundation every page builds on; templated from hi2vi_web but needs adaptation + a net-new primitive, so `medium`, not `low`.

- **P4.S2 — Auth + BFF proxy + authenticated app shell** · `high` · order 2 · depends P4.S1
  The security-sensitive core and the whole server-side data layer. Build the typed **server-side vocky API client** (base-URL env, `getJson`/`sendJson`, `ApiError`, bearer injection — extends hi2vi_web's `content-agent/api.ts` shape). Build the **BFF auth flow**: signup + login pages → Next.js server calls vocky `/auth/signup|login` → seal the returned token into an httpOnly `SameSite` cookie (sealed/encrypted, since it carries a secret — the hi2vi_web HMAC *shape* adapted to hold a token; no web-side DB) → server guards (`requireUser` analog + same-origin check) gating the `/app` routes → logout clears the cookie and calls vocky `/auth/logout` → redirect-to-login on vocky 401/expiry. Build the **authenticated app shell/layout** (topbar/nav, hi2vi_web's sticky-topbar + `[rail | main]` skeleton) that S3–S5 render inside.
  _Rationale:_ auth boundary + session-cookie sealing + novel multi-tenant BFF token wiring = the riskiest slice → top tier (cf. P2.S2, P7.S2).

- **P4.S3 — Tenant dashboard: projects + create + tenant usage** · `medium` · order 3 · depends P4.S2
  The post-login home. Tenant header (`GET /app/tenant`), projects list + create-project (`GET|POST /app/projects`), and the tenant usage summary (`GET /app/usage`: totals + zero-filled daily trend + project list, 30-day default window). Renders with S1 primitives via S2's authed client (server components).
  _Rationale:_ read + one create + derived-metrics rendering (cf. P3.S4) → `medium`.

- **P4.S4 — Project detail: info + credentials + project usage** · `medium` · order 4 · depends P4.S2
  The per-project page. Project info (`GET /app/projects/{id}`), **credentials management** (`POST` mint with a **show-once `vk_` key** modal — never re-render/log it; `GET` list metadata; `DELETE` revoke — `/app/projects/{id}/credentials[/{cid}]`), and project usage (`GET /app/projects/{id}/usage`, surfacing each key's `last_used_at`). 404-never-403 on foreign ids.
  _Rationale:_ CRUD + credential mint/revoke UX; boundary is backend-enforced → `medium` (the orchestrator may bump to `high` at this slice's own planning turn if credential-handling proves riskier).

- **P4.S5 — Cross-project feedback list + Korean-safe search + detail** · `medium` · order 5 · depends P4.S2
  The flagship read surface. Cross-project feedback list (`GET /app/feedback`, newest-first, keyset-paged, each record carries `project_id`), **Korean-safe substring search** (`?q=`) with the standard filters + optional `?project_id=` narrowing, and feedback detail (`GET /app/feedback/{id}` with `comments[]` + `attachments[]`, attachments streamed via the BFF). **Read + search only** — feedback management (PATCH/DELETE/comments) is the `vk_`-keyed `/api/project/feedback` surface and is **out of scope for this app**.
  _Rationale:_ read + search rendering over a backend already tested for Korean search (P3) → `medium`.

**Why 5, not 4:** S1/S2 differ in both risk and concern (design system vs auth security), so splitting lets the auth work take the high tier while the scaffold stays medium. S3/S4/S5 are three distinct surfaces (tenant home / one project + credentials / cross-project search) with distinct API sets; merging project-detail into the dashboard would make one oversized slice. 5 is at the top of the house range (2–4) but justified for a whole app. **You may collapse S3+S4 to a 4-slice shape if you judge the project-detail surface small enough** — record the deviation in `result.md`/`phase.md` if so.

## phase.md seeding (what to write into the notebook)

- **Context:** the greenfield-frontend framing, the BFF/subdir/design-gate decisions, and that P4 replaces the retiring admin UI.
- **Decomposition:** intro para (foundation-chain + fan-out) → the five per-slice bullets above → the "Why 5" split-rationale para.
- **Findings & Notes:**
  - Decisions **D-P4-1** (subdir `web/`), **D-P4-2** (BFF proxy + sealed httpOnly cookie; no CORS; no web-side DB), **D-P4-3** (port design system, build functional, defer heavy design gate to P6).
  - **Implementation anchors** — vocky API: `src/vocky/auth_api.py`, `src/vocky/app_api.py`, `src/vocky/app_feedback_api.py`, `src/vocky/usage_api.py`, guard `src/vocky/accounts/auth.py::require_user`; retiring UI: `src/vocky/admin_ui.py`, `src/vocky/admin_assets/*`. hi2vi_web template: `src/app/globals.css` (`@theme`), `src/components/ui/*` (CVA primitives), `src/lib/utils.ts` (`cn`), `src/lib/agent/auth.ts` (cookie/guard shape), `src/app/operator/(console)/content-agent/{console.tsx,api.ts,hooks.ts}` (dashboard skeleton + fetch wrapper), `design/canvas/` (palette + `SIGNOFF.md`), `next.config.ts`/`Dockerfile`/`deploy/` (P6 deploy reference).
  - **Admin-UI retirement timing:** build the replacement in P4; **defer physical removal** of `admin_ui.py`/`admin_assets`/`/admin/api/*` to **P6** (when the new app is deployed), so no browser surface disappears in the interim. Record as an Open Question, not a P4 slice.
- **Constraints:** session-token client of `/auth/*`+`/app/*` only (never `vk_`); cross-project feedback is **read+search only**; 404-never-403; Korean-safe `?q`; usage derived / 30-day default; credential plaintext shown **once**; copy-as-data; Tailwind-v4 `@theme`, no dark-mode toggle; scaffold `design/canvas/` + DesignSync/`SIGNOFF` convention but defer the heavy session to P6; production deploy (Dockerfile/compose/nginx) is P6, so S1 sets up local-dev-runnable scaffold + `output: standalone` only.
- **Open Questions:** admin-UI removal timing (P4 vs P6 — leaning P6); vocky brand palette vs. reused hi2vi_web tokens for P4 (placeholder now, finalize at the P6 design gate); does P4 need a deployed domain or just local dev (deploy is P6); **D2** deferred-job flag — the dashboard is owner/session-scoped so full-field feedback exposure is fine; D2 stays deferred, revisit only if a non-owner/end-user feedback view is ever added.
- **Doc impact (running list for P4.REVIEW to consolidate):** `frontend.md` authored fresh v0002 (design system, `web/` app structure, BFF+auth/session model, component inventory); `architecture.md` (separate-origin Next.js web app + BFF proxy; resolve the "admin-UI convergence" open question); `experience.md` (dashboard/project-page UX); `decisions.md` (D-P4-1/2/3); `operations.md` (web build/run stub; full deploy = P6); possibly `product.md` (web app as the user surface).

## Exact commands to run

```
python3 scripts/workflow.py new-slice --phase P4 --slice P4.S1 --name "App scaffold + design-system foundation" --kind implementation --risk medium --order 1
python3 scripts/workflow.py new-slice --phase P4 --slice P4.S2 --name "Auth + BFF proxy + authenticated app shell" --kind implementation --risk high --order 2 --depends-on P4.S1
python3 scripts/workflow.py new-slice --phase P4 --slice P4.S3 --name "Tenant dashboard: projects + create + tenant usage" --kind implementation --risk medium --order 3 --depends-on P4.S2
python3 scripts/workflow.py new-slice --phase P4 --slice P4.S4 --name "Project detail: info + credentials + project usage" --kind implementation --risk medium --order 4 --depends-on P4.S2
python3 scripts/workflow.py new-slice --phase P4 --slice P4.S5 --name "Cross-project feedback list + Korean-safe search + detail" --kind implementation --risk medium --order 5 --depends-on P4.S2
python3 scripts/workflow.py validate
```

If you collapse to 4 slices, adjust the S4/S5 orders accordingly and note it.

## Verification (DECOMP writes no code)

- `python3 scripts/workflow.py validate` passes.
- `python3 scripts/workflow.py next` shows **`P4.S1`** as current (order 1), P4.REVIEW last.
- `works/backlog.md` lists P4.S1–S5 with the risk/order/depends above; each new slice folder holds **only `slice.json`** (no `plan.md`/`result.md`).
- `phase.md` has all sections seeded (Context, Decomposition, Findings & Notes, Constraints, Open Questions, Doc impact).
- No files created under `web/`; no new `docs/versions/*`; no commit made by the executor.
