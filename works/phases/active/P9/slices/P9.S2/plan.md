# P9.S2 — Plan: Primitives — `ui/` rewrites + new Select/Chip + barrel

## Context — why this slice exists

Second slice of the strict `1→2→3` chain. S1 landed the tokens; S2 rewrites the CVA primitives that
consume them so every downstream surface (S3/S4/S5/S6) composes the vocky look. `build-prompt.md §4.4–4.12`
give the **exact class strings** for each primitive; §4.8/§4.9 define the two net-new primitives (Select,
Chip). Read those values from `build-prompt.md` — do not hand-transcribe from this plan.

**One breaking API change forces a same-slice call-site migration.** The Badge variants are renamed
(`signal`/`softGreen`/`archive`/`security`/`dark` → `liked`/`disliked`/`unrated`/`active`/`revoked`/
`accent`). Verified consumers of the old names: `feedback-fields.tsx` (RatingBadge) and
`projects/[projectId]/page.tsx` (credential status). Removing the old names makes those two files fail
`typecheck`/`build` — so **S2 migrates them in the same slice** (standard atomic refactor). Every other
change is non-breaking: Select/Chip are additive; Button `secondaryOnDark` and Card `security`/`archive`
have **zero consumers** (verified); the rest is pure restyle.

Source of truth on disk (no DesignSync): `docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md`
§4. Read `works/phases/active/P9/phase.md` (Findings & Constraints) before starting.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## Files S2 owns

All of `web/src/components/ui/` + the two forced Badge call-sites:
- Rewrite: `button.tsx`, `card.tsx`, `badge.tsx`, `field.tsx`, `data-table.tsx`, `endpoint-card.tsx`
- **New:** `select.tsx`, `chip.tsx`
- Barrel: `index.ts`
- Forced Badge migration: `app/(app)/feedback/feedback-fields.tsx` (fully — its only P9 change is the badge
  swap), `app/(app)/projects/[projectId]/page.tsx` (**badge-status lines only**, lines ~91/93)

## The work (per file — exact strings in `build-prompt.md §4`)

### `button.tsx` (§4.4 + §2.5)
Base → `rounded-md` (not `rounded-full`), `font-semibold` (not `font-bold`), keep `font-en text-button-md`
+ the focus/disabled classes. Variants: keep `primary`/`secondary`/`link`; **rename** `secondaryOnDark`→
`dark`; **add** `ghost`, `destructive`, `destructiveOutline`. `primary` shadows use the **green** rgba
(§2.5: `rgba(12,122,82,0.5)` / hover `0.62`). Sizes → `default: min-h-10 px-[18px] py-2` · `sm: min-h-9
px-3.5` · `lg: min-h-12 px-7 text-[15px]`. Keep `defaultVariants {primary, default}` and the anchor-reuse
pattern.

### `card.tsx` (§4.6 + §2.5)
`base` p-5; `feature` p-6 + ink shadow `rgba(14,26,22,0.16)`; `featureMuted` p-5; `dark` p-7; `pricing`
p-7 + ink shadow `rgba(14,26,22,0.18)`; `pricingFeatured` `border-2 border-green` + green shadow
`rgba(12,122,82,0.34)`. **Drop** `security` and `archive` variants (zero consumers — verified). All the
old `rgba(15,23,42,…)`/`rgba(79,70,229,…)`/`#e2e8f0` literals go (§2.5).

### `badge.tsx` (§4.7)
Base `inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-caption font-semibold`. Variants
`liked`/`disliked`/`unrated`/`active`/`revoked`/`accent` with the exact bg/text tokens; `defaultVariants
{unrated}`. Support the optional leading dot (a `<span class="inline-block size-1.5 rounded-full bg-*">`)
so StatTiles/feedback can opt in later — keep the primitive able to render it.

### `field.tsx` (§4.10)
Control base → `px-3` (not `px-3.5`), keep `border-hairline-strong bg-surface … hover:border-steel
aria-[invalid=true]:border-destructive`. `inputVariants` `min-h-[38px] py-2`; `textareaVariants`
`min-h-24 py-2`. `Checkbox` `size-[18px]` (not `size-5`) + `accent-green`. **`FieldError` UNCHANGED** —
keep the empty `min-h-[1.25rem]` `aria-live="polite"` region (locked a11y floor).

