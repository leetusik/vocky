# Round 01 — build-prompt: the implementation contract

**Round:** 01 · **Phase:** P8 → **implemented by P9** · **Repo:** `github.com/leetusik/vocky`
**Companion:** `result.md` (decisions & rationale). This file is the **buildable spec**: exact token values,
component APIs, per-surface layout, and a per-file change manifest. **P9 decomposes and sizes from this file.**

> ## RESPECT THE DESIGN — put this in every P9 slice plan and executor prompt
> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions, empty/error/
> loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save effort** — that is
> a correctness failure, not a shortcut. Where an exact value isn't specified here, pick the option closest to
> the designed intent, **never a plainer fallback**. Where the design implies backend/data work, **build the
> backing** and surface the choice — don't quietly drop the feature. (This round implies **no** backend change;
> §9 confirms it.)

**Visual source of truth:** `Vocky Round 01 — Design System.html` and `Vocky Round 01 — Landing.html`
(this design-system project). When a class string here and the artifact disagree, the artifact's *rendered
result* wins — match it.

**The re-theme property still holds:** Tailwind utilities compile to `var(--color-*)`, so §2 is a value swap —
editing `globals.css` re-themes every surface at once. §2.5 lists the hardcoded literals that a value swap
does **not** reach; they must be edited by hand.

---

## 1. Suggested build order (P9 shape — foundation first)

1. **Foundations** — `globals.css` (color/type/radius/spacing/breakpoint) + `fonts.ts` (Pretendard) + the §2.5
   hardcoded-literal fixes. One slice; everything downstream re-themes off it.
2. **Primitives** — `button` / `card` / `badge` / `field` rewrites + **new** `select` + `chip`; barrel export.
3. **App components** — `app-shell` / `rail-nav` / `logout-button`; `usage/stat-tiles`; `usage/trend-chart`
   (the area redesign).
4. **App surfaces** — auth, dashboard, project detail, feedback list, feedback detail (mostly class swaps +
   the Select/Chip/breadcrumb changes).
5. **Net-new states** — `loading` / `error` / `not-found` / `global-error`.
6. **Landing** — reclaim `/`, `content/landing.ts`, `components/landing/*` (the largest net-new surface).
7. **Design-fidelity fix + consistency/DoD sweep** — per v13's expected shape.

Steps 5–6 are independent of each other and of most of 4; 1→2→3 are strictly ordered.

---

## 2. Color — full `@theme` swap (`web/src/app/globals.css`)

Replace the 41 `--color-*` values in the `@theme` block with these. **Names are unchanged** (call sites stay
put). Update the header comment (it currently says "PLACEHOLDER PALETTE") to describe the vocky brand.

### 2.1 The values (old → new)

