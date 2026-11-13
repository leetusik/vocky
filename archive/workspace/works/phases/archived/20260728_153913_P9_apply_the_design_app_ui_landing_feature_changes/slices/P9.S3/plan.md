# P9.S3 — Plan: App components + brand mark

## Context — why this slice exists

Third slice of the `1→2→3` chain. S1 gave tokens, S2 gave primitives; S3 restyles the **app chrome**
(shell, rail, logout) and the **usage components** (StatTiles, the redesigned area TrendChart), and
creates the **brand mark + wordmark** — the first real vocky brand asset, reused downstream by S4 (auth
card), S5 (error/global-error), and S6 (landing). After S3 the whole signed-in app renders in the vocky
system; S4 then only tweaks the surfaces that compose these.

Source of truth on disk (no DesignSync): `build-prompt.md` §4.5 (logout→Button), §4.13 (StatTiles),
§4.14 (TrendChart area redesign — the algorithm), §5 (app-shell/rail-nav), §7.1 (the brand mark). Read
those directly. Read `works/phases/active/P9/phase.md` (Findings & Constraints) first.

**Non-breaking slice.** StatTiles / TrendChart / AppShell public APIs are unchanged, so S4's consumers
(dashboard, project detail) keep compiling. The brand components are additive.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## Files S3 owns

- **New:** `web/src/components/brand/mark.tsx`, `web/src/components/brand/wordmark.tsx`, `web/src/components/brand/index.ts`
- Rewrite: `web/src/components/app-shell/{app-shell,rail-nav,logout-button}.tsx`
- Rewrite: `web/src/components/usage/{stat-tiles,trend-chart}.tsx`

## The work (exact strings in `build-prompt.md`)

### NEW `components/brand/mark.tsx` + `wordmark.tsx` (§7.1)
- **Mark**: three rising **rounded bars** (a waveform / capture-volume motif) in white on a green
  (`--color-green`) **rounded-square tile**. Inline SVG (cleanest) or 3 `<span>` bars — simple geometry,
  no illustration. A `size` prop: **32** (chrome, default) and **52** (hero / empty states). The exact bar
  proportions aren't on disk (the artifacts stay in the design project) — build the closest faithful
  three-rising-bars geometry per §7.1; the operator eyeballs it at commit / S7.
- **Wordmark**: lowercase **"vocky"**, `font-weight:800; letter-spacing:-1px`. A `tone` prop:
  `light` (default → `text-ink`) and `dark` (→ white) — the shell needs light now; the landing needs both.
