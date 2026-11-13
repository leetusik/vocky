# Round 01 — result: brand, app UI & landing

**Round:** 01 · **Phase:** P8 · **Design session:** Claude Design + operator (sugang)
**Repo:** `github.com/leetusik/vocky` · **Companion:** `build-prompt.md` (the implementation contract P9 sizes from)
**Visual sign-off artifacts:** `Vocky Round 01 — Design System.html`, `Vocky Round 01 — Landing.html`

This file records *what was designed and why*, decision by decision, and answers every §6 question.
`build-prompt.md` is the buildable contract — exact values, APIs, per-file changes. Read that to implement.

---

## 0. The brand, in one paragraph

vocky is **a quiet instrument for hearing your users** — a precise, calm, developer-facing system for the
voice-of-customer layer. It looks like a well-built dev tool: light surfaces, one confident **deep-emerald**
green that always means *signal*, a compact and honest information density, mono for data, and no gradients,
no stock cheer, no decorative emoji. Green is the only voice raised; everything else gets out of the way.

**Direction chosen (operator):** palette swatch **B — vocky's own green** (a cleaner deep-emerald on light
surfaces), *not* hi2vi's dark-forest + neon-mint literal, and *not* the neutral-with-signal minimum. We
inherit hi2vi's **structure** (the token names, the "one signature green" idea, Pretendard, JetBrains Mono)
and give vocky its **own values**.

**Operator rulings that shaped everything:**
- Palette: **B** — vocky's own deep-emerald on light.
- Dark mode: **light-only** (unchanged).
- Density: **compact & data-dense** — more rows on screen; this is a review tool.
- Motion: **minimal**, reduced-motion safe.
- Trend chart: **redesign** (area chart), kept dependency-free.
- Components: **recommended set** — add Select, destructive Button, Chip/Tag; fold LogoutButton; split Badge.
- Pricing: **free now, paid later** → a Free card plus a muted "Pro & Teams — coming later" card.
- Signed-in visitor at `/`: **bounce to `/dashboard`** (unchanged).
- Brand spirit, value prop, wordmark, type: **"decide for me"** — resolved below.

---

## 1. Foundations

### 1.1 Color — value-swap, names kept

We **swap values and keep the token names** (the property the whole gate rests on: utilities compile to
`var(--color-*)`, so one value change re-themes every surface). Renaming is deferred — see the §6.2 answer.
Full old→new table and the `@theme` block are in `build-prompt.md §2`.

The palette is **one green family** on a **faintly green-cool neutral ramp**. Highlights:

- **Brand green** `--color-green: #0C7A52` — primary CTA + signature. Deliberately deep enough that **white
  text clears WCAG AA (5.36:1)** on it, so the `on-primary` flip stays **white** (see §6.2).
- `--color-green-deep #095E40` (hover / pressed / focus ring), `--color-green-dark #064A33` (links & accent
  text on light, 10:1), `--color-green-soft #E4F5ED` (active nav, soft chips).
- **Neutrals** carry a whisper of green so they read as *related* to the accent, not generic slate:
  `--color-ink #0E1A16`, text ramp `--color-charcoal #1C2A24` → `--color-slate #35453E` →
  `--color-steel #556259` (AA on white, 6.4:1) → `--color-muted #8A968F` (decorative only).
- **Signal** stays warm and legible: `--color-danger #C93B2B` (white text 5.05:1, used for dislike *and*
  destructive), `--color-caution #C6820E`.
