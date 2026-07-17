# P9.S1 — Plan: Foundations — `@theme` swap + Pretendard loader

## Context — why this slice exists

First and load-bearing slice of P9. `build-prompt.md §1` makes foundations step 1: because Tailwind
utilities compile to `var(--color-*)`, editing the `@theme` block **re-themes every surface at once** —
so this must land before the primitives (S2) and app components (S3) that consume the tokens. S1 turns
the placeholder palette (slate + one indigo) into the signed-off vocky brand (deep-emerald on a
green-cool neutral ramp) and swaps the type/radius/spacing/breakpoint tokens to the compact scale, then
switches the sans face to Pretendard. **No visual component or surface is touched here** — only the
tokens and the font wiring they resolve through.

Source of truth on disk (executor has **no** DesignSync): `docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md`
— §2 (color), §3 (type), §4.1–4.3 (radius/spacing/breakpoint), §2.5 (shadcn-alias verify). Exact tables
are in that file; **read the values from there, do not hand-transcribe from this plan.** Read the phase
notebook `works/phases/active/P9/phase.md` (Findings & Constraints) before starting.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## Files S1 owns (and only these)

- `web/src/app/globals.css` — the `@theme` block, the shadcn `:root` alias layer, the header + token comments.
- `web/src/lib/fonts.ts` — the font loaders.
- `web/src/app/layout.tsx` — the `<html>` font-variable wiring (root layout only).
- **New asset** (if `next/font/local`, recommended): a vendored Pretendard woff2 co-located for `fonts.ts`.

**Boundary — do NOT touch** `button.tsx` / `card.tsx` (their §2.5 hardcoded-shadow/border literals are
S2's, folded into S2's wholesale rewrite — fixing them here would be thrown away), any `(app)` layout or
component, or any `min-[900px]:` literal (S1 only *defines* `--breakpoint-app`; the 11 literals in
`app-shell.tsx`/`rail-nav.tsx`/`feedback/*` migrate in S3/S4). Verified: the font-var rename surface is
exactly the three files above; no `xs:` variant exists anywhere, so dropping `--breakpoint-xs` is safe.

## The work

### 1. `globals.css` — colors (§2.1) + shadcn verify (§2.5)
- Replace all **41 `--color-*` values** with §2.1's `New (vocky)` column. **Names stay identical** (call
  sites untouched). Refresh each trailing comment to the new role (§2.1 `Role` column) — leaving
  "indigo-500" next to `#0C7A52` would be a lie; do not invent roles, use §2.1's.
- `--color-on-primary` stays **`#FFFFFF`** (§2.2, resolved — white text clears AA 5.36:1 on the green).
- The two **intentional equalities** are correct and kept: `--color-ink == --color-canvas-dark` and
  `--color-archive-olive == --color-muted` (§2.3); every other former collision now holds a distinct value.
- shadcn `:root` layer (§2.5 last bullet): **verify** `--primary: var(--color-green)`,
  `--primary-foreground: var(--color-on-primary)`, `--ring: var(--color-green-deep)`,
  `--destructive: var(--color-danger)` — all already map **by name**, so re-themed automatically; confirm, no edit.

### 2. `globals.css` — type scale (§3.2)
- Rewrite all **14 `--text-*` steps** to §3.2's size / line-height / letter-spacing / weight. This is
  **not a pure value swap** — several lines are added/removed:
  - Drop the odd `680` weights; use Pretendard weights **400/500/600/700/800** exactly per the table
    (hero-display 800, display-lg 800, heading-1..4 = 700, body-md-medium 600, caption 500, micro 700,
    button-md 600, the rest 400).
  - **Remove** `--letter-spacing` on the body/caption/button/code steps (the table shows "—" for them).
  - **Add** `--letter-spacing: -0.2px` to `heading-4` (it has none today) and set `micro` to `0.8px` (was 1px).
  - Watch the size changes: hero-display 68→60, display-lg 56→46, heading-1 48→38, heading-2 36→30,
    heading-3 28→24, heading-4 22→18, body-lg 19→18, body-md **16→15**, body-md-medium 16→15, body-sm
    14→13, caption 13→12, button-md line-height 1.3→1.2.

