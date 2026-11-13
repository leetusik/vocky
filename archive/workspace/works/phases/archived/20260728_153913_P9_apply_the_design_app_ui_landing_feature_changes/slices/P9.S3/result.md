# P9.S3 — Result: App components + brand mark

Restyled the signed-in app chrome + usage components to the vocky system and created the
first real vocky brand asset (mark + wordmark). Non-breaking: no public API of
StatTiles / TrendChart / AppShell changed, so S4's consumers keep compiling. All eight
owned files landed as `plan.md` / `build-prompt.md §4.5, §4.13, §4.14, §5, §7.1` specify.

## Per-file summary

### NEW `components/brand/mark.tsx` (§7.1)
Inline-SVG brand mark: three rising rounded bars (waveform / capture-volume motif) in
white on a green rounded-square tile. `viewBox="0 0 32 32"`, tile `rx=9`, three pill bars
(`rx=2.5`) at rising heights 8 / 13 / 18 on a common baseline. Static (no motion → reduced-
motion-safe by construction). **API:** `<Mark size?={32} tileClassName?="fill-green" …svgProps />`
— `size` is the tile edge in px (32 chrome / 52 hero-empty). The tile fill is a prop so
S5's danger-tinted variant can restyle it (`<Mark tileClassName="fill-danger" />`) **without
a fork** — the variant itself is deliberately left for S5, not pre-built. Decorative by
default (`aria-hidden="true"`, overridable); the Wordmark/heading carries the name.

