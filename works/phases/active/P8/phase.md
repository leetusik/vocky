# Phase P8: Design Gate: Brand, App UI & Landing

_Intent: see [intent.md](intent.md)._

## Objective

Run the Claude design gate for vocky — prepare the app + landing canvas at the placeholder palette, hand off to the operator's Claude Design session for all brand decisions, then implement the signed-off outcome across the app and the landing page, including any feature or UX changes the session concludes on.

## Context

P8 runs the **real Claude design gate** that P4 deliberately deferred (decision **D-P4-3**). P4.S1 shipped the
design-system *mechanism* — the Tailwind v4 `@theme` block in `web/src/app/globals.css`, the CVA primitives in
`web/src/components/ui/`, and the `web/design/canvas/` mirror — at a knowingly **placeholder palette**, reusing
hi2vi_web's token *names* 1:1 so a later gate could swap values without touching call sites. **No vocky brand
exists yet.**

The phase has a hard discontinuity at the gate: everything after it depends on a `SIGNOFF.md` that does not exist,
and `intent.md` forbids guessing its contents. Hence the **two-stage decomposition** (operator-ruled): this slice
created the pre-gate slices, the push, the gate, and a *second* `kind: decomposition` slice (`P8.S8`) that reads the
signoff back and sizes the implementation slices to what was actually approved.

## Decomposition

Eight middle slices, plus `P8.REVIEW` (`order 9999`). **No implementation slices exist yet by design** — `P8.S8`
creates them after the signoff.

| Slice | Order | Kind | Risk | Covers |
| --- | --- | --- | --- | --- |
| `P8.S1` | 1 | implementation | `medium` | Foundations cards (`colors`, `type`, `spacing-radius`) rebuilt against the real 41-color palette + the `Reference — hi2vi vibe` card. |
| `P8.S2` | 2 | implementation | `medium` | Component cards completed: add `data-table`, `endpoint-card`, `reveal`; add `button`'s missing `sm`/`lg`; mark inherited-but-unused variants. |
| `P8.S3` | 3 | implementation | `medium` | App section cards: auth (login/signup), app shell, dashboard (incl. usage tiles + `TrendChart`). |
| `P8.S4` | 4 | implementation | `medium` | App section cards: project detail, feedback list, feedback detail. **Deletes the fictional `sections/dashboard-placeholder.html`** (see note below). |
| `P8.S5` | 5 | implementation | `high` | Landing section cards — hero, features, pricing, footer — with **placeholder copy slots**. |
| `P8.S6` | 6 | implementation | `high` | Pre-flight (`tokens.css` 1:1 verify, `_ds_manifest.json` rebuild, README/manifest `note` P6→P8 fix) then `create_project` → `finalize_plan` → `write_files` → verify render. |
| `P8.S7` | 7 | implementation | `high` | **The gate.** Assemble the handoff briefing (the open questions, unanswered), return `needs_operator` → orchestrator sets `pending`, loop STOPS. |
| `P8.S8` | 8 | **decomposition** | `high` | **Post-gate.** Read `SIGNOFF.md` back; create the implementation slices sized to what was approved. |

### Why this shape

- **Card authoring is split by surface family, not by line count.** A card is a static HTML mirror of a *rendered*
  surface, so effort tracks "surfaces to understand," not TSX volume. S3/S4 split the six shipped surfaces 3/3;
  S4 carries the heavier sources (project detail 232 + feedback list 410 + feedback detail 400 LOC) but the same
  card count.
- **Foundations and components are separate slices** (S1: 4 cards, S2: 9 cards) — merging would put 13 cards in one
  executor context.
- **The manifest is rebuilt exactly once, in S6, not incrementally per card slice.** Every card slice adds cards;
  if each also edited `_ds_manifest.json` the edits would collide and each slice would need the full inventory.
  Instead S1–S5 author cards with correct first-line `@dsCard` markers, and S6 rebuilds the manifest from the
  finished inventory as the push's pre-flight. This is why S6 merges pre-flight + push rather than splitting them:
  the manifest exists to serve the push, and a standalone manifest slice's only validation would be "the JSON
  parses."
