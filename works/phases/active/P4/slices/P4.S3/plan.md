# P4.S3 — Plan: Tenant dashboard (projects + create + tenant usage)

Orchestrator's native plan for slice **P4.S3** (`implementation`, `medium` → executed by **`slice-executor-mid`**). The first real data page: it replaces S2's `/dashboard` placeholder with the tenant dashboard, rendered inside the S2 shell using the S1 primitives and the S2 client seam.

## Context

S2 built the auth/BFF seam **specifically for this slice** — `client.ts` is documented as "the seam S3–S5 extend with the `/app/*` calls", `types.ts` as "S3–S5 extend this file", `data-table.tsx` (S1) as "later slices pass server-fetched rows straight in". S3 is therefore mostly *extension*: one new client module, one new content module, the real page, plus two small reusable usage components S4 will also use.

## Verified `/app/*` contracts (exact — three gotchas)
- `GET /app/projects` → `200 {projects:[{id,name,tenant_id,created_at}]}`, **oldest-first, unpaginated**. Zero projects → `{projects:[]}`.
- `POST /app/projects` `{name}` (1–200 chars, **length measured pre-trim**, stored trimmed) → **201** `{project}`. `400 {detail}` on validation. **Duplicate names are ALLOWED** (no uniqueness anywhere) → the UI must key on `id`, never `name`.
- `GET /app/usage` (call it **bare** — defaults to last 30 days) → `200 {window:{start_ingested_at,end_ingested_at}, totals:{total,liked,disliked,unrated}, daily_counts:[{day,total,liked,disliked,unrated}], projects:[{id,name,created_at}]}`.
- **Gotcha 1 — `daily_counts` elements are `{day,total,liked,disliked,unrated}`**, not `{date,count}`; `day` is a date-only string (`"2026-06-16"`), ascending.
- **Gotcha 2 — zero-fill is CONDITIONAL.** A tenant *with* projects gets a fully zero-filled ~31-bucket series; a tenant with **zero projects gets `daily_counts: []`**. Any chart assuming N buckets breaks on the empty-tenant path — handle `[]` explicitly.
- **Gotcha 3 — read `window` from the response**, don't recompute the default client-side. Note the default window starts at `now−30d` (a mid-day instant), so the first/last buckets are **partial days**.
- Errors are all `{detail:string}`; `401 {detail:"Unauthorized"}`. `usage.projects` uses a *narrower* serializer (no `tenant_id`) than `/app/projects` — **two distinct types, don't share one interface**.

## Design calls (operator-approved)
- **Drop `GET /app/tenant`.** The decomposition sketched it, but the S2 shell topbar already renders the tenant from `identity` (`/auth/me`, `cache()`d), so a second call adds a round-trip and nothing else. Do not add `getTenant`. _(Deviation from the phase.md decomposition sketch — record it in `phase.md`.)_
- **Two parallel calls, not one.** `Promise.all([listProjects(token), getUsage(token)])`. Render the list from **`/app/projects`** (canonical, full shape) and **ignore `usage.projects`** (redundant; don't double-render). Semantically cleaner than overloading the usage endpoint; parallel server-side, so no wall-clock cost.
- **Authed mutations use server actions** (architectural rule for S3–S5): S2's route-handler + `lib/bff.ts` pipeline exists for the *public, unauthenticated, rate-limited* auth surface. Authed data mutations sit behind `requireIdentity()`, get Next's built-in server-action CSRF protection, and use `revalidatePath` — far less boilerplate than a route handler + client fetch. **S4's credential mint/revoke follows this same rule.**
- **No `/projects/[id]` link yet.** S4 owns that route; S2 set the precedent of not shipping links that 404 (it rendered `/feedback` as a muted "Soon"). S3 renders project rows without navigation; **S4 adds the link to its own page** when the route exists (noted here + in `phase.md` so S4 picks it up).
- **Chart with no dependency:** a small, token-styled, accessible inline-SVG bar chart of daily totals (~60 lines). No charting library — the design gate is deferred to P6, so keep it minimal and swappable.

## What S3 builds (all under `web/`)

**1. Client seam extension** — **new** `web/src/lib/vocky/app.ts` (`import "server-only"`, sibling of `auth.ts` — do NOT put `/app/*` calls in `auth.ts`, whose header scopes it to `/auth/*`). Follow `me()`'s exact pattern (private `Raw*` envelope interface → thin exported fn unwrapping it; **token is a positional required arg**; optional trailing `signal`):
```ts
export async function listProjects(token, signal?): Promise<VockyProject[]>   // getJson<{projects?}>("/app/projects") → raw.projects ?? []
export async function createProject(token, name): Promise<VockyProject>       // sendJson<{project}>("/app/projects","POST",{name}) → raw.project
export async function getUsage(token, signal?): Promise<VockyUsage>           // getJson<VockyUsage>("/app/usage") — no envelope
```
Extend `web/src/lib/vocky/types.ts` with `VockyProject`, `VockyUsageProject` (**separate** — no `tenant_id`), `VockyUsageWindow`, `VockyMetricCounts`, `VockyDailyMetricCount`, `VockyUsage`. Ids are strings, timestamps ISO strings (never `Date`). **Do NOT touch `client.ts`** — `getJson`/`sendJson` already cover every need (`cache:"no-store"` is hardcoded by design).

**2. The dashboard page** — replace `web/src/app/(app)/dashboard/page.tsx`. Server component, keeping the established shape: `const { token, identity } = await requireIdentity();` (destructure **both** — the placeholder took only `identity`), then `Promise.all([listProjects(token), getUsage(token)])`. Keep the `<div className="mx-auto max-w-page">` wrapper (the `(app)` layout supplies the shell/`<main>`). Renders:
- **Usage totals** — `Grid cols={4}` of `Card` stat tiles (total / liked / disliked / unrated) + the window label from `usage.window`.
- **Daily trend** — the bar chart over `usage.daily_counts`, with an explicit **empty state when `daily_counts` is `[]`**.
- **Projects** — `DataTable` with `rowKey={(p) => p.id}` (duplicate names are legal!), columns Name + Created, and an `empty` **overridden from `@/content`** (its default `"No items to display."` bypasses copy-as-data). Plus the create-project form.
- **Error policy — mirror `auth-guards.ts` exactly:** only a **401** redirects (mid-request revocation race); any other error **rethrows** — "an outage should surface, not masquerade as a session expiry."

**3. Reusable usage components** — **new** `web/src/components/usage/{stat-tiles.tsx,trend-chart.tsx}` (+ an `index.ts` barrel). Presentational, props-only, server components. **S4 reuses both** for `/app/projects/{id}/usage` (same `window`/`totals`/`daily_counts` shape) — build them generic over `VockyMetricCounts` / `VockyDailyMetricCount[]`. The chart: inline SVG bars, token colors, `aria-label` + an sr-only textual summary, graceful `[]` empty state, and a note that edge buckets are partial days.

**4. Create-project** — **new** `web/src/app/(app)/dashboard/actions.ts` (`"use server"`): `createProjectAction(prevState, formData)` → `requireIdentity()` → zod-validate the name (`zod@^4.4.3` is already a dep) → `createProject(token, name)` → `revalidatePath("/dashboard")`; map failures by **HTTP status, never vocky's `detail` text** (copy the `AUTH_ERRORS` idiom in `content/auth.ts`). **new** `web/src/app/(app)/dashboard/create-project-form.tsx` (`"use client"`): `useActionState` + the S1 `Label`/`Input`/`FieldError`/`Button` primitives; on success the revalidate refreshes the list.

**5. Copy** — **new** `web/src/content/dashboard.ts` (`DASHBOARD` const + types: headings, column headers, empty states, form labels/errors, totals labels), re-exported from `web/src/content/index.ts` under a `// Tenant dashboard (P4.S3)` comment. **Delete `DASHBOARD_PLACEHOLDER`** from `content/app.ts` + its re-export. No nav change — `/dashboard` is already live in `APP_NAV`; leave `/feedback`'s `soon` flag (S5's).