### 3. `globals.css` — fonts chain (§3.1)
- `--font-sans` → Pretendard chain. Recommended: rename the CSS var to `--font-pretendard` (build-prompt
  §3.1 allows it and it's honest) and set the chain to
  `var(--font-pretendard), "Pretendard", "Noto Sans KR", -apple-system, BlinkMacSystemFont, system-ui, sans-serif`
  — **fallback must retain a Korean-capable face** (locked floor).
- `--font-en` → drop the bare system stack; point at the sans (`var(--font-pretendard), Pretendard, "Noto Sans KR", system-ui, sans-serif`).
- `--font-mono` → **unchanged** (JetBrains Mono).

### 4. `globals.css` — radius / spacing / breakpoint (§4.1–4.3)
- **Radius (§4.1):** `--radius` 14→**10**, `--radius-md` 10→**8**, `--radius-lg` 14→**10**, `--radius-xl`
  18→**14**, `--radius-xxl` 28→**20**; `xs 4` / `sm 6` unchanged. Also set the shadcn `:root { --radius }`
  14→**10px**.
- **Spacing (§4.2):** only `--spacing-hero` **128→120** changes; `section-sm 48` / `section 72` /
  `section-lg 104` and both `--container-*` stay.
- **Breakpoint (§4.3):** **remove** `--breakpoint-xs: 30rem`; **add** `--breakpoint-app: 56.25rem;` (900px).
  No `xs:` variant is introduced (zero consumers). The `min-[900px]:` → `app:` migration is **not** S1's —
  S1 only defines the token.

### 5. `globals.css` — header comment
Rewrite the file header (currently "PLACEHOLDER PALETTE … finalized at the P6 design gate") to describe
the applied vocky brand, grounded in the signed-off record (`result.md §0`): deep-emerald green on a
green-cool neutral ramp, **light-only** (keep the "No `.dark` block on purpose" note — still true),
compact/data-dense, Pretendard + JetBrains Mono, and the value-swap-names-kept re-theme property, applied
by P9 from round 01 signoff. Invent nothing — the brand words come from the record.

### 6. `fonts.ts` + `layout.tsx` — Pretendard loader
- **Recommended mechanism: `next/font/local` + a vendored Pretendard variable woff2** (`PretendardVariable.woff2`,
  weight range `45 920` or `400 800`), co-located for `fonts.ts` — self-contained, no runtime dependency,
  matches the app's existing self-host philosophy (it already self-hosts via `next/font`), one file covers
  all weights. Expose `variable: "--font-pretendard"`; keep JetBrains Mono on `next/font/google` unchanged.
  Rewrite the file's doc comment (it currently calls the set a "placeholder … at the P6 design gate").
- `layout.tsx`: rename the import/usage `notoSansKr` → `pretendard`; update the `<html className>` and the
  "Noto Sans KR font" comment. (These three files are the entire rename surface — confirmed by grep.)
- **Alternative** (if the operator prefers a dependency over a committed binary): `@fontsource/pretendard`
  / the `pretendard` npm package via `pnpm add`, wired the same way.
- **Fetch-failure protocol (do not silently degrade):** if the woff2 cannot be obtained (no network) **or**
  the package cannot be added in the execution environment, return **`needs_operator`** with the blocker —
  do **not** ship Noto Sans KR relabeled as Pretendard (that violates RESPECT THE DESIGN; the Korean-capable
  *fallback* stays Noto Sans KR, but the *primary* face must actually be Pretendard).

## Locked floors S1 must preserve

- `h1–h6 { word-break: keep-all }` (base layer) — untouched.
- `--font-sans` stays **Korean-capable** (Pretendard primary, Noto Sans KR fallback).
- `:focus-visible` outline uses `var(--color-green-deep)` — re-themes automatically; leave the rule as-is.
- The reduced-motion and `[data-reveal]` base layers — untouched.
- (FieldError's `aria-live` region and the component floors are **S2**, not S1.)

## Explicitly NOT in S1

Token **renames** beyond the font var (the vestigial `victory-lime`/`archive-*`/`security-*` → semantic
pass) — **out of scope** (`build-prompt §2.4`, a separate optional mechanical slice). Any `web/` file
other than the three above. Any component/surface restyle. Any doc version (constraint: docs at `P9.REVIEW`).

## Verification

- `cd web && pnpm typecheck && pnpm lint` clean.
- `cd web && pnpm build` succeeds — proves the `next/font/local` Pretendard loader resolves the asset and
  compiles (the strongest available signal that the primary face is actually present, not just fallen back).
- `prettier --write` the three touched files (keep them out of the 20 pre-existing `format:check` failures;
  do not touch the unrelated ones).
- Greps: `--breakpoint-xs` gone and `--breakpoint-app` present in `globals.css`; `--font-sans` chain leads
  with Pretendard and still contains a Korean-capable fallback; no `--color-*` value still equals its old
  placeholder except the two intentional equalities; `--font-mono` unchanged.
- Optional smoke (if a dev server is cheap): load a page, confirm Pretendard renders Latin **and** Korean.

## Doc impact (append one line to `phase.md` → Doc impact; do NOT version docs here)

Foundations applied: `globals.css` now holds the vocky deep-emerald palette (names kept), the compact
type/radius/spacing scale, `--breakpoint-app`, and a Pretendard loader — the durable truth `frontend.md`
(v0003) still describes as a *live placeholder*. For `P9.REVIEW` to consolidate.
