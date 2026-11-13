# P9.S2 — Result: Primitives — `ui/` rewrites + new Select/Chip + barrel

**Verdict:** done. Every `ui/` primitive rewritten to the vocky system per `build-prompt.md §4.4–4.12`
(+ §2.5 literal fixes), two net-new primitives added (Select, Chip), the barrel updated, and the one
breaking API change (Badge variant rename) migrated at its two call sites so the tree compiles. `typecheck`,
`lint`, and `build` are all green.

## Per-file summary

- **`button.tsx`** — base is now `rounded-md` + `font-semibold` + `gap-2` (was `rounded-full`/`font-bold`,
  no gap), keeps `font-en text-button-md` and the focus/disabled classes. Variants: kept
  `primary`/`secondary`/`link`; **renamed** `secondaryOnDark`→`dark`; **added** `ghost`, `destructive`,
  `destructiveOutline`. `primary`'s two shadows now use the green signature rgba (`rgba(12,122,82,0.5)` /
  hover `0.62`, §2.5). Sizes retuned to `default: min-h-10 px-[18px] py-2` · `sm: min-h-9 px-3.5` ·
  `lg: min-h-12 px-7 text-[15px]`. `defaultVariants {primary, default}` and the anchor-reuse pattern kept.
- **`card.tsx`** — `base` p-5; `feature` p-6 + ink shadow `rgba(14,26,22,0.16)`; `featureMuted` p-5;
  `dark` p-7; `pricing` p-7 + ink shadow `rgba(14,26,22,0.18)`; `pricingFeatured` `border-2 border-green`
  + green shadow `rgba(12,122,82,0.34)`. **Dropped** `security` and `archive` (zero consumers; the old
  `#e2e8f0`/`rgba(79,70,229,…)`/`rgba(15,23,42,…)` literals are gone with them).
- **`badge.tsx`** — base `inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption
  font-semibold`. Variants split into `liked`/`disliked`/`unrated`/`active`/`revoked`/`accent` with the
  exact §4.7 tokens; `defaultVariants {unrated}`. Added an optional `dot?: boolean` prop that prepends a
  `size-1.5 rounded-full` dot whose color is derived from the variant (`liked/active`→green,
  `disliked`→danger, `unrated/revoked`→muted, `accent`→on-primary) — the base `gap-1.5` spaces it. This
  keeps the primitive "able to render the optional leading dot" for StatTiles/feedback to opt into later.
- **`field.tsx`** — control base `px-3.5`→`px-3`; `inputVariants` now `min-h-[38px] py-2`; `textareaVariants`
  `min-h-24 py-2`; `Checkbox` `size-5`→`size-[18px]` (`accent-green` kept). **`FieldError` untouched** — the
  empty `min-h-[1.25rem]` `aria-live="polite"` region is preserved verbatim (locked a11y floor).
- **`data-table.tsx`** — `thead th` moved to `border-b border-hairline bg-surface px-4 py-2 text-micro
  font-bold uppercase tracking-[0.6px] text-steel` (styling now on the `th`, the `<tr>` classes dropped);
  `tbody td` `py-3`→`py-2`. Row hover, `border-hairline-soft` dividers, wrapper, empty `colSpan` slot, and
  the typed `columns`/`rows`/`rowKey`/`empty`/`actions` API all unchanged.
- **`endpoint-card.tsx`** — panel border `border-green-deep`→`border-forest-soft`; label-chip text
  `text-green`→`text-security-teal`. `bg-ink … font-mono text-caption rounded-full px-2.5 py-1` chip and
  `pre font-mono text-code-md` kept.
- **NEW `select.tsx`** — styled **native** `<select>` (a11y preserved). Wrapper `<span class="relative
  block">` + select + a CSS chevron (a `rotate-45` bordered square at `right-3 top-1/2`). `selectVariants`
  reuses `inputVariants()` (so filter selects match form fields) + `appearance-none pr-9`. Exports `Select`,
  `selectVariants`, `SelectProps`. `className` targets the `<select>`, optional `wrapperClassName` the
  wrapper. Not yet adopted (feedback filter bar is S4).