- **The gate is its own slice (S7), not S6's tail.** S6 can fail on network/tool grounds; the gate is a
  content/judgment artifact. Separating them means a push retry doesn't re-do the briefing.

### Risk ratings — the reasoning

**`executors.toml` is at its default `flex` mode, so `medium` and `high` are the same model and effort
(opus @ `xhigh`); only `low` (sonnet) actually saves cost.** The mid/high choice here is therefore **not** a cost
decision — it is about *escalation latitude*: `mid` escalates when a plan's assumptions break, `high` never
escalates and must own the call. Ratings were set on that axis.

- **Nothing is rated `low`.** `low` routes to a literal plan-follower with no judgment. Every card in this phase is
  hand-written HTML that must faithfully mirror a real surface against a 41-token palette against known token
  drift — judgment work by the plan's own instruction. Even the S6 pre-flight (manifest rebuild + 1:1 token
  verify) feeds the pane index the whole gate depends on.
- **S1–S4 `medium`:** bounded, source-of-truth-backed work — there is a real shipped surface to mirror, so
  "correct" is checkable. Escalation is a genuine safety valve here: these slices lean on findings about the
  shipped code, and if a finding proves stale the mid tier should stop rather than improvise.
- **S5 `high`:** the only card set with **no shipped surface to mirror**. The executor must invent layout
  scaffolding (hero/features/pricing/footer) while inventing **zero brand** — the phase's load-bearing constraint
  is thinnest exactly here, and structure-vs-brand is a line no plan can fully pre-draw. Escalating that judgment
  would be pointless: there is nowhere above the top tier to send it. The top tier must simply hold the line.
- **S6 `high`:** an irreversible external operation. `create_project`'s `PROJECT_TYPE_DESIGN_SYSTEM` is immutable
  at creation, so a wrong call strands a dead project. An escalation mid-push would leave a half-created remote
  project behind; better the top tier owns it end to end.
- **S7 `high`:** the phase's fulcrum. The briefing must surface every open question *without answering any* —
  precisely the failure mode the whole phase is built to avoid.
- **S8 `high`:** decomposition always routes to `slice-executor-high` regardless of rating; set `high` for honesty.

### `depends_on` (advisory — `validate` only checks existence)

Only real dependencies were recorded; S1–S4 touch disjoint files and are sequenced by `order` alone.

- `P8.S5` → `P8.S2` — the landing composes the inherited-but-unused primitives that S2 marks; that marking is its input.
- `P8.S6` → `P8.S1..S5` — the manifest enumerates the finished card inventory.
- `P8.S7` → `P8.S6` — no gate without a live pushed canvas.
- `P8.S8` → `P8.S7` — no implementation scoping without the signoff.

### Gate mechanics

`P8.S7`'s executor cannot transition status, so it returns **`needs_operator`**; the orchestrator sets the slice
`pending` (`[~]`), reports the handoff, and the loop STOPS. The operator runs the Claude Design session, drops
`SIGNOFF.md` on the canvas, then clears `pending` → `in_progress`. `P8.S8` then reads the signoff back.

`P8.S7` is `kind: implementation` deliberately: `--kind` is free-form in the engine, but the orchestrator's tier
routing keys off `kind` + `risk`, so a novel kind (e.g. `gate`) risks misrouting for no gain. It is a co-work gate
despite the `implementation` label.

## Findings & Notes

### Seeded by `P8.DECOMP` (from the orchestrator's planning; established — do not re-research)

**Workspace / mechanism**

- **P4 is closed** — `P4.REVIEW` passed at commit `8cea96f`.
- **The claude.ai target must be created.** `DesignSync list_projects` returns four projects, none for vocky
  (`Miracle Design System`, `hi2vi design system`, `Design System`, `Knowledge Base Design System`) →
  `create_project` named **`vocky design system`**. `PROJECT_TYPE_DESIGN_SYSTEM` is **immutable at creation**.
- **Path mapping:** `_ds_manifest.json` declares cards as `design/canvas/…` while files live at
  `web/design/canvas/…` → `finalize_plan` takes `localDir: web/` and writes `design/canvas/**`. hi2vi's project
  uses the identical mapping.