| Token | Old (placeholder) | **New (vocky)** | Role |
|---|---|---|---|
| `--color-ink` | #0f172a | **#0E1A16** | primary text, darkest base |
| `--color-forest` | #1e293b | **#14231E** | dark section / footer bg |
| `--color-forest-mid` | #334155 | **#24322C** | code/endpoint panel bg |
| `--color-forest-soft` | #475569 | **#3A4A43** | dark borders |
| `--color-green` | #6366f1 | **#0C7A52** | primary CTA + signature (white text AA 5.36:1) |
| `--color-green-deep` | #4f46e5 | **#095E40** | hover/pressed, focus ring |
| `--color-green-dark` | #4338ca | **#064A33** | links + accent text on light |
| `--color-green-soft` | #e0e7ff | **#E4F5ED** | active nav bg, soft chips |
| `--color-security-mint` | #c7d2fe | **#BEE9D5** | mint tint (chip borders, key panel) |
| `--color-security-teal` | #818cf8 | **#2FA477** | brighter data accent (endpoint label) |
| `--color-trust-sage` | #cbd5e1 | **#7FB8A0** | sage / on-dark small accents |
| `--color-victory-lime` | #a5b4fc | **#9AD4A8** | soft positive tint (rare) |
| `--color-archive-olive` | #94a3b8 | **#8A968F** | muted neutral (= `muted`, intentional) |
| `--color-archive-cream` | #f1f5f9 | **#F1F4F0** | light neutral surface |
| `--color-danger` | #dc2626 | **#C93B2B** | dislike + destructive (white text AA 5.05:1) |
| `--color-danger-deep` | #b91c1c | **#A32A1D** | danger text on light |
| `--color-surface-danger` | #fef2f2 | **#FCEEEB** | light danger surface |
| `--color-hairline-danger` | #fecaca | **#F3D2CB** | danger border |
| `--color-caution` | #d97706 | **#C6820E** | warning accent |
| `--color-caution-deep` | #b45309 | **#8F5C06** | caution text on light |
| `--color-surface-caution` | #fffbeb | **#FBF3E3** | light caution surface |
| `--color-hairline-caution` | #fde68a | **#EEDCB2** | caution border |
| `--color-canvas` | #ffffff | **#FFFFFF** | base surface |
| `--color-canvas-dark` | #0f172a | **#0E1A16** | (= ink, intentional) |
| `--color-surface` | #f8fafc | **#F5F8F6** | app background |
| `--color-surface-soft` | #f1f5f9 | **#EEF3F0** | soft band |
| `--color-surface-green` | #eef2ff | **#EAF6F0** | accent-tinted panel |
| `--color-surface-archive` | #f9fafb | **#F4F7F5** | neutral tint |
| `--color-surface-security` | #eef2ff | **#ECF6F0** | green-tinted panel |
| `--color-surface-band` | #f1f5f9 | **#EDF2EF** | tinted band (now ≠ surface-soft) |
| `--color-hairline` | #e2e8f0 | **#E2E9E5** | default border |
| `--color-hairline-soft` | #f1f5f9 | **#EEF2F0** | soft divider |
| `--color-hairline-strong` | #cbd5e1 | **#CBD6D0** | input border |
| `--color-hairline-dark` | #334155 | **#2C3B34** | borders on dark |
| `--color-charcoal` | #1e293b | **#1C2A24** | headings, strong text |
| `--color-slate` | #334155 | **#35453E** | body strong |
| `--color-steel` | #64748b | **#556259** | secondary text (AA on white 6.4:1) |
| `--color-muted` | #94a3b8 | **#8A968F** | decorative/disabled only |
| `--color-on-dark` | #ffffff | **#FFFFFF** | text on dark |
| `--color-on-dark-muted` | #cbd5e1 | **#B7C7BE** | muted text on dark |
| `--color-on-primary` | #ffffff | **#FFFFFF** | **stays white** — see §2.2 |

### 2.2 `on-primary` flip — resolved: **white**
`--color-green #0C7A52` is a saturated mid-dark tone that passes AA (5.36:1) with white text, so the primary
CTA keeps **white** text. Do **not** copy hi2vi's dark `on-primary` — that was for their bright `#2ff28f`.

### 2.3 Collision groups — resolved
All 8 placeholder collision groups are broken except **two intentional equalities**, which are correct:
`--color-ink == --color-canvas-dark` (canvas-dark *is* ink) and `--color-archive-olive == --color-muted`
(both "muted neutral"). Everything else (`surface-soft`/`surface-band`/`surface-green`, the `slate/steel/muted`
text ramp, `forest*`) now holds distinct values, so a palette specimen no longer renders duplicates.

### 2.4 Renames — deferred (cost named)
Token *names* stay hi2vi-identical (value swap only). The vestigial-name pass — renaming
`victory-lime`/`archive-olive`/`archive-cream`/`security-mint`/`security-teal`/`trust-sage` to vocky-semantic
names — is **optional and out of scope for this round.** Cost if ever done: it is call-site churn across
`web/src/**` (every `bg-*`/`text-*`/`border-*` using those names) plus `globals.css`; do it as its own
mechanical slice, not mixed into a visual one.

### 2.5 Hardcoded literals a value swap does NOT reach — fix by hand
- **`web/src/components/ui/button.tsx`** — the two `primary` shadows use `rgba(79,70,229,…)` (old accent).
  Replace with the green: `shadow-[0_10px_24px_-12px_rgba(12,122,82,0.5)]` and hover
  `shadow-[0_14px_30px_-12px_rgba(12,122,82,0.62)]`.
- **`web/src/components/ui/card.tsx`** — `feature`/`pricing` shadows use `rgba(15,23,42,…)` (old ink) → ink
  `rgba(14,26,22,…)`; `pricingFeatured` border `rgba(79,70,229,0.55)` → `var(--color-green)` (use `border-green`
  / `border-2 border-green`), its shadow → `rgba(12,122,82,0.34)`; `archive` border literal `#e2e8f0` →
  `border-hairline`.
- **`web/src/app/globals.css`** shadcn alias layer: confirm `--ring: var(--color-green-deep)`,
  `--primary: var(--color-green)`, `--primary-foreground: var(--color-on-primary)`,
  `--destructive: var(--color-danger)`. (All already map by name; just verify after the swap.)