- **Rating semantics** (the product's core signal) are now explicit: **liked = green, disliked = red,
  unrated = neutral**. This is what drives the split of the overloaded `archive` badge (§6.5).

**Collision groups resolved.** The 8 placeholder collision groups (distinct names holding identical values)
are given distinct values wherever they render together — e.g. `surface-soft #EEF3F0` ≠ `surface-band #EDF2EF`
≠ `surface-green #EAF6F0`; `ink` ≠ `charcoal`; the text ramp `slate/steel/muted` are all distinct.
Intentionally-equal remaining pairs are listed in `build-prompt.md §2.3`.

### 1.2 Type — Pretendard + JetBrains Mono

- **`--font-sans` → Pretendard** (Korean-capable, geometric). This is the honest inheritance of "hi2vi vibe"
  and a real upgrade over Noto Sans KR's slightly generic UI feel; it reads cleanly in dense tables and at
  small sizes. **Cost, named:** Pretendard is *not* on Google Fonts, so this changes the loader from
  `next/font/google` to `next/font/local` with a vendored Pretendard woff2 (or a Fontsource package). Fallback
  chain keeps Noto Sans KR so nothing breaks if vendoring slips. See `build-prompt.md §3`.
- **`--font-mono` → JetBrains Mono** — unchanged (already shared with hi2vi). Used heavily: numerals, IDs,
  `vk_` keys, timestamps, code samples, table metadata.
- **`--font-en` → retired.** The bare system stack that made every button render in the visitor's font is
  dropped; `--font-en` now points at Pretendard (§6.5). No new English face is vendored.
- **Scale** retuned for a compact, technical feel (full table in `build-prompt.md §3.2`): hero-display 60,
  display-lg 46, heading-1..4 = 38/30/24/18, body-md **15** (down from 16 for density), body-sm 13, caption 12,
  micro 11 (uppercase tracked), button-md 14, code-md 13. Heading weight 700/800; Korean line-height stays ≥1.55.
- **`h1–h6 { word-break: keep-all }` preserved** (locked floor).

### 1.3 Spacing, radius, containers, breakpoints, motion

- **Density = compact.** The app uses a tighter rhythm: block gap 24px (was 32), card padding 20px (was 24),
  **table rows py-2 / cells px-4**, stat-tile padding 12–16px. The landing keeps generous section rhythm
  (`--spacing-section` 72/104, `--spacing-hero` 120).
- **Radius scale tightened for precision:** base/`--radius` **10px** (was 14); xs 4 / sm 6 / md 8 / lg 10 /
  xl 14 / xxl 20 / full. **Buttons move from `rounded-full` pills to `rounded-md` (8px)** — a deliberate
  departure toward "instrument, not marketing." Rating/status **badges stay `rounded-full`**; **tags/chips are
  `rounded-sm` (6px)**, mono.
- **Breakpoints:** **drop the zero-consumer `--breakpoint-xs`** and **tokenize the real one** — the app uses
  `min-[900px]:` 11 times, so define `--breakpoint-app: 56.25rem` (900px) and migrate those utilities to
  `app:` (§6.5).
- **Motion: minimal.** 150ms ease on hover/focus. The landing may use the existing reduced-motion-safe
  `Reveal` for one-shot section reveals; no parallax, no autoplay. Skeletons are static (no shimmer) under
  reduced motion.

---

## 2. Components

Every primitive is token-driven and restyled to the new palette/type/radius. New and changed:

- **Button** — variants `primary` (green fill, white text, `rounded-md`, soft green shadow), `secondary`
  (hairline-strong border, canvas), `ghost` (transparent → surface on hover; **this is where LogoutButton
  folds in**), **`destructive`** (danger fill, white — *new*), **`destructiveOutline`** (danger-tinted border,
  used for per-row revoke — *new*), `link`. Sizes sm/default/lg. `--font-en`→Pretendard so buttons match.
- **Badge** — **split from the overloaded `archive`** into rating + status semantics: `liked`, `disliked`,
  `unrated`, `active`, `revoked`, `accent`. Revoked (neutral) and Disliked (danger) are now visually distinct.
- **Chip/Tag** *(new primitive)* — mono, `rounded-sm`, hairline; one primitive for feedback tags **and**
  active-filter pills (removable variant with a trailing ✕).
- **Select** *(new primitive)* — styled native `<select>` with a custom chevron, matching `Input`; **replaces
  the raw `inputVariants()`-via-template-literal `<select>`** in the feedback filter bar.
- **Field** (Label/Input/Textarea/Checkbox/FieldError) — restyled, inputs `rounded-md`, ~38px min-height
  (compact). **`FieldError`'s empty `min-h` `aria-live` region is preserved** (locked a11y floor).
- **DataTable** — compact density (uppercase micro headers, py-2 rows, hairline-soft dividers, hover surface),
  `rounded-lg` wrapper, `overflow-x-auto`. Distinct-empty-state slot preserved.
- **Card** — `base`, `feature`, `featureMuted`, `dark` restyled; **adopt** `pricing` / `pricingFeatured` for
  the landing; the placeholder-only `security`/`archive` variants are dropped/repurposed (§6.4).
- **Section / Grid / EndpointCard / Reveal** — **adopted** for the landing (Section tonal bands incl. a dark
  band; EndpointCard = the forest code panel; Reveal = the one motion primitive). `surfaceSoft`≠`band` fixed.
- **StatTiles** — compact; **mono tabular numerals**; each tile gets a small rating dot (liked green / disliked
  red / unrated neutral) for at-a-glance scanning.
- **TrendChart** — **redesigned to a dependency-free area chart**: thin green line, soft green→transparent
  gradient fill, hairline baseline, per-point `<title>` hover, and the **same `role="img"` + sr-only summary**
  a11y contract. Handles both real empty-series shapes (no projects → empty note; all-zero → flat baseline).
- **App shell** — sticky compact topbar (mark + wordmark · workspace/user · ghost Sign-out) over a compact
  rail (active item: green-soft bg, green-dark text, inset green accent bar) + main. **Project detail gains a
  breadcrumb** (`Dashboard / {project}`) — see §6.5.

Full APIs, variants, exact class strings, and files are in `build-prompt.md §4`.

---

## 3. App surfaces (all six shipped surfaces — designed, real strings)

All copy below is the **shipped strings** from `web/src/content/*` — nothing invented (app copy is locked).

- **Login / signup** — centered card on `surface`, mark+wordmark above, `feature` card. **The identical-error
  floor is honored**: one message for wrong password and unknown email.
- **App shell** — as above; compact.
- **Dashboard** — page title, `Capture volume` stat tiles (4, with rating dots), the redesigned `Daily trend`
  area chart, `Projects` table (name links into detail), `New project` inline form. Compact spacing throughout.
- **Project detail** — breadcrumb + project name, usage tiles + trend, **`API keys`** table (Name / Key /
  Created / Last used / Status / Revoke), the **show-once key panel** (green-tinted, carrying the full
  irrecoverable-key warning — locked floor), mint form. Revoke uses the new `destructiveOutline` button;
  revoked keys stay listed with a `revoked` badge.
- **Feedback list** — filter card (real `Search` / `Project` Select / `Rating` Select + Search/Clear), the
  `Recent feedback` compact table (When / Project / Feedback / Rating / Source), `Times are shown in UTC`
  note, forward-only `Next page`. **Distinct empty states preserved** (no-projects vs no-matches).
- **Feedback detail** — back link, message card (whitespace-preserving, Korean-safe), comment, `Details` dl,
  `Tags` as the new Chip, `Operator comments` (read-only), `Attachments` (**download-only** — locked floor),
  collapsible `Raw data`. Read-only by design.

Mockups of dashboard, feedback list/detail, project detail and login are in the Design System artifact §06.

---

## 4. Landing (`/` — net-new; reclaims the redirect)

Structure, with **authored copy** (landing copy is in-play this pass; grounded in real product facts — no lorem):

- **Nav** — mark+wordmark · Features / How it works / Pricing / Docs · Sign in (secondary) · **Start free**
  (primary → `/signup`).
- **Hero** — eyebrow *"Voice of customer, for builders"*; headline **"Capture the feedback your product is
  already getting."**; subhead grounding it in the real mechanism (server-to-server REST, likes/dislikes/
  comments, structured signal, cross-project search); CTAs **Start free** / **Read the docs**; a real
  **`POST /api/feedback`** request panel beside a "captured" record card (Korean sample, Disliked badge, tags).