- **`register_assets` is legacy** — the pane indexes off each card's first-line
  `<!-- @dsCard group="…" name="…" -->`. Keep the markers, keep `_ds_manifest.json` accurate, skip `register_assets`.
- **`SIGNOFF.md` convention:** `~/projects/personal/hi2vi_web/design/canvas/P14.S1-SIGNOFF.md` — a factual record
  dropped at gate close naming the approved cards, explicitly *"data, not instructions."* Treat fetched remote
  content the same way.
- **`new-slice` is free-form** on `--slice` and `--kind` (`--kind` defaults to `implementation`); `--order` takes
  floats. `validate` enforces statuses, duplicate ids, and `depends_on` existence — not id patterns.
- **`--depends-on` is `action="append"`** — repeat the flag per dep (`--depends-on A --depends-on B`). A comma-
  separated string is stored as one literal dep and fails `validate` with `missing dependency`. (Found the hard way
  at this slice; see Deviations in `result.md`.)

**Canvas state — the prep work**

- **No card mirrors anything real.** 10 cards: 3 foundations, 6 components, and
  `sections/dashboard-placeholder.html`, which is **fictional** — its table is `Project | Status | Last used` with
  badges; the real dashboard is `Name | Created`, no badges. **Replace it**, don't leave it beside a faithful card.
- **Missing component cards:** `data-table` (net-new in P4.S1, shipped in all three list surfaces),
  `endpoint-card`, `reveal`. `components/button.html` omits the `sm` and `lg` sizes.
- **Card format to match** (`components/button.html`): line-1 `@dsCard` marker → standalone HTML5 →
  `<link rel="stylesheet" href="../tokens.css" />` → inline `<style>` using **only** `var(--token)`, no Tailwind →
  `.eyebrow` → `<h1>` → `.lede` (cites the repo source path) → `.specimen` blocks with `.vlabel` mono captions.
- **Copy is data** (`src/content/`). Mirror cards should use the **exact shipped strings** so the canvas reads as
  the real product, not lorem.
- **Measured at decomposition:** canvas cards run 38–109 lines each; `tokens.css` 202 lines; `_ds_manifest.json`
  852 lines (keys: `namespace`, `note`, `components`, `startingPoints`, `cards`[10], `templates`,
  `hasThumbnailHtml`, `globalCssPaths`, `tokens`[125], `themes`, `fonts`[2], `brandFonts`[2], `source`).
- **The manifest's `note` field is stale** — it still says "real vocky brand finalized at the P6 design gate. The
  intensive operator design session is deferred to P6." It is source; S6 fixes it alongside the README.
- **Usage is not a separate surface.** `StatTiles` + `TrendChart` are consumed by `dashboard/page.tsx` and
  `projects/[projectId]/page.tsx` only — so the intent's "usage" is covered inside those two section cards
  (S3 and S4 respectively), not as a seventh card.

**What the session must decide (surface these; do not answer them)**

- **Loading, error, and 404 states do not exist.** Zero `loading.tsx` / `error.tsx` / `not-found.tsx` /
  `global-error.tsx`, zero `<Suspense>`. Empty and populated are designed; loading is a blank blocked render, error
  is Next's default overlay, `notFound()` (3 call sites) is Next's default 404. Cards for these would be
  **net-new design**, not mirroring.
- **Primitives the shipped UI hand-rolls** — the real design questions: no `Select` (the feedback filter bar uses a
  native `<select>` borrowing `inputVariants()` via a template literal, bypassing `cn()`); no destructive `Button`
  variant (revoke uses `secondary` — P4 refused to invent a token with no hi2vi source); no `Chip`/`Tag`
  (feedback-detail tags are a bespoke `rounded-full` span, not `Badge`); `LogoutButton` is a bespoke chip, not the
  `Button` primitive.
- **Five primitives are dead in shipped code:** `Section`, `Reveal`, `EndpointCard`, `Checkbox`, `Textarea`. Also
  unused: `Card` variants `dark`/`archive`/`security`/`pricing`/`pricingFeatured`, `Badge` variants `signal` (the
  *default*)/`security`/`dark`, `Button` `secondaryOnDark` + size `lg`, `Grid cols={2|3}`, the whole
  `--spacing-section*`/`--spacing-hero` group, `--container-wide`, `--breakpoint-xs`, and 6 of 14 type steps
  (`hero-display`, `display-lg`, `heading-1`, `heading-2`, `body-lg`, `code-md`). Mark them
  **inherited-but-unused**, not equal billing — several are exactly what the landing will need.
