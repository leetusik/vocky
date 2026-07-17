# Phase P9: Apply the Design: App UI, Landing & Feature Changes

_Intent: see [intent.md](intent.md)._

## Objective

Implement P8's signed-off design across the app and the landing page, from the gate's build-prompt.md — foundation first, net-new capabilities isolated, backend reopened where the design requires it, closing with a design-fidelity fix and a consistency/DoD sweep.

## Context

P9 is the **apply half** of P8's now-closed design gate. P8 landed a complete, **verbatim, read-only**
implementation contract at
`docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md` (companions:
`output/result.md` — decisions + §7 departures + §9 apply-time to-dos; `SIGNOFF.md` — the token delta).
P9's whole job is to build that faithfully: the deep-emerald value swap, the compact type/radius/spacing
retune, the new component vocabulary (Select, Chip, destructive Button, split Badge, folded LogoutButton,
area TrendChart), the four net-new states, and the public landing that reclaims `/`.

**`build-prompt.md` is the on-disk source of truth.** P9's implement executors are dispatched with **no
DesignSync tool** — what's on disk (`build-prompt.md` primary, `result.md` + `SIGNOFF.md` companions) is
all they get. The 30-card set + `tokens.css` stay in the design project (`1eaa0803-…`) by design and were
**not** copied down; `build-prompt.md` carries every exact value, so it is complete. **Everything under
`output/` and `SIGNOFF.md` is read-only** — never edit the returned record (apply-time nits are catalogued,
not corrected). All measured codebase facts live in [P8's phase.md](../P8/phase.md) → *Findings & Notes*;
`P9.DECOMP` referenced them rather than re-deriving.

## Decomposition

Cut by `P9.DECOMP` (2026-07-18) from `build-prompt.md §1` (foundation-first build order) and the phase
intent's expected shape (*foundation first → net-new capabilities isolated → design-fidelity fix →
consistency/DoD sweep last*). **Seven middle slices**, bare folders only — each slice's `plan.md` is
written by the orchestrator at that slice's own turn.

| Slice | Name | Kind | Risk | Order | Depends on | Scope (build-prompt §) |
|---|---|---|---|---|---|---|
| `P9.S1` | Foundations: `@theme` swap + Pretendard loader | implementation | medium | 1 | — | §2 color, §3 type + `fonts.ts`, §4.1 radius, §4.2 spacing/containers, §4.3 breakpoint token, header comment; verify shadcn aliases (§2.5 last bullet) |
| `P9.S2` | Primitives: button/card/badge/field + new Select/Chip + barrel | implementation | medium | 2 | S1 | §4.4–4.12 rewrites incl. the §2.5 button/card literal fixes; new `select.tsx`/`chip.tsx`; `ui/index.ts` barrel |
| `P9.S3` | App components + brand mark | implementation | medium | 3 | S2 | §4.5 logout→Button, §4.13 StatTiles, §4.14 area TrendChart, §5 app-shell/rail-nav, §7.1 new `brand/{mark,wordmark}` |
| `P9.S4` | App surfaces (all six) | implementation | medium | 4 | S3 | §5 auth-card, dashboard, project detail (breadcrumb/badges/revoke/key panel), feedback list (Select/Chip), feedback-fields, feedback detail (Chip), island forms |
| `P9.S5` | Net-new states: loading/error/not-found/global-error | implementation | medium | 5 | S2 | §6 `loading`/`error`/`not-found`/`global-error` |
| `P9.S6` | Landing: reclaim `/`, `landing.ts`, `components/landing/*` | implementation | **high** | 6 | S3 | §7 `page.tsx`, new `content/landing.ts`, new `components/landing/*` |
| `P9.S7` | Consistency & DoD sweep + design-fidelity fixes | implementation | **high** | 7 | S4, S5, S6 | §10 DoD checklist; kill any residual `min-[900px]:` / `--breakpoint-xs` / `inputVariants()` `<select>`; retire dead `content/nav.ts`/`section-ids.ts` if unused; fix drift from build-prompt exact specs |

**Ordering — foundation-first, faithful to `build-prompt.md §1`.** `1→2→3` are strictly ordered: the
`@theme` value swap (S1) re-themes every surface, so it must land before the primitives that consume the
tokens (S2), which must land before the app components that compose them (S3). S4 (app surfaces) composes
S3's components, so it follows S3. **S5 and S6 are independent of each other and of most of S4** —
`build-prompt.md §1` states "steps 5–6 are independent of each other and of most of 4". S5 (net-new
states) needs only the primitives (S2) for its skeletons/cards/buttons (and the brand mark from S3 for
`error`/`global-error` — see Findings; S5 is ordered after S3, so the mark exists at its turn). S6
(landing) composes the brand mark + Section/EndpointCard/Reveal + primitives, so it depends on S3. S7 is
the closing sweep and depends on all three leaf slices (S4, S5, S6).