- **shadow/arbitrary sizes** in `app-shell.tsx` (`text-[18px] tracking-[-0.3px]` brand,
  `min-h-[calc(100dvh-57px)]`, `max-w-[420px]`) are addressed in §4/§6.

---

## 3. Type (`web/src/lib/fonts.ts` + `globals.css`)

### 3.1 Faces
- **`--font-sans` → Pretendard** (Korean-capable). **Loader change — the one named build cost:** Pretendard is
  not on Google Fonts, so replace the `Noto_Sans_KR` import with a `next/font/local` load of vendored
  Pretendard woff2 **or** add `@fontsource/pretendard`. Keep the CSS var name `--font-noto-sans-kr` **or** rename
  to `--font-pretendard` and update the `@theme --font-sans` chain to match. **Fallback chain must retain a
  Korean-capable face:** `var(--font-pretendard), "Pretendard", "Noto Sans KR", -apple-system, BlinkMacSystemFont, system-ui, sans-serif`.
- **`--font-mono` → JetBrains Mono** — unchanged.
- **`--font-en` → drop the bare system stack.** Point it at the sans:
  `--font-en: var(--font-pretendard), Pretendard, "Noto Sans KR", system-ui, sans-serif;` (or simply reuse
  `--font-sans`). Buttons (`button.tsx:18` uses `font-en`) then render in Pretendard, not the visitor's font.
- **Preserve** `h1–h6 { word-break: keep-all }` and the reduced-motion / focus-ring base layers exactly.

### 3.2 Type scale — replace the `@theme --text-*` values
Keep all 14 step names; new size / line-height / letter-spacing / weight:

| Step | size | line-height | letter-spacing | weight |
|---|---|---|---|---|
| `hero-display` | 60px | 1.05 | -1.5px | 800 |
| `display-lg` | 46px | 1.1 | -1.1px | 800 |
| `heading-1` | 38px | 1.15 | -0.8px | 700 |
| `heading-2` | 30px | 1.2 | -0.5px | 700 |
| `heading-3` | 24px | 1.25 | -0.4px | 700 |
| `heading-4` | 18px | 1.35 | -0.2px | 700 |
| `body-lg` | 18px | 1.6 | — | 400 |
| `body-md` | 15px | 1.6 | — | 400 |
| `body-md-medium` | 15px | 1.55 | — | 600 |
| `body-sm` | 13px | 1.55 | — | 400 |
| `caption` | 12px | 1.45 | — | 500 |
| `micro` | 11px | 1.4 | 0.8px | 700 |
| `button-md` | 14px | 1.2 | — | 600 |
| `code-md` | 13px | 1.55 | — | 400 |

(Weights are standard Pretendard weights — drop the odd `680`; load Pretendard 400/500/600/700/800.)

---

## 4. Spacing / radius / containers / breakpoints (`globals.css`) + primitives

### 4.1 Radius — replace `@theme --radius*`
`--radius: 10px` · `--radius-xs: 4px` · `--radius-sm: 6px` · `--radius-md: 8px` · `--radius-lg: 10px` ·
`--radius-xl: 14px` · `--radius-xxl: 20px` · `--radius-full: 9999px`. Update the shadcn `:root --radius: 10px`.

### 4.2 Spacing & containers (landing keeps generous rhythm)
`--spacing-section-sm: 48px` · `--spacing-section: 72px` · `--spacing-section-lg: 104px` · `--spacing-hero: 120px`.
`--container-page: 1180px` (app + landing content) · `--container-wide: 1320px`.
**App density (compact) — use these utilities, not tokens:** page blocks `space-y-6` (was 8); cards `p-5`;
table cells `px-4 py-2`; stat tiles `p-4`; section headers `mt-6`.

### 4.3 Breakpoints — drop `xs`, tokenize the real one
Remove `--breakpoint-xs`. Add `--breakpoint-app: 56.25rem;` (900px). **Migrate all 11 `min-[900px]:`
utilities** in `app-shell.tsx`, `rail-nav.tsx`, `feedback/page.tsx`, `feedback/[feedbackId]/page.tsx` to the
`app:` variant. No `xs:` variant is introduced (there were zero consumers).