**6. Tests** — **new** `web/tests/vocky-app.test.ts` (terse, per the repo's small-tests rule). Follow the established pattern exactly: `environment: node`, `tests/**/*.test.ts` (**`.ts` only — no component-render tests**), and the fetch stub built with **`mockImplementation` (NOT `mockResolvedValue` — a `Response` body can only be read once)**, asserting the outgoing path + `Authorization: Bearer`. Cover: `listProjects` unwraps + `?? []` on a missing key; `createProject` unwraps `{project}` and POSTs `{name}`; `getUsage` passes through incl. the **`daily_counts: []`** zero-project shape. Keep `next/*`-mocking tests in their own file if needed (mocks leak across a file).

## Verification
1. `cd web && pnpm install` → `pnpm typecheck` → `pnpm lint` → `pnpm test` → `pnpm build` — all green.
2. **Live E2E — vocky is already running on `:8000`** (S2 rebuilt it from current source and left it healthy; confirm with `curl -s -o/dev/null -w '%{http_code}' http://127.0.0.1:8000/healthz` → 200, and that `/auth/signup` is not 404). Start web with `VOCKY_API_BASE_URL=http://127.0.0.1:8000` + a `SESSION_SECRET`, then drive **both paths**:
   - **Zero-project path (the gotcha):** sign up a fresh user → `/dashboard` renders with zeroed totals, the projects empty state, and the **`daily_counts: []` trend empty state** — no crash, no broken chart.
   - **Happy path:** create a project via the form → it appears in the list (revalidated) → totals/trend still render. Create a **second project with the same name** → both rows render distinctly (keyed by `id`).
   - Curl-with-cookie-jar is sufficient; a browser is optional.
3. `python3 scripts/workflow.py validate`.
- **Fallback:** if the live run is blocked, complete (1), capture the exact failing command + error, and return **`needs_operator`** with the commands. Do not claim a live pass you didn't drive.

## Executor guardrails
- **Do NOT touch:** `client.ts`, `auth-guards.ts`, `session.ts`, `env.ts`, `bff.ts`, `app-shell/*`, `data-table.tsx`, `vitest.config.ts`, `.env.example` (S3 needs **no new env**).
- Everything lands under `web/`; **no** `src/vocky/**` edits; **no** `works/**` except `works/phases/active/P4/slices/P4.S3/result.md` + one `phase.md` "Landed changes" line (record the dropped-`/app/tenant` deviation and the S4-adds-the-project-link handoff).
- **No** commits, **no** `doc-new-version`, **no** status transitions. Return a structured verdict.