- **Trust strip** — real facts, not fake logos: `POST /api/feedback` · structured signal · search 결제 or
  checkout · MIT-licensed.
- **How it works** — 3 steps: mint a `vk_` key → your backend POSTs feedback → search & review across projects.
- **One place to look** — a browser-framed mock of the feedback list ("Every reaction, across every project").
- **Features** — 6, all real: server-to-server capture · structured, not log noise · search in any language ·
  per-project keys (shown once) · like/dislike/listen (explicit only) · free & self-hostable.
- **Pricing** — **Free** card (`Available now`, `$0 / forever, for now`, real inclusions, Start-free CTA) +
  a muted **Pro & Teams — coming later** card (team seats, retention, saved views/exports, priority support;
  disabled "Not yet — vocky is free today"). Resolves the §6.1 contradiction per the operator.
- **Closing CTA** (dark band) + **footer** (dark forest, Product / Project / Account columns, MIT, © 2026).

---

## 5. New states (net-new — designed, not framework defaults)

- **`loading.tsx`** — skeleton of the real layout (title + 4 stat blocks + chart + rows), static under reduced
  motion. Per-surface skeletons (dashboard / feedback / project).
- **`error.tsx`** — calm centered card, danger-tinted mark, "Something went wrong" + "Try again" reset button.
- **`not-found.tsx`** — mono `404`, "This page doesn't exist", generic subcopy that **honors 404-never-403**
  ("…or isn't yours to see" — never confirms existence), "Back to dashboard".