### 4.4 Buttons — `web/src/components/ui/button.tsx`
Base (note **`rounded-md`, not `rounded-full`**):
`inline-flex items-center justify-center gap-2 rounded-md font-en text-button-md font-semibold transition focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50`
Variants:
- `primary`: `bg-green text-on-primary shadow-[0_10px_24px_-12px_rgba(12,122,82,0.5)] hover:-translate-y-0.5 hover:bg-green-deep hover:shadow-[0_14px_30px_-12px_rgba(12,122,82,0.62)]`
- `secondary`: `border border-hairline-strong bg-canvas text-ink hover:bg-surface`
- `ghost`: `bg-transparent text-steel hover:bg-surface-soft hover:text-charcoal` *(new — LogoutButton uses this)*
- `destructive`: `bg-danger text-on-dark hover:bg-danger-deep` *(new)*
- `destructiveOutline`: `border border-hairline-danger bg-canvas text-danger-deep hover:bg-surface-danger` *(new — per-row Revoke)*
- `dark` *(rename of `secondaryOnDark`)*: `border border-hairline-dark bg-transparent text-on-dark hover:bg-white/10`
- `link`: `h-auto min-h-0 rounded-none bg-transparent p-0 text-body-md-medium text-green-dark hover:underline`
Sizes: `default: min-h-10 px-[18px] py-2` · `sm: min-h-9 px-3.5` · `lg: min-h-12 px-7 text-[15px]`.
Keep `defaultVariants {variant:"primary", size:"default"}`; keep the anchor-reuse pattern (`buttonVariants` on `<a>`).

### 4.5 `LogoutButton` — `web/src/components/app-shell/logout-button.tsx`
Replace the bespoke chip markup with `<Button variant="ghost" size="sm" disabled={pending} onClick={…}>`.
Keep the pending state + best-effort logout logic verbatim.

### 4.6 Card — `web/src/components/ui/card.tsx`
- `base`: `rounded-lg border border-hairline bg-canvas p-5`
- `feature`: `rounded-xl border border-hairline bg-canvas p-6 shadow-[0_12px_32px_-18px_rgba(14,26,22,0.16)]`
- `featureMuted`: `rounded-xl border border-hairline-soft bg-surface p-5`
- `dark`: `rounded-xl border border-hairline-dark bg-forest p-7 text-on-dark`
- `pricing`: `rounded-xl border border-hairline bg-canvas p-7 shadow-[0_14px_38px_-22px_rgba(14,26,22,0.18)]`
- `pricingFeatured`: `rounded-xl border-2 border-green bg-canvas p-7 shadow-[0_24px_56px_-28px_rgba(12,122,82,0.34)]`
- **Drop** `security` and `archive` variants (placeholder-only; no consumer keeps them — the credential "Revoked"
  case moves to the `revoked` Badge, §4.7).

### 4.7 Badge — `web/src/components/ui/badge.tsx` (split the overloaded `archive`)
Base: `inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption font-semibold`. Variants:
- `liked`: `bg-green-soft text-green-dark`
- `disliked`: `bg-surface-danger text-danger-deep`
- `unrated`: `bg-surface-soft text-steel`
- `active`: `bg-green-soft text-green-dark`
- `revoked`: `bg-surface-soft text-steel`
- `accent`: `bg-green text-on-primary`
`defaultVariants {variant:"unrated"}`. **Migrate call sites:** `feedback-fields.tsx` `RatingBadge` →
`liked|disliked|unrated`; `projects/[id]/page.tsx` credential status → `active` / `revoked` (was
`softGreen`/`archive`). Optional dot: prepend `<span class="inline-block size-1.5 rounded-full bg-*">`.

### 4.8 Select — **new** `web/src/components/ui/select.tsx`
A styled native `<select>` (keep native for a11y). Wrapper `<span class="relative block">` + the select +
a CSS chevron. Select classes: same control base as Input plus `appearance-none pr-9`. Chevron: an
`::after`/absolutely-positioned element `right-3 top-1/2` (a rotated bordered square, per the artifact).
Export `Select` + `selectVariants`. **Replace** the two raw `<select className={inputVariants()}>` in
`feedback/page.tsx`'s `FilterBar` (Project, Rating) — this removes the `cn()`-bypassing template-literal hack.

### 4.9 Chip / Tag — **new** `web/src/components/ui/chip.tsx`
Base: `inline-flex items-center gap-1.5 rounded-sm border border-hairline bg-surface px-2 py-0.5 font-mono text-caption text-slate`.
Variants: `default` (above); `filter` (active-filter pill): `border-security-mint bg-green-soft text-green-dark`,
with an optional trailing remove `<button aria-label>✕</button>` (`removable` prop + `onRemove`). **Use it for**
feedback-detail tags (replaces the bespoke `rounded-full` span in `feedback/[feedbackId]/page.tsx`) and,
optionally, active-filter pills on the feedback list.