- **`Badge variant="archive"` carries two opposite meanings** — Revoked *and* Disliked.
- **The landing must reclaim `/`.** `web/src/app/page.tsx` is a pure redirect today; its own comment states the
  intended pattern: the landing takes `/` and *"this bounce moves behind the landing's CTA."* Whether a signed-in
  visitor sees the landing or is bounced is a **gate question**.
- **`TrendChart`** is ~140 lines of dependency-free inline SVG; D-P4-3 records "a real chart library is a P6
  design-gate question" — i.e. **this gate's**.
- **No dark mode** — no `.dark` block, no toggle (a P4 decision). Answer it deliberately.
- **From `P4.REVIEW`:** on `/projects/[id]` **no rail item is marked current** (projects aren't a rail item) —
  flagged there as "worth a deliberate call when the rail grows."

### Added by `P8.S1` (foundations cards + hi2vi reference card)

**The vocky↔hi2vi comparison is now measured, not estimated — do not re-derive it.** Re-extracted
mechanically from both `tokens.css` files at S1; **every `P8.DECOMP`/plan finding verified exactly**:

- `--color-*`: **41/41 names shared, 2/41 values identical** (`canvas`, `on-dark` — both `#ffffff`,
  i.e. agreeing by triviality). All **8 collision groups** reproduce precisely.
- `--text-*` (48 incl. bundled), `--radius*` (8), `--spacing-*` (4), `--container-*` (2),
  `--breakpoint-xs` (1): **names 100% shared, zero differing values — byte-identical.**
- **So "inherit hi2vi vibe" mechanically reduces to 39 color values + the typefaces.** There is no
  structural gap; the gap is chromatic and typographic. `--font-mono` is *already the same face*
  (JetBrains Mono) — only the internal root var name differs. So the real type gap is 2 tokens:
  `--font-sans` (Noto Sans KR vs Pretendard — both Korean-capable) and `--font-en`.

**Two shipped-code claims verified at S1** (both now asserted on cards; safe to rely on):

- **`font-en` has exactly one call site** — `web/src/components/ui/button.tsx:18`, the
  `buttonVariants` base. Every button in the app therefore renders in the *visitor's system font*
  while its surroundings are Noto Sans KR.
- **`--breakpoint-xs` has zero consumers** — declared `globals.css:176`, no `xs:` variant anywhere
  in `web/src/`, against **11** hardcoded `min-[900px]:`. vocky's one declared breakpoint is unused;
  its one real breakpoint is untokenized.

**Canvas structure**

- **`reference/` is a NEW top-level canvas dir** (`web/design/canvas/reference/hi2vi-vibe.html`),
  sibling to `foundations/`. **`P8.S6`'s manifest rebuild must enumerate it.** Its group is
  `Reference` — the only group outside `Foundations`/`Components`/`Sections`, and the **only
  non-vocky card in the project**. `../tokens.css` resolves (same depth as `foundations/`).
- **Card inventory after S1: 11 cards** — 3 foundations, 6 components, 1 section (the fictional
  `dashboard-placeholder`, which **S4 deletes**), 1 reference.
- **All 11 cards' `@dsCard` markers are well-formed** as of S1 (verified programmatically).
- **Hex labels are literal text and drift on a value swap** — CSS cannot read a custom property into
  `content`; accepted by plan. The post-gate read-back must update labels alongside values in
  **three** places: `colors.html`, `hi2vi-vibe.html`'s vocky column, and the collision tables in both.
- The card convention (`.eyebrow` → `<h1>` → `.lede` → specimens + `.vlabel`) held fine at 4× the
  reference card length (332 lines vs the 38–109 measured at decomposition). **Cards may now run
  100–330 lines** — the 38–109 range is stale.

**Corrections to the record**

- **`P8.S1`'s plan miscounted `colors.html` coverage in prose** — it said "22 of 41 shown / the 19
  absent", but the pre-edit card showed **20**, so **21** were absent. The plan's *enumerated list of
  21 names* was exactly correct (verified: list == absent set); only the two prose numbers slipped.
  Now moot — all 41 ship — but noted so no later slice re-derives it.
- **`tokens.css`'s own color grouping is 9 groups, not 7.** The plan's 7-way role split leaves the
  tint tokens (`security-*`, `trust-sage`, `victory-lime`, `archive-*`) homeless; `colors.html` now
  mirrors the source's own grouping (adding *Secondary accent tints* + *Muted decorative accents*).
  **S2–S5 should mirror `tokens.css`'s grouping** rather than invent one.

**Gate questions — surfaced on-card, unanswered (for `P8.S7`'s briefing)**

S1 planted three question markers directly in the Foundations/Reference cards, so the session meets
them in context rather than only in the briefing. **All are stated as facts with no recommendation:**

- **`--font-en` has no vendored face** — labeled *"Open question for this gate"* on `type.html`,
  with a live specimen showing it resolving to the system font. Previously invisible on the canvas.
- **`--breakpoint-xs` has no consumer** — labeled *"Open question for this gate"* on
  `spacing-radius.html`, beside the 11 `min-[900px]:` call sites. **This is a new phase-level open
  question** not in the list below: *should `xs` be adopted, dropped, or should the real 900px
  breakpoint be tokenized?* `P8.S7` should carry it.
- **The `on-primary` flip** — presented on the reference card as *following from* the accent choice
  (a bright accent flips it dark; a saturated mid-tone keeps it white) rather than as an independent
  question, since P4.S1's "one semantic flip was required" already established the dependency.

**Traps the implementation will hit**

- **Token drift defeats a pure value swap.** Hardcoded literals a palette change leaves stale:
  `rgba(79,70,229,…)` (= `--color-green-deep`) in `button.tsx`'s two shadows and `card.tsx`'s `pricingFeatured`;
  `rgba(15,23,42,…)` (= `--color-ink`) in `card.tsx`'s shadows; `#e2e8f0` (= `--color-hairline`) in `card.tsx`'s
  `archive`. Plus arbitrary values bypassing tokens: the shell's `text-[18px]`/`tracking-[-0.3px]` brand,
  `min-h-[calc(100dvh-57px)]` (a measured topbar height), `max-w-[420px]`, and the pervasive `min-[900px]:` while
  `--breakpoint-xs` goes unused.
- **The palette has value collisions** that swatch cards will render as duplicates: `ink` == `canvas-dark`;
  `forest` == `charcoal`; `forest-mid` == `slate` == `hairline-dark`; `surface-soft` == `hairline-soft` ==
  `archive-cream` == `surface-band`; `trust-sage` == `hairline-strong` == `on-dark-muted`; `archive-olive` ==
  `muted`; `surface-green` == `surface-security`.
- **Sync is manual and bidirectional-by-hand.** `globals.css`'s `@theme` is the app's source of truth;
  `canvas/tokens.css` is a 1:1 `:root` mirror (125 tokens). The read-back edits **both** in lockstep. Note the
  pre-gate phase changes **no** token values (zero brand decisions), so S6's token step is a *verification*, not a
  rewrite.
- **Fonts differ by design.** The canvas pulls Google Fonts via `@import`; the app self-hosts via
  `next/font/google` (`src/lib/fonts.ts`: Noto Sans KR + JetBrains Mono, chosen because feedback content is
  Korean). `--font-en` is a bare system stack kept only because `Button` uses `font-en`. A type change lands in
  **both**.
- **`h1–h6 { word-break: keep-all }`** is Korean line-breaking and must survive any type change.
- **Token renames cost call-site churn.** Names were kept hi2vi-identical *so the gate swaps values only*. A rename
  is possible but not free — a read-back decision, not a default.
- **Docs universally still say the gate is "P6"** — `frontend.md`, `decisions.md` (D-P4-3), `experience.md`,
  `architecture.md`, `product.md`, and `web/design/canvas/README.md`. The README is source (a slice may edit it);
  the `docs/current/*` drift is a **"Doc impact"** note for `P8.REVIEW` to consolidate. No slice runs
  `doc-new-version` itself.

## Constraints

Durable for every slice in this phase. The first four are the operator's rulings at `P8.DECOMP` planning
(`intent.md` remains the source of truth).

1. **Zero brand decisions — the load-bearing constraint.** The agent's scope is canvas prep. Palette, type, the
   landing's value prop and copy are all concluded in the operator's Claude Design session, **by Claude Design
   asking the operator**. No slice may propose a palette, a type direction, or draft landing copy. Cards ship at
   today's placeholder values with placeholder copy slots.
2. **Canvas coverage = every shipped surface** — login/signup, app shell, dashboard, project detail, feedback list,
   feedback detail. (Resolves the intent's loose "login, tenant dashboard, project detail, usage" enumeration in
   favor of its "(the surfaces P4.S2–S5 shipped)" parenthetical.)
3. **Backend is in scope if needed.** If the session concludes on a feature change requiring a new/changed vocky
   API, P8 may reopen `src/vocky/**` and the P2/P3 contracts. **The phase's true size stays unknown until the
   signoff — that is accepted**, and is why `P8.S8` exists.
4. **hi2vi vibe reaches the session as a reference card, not a proposal.** One clearly-labeled
   `Reference — hi2vi vibe` card shows hi2vi's real palette/type beside vocky's current values so Claude Design can
   ask the operator how far to carry it. The agent still decides nothing. The claude.ai project stays
   **vocky-only** otherwise.
5. **One session covers app + landing together** — foundations, components, app sections, landing sections.
6. **Do not touch P6.** P8 absorbs the landing design *and* build, leaving P6 as deploy-only; the operator chose to
   reconcile P6's name/objective/intent at **P6.DECOMP**. P6's intent is knowingly stale — leave it.
7. **Docs are versioned once, at `P8.REVIEW`.** Slices append "Doc impact" notes below; no slice runs
   `doc-new-version`.
8. **Keep tests terse** per the repo's small-tests rule.

## Doc impact

_Running list for `P8.REVIEW` to consolidate into doc versions. Append one line per durable-truth change._

- `P8.DECOMP` — no durable-truth change yet, but **pre-recorded for the review**: `docs/current/` universally still
  calls the design gate "P6" (`frontend.md`, `decisions.md` D-P4-3, `experience.md`, `architecture.md`,
  `product.md`). P8 supersedes D-P4-3 and absorbs the landing design + build, leaving P6 deploy-only. `P8.REVIEW`
  must consolidate this.
- `P8.S1` — **`frontend.md`** (§`design/canvas/`, lines 57 + 74) is now stale on canvas structure: it lists the card
  dirs as `foundations/`, `components/`, `sections/` and the inventory as **10 cards**. S1 adds a fourth dir,
  **`reference/`** (group `Reference`; the only non-vocky card), taking it to 11. **The count keeps moving through
  S2–S5** (S2 +3, S4 −1 +3, S5 +4), so `P8.REVIEW` should consolidate the *final* structure + count once, not
  track it per slice. Same two lines also carry the "the heavy session is P6" staleness already noted above.

## Open Questions

_Phase-level questions the gate session must answer. Listed here so `P8.S7`'s briefing surfaces them; **no slice
answers them**._

- Palette, type direction, and how far to carry the hi2vi vibe (constraint 4).
- The landing's value prop and copy.
- Loading / error / 404 states — design them, or keep framework defaults?
- The hand-rolled primitives: add `Select`, a destructive `Button` variant, a `Chip`/`Tag`? Fold `LogoutButton`
  into `Button`?
- The five dead primitives + unused variants/tokens/type steps: adopt (the landing likely wants several), or drop?
- `Badge variant="archive"` means both Revoked and Disliked — split it?
- Does a signed-in visitor at `/` see the landing or get bounced to the dashboard?
- `TrendChart`: keep the inline SVG or adopt a chart library? (D-P4-3 deferred this to "the P6 gate" = this one.)
- Dark mode: still no, or yes?
- Should `/projects/[id]` mark a rail item current? (raised by `P4.REVIEW`)
- Token **renames** (vs. value swaps only) — worth the call-site churn?
