# P9.S5 — Plan: Net-new states (loading / error / not-found / global-error)

## Context — why this slice exists

The app ships **no** loading, error, or 404 states today — loading is a blank blocked render, error is
Next's default overlay, and the 3 `notFound()` call sites fall back to Next's default 404. `build-prompt.md
§6` designs all four as real vocky states. **Net-new, additive** — no existing file changes, so the tree
stays green. Independent of S4 and S6 (depends only on S2 primitives + the S3 brand Mark). The Mark already
exposes `tileClassName` (default `fill-green`) precisely so error/global-error can pass a **danger** tint.

Source of truth on disk (no DesignSync): `build-prompt.md §6` (exact copy + structure per file). Read
`works/phases/active/P9/phase.md` first.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## Files S5 creates (all new)

- `web/src/app/(app)/loading.tsx` (required) — and **optionally** per-route `feedback/loading.tsx` (its
  layout differs — filter card + table, not stat-tiles+chart).
- `web/src/app/(app)/error.tsx` (`"use client"`)
- `web/src/app/not-found.tsx` (root, required) — and **optionally** `web/src/app/(app)/not-found.tsx` (so
  the 3 in-app `notFound()` calls render inside the app shell). Recommended: build both.
- `web/src/app/global-error.tsx` (`"use client"`)
- Copy: add the §6 strings to a content module (below).

## The work (exact copy + structure in `build-prompt.md §6`)

### `(app)/loading.tsx` (§6) — skeleton of the real layout
A `text-heading-3`-height title block, a `Grid cols={4}` of **4 stat-tile skeletons**, a chart-height block
(`h-40`), and **4–6 table-row skeletons**. Skeleton block = `rounded-md bg-hairline-soft` at each element's
height. Reduced-motion: **static** — a subtle `animate-pulse` is fine because `globals.css`'s global
reduced-motion layer already freezes animations; add `motion-reduce:animate-none` to make the intent
explicit. Reuse `Grid`/`Card` from `@/components/ui` for the shape. (Optional `feedback/loading.tsx`:
filter-card + table skeleton.)

### `(app)/error.tsx` (§6) — `"use client"`, `{ error, reset }`
A centered `Card`: a **danger-tinted Mark** (`<Mark size={52} tileClassName="fill-danger" />`), `heading-4`
**"Something went wrong"**, `body-sm text-steel` **"We couldn't load this page. Please try again."**, and a
`<Button size="sm" onClick={reset}>` **"Try again"**. **Never render `error.message`** (may leak internals —
security floor). It's a boundary component, so `"use client"` and the `{error, reset}` signature are required.

### `app/not-found.tsx` (root, §6) + optional `(app)/not-found.tsx`
Mono **`404`** in `text-green-dark`, `heading-4` **"This page doesn't exist"**, `body-sm text-steel`
**"The page you asked for isn't here — or isn't yours to see."** (the **404-never-403** floor — never
confirms existence), and a `Button variant="secondary"` **link** "Back to dashboard" (→ `/dashboard`).
Build `(app)/not-found.tsx` too (same content) so in-app `notFound()` renders inside the shell.

### `app/global-error.tsx` (§6) — `"use client"`, renders its own `<html><body>`
Minimal full-page variant of `error`: its own `<html><body>` (required — it replaces the root layout on a
root-layout crash), the **brand Mark**, **"Something went wrong"**, and a reset `<Button>`. Keep it minimal;
a system-font fallback is acceptable here (it renders outside the `next/font` variable scope).

## Copy-as-data (the §6 strings)

Author the §6 strings **verbatim** into a content module (the app's copy-as-data convention) — add a
`STATES` const to `web/src/content/app.ts` (or a new `content/states.ts`, exported via `content/index.ts`).
`error.tsx`/`global-error.tsx` are client components, so confirm the content module is client-safe (plain
data, no `server-only`) — it is; if any issue, inline the strings for those two files. **The 404 subcopy
and all §6 wording are exact** — do not paraphrase.

## Reuse (don't reinvent)

`Mark` (`@/components/brand`, `size`/`tileClassName`), `Wordmark`, `Card`/`Button`/`Grid` (`@/components/ui`).
The danger Mark is a one-prop restyle of the S3 component — do **not** fork the geometry.

## Locked floors S5 must honor

- **404-never-403:** the not-found subcopy never confirms whether a resource exists.
- **Error boundary never leaks:** `error.tsx` must not render `error.message`.
- **Reduced-motion:** skeletons static (the global layer handles it; `motion-reduce:animate-none` makes it explicit).

## Boundary — do NOT touch

Any existing file — S5 is purely additive (new state files + a small content addition). No surface,
component, primitive, token, or backend change. No `content/*` edits beyond adding the new state strings.

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean; **`cd web && pnpm build` green** (compiles the client
  boundaries + `global-error`'s own `<html>`).
- `prettier --write` the new files only.
- Greps: the four files exist; `error.tsx`/`global-error.tsx` start with `"use client"`; the exact 404
  subcopy string is present; `error.tsx` does not reference `error.message`; the danger Mark uses
  `fill-danger`.
- Smoke (if cheap): hit an unknown URL → the vocky 404; the skeleton flashes on a slow nav. (Triggering the
  error boundary is harder to smoke — the build + the `{error, reset}` signature are the practical proof.)

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

Net-new loading/error/not-found/global-error states added (skeletons, danger-mark error boundary,
404-never-403 not-found, minimal global-error) — `frontend.md` (v0003) records that these states "do not
exist." For `P9.REVIEW`.
