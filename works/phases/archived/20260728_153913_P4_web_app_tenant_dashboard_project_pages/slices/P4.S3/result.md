# P4.S3 — Result: Tenant dashboard (projects + create + tenant usage)

Replaced S2's `/dashboard` placeholder with the real tenant dashboard: usage stat
tiles + a dependency-free daily-trend chart + the projects `DataTable` + a
create-project server action. Everything landed under `web/`; no `src/vocky/**`
edits, no new env, none of the guardrail files touched.

Both verification tiers ran: the full in-sandbox gate is green **and** the live
E2E drove **both** required paths against the running vocky — including the
zero-project `daily_counts: []` gotcha.

## What was built (all under `web/`)

**Client seam** — `src/lib/vocky/app.ts` (new, `import "server-only"`, sibling of
`auth.ts`): `listProjects(token, signal?)` (unwraps `{projects}`, `?? []`),
`createProject(token, name)` (unwraps `{project}`), `getUsage(token, signal?)`
(bare call, no envelope). `types.ts` extended with `VockyProject`,
`VockyUsageProject` (**separate** — the usage serializer omits `tenant_id`),
`VockyUsageWindow`, `VockyMetricCounts`, `VockyDailyMetricCount`, `VockyUsage`.
`client.ts` untouched — `getJson`/`sendJson` covered every need.

**Page** — `(app)/dashboard/page.tsx`: `const { token } = await requireIdentity()`
→ `Promise.all([listProjects, getUsage])`. Renders the list from `/app/projects`
(canonical) and **ignores `usage.projects`**. `rowKey={(p) => p.id}` — never
`name`. Projects `empty` overridden from `@/content`. No `GET /app/tenant` (see
Deviations). Error policy mirrors `auth-guards.ts`: only 401 redirects (via
`requireIdentity`), everything else propagates.

**Reusable usage components** — `src/components/usage/{stat-tiles,trend-chart}.tsx`
+ barrel. Presentational, props-only server components, generic over
`VockyMetricCounts` / `VockyDailyMetricCount[]` — **S4 reuses both** for
`/app/projects/{id}/usage` (identical shapes). The chart is ~60 lines of inline
SVG (`preserveAspectRatio="none"` so axis-aligned bars stretch fluidly without
distortion), `role="img"` + `aria-label` + an `sr-only` peak/total summary, a
`<title>` per bar, an explicit `[]` empty state, and the partial-edge-day note.
`maxTotal` is floored at 1 so an all-zero zero-filled series can't divide by zero.