### 4.10 Field — `web/src/components/ui/field.tsx`
Control base: `w-full rounded-md border border-hairline-strong bg-surface px-3 text-body-md text-ink placeholder:text-steel transition-colors focus-visible:outline-none hover:border-steel disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-destructive`.
`inputVariants = base + "min-h-[38px] py-2"` · `textareaVariants = base + "min-h-24 py-2"`.
`Checkbox`: `mt-0.5 size-[18px] shrink-0 rounded-sm border border-hairline-strong accent-green focus-visible:outline-none aria-[invalid=true]:border-destructive`.
**`FieldError` unchanged** — keep the empty `min-h-[1.25rem]` `aria-live="polite"` region (locked a11y floor).

### 4.11 DataTable — `web/src/components/ui/data-table.tsx` (compact)
Wrapper `overflow-x-auto rounded-lg border border-hairline`. `thead th`:
`px-4 py-2 text-micro font-bold uppercase tracking-[0.6px] text-steel bg-surface border-b border-hairline`
(text-align left, or right when `actions`). `tbody td`: `px-4 py-2 align-middle text-ink`. Row:
`border-b border-hairline-soft transition-colors last:border-b-0 hover:bg-surface`. Empty slot: keep the
`colSpan` full-width note (`px-4 py-10 text-center text-body-sm text-steel`). Keep the typed `columns`/`rows`/
`rowKey`/`empty`/`actions` API exactly.

### 4.12 Section / Grid / EndpointCard / Reveal
- **Section** tones: `default bg-canvas text-ink` · `surface bg-surface` · `surfaceSoft bg-surface-soft` ·
  `band bg-surface-band` (now visually distinct from surfaceSoft) · `security bg-surface-security` ·
  `archive bg-surface-archive` · `ink bg-ink text-on-dark` · `forest bg-forest text-on-dark`. Landing bands use
  `py-section md:py-section-lg`. Widen the `SectionId` type to include the landing anchors (`features`,
  `how`, `pricing`, `docs`) or relax `id` to `string` for the landing (the `overview`/`primitives` values are
  dead — replace them).
- **Grid** unchanged; remember `gap` takes a scanned class only (`gap-1..4` exist; add any new gap class to the
  content scan). Landing feature grid = `Grid cols={3}`.
- **EndpointCard**: `rounded-xl border border-forest-soft bg-forest-mid p-6 text-on-dark`; label chip
  `bg-ink text-security-teal font-mono text-caption rounded-full px-2.5 py-1`; `pre font-mono text-code-md`.
- **Reveal** unchanged (reduced-motion-safe); this is the only motion primitive — use sparingly on the landing.

### 4.13 StatTiles — `web/src/components/usage/stat-tiles.tsx`
Compact: tile = `Card variant="base"` at `p-4`. Label `text-caption font-medium text-steel` with a leading
rating dot per `tile.key` (`total`→none, `liked`→`bg-green`, `disliked`→`bg-danger`, `unrated`→`bg-muted`).
Number `font-mono text-heading-3 text-ink tabular-nums`. Keep the `window` label + `aria-labelledby` + `Grid cols={4}`.

### 4.14 TrendChart — `web/src/components/usage/trend-chart.tsx` (area redesign, dependency-free)
Replace the bars with a filled **area chart** — no chart library. Algorithm:
- `n = days.length`; `max = Math.max(1, ...days.map(d=>d.total))` (floor 1). viewBox `0 0 100 H`, `H=42`,
  `pad=2`. `x_i = n>1 ? (i/(n-1))*100 : 50`; `y_i = H - (d.total/max)*(H-2*pad) - pad`.
- `line = "M x0 y0 L x1 y1 …"`; `area = line + " L 100 " + (H-pad) + " L 0 " + (H-pad) + " Z"`.
- `<defs><linearGradient>` green `stop 0 opacity .22 → stop 1 opacity 0`. Baseline `<line y=H-pad stroke=hairline stroke-width .6>`.
  Area `fill=url(#…)`; line `fill=none stroke=var(--color-green) stroke-width 1.4 vector-effect="non-scaling-stroke" stroke-linejoin/linecap round`.
  Optional small `<circle r=0.9 fill=green>` per point, each with `<title>{dayLabel}: {total}</title>` for native hover.
- SVG `role="img"` + `aria-label`, `preserveAspectRatio="none"`, `class="h-40 w-full"`. **Keep the existing
  sr-only summary sentence** (peak/total/range) and the two axis labels underneath, and the partial-day note.