- Barrel `index.ts` exports both. Note for S5: `error.tsx` wants a "danger-tinted mark" — leave that
  variant for S5 to add (don't speculatively build it), but keep Mark cleanly parameterized so it can.

### `app-shell.tsx` (§5)
- Replace the `text-[18px] font-extrabold tracking-[-0.3px]` brand span with `<Mark size={32}/>` +
  `<Wordmark/>` (non-link group, matching today's non-interactive brand). If `SITE` import becomes unused,
  drop it.
- Topbar stays `px-6 py-3`. Main: `px-4 pt-[22px] pb-10 min-[900px]:px-[26px]` → **`px-4 pt-5 pb-10 app:px-6`**.
- **Migrate `min-[900px]:` → `app:`** (the grid `min-[900px]:grid-cols-[248px_…]` and the main padding).
  Keep the `min-h-[calc(100dvh-57px)]` calc and the 248px rail column. Keep it a **server component**;
  topbar order = mark+wordmark · divider · `Workspace {tenant}` · spacer · `{email}` · `<LogoutButton/>`.

### `rail-nav.tsx` (§5)
- Active item → **`bg-green-soft font-medium text-green-dark`** (today it's `bg-surface-green`) **+ an inset
  green accent bar** `shadow-[inset_2px_0_0_var(--color-green)]`. Inactive stays
  `text-slate hover:bg-surface-soft hover:text-ink`; item base `rounded-md px-3 py-2 text-body-sm`.
- **Migrate `min-[900px]:` → `app:`** (`border-r`/`border-b-0` and `flex-col`). Keep the `soon` affordance
  and the `aria-current` logic exactly.

### `logout-button.tsx` (§4.5)
Replace the bespoke chip markup with `<Button variant="ghost" size="sm" disabled={pending} onClick={handleLogout}>`
(import `Button` from `@/components/ui`). **Keep the `pending` state + best-effort logout logic verbatim**
(the fetch, the navigate-anyway `finally`). Stays `"use client"`.

### `stat-tiles.tsx` (§4.13)
- Tile → `Card variant="base" className="p-4"` (base is now p-5; p-4 overrides via tailwind-merge).
- Label `text-caption font-medium text-steel` gains a **leading rating dot** per `tile.key`: `total`→none,
  `liked`→`bg-green`, `disliked`→`bg-danger`, `unrated`→`bg-muted` (a small `<span class="inline-block
  size-1.5 rounded-full bg-*">`). Number stays `font-mono text-heading-3 text-ink tabular-nums`.
- Keep the window label, `aria-labelledby`, and `Grid cols={4}` exactly.

### `trend-chart.tsx` (§4.14) — the area redesign, dependency-free
Replace the bars with a filled **area chart** (no library). Rewrite the doc comment (drop "P6/D-P4-3",
"bar chart"). Algorithm (§4.14):
- `n = days.length`; `max = Math.max(1, ...days.map(d=>d.total))`; viewBox `0 0 100 H`, `H=42`, `pad=2`.
- `x_i = n>1 ? (i/(n-1))*100 : 50`; `y_i = H - (d.total/max)*(H-2*pad) - pad`.
- `line = "M x0 y0 L x1 y1 …"`; `area = line + " L 100 " + (H-pad) + " L 0 " + (H-pad) + " Z"`.
- `<defs><linearGradient>` green `stop-0 opacity .22 → stop-1 opacity 0`; baseline `<line y=H-pad
  stroke=hairline stroke-width .6>`; area `fill=url(#…)`; line `fill=none stroke=var(--color-green)
  stroke-width 1.4 vector-effect="non-scaling-stroke"` round join/cap; optional `<circle r=0.9 fill=green>`
  per point each with a `<title>{dayLabel}: {total}</title>` for native hover.
- SVG `role="img"` + `aria-label`, `preserveAspectRatio="none"`, `class="h-40 w-full"`.
- **Preserve exactly:** the `TrendChartProps` API, the `sr-only` summary sentence (peak/total/range), the
  two HTML axis labels underneath, the partial-day note, the UTC `dayLabel`, and **both empty shapes** —
  `days.length===0` → the empty note box; all-zero series → a flat line on the baseline (the `max` floor
  guarantees no divide-by-zero).

## Breakpoint migration (partial, by design)

S3 migrates **4 of the 11** `min-[900px]:` literals (app-shell ×2, rail-nav ×2). The other 7 are S4's
(feedback pages). **S7 verifies zero `min-[900px]:` remain** — the DoD backstop. `--breakpoint-app` was
defined in S1, so `app:` resolves.

## Locked floors S3 must preserve

- TrendChart's `role="img"` + `aria-label` + the `sr-only` peak/total/range summary; both empty shapes;
  UTC-parsed `dayLabel` (never a local-offset shift).
- The reduced-motion contract: the mark is **static** (no animation); if any motion is added it must be
  reduced-motion-safe (none is needed here).
- Rail `aria-current` logic and the `soon` non-interactive affordance.

## Boundary — do NOT touch

`ui/` primitives (S2), `globals.css`/`fonts.ts` (S1), the root `layout.tsx`, or any page/surface file
(dashboard, project detail, feedback, auth — all S4). Do not migrate the feedback pages' `min-[900px]:`
(S4). Do not build the landing (S6) or the states (S5) — just the reusable brand + app components they'll
consume.

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean; **`cd web && pnpm build` green** (compiles the new SVG/JSX
  and the brand components).
- `prettier --write` the touched files only (avoid the 20 pre-existing unrelated `format:check` failures).
- Greps: no `min-[900px]:` in `app-shell.tsx`/`rail-nav.tsx` (they use `app:`); `components/brand/{mark,wordmark}.tsx`
  exist and are exported; `logout-button.tsx` renders `<Button variant="ghost"`; TrendChart contains
  `linearGradient` + `role="img"` + the `sr-only` summary.
- Smoke (if cheap): render `/dashboard` — the area chart, stat tiles with dots, the mark+wordmark topbar,
  and the rail active-accent all show; Korean still renders.

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

App chrome + usage components restyled to vocky; new brand mark + wordmark; TrendChart is now a
dependency-free area chart. `frontend.md` (v0003)'s TrendChart/app-shell descriptions are now stale.
For `P9.REVIEW`.