**Create-project** — `(app)/dashboard/actions.ts` (`"use server"`):
zod-validate (1–200, length pre-trim, matching vocky's pydantic order) →
`requireIdentity()` → `createProject` → `revalidatePath("/dashboard")`; failures
mapped by **status** (400/401/else), never vocky's `detail`.
`create-project-form.tsx` (`"use client"`): `useActionState` + S1
`Label`/`Input`/`FieldError`/`Button`.

**Copy** — `src/content/dashboard.ts` (`DASHBOARD` + `CREATE_PROJECT_ERRORS`),
re-exported from `content/index.ts`. `DASHBOARD_PLACEHOLDER` deleted from
`content/app.ts` + its re-export. `APP_NAV` unchanged (`/feedback` keeps `soon`).

**Tests** — `tests/vocky-app.test.ts` (8 cases, `.ts`-only, `mockImplementation`
fetch stub): envelope unwrapping + `?? []`, outgoing path + `Authorization: Bearer`,
`{name}` POST body, a 400 → `ApiError(status)`, duplicate-named projects staying
distinct, `/app/usage` called bare, and the `daily_counts: []` zero-project shape.

## Two implementation notes worth carrying forward

1. **`requireIdentity()` is called OUTSIDE the action's `try`.** It signals "no
   session" by calling `redirect()`, which works by *throwing* — a wrapping
   `catch` would swallow the redirect and render a bogus "please try again"
   instead of bouncing to `/login`. S4's mint/revoke actions must do the same.
2. **A `"use server"` file may export only async functions** — every export is
   registered as a callable server action. This was a real bug found live (below);
   the form's initial state now lives in the client island. Type exports are fine
   (erased before the loader runs).

## Verification

### A. In-sandbox floor — all green (re-run clean after the fix)

| Command | Outcome |
| --- | --- |
| `pnpm install --frozen-lockfile` | **pass** — no new deps (zod was already there) |
| `pnpm typecheck` | **pass** — clean |
| `pnpm lint` | **pass** — clean |
| `pnpm test` | **pass** — **44/44**, 5 files (36 S2 + 8 new) |
| `pnpm build` | **pass** — `/dashboard` still `ƒ (Dynamic)`; **exactly 1** server action registered |
| `python3 scripts/workflow.py validate` | **pass** |

### B. Live E2E — **RAN** against the vocky S2 left healthy on `:8000`

Confirmed first: `/healthz` → 200, `POST /auth/signup` → 400 (not 404), `/auth/me`
→ 401. Web started with `VOCKY_API_BASE_URL=http://127.0.0.1:8000` + a
`SESSION_SECRET`; driven with a curl cookie jar. The create-project form was
posted exactly as a **JS-less browser** does — replaying the rendered `$ACTION_*`
hidden inputs as a multipart POST — so the real progressive-enhancement path ran,
not a simulation.

| # | Check | Result |
| --- | --- | --- |
| 1 | Fresh signup → sealed cookie | **200** |
| 2 | **Zero-project** `/dashboard` | **200** — all four totals `0` |
| 3 | **`daily_counts: []` trend empty state** (gotcha 2) | **rendered**, `0` `<rect>`, no `<svg>` — no crash |
| 4 | Zero-project projects empty state | **rendered** (the `@/content` override, not DataTable's default) |
| 5 | Window label read from the **response** (gotcha 3) | `Last 30 days · Jun 16 – Jul 16` |
| 6 | Create project → server action | **200**; row appears after `revalidatePath` |
| 7 | Trend after 1st project | **31 zero-filled bars** — proves the zero-fill really is **conditional** |
| 8 | **Second project, SAME name** | both render distinctly, **2 rows**, **0** React duplicate-key warnings |
| 9 | Duplicate names → distinct ids at vocky | confirmed directly (`['Twin','Twin']`, 2 distinct uuids) |
| 10 | Blank name / 201 chars / 200 chars | invalid-name copy / invalid-name copy / **accepted** |
| 11 | Token leak into dashboard HTML | **none** (0 × `Bearer`, `vocky_session`, `v1.`) |

**The live run earned its keep — it caught a bug the whole in-sandbox gate
missed.** `actions.ts` exported `CREATE_PROJECT_INITIAL_STATE` (a plain object);
typecheck, lint, 44 tests, and `pnpm build` **all passed**, but every form submit
500'd at runtime with *"A 'use server' file can only export async functions,
found object"* — Next had registered the constant as a second server action
(two ids in the manifest). Moved the constant into the client island; the manifest
now shows exactly one action, and the gate + both E2E paths were re-run clean.

**Not driven live (out of scope, no code impact):** a **non-zero** trend series.
Captures `202`-accept and the worker logs "Persisted", but the records surface in
neither `/app/usage` nor `/app/feedback` for the owning tenant — the local docker
`worker` is a stale image (S2 rebuilt only `app`). The chart's scaling path is
covered by construction + unit test instead. **S4/S5 should expect this**: usage
and feedback read empty locally until `worker` is rebuilt.

## Deviations from plan.md

- **`CREATE_PROJECT_INITIAL_STATE` lives in `create-project-form.tsx`, not
  `actions.ts`** — forced by Next's `"use server"` export rule (bug found live,
  above). The plan implied it would sit beside the action.
- Dropped `GET /app/tenant` and the `/projects/[id]` link — **as the plan
  directed** (both recorded in `phase.md`); noted here only because they depart
  from the DECOMP sketch.
- Otherwise none. `web/` only; no `works/**` beyond this file + one `phase.md`
  line; no commits, no `doc-new-version`, no status transitions.