- **Both empty shapes preserved:** `days.length===0` → the empty note box; all-zero series → a flat line at the
  baseline (the `max` floor guarantees no divide-by-zero). See the artifact §05 for populated / all-zero / empty.

---

## 5. App surfaces — per-file changes (real strings; app copy is locked)

- **`components/app-shell/app-shell.tsx`** — replace the `text-[18px] tracking-[-0.3px]` brand with the
  **mark + wordmark** (see §7.1 for the mark). Migrate `min-[900px]:` → `app:`. Compact paddings (topbar
  `px-6 py-3`; main `px-4 pt-5 pb-10 app:px-6`). Keep it a server component; topbar = mark+wordmark · divider ·
  `Workspace {tenant}` · spacer · `{email}` · `<LogoutButton/>`.
- **`components/app-shell/rail-nav.tsx`** — active item: `bg-green-soft font-medium text-green-dark` **+ an inset
  green accent bar** (`shadow-[inset_2px_0_0_var(--color-green)]` or a left border); inactive
  `text-slate hover:bg-surface-soft hover:text-ink`. `rounded-md px-3 py-2 text-body-sm`. Migrate breakpoint.
  Keep the `soon` affordance and `aria-current` logic.
- **`(auth)/auth-card.tsx`** — mark+wordmark above the card; `Card variant="feature"`. Login/signup forms
  unchanged in logic — **the identical-error mapping (401 → one message) is in the form/BFF and must not
  change.** Auth layout stays `bg-surface`, centered, `max-w-[400px]`.
- **`(app)/dashboard/page.tsx`** — `space-y-8` → `space-y-6`; page title `text-heading-3`. Uses the new
  StatTiles + TrendChart. Project name link `font-medium text-ink hover:text-green-dark hover:underline`.
- **`(app)/projects/[projectId]/page.tsx`** — **add a breadcrumb** above the title:
  `<nav class="text-body-sm text-steel"><a href="/dashboard" class="text-green-dark hover:underline">Dashboard</a> / {project.name}</nav>`
  (data already loaded; no rail-current change). Credential status badges → `active`/`revoked`. Revoke control →
  `Button variant="destructiveOutline" size="sm"` with the existing confirm step. **Show-once key panel:** render
  in a green-tinted card (`border-security-mint bg-surface-green`), keep the full warning string verbatim
  (`PROJECT.keyPanel.warning`) and the Copy/Dismiss controls. Revoked keys stay listed.
- **`(app)/feedback/page.tsx`** — swap the two raw `<select>` for `<Select>`; filter Card `variant="base"`.
  Optionally render active filters as removable `Chip variant="filter"` pills above the table. Compact table.
  Migrate breakpoint. **Keep the plain `<form method="GET">`, the blank-is-absent param logic, forward-only
  Next page, and the two distinct empty states** verbatim.
- **`(app)/feedback/feedback-fields.tsx`** — `RatingBadge` → `Badge` `liked|disliked|unrated`; `Timestamp`
  stays mono/tabular UTC.
- **`(app)/feedback/[feedbackId]/page.tsx`** — tags → `<Chip>`; keep the `dl` Details grid (`app:` breakpoint),
  the whitespace-preserving message/comment cards, read-only operator comments, **download-only attachments**
  (unchanged proxy `href` + `download`), and collapsible Raw blocks.
- **Island forms** (`create-project-form.tsx`, `mint-credential-form.tsx`, `revoke-credential-button.tsx`) —
  buttons to the new variants; no logic change.

---

## 6. Net-new states (net-new files — design them, not framework defaults)

- **`web/src/app/(app)/loading.tsx`** (+ optionally per-route `dashboard/loading.tsx`, `feedback/loading.tsx`,
  `projects/[projectId]/loading.tsx`) — a skeleton of the real layout: a `text-heading-3`-height title block,
  a `Grid cols={4}` of 4 stat-tile skeletons, a chart-height block, and 4–6 table-row skeletons. Skeleton block:
  `rounded-md bg-hairline-soft` at the element's height. **Static under reduced motion** (no shimmer); a subtle
  `animate-pulse` is allowed only outside reduced-motion.
- **`web/src/app/(app)/error.tsx`** (`"use client"`, takes `{error, reset}`) — centered `Card`: danger-tinted
  mark, `heading-4` "Something went wrong", `body-sm text-steel` "We couldn't load this page. Please try again.",
  and a `Button size="sm" onClick={reset}` "Try again". Never render `error.message` (may leak internals).