### NEW `components/brand/wordmark.tsx` (§7.1)
Lowercase "vocky" (hardcoded, so app-shell no longer needs `SITE`), `font-en`,
`font-extrabold` (800), `tracking-[-1px]`, `leading-none`, `text-[18px]`. **API:**
`<Wordmark tone?="light" …spanProps />` — `light` → `text-ink` (default), `dark` → white.
`className` overrides size (S6's hero scales it up).

### NEW `components/brand/index.ts`
Barrel exporting `Mark`, `MarkProps`, `Wordmark`, `WordmarkProps`. **Import path for
downstream: `@/components/brand`.**

### `app-shell/app-shell.tsx` (§5)
Replaced the `text-[18px] font-extrabold tracking-[-0.3px]` brand span with a non-link
`<Mark size={32}/> + <Wordmark/>` group (`flex items-center gap-2`). Dropped the now-unused
`SITE` import. Migrated both `min-[900px]:` → `app:` (grid `app:grid-cols-[248px_minmax(0,1fr)]`;
main `px-4 pt-5 pb-10 app:px-6`, was `pt-[22px] … min-[900px]:px-[26px]`). Topbar stays
`px-6 py-3`; still a server component; kept `min-h-[calc(100dvh-57px)]`, the 248px rail
column, and topbar order (mark+wordmark · divider · Workspace {tenant} · spacer · {email} ·
LogoutButton).

### `app-shell/rail-nav.tsx` (§5)
Active item now `bg-green-soft font-medium text-green-dark` **+ inset accent bar**
`shadow-[inset_2px_0_0_var(--color-green)]` (was `bg-surface-green …`). Inactive unchanged
(`text-slate hover:bg-surface-soft hover:text-ink`); item base unchanged (`rounded-md px-3
py-2 text-body-sm`). Migrated both `min-[900px]:` → `app:` (`app:border-r app:border-b-0`,
`app:flex-col`). `soon` affordance and `aria-current` logic untouched.

### `app-shell/logout-button.tsx` (§4.5)
Bespoke chip markup → `<Button variant="ghost" size="sm" disabled={pending} onClick={handleLogout}>`
(imported from `@/components/ui`). The pending state + best-effort logout (`fetch` in `try`,
navigate-anyway `finally`) are **verbatim**. Stays `"use client"`.

### `usage/stat-tiles.tsx` (§4.13)
Tile → `Card variant="base" className="p-4"` (p-4 overrides base p-5 via tailwind-merge).
Added a leading rating dot per `tile.key` via an exhaustive `TILE_DOT` map: `total`→none,
`liked`→`bg-green`, `disliked`→`bg-danger`, `unrated`→`bg-muted` (small `inline-block
size-1.5 rounded-full`, `aria-hidden`). Label row became `flex items-center gap-1.5`.
Number, window label, `aria-labelledby`, and `Grid cols={4}` all unchanged.

### `usage/trend-chart.tsx` (§4.14) — area redesign, dependency-free
Full rewrite from bars to a filled area chart. Rewrote the doc comment (dropped
"P6/D-P4-3" and "bar chart"). Algorithm exactly per §4.14: `n = days.length`, `max =
Math.max(1, …totals)`, `viewBox "0 0 100 42"` (`H=42`, `PAD=2`), `x = n>1 ? (i/(n-1))*100 :
50`, `y = H - (total/max)*(H-2*PAD) - PAD`. `line` = `M/L` path; `area = line + " L 100 40
L 0 40 Z"`. `<defs><linearGradient>` green stop-0 opacity .22 → stop-1 opacity 0; hairline
baseline `<line>` at `y=40` stroke-width .6; area `fill=url(#…)`; line `fill=none
stroke=var(--color-green) stroke-width 1.4 vector-effect="non-scaling-stroke"` round
join/cap; a `<circle r=0.9>` per point each with a `<title>{dayLabel}: {total}</title>` for
native hover (kept from the old per-bar titles — preserves the hover affordance).
**Preserved exactly:** `TrendChartProps` API, the `sr-only` peak/total/range summary, the two
HTML axis labels, the partial-day note, the UTC `dayLabel`, `role="img"` + `aria-label`,
`preserveAspectRatio="none"`, `class="h-40 w-full"`, and **both empty shapes** —
`days.length===0` → the empty note box; all-zero → every point on the baseline (flat line,
`max` floor guards divide-by-zero).

## Verification

| Command | Result |
|---|---|
| `cd web && pnpm typecheck` | PASS (clean, no output) |
| `cd web && pnpm lint` | PASS (clean, no output) |
| `cd web && pnpm build` | **GREEN** — Compiled successfully; TypeScript checked; 7/7 static pages generated |
| `prettier --write` (8 touched files only) | applied; `prettier --check` on the 8 → "All matched files use Prettier code style" (left the 20 pre-existing unrelated `format:check` failures untouched) |

Grep-asserts (all pass): no `min-[900px]:` in `app-shell/` (rail-nav or app-shell); `brand/{mark,wordmark}.tsx`
exist + exported from `brand/index.ts`; `logout-button.tsx` renders `<Button variant="ghost"`;
`trend-chart.tsx` contains `linearGradient`, `role="img"`, and the `sr-only` summary; app-shell
uses `app:grid-cols` / `app:px-6` + `Mark`/`Wordmark`; rail uses the inset accent + `app:` variants.

## Breakpoint migration status

S3 migrated **4 of the 11** `min-[900px]:` literals (app-shell ×2, rail-nav ×2). The other 7 are
S4's (feedback pages). S7 backstops zero `min-[900px]:` remaining.

## Notes for S4 / S5 / S6 (downstream consumers)

- **Brand import path + API:** `import { Mark, Wordmark } from "@/components/brand";`
  - `<Mark size={32|52} tileClassName?="fill-green" {...svgProps} />` — decorative (`aria-hidden`)
    by default; pass `aria-hidden={false}` + `aria-label` for a standalone labeled mark. `size` 32
    = chrome, 52 = hero/empty. **S5:** for the danger-tinted error mark, pass
    `tileClassName="fill-danger"` — the geometry is already parameterized; do **not** fork the file.
  - `<Wordmark tone?="light|dark" className? {...spanProps} />` — `light`=`text-ink`, `dark`=white.
    Carries the accessible brand name (the Mark is decorative). Scale via `className` (e.g. hero).
- **StatTiles / TrendChart public APIs are unchanged** — S4's dashboard + project-detail reuse them
  as-is. TrendChart's gradient id is a module constant (`"trend-area-gradient"`); one chart per page
  in practice, and the fill is identical across instances, so a shared id is harmless.
- **app-shell dropped the `SITE` import** — the wordmark now owns the brand text ("vocky" hardcoded).
- **LogoutButton is now a `<Button variant="ghost" size="sm">`** — any surface referencing its old
  bespoke chip classes should use the Button instead (no other consumer exists today).

## Deviations from `plan.md`

None. The one judgment call the plan left open — the exact mark bar proportions ("aren't on disk …
build the closest faithful three-rising-bars per §7.1; the operator eyeballs it at commit / S7") —
was built as three pill bars at rising heights 8/13/18 in a 32-unit tile, per §7.1's waveform intent.