- **NEW `chip.tsx`** — base `inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 font-mono
  text-caption`; variants `default` (`border-hairline bg-surface text-slate`) and `filter`
  (`border-security-mint bg-green-soft text-green-dark`); optional `removable` + `onRemove` renders a
  trailing `<button aria-label="Remove">✕</button>` (`removeLabel` overridable). Exports `Chip`,
  `chipVariants`, `ChipProps`. Kept as a plain (non-`"use client"`) primitive like `Button` — a client
  parent supplies `onRemove`. Not yet adopted (feedback-detail tags / filter pills are S4).
- **`index.ts`** — added `Select`/`selectVariants`/`SelectProps` and `Chip`/`chipVariants`/`ChipProps`;
  refreshed the stale "placeholder … P6 swaps values" header comment to describe the applied vocky system.

## Forced Badge call-site migration (kept the tree green)

- **`feedback-fields.tsx`** — `RatingBadge`: `1`→`Badge variant="liked"`, `2`→`Badge variant="disliked"`,
  **`null`→`Badge variant="unrated"`**. The old `null` branch rendered muted `<span>` text; per §4.7 the
  design gives `null` an *explicit* `unrated` badge, so the rating column now reads as three consistent
  badges. **No content string was added** — `FEEDBACK.list.valueUnrated` ("Unrated") already existed and is
  reused (alongside the existing `valueLiked`/`valueDisliked`). `Timestamp` stays mono/tabular UTC —
  untouched. This is the file's *entire* P9 change.
- **`projects/[projectId]/page.tsx`** — credential-status badges only: `softGreen`→`active`,
  `archive`→`revoked` (lines 91/93). Breadcrumb, revoke button, key panel, and compaction were **not**
  touched (they are S4).

The **green `pnpm build`** is the proof the rename caught every call site — a grep confirms no old Badge
variant name (`signal`/`softGreen`/`archive`/`security`/`dark`) remains in `src/`.

## Verification

| Command | Result |
|---|---|
| `cd web && pnpm typecheck` | ✅ clean |
| `cd web && pnpm lint` | ✅ clean |
| `cd web && pnpm build` | ✅ green (all 12 routes compiled + page data collected) |
| `pnpm exec prettier --write <11 touched files>` | ✅ formatted (tidied Tailwind class order in 3 files; the 20 pre-existing unrelated `format:check` failures were left untouched) |
| grep: old Badge variant names in `src/` | ✅ none |
| grep: `Select`/`Chip` exported from barrel | ✅ present |
| grep: button base `rounded-md` | ✅ present |
| grep: Card `security`/`archive` variants | ✅ gone |
| grep: `FieldError` `aria-live="polite"` + `min-h-[1.25rem]` | ✅ intact |
| grep: `secondaryOnDark` anywhere | ✅ none |

## Notes for S3 / S4

- **`feedback-fields.tsx` is fully migrated — S4 need not re-touch it.** Its only P9 change (the RatingBadge
  variant swap, incl. `null`→`unrated` badge) is done.
- **`projects/[projectId]/page.tsx`: only the two credential-status badge lines were changed.** The
  breadcrumb, `Button variant="destructiveOutline"` revoke control, show-once key panel, and `min-[900px]:`
  compaction are all **still S4's** — untouched here.
- **`Select` and `Chip` exist and are barrel-exported but not adopted.** S4 replaces the two raw
  `<select className={inputVariants()}>` in `feedback/page.tsx`'s FilterBar with `<Select>`, and the bespoke
  `rounded-full` tag spans in `feedback/[feedbackId]/page.tsx` with `<Chip>` (optionally active-filter
  `Chip variant="filter"` removable pills). `Select`'s `className` targets the `<select>`; a removable Chip
  needs a client parent for `onRemove`.
- **Badge dot is available for StatTiles (S3).** `<Badge dot variant=…>` renders a variant-colored leading
  dot; StatTiles (§4.13) renders its *own* per-key dots inside a Card, not via Badge — so it need not use
  this, but the affordance exists if wanted.
- **`Card dark`/`pricing`/`pricingFeatured` now exist** but have no consumer until the landing (S6) — as
  planned. `EndpointCard` is retoned and ready for the landing hero (S6).
- **No `section.tsx`/`grid.tsx`/`reveal.tsx` change** (per the boundary); the `SectionId` widening is S6.

## Deviations from `plan.md`

None. Every string was taken from `build-prompt.md §4` as directed. The one judgment call — the Badge
`dot` prop shape — resolves the plan's "keep the primitive able to render the optional leading dot" with a
`dot?: boolean` whose color derives from the variant (closest-to-designed-intent, not a plainer fallback).