- **`global-error.tsx`** — minimal full-page variant of `error` (own `<html>`), brand mark + retry.

---

## 6. Answers to §6 — every question

### 6.1 Landing
- **Value prop?** → *"Capture the feedback your product is already getting."* VoC-for-builders angle:
  outcome-led headline, developer mechanism in the subhead. (operator: decide-for-me)
- **Pricing section vs "free"?** → **Yes, a pricing section**, resolved as **Free now + paid later**: a
  prominent **Free** card and a muted **Pro & Teams — coming later** card. (operator: *"free, the paid ones
  will come later"*)
- **Signed-in visitor at `/`?** → **Bounce to `/dashboard`** (unchanged). `/` serves the public landing to
  signed-out visitors only. (operator)

### 6.2 Brand & foundations
- **Palette / how far to carry hi2vi?** → **Direction B**: inherit hi2vi's *structure* (names, one-signature-
  green idea, faces) but give vocky **its own deep-emerald-on-light values**. Not the literal dark-forest+neon.
- **Type direction?** → **Pretendard (sans) + JetBrains Mono (data)**; single sans family, no separate display
  face. (operator: decide-for-me)
- **`on-primary` flip?** → **White** (`--color-on-primary: #FFFFFF`). The chosen green `#0C7A52` is a saturated
  mid-dark tone that passes AA with white text, so — unlike hi2vi's bright mint which needs dark text — vocky
  keeps white. (dependency resolved, not an independent choice)
- **Dark mode?** → **Light-only.** No `.dark` block, explicit surface tokens retained. (operator)
- **Token renames vs value swaps?** → **Value-swap only** now (keep names) to preserve the one-swap-re-themes
  property and avoid call-site churn. Vestigial names (`victory-lime`, `archive-olive`, `security-*`) are
  repurposed as green/neutral tints and flagged for an **optional** later rename pass with its cost named in
  `build-prompt.md §2.4`. Not done this round.

### 6.3 Hand-rolled primitives (operator: recommended set)
- **Add `Select`?** → **Yes** — new primitive; replaces the raw native `<select>` in the feedback filters.
- **Destructive `Button` variant?** → **Yes** — `destructive` (fill) + `destructiveOutline` (per-row revoke).
- **`Chip`/`Tag`?** → **Yes** — one primitive for tags + removable filter pills.
- **Fold `LogoutButton` into `Button`?** → **Yes** — `Button variant="ghost" size="sm"`.

### 6.4 Inherited-but-unused — adopt or drop
- **Adopt** (the landing needs them): `Section` (+ tonal bands incl. dark), `Reveal`, `EndpointCard`,
  `Checkbox`, `Textarea`, `Card` `dark`/`pricing`/`pricingFeatured`, `Grid cols={2|3}`, the
  `--spacing-section*`/`--spacing-hero` group, `--container` widths, and the large type steps
  (`hero-display`, `display-lg`, `heading-1/2`, `body-lg`).
- **Drop / repurpose:** `--breakpoint-xs` (dropped, replaced by `--breakpoint-app`); `Card` `security`/
  `archive` variants and `Badge` `security`/`dark` (placeholder-only — dropped or repurposed);
  `Button secondaryOnDark` kept as `dark` for the landing's dark bands; `code-md` kept (used by EndpointCard).
- Full adopt/drop ledger in `build-prompt.md §4`.

### 6.5 Semantics & specifics
- **`Badge variant="archive"` split?** → **Yes.** Now `revoked` (neutral) and `disliked` (danger) are separate;
  plus `liked`/`unrated`/`active`/`accent`.