**Risk — the phase's cost lever.** Under flex mode `low`=sonnet@xhigh and `mid`/`high`=opus@xhigh, so
`low` is the only real cost saver and is reserved for *fully mechanical, no-judgment* plans. **No P9 slice
qualifies:** RESPECT-THE-DESIGN requires "closest-to-designed-intent, never a plainer fallback" wherever a
value isn't spelled out — a judgment call in every slice — so every slice is **≥ medium** (opus). **S6
(landing)** and **S7 (sweep/fidelity)** are rated **high**: S6 is the largest net-new surface with the most
composition and grounded copy; S7 must catch cross-slice drift and is the last line of defense before
review. This is the operator's brand-defining phase and the intent is emphatic about fidelity — spending
opus across the board is the intended trade.

**File-ownership boundaries — no file edited by two slices.** `globals.css` + `fonts.ts` → **S1 only**; S1
does **not** touch `button.tsx`/`card.tsx` (their §2.5 literal fixes are subsumed by S2's wholesale rewrite
— fixing them in S1 would be thrown away). S1 owns only the `globals.css` shadcn-alias *verify* (§2.5 last
bullet). New components are owned once: `select`/`chip` → S2; `brand/{mark,wordmark}` → S3;
`content/landing.ts` + `components/landing/*` → S6. The `min-[900px]:` → `app:` migration is **distributed,
not one slice**: S1 defines `--breakpoint-app` + removes `--breakpoint-xs`; each slice migrates the literals
in *its own* files (S3: app-shell/rail-nav; S4: feedback pages); **S7 verifies zero `min-[900px]:` remain**
(the DoD backstop).