### `data-table.tsx` (§4.11)
Compact: `thead th` → `px-4 py-2 text-micro font-bold uppercase tracking-[0.6px] text-steel bg-surface
border-b border-hairline`; `tbody td` → `px-4 py-2` (from `py-3`); keep the row hover / `border-hairline-soft`
dividers / `overflow-x-auto rounded-lg border` wrapper / empty `colSpan` slot / the typed
`columns`/`rows`/`rowKey`/`empty`/`actions` API exactly.

### `endpoint-card.tsx` (§4.12)
Panel border `border-green-deep` → **`border-forest-soft`**; label chip text `text-green` →
**`text-security-teal`**; keep `bg-ink … font-mono text-caption rounded-full px-2.5 py-1` and `pre
font-mono text-code-md`.

### NEW `select.tsx` (§4.8)
Styled **native** `<select>` (keep native for a11y). Wrapper `<span class="relative block">` + select +
a CSS chevron (absolutely-positioned rotated bordered square at `right-3 top-1/2`). Select classes: the
Input control base + `appearance-none pr-9`. Export `Select` + `selectVariants`. (Adoption in the feedback
filter bar is **S4**, not here.)

### NEW `chip.tsx` (§4.9)
Base `inline-flex items-center gap-1.5 rounded-sm border border-hairline bg-surface px-2 py-0.5 font-mono
text-caption text-slate`. Variants `default` + `filter` (`border-security-mint bg-green-soft
text-green-dark`) with an optional `removable` prop + `onRemove` rendering a trailing `<button
aria-label>✕</button>`. Export `Chip` + `chipVariants`. (Adoption in feedback-detail tags is **S4**.)

### `index.ts` (barrel)
Add `Select`/`selectVariants`/`SelectProps` and `Chip`/`chipVariants`/`ChipProps` exports; add the new
Badge/Button variant type exports if the types changed. Refresh the stale "placeholder … P6 swaps values"
header comment.

### Forced Badge call-site migration (to keep the tree green)
- `feedback-fields.tsx` — `RatingBadge(value: 1|2|null)`: `1`→`liked`, `2`→`disliked`, **`null`→`unrated`**
  (the designed explicit-unrated state, §4.7). Reuse the existing copy strings from `content/feedback.ts`
  (add/consume a `valueUnrated` label — check the content file; do not invent copy). `Timestamp` stays
  mono/tabular UTC. This is the file's *entire* P9 change — S4 will not re-touch it.
- `projects/[projectId]/page.tsx` — credential status badges `softGreen`→`active`, `archive`→`revoked`
  (lines ~91/93) **only**. The breadcrumb / revoke button / key panel / compaction are **S4** — leave them.

## Deferred / not in S2 (boundary)

- **`Section` `SectionId` type widening (§4.12) → S6.** The landing anchors (`features`/`how`/`pricing`/
  `docs`) don't exist yet; `SECTION_IDS = {overview, primitives}` and `content/nav.ts` consume them today.
  S6 relaxes/widens the type when it adds the landing anchors; S7 retires the dead `overview`/`primitives`
  + `nav.ts` if unused. Section's **tones** already match §4.12 (S1 fixed `surfaceSoft`≠`band`), so S2
  leaves `section.tsx` unchanged. `Grid`/`Reveal` are §4.12 "unchanged" — leave them.
- **`Card` `dark`/`pricing`/`pricingFeatured`** now exist but have no consumer until the landing (S6) —
  correct; S2 defines them, S6 uses them.
- **Do NOT touch** `globals.css`/`fonts.ts` (S1), any `min-[900px]:` literal, or any surface file beyond
  the two forced Badge migrations above.

## Locked floors S2 must preserve

`FieldError` empty `min-h-[1.25rem]` `aria-live="polite"` region; the Button/Field `focus-visible:outline-none`
pairs only suppress the browser default (the global accent ring still shows); native `<select>`/checkbox
for a11y.

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean.
- **`cd web && pnpm build` green** — this is the point of folding the Badge migration in; a red build means
  a call-site was missed.
- `prettier --write` the touched files only (avoid the 20 pre-existing unrelated `format:check` failures).
- Greps: no old Badge variant names (`softGreen`/`"archive"` badge/`signal`/`security`/`"dark"` badge)
  remain in `src/`; `Select`/`Chip` exported from the barrel; button base is `rounded-md`; Card `security`/
  `archive` variants gone; `FieldError` `aria-live` intact.

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

Primitives rewritten to the vocky system: Button (`rounded-md`, +ghost/destructive/destructiveOutline,
secondaryOnDark→dark), Card (dropped security/archive), Badge split into rating+status, Field compact,
DataTable compact, new Select + Chip. `frontend.md` (v0003) still describes the placeholder component set.
For `P9.REVIEW`.