- **`TrendChart` — keep SVG or library?** → **Redesign, keep dependency-free.** New area chart (line + gradient
  fill + baseline), no chart library added. (operator chose "redesign")
- **`--font-en` no vendored face?** → **Drop the system stack; point `--font-en` at Pretendard.** Buttons stop
  rendering in the visitor's font; no separate English face vendored.
- **`--breakpoint-xs` no consumer?** → **Tokenize the real breakpoint:** drop `xs`, add
  `--breakpoint-app: 56.25rem` (900px), migrate the 11 `min-[900px]:` utilities to `app:`.
- **`/projects/[id]` marks no rail item current?** → **Keep no rail-current** (projects aren't a rail item) but
  **add a breadcrumb** (`Dashboard / {project name}`) so location stays legible. Small UX add — logged in §7.
- **8 palette collision groups?** → **Resolved** by assigning distinct values where they co-render; the few
  intentionally-equal pairs are listed in `build-prompt.md §2.3`.

---

## 7. Departures from the handoff — logged

Every change from what exists today, and why:

1. **Buttons: `rounded-full` → `rounded-md` (8px).** Brand is "instrument, not marketing." Pills read too soft.
2. **Radius base 14 → 10px**, scale tightened. Precision/density.
3. **Type sizes reduced** (body 16→15, hero 68→60–62, headings tightened). Operator's compact/data-dense call.
4. **`--font-sans`: Noto Sans KR → Pretendard.** Named cost: loader changes `next/font/google` →
   `next/font/local` (vendored woff2) or Fontsource. Fallback chain retains Noto Sans KR.
5. **Pricing section added** (Free + coming-later). Resolves a scope-vs-"free" contradiction the handoff
   explicitly refused to resolve; done per the operator's ruling.
6. **Breadcrumb on project detail** — small navigational UX add (not in shipped code).
7. **StatTiles rating dots** — minor at-a-glance affordance (new).
8. **New component vocabulary** — Select, destructive/destructiveOutline Button, Chip/Tag, split Badge — a
   deliberate bootstrapping expansion (operator approved the recommended set).
9. **`--breakpoint-xs` dropped; `--breakpoint-app` (900px) added** and 11 utilities migrated. Real cleanup.
10. **Vestigial hi2vi-legacy token names repurposed** (values), not renamed. Rename deferred (cost named).

**No backend/data contract change is required by this design.** Everything maps to existing serializers and
routes. Two behaviors touch the web tier only (not vocky's API): `/` gains a public landing behind the
existing signed-in→dashboard bounce; the project breadcrumb uses data already fetched. Named per the handoff's
"name the cost" rule: the only non-trivial build cost is **Pretendard vendoring** (§3).

---

## 8. Locked floors — honored

- Identical login error for wrong password vs unknown email ✓
- 404-never-403 (the `not-found` copy never confirms existence) ✓
- Show-once `vk_` key panel keeps the full irrecoverable warning; revoked keys stay listed ✓
- Attachments download, never inline ✓
- Times shown in UTC and labeled ✓
- `h1–h6 { word-break: keep-all }` preserved ✓
- `--font-sans` stays Korean-capable (Pretendard) ✓
- `FieldError` empty `min-h` `aria-live` region preserved ✓
- Distinct empty states ("no projects yet" vs "no feedback matches these filters") preserved ✓

---

## 9. Left open / apply-time to-dos (for P9, not blockers)

- **Pretendard vendoring** — pick the mechanism (`next/font/local` + woff2, or Fontsource `@fontsource/pretendard`)
  at implementation; the design assumes Pretendard with a Noto Sans KR fallback either way.
- **Optional token rename pass** — retiring the hi2vi-legacy names (`victory-lime`, `archive-*`, `security-*`)
  for vocky-semantic names is possible later; costed in `build-prompt.md §2.4`. Not required to ship this design.
- **Docs favicon/OG mark** — the waveform mark can generate the app icon / OG image at deploy (P6 concern).
- **"Notify me" on the coming-later pricing card** — currently a disabled control; if a waitlist is ever
  wanted it needs a backing endpoint. Out of scope now; flagged.

Nothing here blocks P9; each is a choice with its cost named, per the handoff.