- **`web/src/app/not-found.tsx`** (root) and optionally `web/src/app/(app)/not-found.tsx` — mono `404`
  (`text-green-dark`), `heading-4` "This page doesn't exist", `body-sm text-steel` **"The page you asked for
  isn't here — or isn't yours to see."** (honors **404-never-403** — never confirms existence), and a
  `Button variant="secondary"` link "Back to dashboard".
- **`web/src/app/global-error.tsx`** (`"use client"`, renders its own `<html><body>`) — minimal full-page
  variant of `error`: brand mark, "Something went wrong", reset.

---

## 7. Landing — reclaim `/` (largest net-new surface)

### 7.1 The brand mark (define once, reuse)
The mark is **three rising rounded bars** (a waveform / capture-volume motif) in white on a green
(`--color-green`) rounded-square tile. Build as a small component (`components/brand/mark.tsx` + `wordmark`):
inline SVG or 3 `<span>` bars — simple geometry only, no illustration. Sizes: 32px (chrome), 52px (hero/empty
states). Wordmark: `font-weight:800; letter-spacing:-1px` lowercase "vocky", `text-ink` on light / white on
dark. See both artifacts' headers/footers for exact proportions.

### 7.2 Route & behavior
`web/src/app/page.tsx` becomes the **public landing** (server component). Keep the signed-in bounce:
`const token = await getSession(); if (token) redirect("/dashboard");` then render the landing for signed-out
visitors. (Preserves the operator's "signed-in → dashboard" ruling; `/` stops being a pure redirect.) The
landing renders its own nav/footer — it is **outside** the `(app)` group, so no app shell.

### 7.3 Copy — **new** `web/src/content/landing.ts` (landing copy is in-play this pass; authored, grounded)
Author the strings below into a `LANDING` const (copy-as-data, per the S1 convention). All are grounded in real
product facts — no lorem.
- **nav:** links `Features` `How it works` `Pricing` `Docs`; `Sign in` → `/login`; `Start free` → `/signup`.
- **hero:** eyebrow "Voice of customer, for builders"; headline **"Capture the feedback your product is already
  getting."**; sub "vocky is a feedback layer for your product. Your backend sends explicit user reactions —
  likes, dislikes, comments — over a single REST call, and vocky turns them into structured signal you can
  search across every project."; CTAs "Start free" / "Read the docs". Hero visual = an `EndpointCard`
  (`POST /api/feedback` with a real JSON body incl. a Korean `message`) beside a "captured" record `Card`
  (Korean message + `disliked` badge + two `Chip` tags).
- **trust strip:** `POST /api/feedback` · "structured signal, not log noise" · "search 결제 or checkout" ·
  "MIT-licensed".
- **how (3 steps):** 1 "Create a project, mint a key" (vk_ key, shown once, hashed, revocable) · 2 "Your backend
  sends feedback" (POST /api/feedback on like/dislike/comment; server-to-server, no browser SDK) · 3 "Search &
  review it" (across projects, Korean & English).
- **showcase:** eyebrow "One place to look"; "Every reaction, across every project."; a browser-framed feedback
  table mock (When/Project/Feedback/Rating rows with rating badges).
- **features (6):** server-to-server capture · structured, not log noise · search in any language · per-project
  API keys (shown once) · like/dislike/listen (explicit only) · free & self-hostable. (Exact sentences in the
  Landing artifact §Features.)
- **pricing:** heading "Free while we're building. Paid plans later."; **Free** card — badge "Available now",
  "$0 / forever, for now", inclusions (unlimited projects & keys, unlimited capture, cross-project search,
  comments & attachments, self-host or hosted), CTA "Start free"; **muted "Pro & Teams — coming later"** card —
  "—", items (team seats & roles, longer retention, saved views & exports, priority support), disabled control
  "Not yet — vocky is free today".
- **closing CTA:** "Start hearing what your users actually think." + sub + "Start free" / "Read the docs".
- **footer:** columns Product (Features/How it works/Pricing) · Project (Documentation/GitHub/MIT license) ·
  Account (Sign in/Start free); "© 2026 vocky · pre-MVP".

### 7.4 Components — **new** `web/src/components/landing/*`
Compose from the adopted primitives: `LandingNav`, `Hero`, `TrustStrip`, `HowItWorks`, `Showcase`, `Features`
(`Grid cols={3}` of `Card`/feature blocks), `Pricing` (`Card variant="pricingFeatured"` + `pricing`),
`ClosingCTA` (`Section tone="forest"`), `LandingFooter` (`Section tone="forest"`). Use `Section` tonal bands,
`EndpointCard`, `Button` (`primary`/`secondary`/`dark`), and `Reveal` for one-shot section reveals only.
Content max-width `--container-page`.

---

## 8. Per-file change manifest (what P9 slices from)

**Foundations** — `web/src/app/globals.css` (color, type scale, radius, spacing, breakpoint, header comment);
`web/src/lib/fonts.ts` (Pretendard loader); Pretendard asset (`public/fonts/*` via `next/font/local`, or add
`@fontsource/pretendard` to `web/package.json`).

**Primitives** — `components/ui/`: `button.tsx`, `card.tsx`, `badge.tsx`, `field.tsx` (rewrites);
**new** `select.tsx`, `chip.tsx`; update `index.ts` barrel (+ `Select`, `Chip`, new variant exports).

**App components** — `components/app-shell/{app-shell,rail-nav,logout-button}.tsx`;
`components/usage/{stat-tiles,trend-chart}.tsx`; **new** `components/brand/{mark,wordmark}.tsx`.

**App surfaces** — `app/(auth)/auth-card.tsx`; `app/(app)/dashboard/page.tsx`;
`app/(app)/projects/[projectId]/page.tsx` (+ `mint-credential-form.tsx`, `revoke-credential-button.tsx`);
`app/(app)/feedback/page.tsx`, `feedback-fields.tsx`, `[feedbackId]/page.tsx`;
`app/(app)/dashboard/create-project-form.tsx`.

**States** — **new** `app/(app)/loading.tsx` (± per-route), `app/(app)/error.tsx`, `app/not-found.tsx`
(± `app/(app)/not-found.tsx`), `app/global-error.tsx`.

**Landing** — `app/page.tsx` (reclaim `/`); **new** `content/landing.ts`; **new** `components/landing/*`;
update `content/section-ids.ts` (replace dead `overview`/`primitives` with the landing anchors) or relax the
`Section` `id` type.

**Cleanup** — remove `--breakpoint-xs` and migrate `min-[900px]:` → `app:` (across the files above); retire the
dead `content/nav.ts` / `section-ids.ts` leftovers if unused after the landing lands.

---

## 9. Backend / data implications — **none required**
Everything maps to existing serializers, routes, and already-fetched data:
- Landing is static marketing; the signed-in bounce reuses `getSession()` (already present).
- Project-detail breadcrumb uses the already-loaded `project.name`.
- `Select`/`Chip`/badge split/area chart are all presentational.
- The pricing "coming later" card is copy only (its control is disabled — **no** waitlist endpoint this round;
  if a waitlist is ever wanted, that is net-new backend, flagged, not built here).
The **only** non-trivial build cost is **Pretendard vendoring** (§3.1). No `src/vocky/**` or P2/P3 contract
change is implied by this design.

---

## 10. Definition of done (the bar the read-back checks against)
- [ ] `globals.css` holds the §2/§3/§4 values; the palette specimen shows no accidental duplicates; header comment updated.
- [ ] Pretendard loads (Korean renders), with a Korean-capable fallback; `--font-en` no longer a bare system stack.
- [ ] Buttons are `rounded-md`; the new `ghost`/`destructive`/`destructiveOutline` variants exist; LogoutButton is a `Button`.
- [ ] `Select` and `Chip` exist and are used (feedback filters use `Select`; feedback tags use `Chip`); no `inputVariants()` template-literal `<select>` remains.
- [ ] Badge `archive` is split; credential status uses `active`/`revoked`; rating uses `liked`/`disliked`/`unrated`.
- [ ] TrendChart is the area redesign, dependency-free, with the a11y summary + both empty shapes handled.
- [ ] All six app surfaces render with the new system at compact density; project detail has a breadcrumb.
- [ ] `/` serves the landing to signed-out visitors and bounces signed-in ones to `/dashboard`; all landing copy from `content/landing.ts`.
- [ ] `loading` / `error` / `not-found` / `global-error` exist and match the designed states; 404 copy is generic (404-never-403).
- [ ] `--breakpoint-xs` gone; `--breakpoint-app` (900px) used; no `min-[900px]:` literals remain.
- [ ] **Locked floors intact:** identical login error, 404-never-403, show-once key warning + revoked-stays-listed, download-only attachments, UTC labels, `word-break: keep-all`, Korean-capable `--font-sans`, `FieldError` `aria-live`, distinct empty states.
- [ ] No `src/vocky/**` change; all data maps to existing serializers.
