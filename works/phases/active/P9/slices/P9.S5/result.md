# P9.S5 — Result: Net-new states (loading / error / not-found / global-error)

**Verdict: done.** All four net-new framework states from `build-prompt.md §6` now exist as real
vocky-designed surfaces (they were framework defaults / a blank blocked render before). Purely additive —
no existing file was modified except the small copy addition. `typecheck` / `lint` / `build` all green.

## Files created (all new)

| File | What it is |
|---|---|
| `web/src/content/states.ts` | The §6 copy as data — `STATES.{loading,error,notFound,globalError}`, verbatim. Plain data (no `server-only`) so the two client boundaries can import it. |
| `web/src/app/(app)/loading.tsx` | Required app-group loading skeleton — mirrors the dashboard/project shape (title + `Grid cols={4}` of 4 stat-tile skeletons + `h-40` chart block + 5 table-row skeletons). |
| `web/src/app/(app)/feedback/loading.tsx` | **Optional** route-level skeleton for the feedback list (different shape: filter card + 6 table rows). Built for fidelity so the generic stat-tile skeleton does not flash on a feedback nav. |
| `web/src/app/(app)/error.tsx` | `"use client"` error boundary, `{ error, reset }`. Centered `Card variant="feature"`, danger-tinted `Mark`, heading-4 title, body-sm body, `Button size="sm" onClick={reset}`. |
| `web/src/app/not-found.tsx` | Root not-found — full-page centered on the bare canvas body. Mono `404`, heading-4, the 404-never-403 subcopy, secondary link "Back to dashboard". |
| `web/src/app/(app)/not-found.tsx` | **Recommended** in-app not-found — same content, centered inside the app shell so the 3 in-app `notFound()` calls (project detail, feedback list, feedback detail) render inside the chrome. |
| `web/src/app/global-error.tsx` | `"use client"` root-layout fallback — renders its own `<html><body>`; brand `Mark`, heading, reset. Minimal. |

One existing file touched (allowed copy addition): `web/src/content/index.ts` — added `export { STATES } from "./states";`.

## Where the copy lives

All §6 strings are in `web/src/content/states.ts` (exported via `@/content`), **verbatim**:
- error: "Something went wrong" / "We couldn't load this page. Please try again." / "Try again"
- not-found: `404` / "This page doesn't exist" / **"The page you asked for isn't here — or isn't yours to see."** (real em-dash U+2014, straight ASCII apostrophes — byte-checked against `build-prompt.md §6`) / "Back to dashboard"
- global-error: "Something went wrong" / "Try again"
- loading has no §6 visible copy; `STATES.loading.label = "Loading"` is a screen-reader-only status for the busy region (a11y affordance, not a designed string).

## Key correctness decisions

- **Danger Mark is a one-prop restyle, not a fork** — `error.tsx` uses `<Mark size={52} tileClassName="fill-danger" />`; `global-error.tsx` uses the default `fill-green` brand mark. `--color-danger` exists in `globals.css`, so `fill-danger` is a live Tailwind utility (Mark already uses `fill-green`/`fill-white`).
- **Security floor honored** — `error.tsx` types `error` in its props but never destructures or renders it; `error.message` appears only in explanatory comments in both boundary files. No message is ever surfaced.
- **404-never-403 floor** — the subcopy is the verbatim locked line and lives once in `STATES.notFound.body`; both not-found files read it, so they cannot drift.
- **Reduced motion** — both skeletons put `animate-pulse motion-reduce:animate-none` on the pulsing wrapper. `globals.css`'s global reduced-motion layer already freezes `animation-duration`, so the explicit `motion-reduce:animate-none` is belt-and-suspenders per §6 (static under reduced motion). The visual skeleton is `aria-hidden`; an `sr-only role="status"` sibling announces the wait.
- **Skeleton grammar** — every placeholder block is `rounded-md bg-hairline-soft` at the element's real height, per §6. The app skeleton renders inside the app shell (the `(app)` Suspense fallback sits under `(app)/layout.tsx`), so it carries only content, not chrome.
- **global-error font** — uses `font-sans`, which degrades to the Korean-capable system fallback outside the `next/font` variable scope (`--font-pretendard` is set by a className on the crashed root `<html>`); acceptable per §6.

## Verification

| Command | Result |
|---|---|
| `cd web && pnpm typecheck` | PASS (tsc --noEmit, clean) |
| `cd web && pnpm lint` | PASS (eslint, clean) |
| `cd web && pnpm build` | **GREEN** — compiled successfully; `/_not-found` prerendered static; all 12 routes build |
| `prettier --write` (7 new files + `content/index.ts`) | all unchanged (already formatted) |

Grep-asserts (all pass): the four required files + the two recommended + `states.ts` exist; `error.tsx`
and `global-error.tsx` begin `"use client"`; the exact 404 subcopy string is present once; no non-comment
`error.message` reference in either boundary; the danger Mark uses `fill-danger`; `global-error.tsx` renders
its own `<html><body>`.

Not smoke-tested at runtime (no dev server spun up) — the green build + the `{error, reset}` signatures are
the practical proof, as the plan notes. Triggering the error/global-error boundaries live is out of scope
for this slice.

## Notes for S7 (DoD sweep)

- **Optional per-route loading skeletons NOT built for `dashboard/` or `projects/[projectId]/`** — §6 lists
  those as optional. The generic `(app)/loading.tsx` already mirrors their exact stat-tile+chart shape, so a
  dedicated file would be redundant. Only `feedback/loading.tsx` was added (its shape genuinely differs).
  If S7/operator wants per-route skeletons for symmetry, they'd be near-duplicates of `(app)/loading.tsx`.
- **`error.tsx` is scoped to `(app)` only** — there is no `app/error.tsx` at the root. A throw in the auth
  group or the landing bubbles to `global-error.tsx` (the root-layout fallback). This matches §6, which
  designs only `(app)/error.tsx` + `global-error.tsx`. Flag for S7 only if the operator wants a styled
  boundary on the public/auth surfaces too (net-new, not in this round's design).
- **No new component was created** — `error`/`global-error` reuse `Mark` (danger tint via `tileClassName`),
  and all four states reuse `Card`/`Button`/`Grid`. No geometry fork, no new primitive.