**Design-fidelity fix is folded into S7, not pre-cut.** Per v13 (*"part of the normal shape, not a
failure"*) and P8's carried note, S7 folds the fidelity check into the DoD sweep. A separate `--kind fix`
slice at a fractional order gets cut **reactively** only if a slice reveals substantial drift — not pre-cut
here.

**Deviation from the proposed manifest: none.** The `P9.DECOMP` plan's 7-slice cut was executed verbatim
(names, kinds, risks, orders, dependency edges). One dependency nuance was surfaced as a Finding rather
than changed: S5's `error`/`global-error` consume the brand mark from S3, but S5's recorded dep stays
**S2** (its foundational primitive need) because `depends_on` is advisory/existence-only and S5's order (5)
already sequences it after S3 (3), so the mark exists at S5's turn — changing the edge would not alter
execution and would blur the "S5 is primitive-level, independent of S4/S6" framing. See Findings.

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

### Seeded by `P9.DECOMP` — load-bearing traps every middle slice must carry

- **The re-theme property is the phase's foundation.** Tailwind utilities compile to `var(--color-*)`
  (verified in the compiled bundle, per P8), so `build-prompt.md §2` is a **value swap**: S1's `globals.css`
  edit re-themes every surface at once, names unchanged, call sites untouched. The literals a swap does
  **not** reach are §2.5 (owned by S2, below) — no re-theme reaches them, they are edited by hand.
- **§2.5 hardcoded literals belong to S2, not S1.** `button.tsx`'s two `primary` shadows
  (`rgba(79,70,229,…)` → green `rgba(12,122,82,…)`) and `card.tsx`'s `feature`/`pricing`/`pricingFeatured`
  shadows + borders (`rgba(15,23,42,…)` → ink `rgba(14,26,22,…)`, `#e2e8f0` → `border-hairline`) are fixed
  as part of S2's wholesale rewrite of those files. S1 owns only the `globals.css` shadcn-alias **verify**
  (`--ring`/`--primary`/`--primary-foreground`/`--destructive` already map by name).
- **The `min-[900px]:` → `app:` migration is distributed.** S1 declares `--breakpoint-app: 56.25rem`
  (900px) and removes `--breakpoint-xs`; each slice migrates the 11 literals in **its own** files
  (S3: `app-shell.tsx`/`rail-nav.tsx`; S4: `feedback/page.tsx`, `feedback/[feedbackId]/page.tsx`). **S7
  verifies zero `min-[900px]:` and zero `--breakpoint-xs` remain** — the DoD backstop.
- **Backend / data: no change required** (`build-prompt.md §9` / SIGNOFF). No `src/vocky/**`, no P2/P3
  contract reopening. The pricing "coming later" control is **disabled copy — no waitlist endpoint** this
  round (net-new backend if ever wanted, flagged not built). Everything maps to existing serializers; the
  breadcrumb reuses already-loaded `project.name`; the signed-in bounce reuses `getSession()`.
- **The one named build cost is Pretendard vendoring** — an **S1 apply-time decision** (`result.md §9`),
  not a DECOMP one: `next/font/local` + vendored woff2 (`public/fonts/*`) **or** `@fontsource/pretendard`.
  Either way the fallback chain must retain a Korean-capable face (Noto Sans KR). `--font-en` stops being a
  bare system stack and points at Pretendard, so buttons (its one call site, `button.tsx:18`) match.
- **S5's `error`/`global-error` render the brand mark (§7.1, owned by S3).** S5's recorded dep is **S2**
  (its primitive foundation: Card/Button/Grid skeletons); but its `error.tsx` (danger-tinted mark) and
  `global-error.tsx` (brand mark) compose the `components/brand/mark` created in S3. S5's order (5) runs
  after S3 (3), so the mark exists at S5's turn — the S5 planner should compose it, not re-create it. This
  is why the dep edge was left at S2 rather than moved to S3 (see Decomposition deviation note).
- **File-ownership boundaries (no file edited twice):** `globals.css`/`fonts.ts`→S1; the `ui/` primitive
  rewrites + new `select.tsx`/`chip.tsx` + `index.ts` barrel→S2; `app-shell`/`rail-nav`/`logout-button`,
  `usage/stat-tiles`, `usage/trend-chart`, new `brand/{mark,wordmark}`→S3; the six app surfaces + island
  forms→S4; the four state files→S5; `page.tsx` + `content/landing.ts` + `components/landing/*`→S6; the DoD
  sweep + dead-file retirement→S7.
- **Known record staleness (apply-time nit — do NOT edit the read-only record):** both returned files
  (`build-prompt.md` "Visual source of truth" line; `result.md` header) still name the two monolith HTMLs
  (`Vocky Round 01 — Design System.html` / `— Landing.html`) as the visual source of truth. Those were
  superseded by the card set and deleted from the project. **`build-prompt.md` is the on-disk truth P9
  builds from**; the card set is the visual truth (in the project, not on disk). The record stays untouched.
- **Design-fidelity fixes are reactive, not pre-cut.** S7 folds the fidelity check into the DoD sweep; cut
  a separate `--kind fix` slice at a fractional order (7.5, …) only if a slice reveals substantial drift
  (v13: *"part of the normal shape, not a failure"*).
- **`--depends-on` is `action="append"`** — repeat the flag per dep (never comma-separate; a comma-joined
  value stores as one literal dep and fails `validate`). Used correctly here: S7 → `--depends-on P9.S4
  --depends-on P9.S5 --depends-on P9.S6`.

### Appended by `P9.S1` — foundations landed

- **The `@theme` swap is DONE and green.** `globals.css` now holds the vocky deep-emerald palette (41 hex
  values swapped, names kept), the compact type scale (14 steps, Pretendard weights 400–800), the compact
  radius (base 10) / `--spacing-hero: 120px`, and `--breakpoint-app: 56.25rem` (with `--breakpoint-xs`
  gone). Every downstream slice re-themes off this — no further token edits needed in `globals.css` for the
  re-theme (S2's §2.5 literal fixes are in `button.tsx`/`card.tsx`, not here).
- **Pretendard font var is `--font-pretendard`** (renamed from `--font-noto-sans-kr`). Loaded via
  **`next/font/local`** from a vendored variable woff2 at **`web/src/lib/fonts/PretendardVariable.woff2`**
  (~2 MB, official `orioncactus/pretendard` release, `weight: "400 800"`). Export in `fonts.ts` is now
  `pretendard` (was `notoSansKr`); `layout.tsx` wires `pretendard.variable`. `--font-sans` and `--font-en`
  both lead with Pretendard; **Noto Sans KR stays as the Korean-capable fallback** (locked floor). The
  rename surface was exactly `globals.css` + `fonts.ts` + `layout.tsx` — `pnpm build` is green, so no stale
  `notoSansKr` / `--font-noto-sans-kr` reference exists.
- **`--font-en` now resolves to Pretendard** (no longer a bare system stack), so `button.tsx:18`'s
  `font-en` will pick up the brand face when S2 rewrites the button — no extra wiring for S2 to add.
- **`--breakpoint-app` is defined but not yet consumed** — the 11 `min-[900px]:` literals are untouched
  (S3: app-shell/rail-nav; S4: feedback pages; S7 backstops zero `min-[900px]:` + zero `--breakpoint-xs`).
- **shadcn aliases verified (§2.5 last bullet), no edit:** `--primary`/`--primary-foreground`/`--ring`/
  `--destructive` all map by name → re-theme automatically.
- **Verification for S1:** `pnpm typecheck`, `pnpm lint`, `pnpm build` all clean; the build success is the
  strongest signal the Pretendard loader resolved the real asset, not a fallback. Repo has 20 pre-existing
  unrelated `format:check` failures — S1 ran `prettier --write` on only its three touched files.

### Appended by `P9.S2` — primitives landed

- **The CVA primitives now carry the vocky system and are green.** All of `ui/` was rewritten to
  `build-prompt.md §4.4–4.12` (+ the §2.5 literal fixes): Button (`rounded-md`/`font-semibold`/`gap-2` base,
  green shadows, `secondaryOnDark`→`dark`, +`ghost`/`destructive`/`destructiveOutline`, retuned sizes), Card
  (dropped `security`/`archive`, ink/green shadow literals), Badge (split into `liked|disliked|unrated|
  active|revoked|accent`, `defaultVariants {unrated}`), Field (compact `px-3`, `min-h-[38px]`/`min-h-24`,
  `size-[18px]` checkbox), DataTable (compact `px-4 py-2` + `text-micro` uppercase header), EndpointCard
  (`border-forest-soft` + `text-security-teal` label). New `select.tsx` + `chip.tsx` added and barrel-wired.
  `typecheck`/`lint`/`build` all clean.
- **Badge dot is a prop, not a caller-built span.** `<Badge dot variant=…>` renders a variant-colored
  `size-1.5` leading dot (the base `gap-1.5` spaces it). StatTiles (§4.13, S3) builds its *own* per-key dots
  inside a Card and need not use this, but the affordance exists.
- **`Select`/`Chip` exist + are exported but NOT yet adopted — adoption is S4.** `selectVariants` reuses
  `inputVariants()` so filter selects match form fields; `Select`'s `className` targets the inner
  `<select>` (`wrapperClassName` the positioning span). `Chip` is a plain (non-`"use client"`) primitive
  like `Button`: a removable chip needs a *client* parent to supply `onRemove`. S4 swaps the two raw
  `<select className={inputVariants()}>` in the feedback FilterBar for `<Select>`, and the bespoke tag
  spans in feedback detail for `<Chip>`.
- **Badge migration is complete at both consumers — no re-touch needed.** `feedback-fields.tsx` is
  **fully** P9-migrated (`RatingBadge`: `1`→`liked`, `2`→`disliked`, `null`→`unrated` *badge* per §4.7 — the
  old muted-`<span>` null branch is gone; `FEEDBACK.list.valueUnrated` already existed, no copy invented).
  `projects/[projectId]/page.tsx` had **only** its two credential-status badge lines changed
  (`softGreen`→`active`, `archive`→`revoked`); its breadcrumb / revoke button / key panel / `min-[900px]:`
  compaction remain S4's. The green `build` is the proof the rename hit every call site.
- **Zero-consumer removals confirmed by build:** dropping Card `security`/`archive` and Button
  `secondaryOnDark` broke nothing (grep + build both clean) — they were placeholder-only as DECOMP noted.
- **`section.tsx`/`grid.tsx`/`reveal.tsx` untouched** (boundary); `SectionId` widening stays S6; `Card
  dark`/`pricing`/`pricingFeatured` and the retoned `EndpointCard` are defined and await the landing (S6).

## Constraints

Durable for every slice in this phase. Carry the RESPECT-THE-DESIGN block into **every** slice's `plan.md`
and every executor dispatch prompt (intent.md + `build-prompt.md §1` both require it).

1. **RESPECT THE DESIGN — the load-bearing constraint of this phase (verbatim, from `build-prompt.md §1`):**

   > Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
   > empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
   > effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified here,
   > pick the option closest to the designed intent, **never a plainer fallback**. Where the design implies
   > backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
   > (This round implies **no** backend change; §9 confirms it.)

2. **Locked floors — must survive every slice** (`build-prompt.md §10` / `result.md §8`): identical login
   error (401 → one message, in the form/BFF — do not change); 404-never-403 copy (the `not-found` subcopy
   never confirms existence — *"…or isn't yours to see"*); show-once `vk_` key warning verbatim
   (`PROJECT.keyPanel.warning`) + revoked keys stay listed; **download-only** attachments (proxy `href` +
   `download`, never inline); UTC labels on timestamps; `h1–h6 { word-break: keep-all }` preserved;
   Korean-capable `--font-sans` (Pretendard, Noto Sans KR fallback); `FieldError`'s empty
   `min-h-[1.25rem]` `aria-live="polite"` region preserved; distinct empty states (no-projects vs
   no-matches).
3. **Backend / data: no change required** — no `src/vocky/**`, no P2/P3 contract reopening
   (`build-prompt.md §9`). Everything maps to existing serializers, routes, and already-fetched data.
4. **The design record is read-only.** Never edit anything under
   `docs/reference/design/rounds/01-brand-app-landing/output/` or `SIGNOFF.md`. Apply-time nits are
   catalogued (see Findings), not corrected into the record. `build-prompt.md` is the on-disk source of
   truth; executors have no DesignSync.
5. **Docs are versioned once, at `P9.REVIEW`.** Implementation slices never run `doc-new-version`; when a
   slice changes durable truth it appends a one-line note to the **Doc impact** list below, and the review
   consolidates them into new versions on a passing review.
6. **Keep tests terse** per the repo's small-tests rule — minimal high-value cases, no fixture sprawl;
   prefer `pnpm typecheck` / `pnpm lint` / a small smoke check over a grown suite.
7. **Do not touch P6.** P8 + P9 absorb the landing design *and* build, leaving P6 as production-deploy-only;
   P6's stale name/objective/intent are the operator's to reconcile at `P6.DECOMP`.

## Doc impact

_Running list for `P9.REVIEW` to consolidate into doc versions. Append one line per durable-truth change._

- **Pre-recorded by `P9.DECOMP`:** applying round 01 will make durable truth concrete that
  `docs/current/frontend.md` (v0003) currently describes as a *still-live placeholder* — the deep-emerald
  value swap (names kept), the compact type/radius/spacing scale, Pretendard, the new component vocabulary
  (Select, Chip, destructive/destructiveOutline/ghost Button, split Badge, folded LogoutButton, area
  TrendChart), the `--breakpoint-app` migration, the four net-new states, and the public `/` landing.
  `experience.md` gains the landing as a real signed-out surface. `decisions.md`'s `D-P8-1` is *applied*,
  not superseded. `P9.REVIEW` consolidates these into new versions once — no implementation slice versions
  docs (constraint 5). Backend docs (`api.md`, `architecture.md`, `product.md`, `operations.md`) need **no**
  change (constraint 3 / `build-prompt.md §9`).
- **`P9.S1`:** foundations applied to `globals.css` + `fonts.ts` + `layout.tsx` — the vocky deep-emerald
  palette (names kept), the compact type/radius/spacing scale, `--breakpoint-app` (and `--breakpoint-xs`
  removed), and a `next/font/local` Pretendard loader (vendored variable woff2). `docs/current/frontend.md`
  (v0003) still describes these as a *live placeholder* — for `P9.REVIEW` to consolidate.
- **`P9.S2`:** the `ui/` primitives were rewritten to the vocky system — Button (`rounded-md`,
  +`ghost`/`destructive`/`destructiveOutline`, `secondaryOnDark`→`dark`, green shadows), Card (dropped
  `security`/`archive`), Badge split into rating (`liked`/`disliked`/`unrated`) + status
  (`active`/`revoked`) + `accent` with an optional variant-colored leading dot, Field compact, DataTable
  compact, EndpointCard retoned — plus **new** `Select` + `Chip` primitives and the barrel export.
  `docs/current/frontend.md` (v0003) still describes the placeholder component set (pill buttons, overloaded
  `archive` badge, no Select/Chip). For `P9.REVIEW` to consolidate.

## Open Questions

_None block P9._ The two apply-time choices left open by `result.md §9` are **named with their cost and are
slice-level decisions, not phase blockers**:

- **Pretendard vendoring mechanism** — `next/font/local` + vendored woff2 vs `@fontsource/pretendard`. An
  **S1** decision at implementation; the design assumes Pretendard + Noto Sans KR fallback either way.
- **Optional token-rename pass** (retiring vestigial hi2vi names `victory-lime`/`archive-*`/`security-*`
  for vocky-semantic names) — **out of scope this round**, costed in `build-prompt.md §2.4` as its own
  mechanical slice (call-site churn across `web/src/**`). Not required to ship the design; do not fold it
  into a visual slice.
