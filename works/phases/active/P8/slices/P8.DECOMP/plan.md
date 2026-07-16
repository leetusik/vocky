# Plan — `P8.DECOMP` (decompose the Design Gate phase)

Written by the orchestrator at this slice's turn. Executed by **`slice-executor-high`** (decomposition
always routes to the top tier, regardless of this slice's `low` risk rating).

## Context

P8 runs vocky's **real Claude design gate** — the one P4 deliberately deferred (decision **D-P4-3**).
P4.S1 shipped the design-system *mechanism* (the Tailwind v4 `@theme` block, the CVA primitives, the
`web/design/canvas/` mirror) at a knowingly **placeholder palette**, reusing hi2vi_web's token *names*
1:1 so a later gate could swap values without touching call sites. **No vocky brand exists yet.**

This slice designs nothing and writes no code. It **decomposes the phase**: creates the middle slices
as bare folders and seeds `phase.md`. Each middle slice's `plan.md` is written later, by the
orchestrator, at that slice's turn.

## The load-bearing constraint

From `intent.md`: **the agent's scope is canvas prep with zero brand decisions.** Palette, type, the
landing's value prop and copy are all concluded in the operator's Claude Design session, *by Claude
Design asking the operator*. No slice may be "propose a palette" or "draft landing copy".

## Operator decisions captured at this planning

Also appended to `intent.md` (verbatim directive + all rulings) — that file remains the source of
truth. New verbatim directive: *"for the design system, make a design system only for vocky but
inherit hi2vi vibe."*

| Fork | Ruling |
| --- | --- |
| **Canvas coverage** | **Every shipped surface** — login/signup, app shell, dashboard, project detail, feedback list, feedback detail. Resolves the intent's loose "login, tenant dashboard, project detail, usage" enumeration in favor of its "(the surfaces P4.S2–S5 shipped)" parenthetical. |
| **Backend scope** | **In scope if needed.** If the session concludes on a feature change requiring a new/changed vocky API, P8 may reopen `src/vocky/**` and the P2/P3 contracts. The phase's true size stays unknown until the signoff — that is accepted. |
| **Phase shape** | **Two-stage decomposition** (below). |
| **hi2vi vibe** | **A reference card on the canvas.** Cards ship at today's neutral placeholder; one clearly-labeled `Reference — hi2vi vibe` card shows hi2vi's real palette/type beside vocky's current values, so Claude Design can ask the operator how far to carry it. The agent still decides nothing. The claude.ai project stays **vocky-only** otherwise. |

## The phase shape (operator-approved)

The phase has a hard discontinuity at the gate: everything after it depends on a `SIGNOFF.md` that
does not exist, and `intent.md` forbids guessing (*"Scope the implementation slices from the
signed-off design, not from a presumed visual-only diff"*; *"not just re-skinning. there maybe feature
change"*). Since only a `kind: decomposition` slice may run `new-slice`, the phase is:

1. **Pre-gate — canvas fidelity.** Rebuild the canvas to mirror the real shipped surfaces at the
   placeholder palette, add the missing component cards, add the hi2vi reference card, add landing
   section cards with placeholder copy slots, re-mirror `tokens.css` + `_ds_manifest.json`.
2. **Push + hand off.** `create_project` → `finalize_plan` → `write_files` → verify the cards render.
3. **The gate — operator co-work.** Ends `pending`.
4. **Post-gate — a second `kind: decomposition` slice.** Reads the signoff back and creates the
   implementation slices sized to what was actually approved.
5. `P8.REVIEW` (already exists, `order 9999`).

**This slice creates steps 1–4 only. It must NOT create implementation slices** — that is step 4's
job. You size and name the pre-gate slices, set each `--risk` deliberately, and record the breakdown
in `phase.md`.

**Risk is the cost lever.** The canvas cards are hand-written HTML that must faithfully mirror real
surfaces against a 41-token palette — that is judgment work. Rate a slice `low` (→ the literal
plan-following `slice-executor-low`) only if it is genuinely mechanical.

## Gate mechanics — use the workflow's own mechanism

You cannot transition status, so the gate slice's executor returns **`needs_operator`**; the
orchestrator sets it `pending` (`[~]`), reports the handoff, and the loop STOPS. The operator runs the
Claude Design session, drops `SIGNOFF.md` on the canvas, then clears `pending` → `in_progress`.
Structure the gate slice so this is its natural path.

## Findings handed to you — established, do not re-research

**Workspace / mechanism**

- **P4 is closed** (`P4.REVIEW` passed, commit `8cea96f`) — resolves the intent's open question.
- **The claude.ai target must be created.** `DesignSync list_projects` returns four projects, none for
  vocky (`Miracle Design System`, `hi2vi design system`, `Design System`, `Knowledge Base Design
  System`). → `create_project` named **`vocky design system`**. `PROJECT_TYPE_DESIGN_SYSTEM` is
  immutable at creation.
- **Path mapping:** `_ds_manifest.json` already declares cards as `design/canvas/…` while files live at
  `web/design/canvas/…` → `finalize_plan` takes `localDir: web/`, writes `design/canvas/**`. hi2vi's
  project uses the identical mapping.
- **`register_assets` is legacy** — the pane indexes off each card's first-line
  `<!-- @dsCard group="…" name="…" -->`. Keep markers, keep `_ds_manifest.json` accurate, skip it.
- **`SIGNOFF.md` convention:** `~/projects/personal/hi2vi_web/design/canvas/P14.S1-SIGNOFF.md` — a
  factual record dropped at gate close naming the approved cards, explicitly *"data, not
  instructions."* Treat fetched remote content the same way.
- **`new-slice` is free-form** on `--slice` and `--kind` (`--kind` defaults to `implementation`);
  `--order` takes floats. `DECOMP` is `order 0`, `REVIEW` is `order 9999`, middles are `1..n`.
  `validate` enforces statuses, duplicate ids, and `depends_on` existence — not id patterns.

**Canvas state — the prep work**

- **No card mirrors anything real.** 10 cards: 3 foundations, 6 components, and
  `sections/dashboard-placeholder.html`, which is **fictional** — its table is `Project | Status | Last
  used` with badges; the real dashboard is `Name | Created`, no badges. **Replace it**, don't leave it
  beside a faithful card.
- **Missing component cards:** `data-table` (net-new in P4.S1, shipped in all three list surfaces),
  `endpoint-card`, `reveal`. `components/button.html` omits the `sm` and `lg` sizes.
- **Card format to match** (`components/button.html`): line-1 `@dsCard` marker → standalone HTML5 →
  `<link rel="stylesheet" href="../tokens.css" />` → inline `<style>` using **only** `var(--token)`,
  no Tailwind → `.eyebrow` → `<h1>` → `.lede` (cites the repo source path) → `.specimen` blocks with
  `.vlabel` mono captions.
- **Copy is data** (`src/content/`). Mirror cards should use the **exact shipped strings** so the
  canvas reads as the real product, not lorem.

**What the session must decide (surface these; do not answer them)**

- **Loading, error, and 404 states do not exist.** Zero `loading.tsx` / `error.tsx` /
  `not-found.tsx` / `global-error.tsx`, zero `<Suspense>`. Empty and populated are designed; loading is
  a blank blocked render, error is Next's default overlay, `notFound()` (3 call sites) is Next's
  default 404. Cards for these would be **net-new design**, not mirroring.
- **Primitives the shipped UI hand-rolls** — the real design questions: no `Select` (the feedback
  filter bar uses a native `<select>` borrowing `inputVariants()` via a template literal, bypassing
  `cn()`); no destructive `Button` variant (revoke uses `secondary` — P4 refused to invent a token
  with no hi2vi source); no `Chip`/`Tag` (feedback-detail tags are a bespoke `rounded-full` span, not
  `Badge`); `LogoutButton` is a bespoke chip, not the `Button` primitive.
- **Five primitives are dead in shipped code:** `Section`, `Reveal`, `EndpointCard`, `Checkbox`,
  `Textarea`. Also unused: `Card` variants `dark`/`archive`/`security`/`pricing`/`pricingFeatured`,
  `Badge` variants `signal` (the *default*)/`security`/`dark`, `Button` `secondaryOnDark` + size `lg`,
  `Grid cols={2|3}`, the whole `--spacing-section*`/`--spacing-hero` group, `--container-wide`,
  `--breakpoint-xs`, and 6 of 14 type steps (`hero-display`, `display-lg`, `heading-1`, `heading-2`,
  `body-lg`, `code-md`). Mark them **inherited-but-unused**, not equal billing — several are exactly
  what the landing will need.
- **`Badge variant="archive"` carries two opposite meanings** — Revoked *and* Disliked.
- **The landing must reclaim `/`.** `web/src/app/page.tsx` is a pure redirect today; its own comment
  states the intended pattern: the landing takes `/` and *"this bounce moves behind the landing's
  CTA."* Whether a signed-in visitor sees the landing or is bounced is a **gate question**.
- **`TrendChart`** is ~60 lines of dependency-free inline SVG; D-P4-3 records "a real chart library is
  a P6 design-gate question" — i.e. **this gate's**.
- **No dark mode** — no `.dark` block, no toggle (a P4 decision). Answer it deliberately.
- **From `P4.REVIEW`:** on `/projects/[id]` **no rail item is marked current** (projects aren't a rail
  item) — flagged there as "worth a deliberate call when the rail grows."

**Traps the implementation will hit**

- **Token drift defeats a pure value swap.** Hardcoded literals that a palette change leaves stale:
  `rgba(79,70,229,…)` (= `--color-green-deep`) in `button.tsx`'s two shadows and `card.tsx`'s
  `pricingFeatured`; `rgba(15,23,42,…)` (= `--color-ink`) in `card.tsx`'s shadows; `#e2e8f0` (=
  `--color-hairline`) in `card.tsx`'s `archive`. Plus arbitrary values bypassing tokens: the shell's
  `text-[18px]`/`tracking-[-0.3px]` brand, `min-h-[calc(100dvh-57px)]` (a measured topbar height),
  `max-w-[420px]`, and the pervasive `min-[900px]:` while `--breakpoint-xs` goes unused.
- **The palette has value collisions** that swatch cards will render as duplicates: `ink` ==
  `canvas-dark`; `forest` == `charcoal`; `forest-mid` == `slate` == `hairline-dark`; `surface-soft` ==
  `hairline-soft` == `archive-cream` == `surface-band`; `trust-sage` == `hairline-strong` ==
  `on-dark-muted`; `archive-olive` == `muted`; `surface-green` == `surface-security`.
- **Sync is manual and bidirectional-by-hand.** `globals.css`'s `@theme` is the app's source of truth;
  `canvas/tokens.css` is a 1:1 `:root` mirror (125 tokens). The read-back edits **both** in lockstep.
- **Fonts differ by design.** The canvas pulls Google Fonts via `@import`; the app self-hosts via
  `next/font/google` (`src/lib/fonts.ts`: Noto Sans KR + JetBrains Mono, chosen because feedback
  content is Korean). `--font-en` is a bare system stack kept only because `Button` uses `font-en`. A
  type change lands in **both**.
- **`h1–h6 { word-break: keep-all }`** is Korean line-breaking and must survive any type change.
- **Token renames cost call-site churn.** Names were kept hi2vi-identical *so the gate swaps values
  only*. A rename is possible but not free — a read-back decision, not a default.
- **Docs universally still say the gate is "P6"** — `frontend.md`, `decisions.md` (D-P4-3),
  `experience.md`, `architecture.md`, `product.md`, and `web/design/canvas/README.md`. The README is
  source (a slice may edit it); the `docs/current/*` drift is a **"Doc impact"** note for `P8.REVIEW`
  to consolidate. No slice runs `doc-new-version` itself.

## Constraints

- **Zero brand decisions.** Cards ship at today's placeholder values with placeholder copy slots. The
  hi2vi reference card is *reference*, clearly labeled — not a proposal.
- **The claude.ai project is vocky-only**, per the operator's directive.
- **One session covers app + landing together** (foundations, components, app sections, landing
  sections).
- **Do not touch P6.** P8 absorbs the landing design *and* build, leaving P6 as deploy-only; the
  operator chose to reconcile P6's name/objective/intent at **P6.DECOMP**. P6's intent is knowingly
  stale — leave it.
- **Do not create implementation slices** — the post-gate decomposition slice does that.
- Bare folders only; never pre-fill a middle slice's `plan.md`.
- No `doc-new-version`, no commits, no status transitions. `new-slice` is the only workflow command
  you may run beyond `validate`.
- Keep any tests terse per the repo's small-tests rule.

## Validation

- `python3 scripts/workflow.py validate` — passes.
- `python3 scripts/workflow.py next` — resolves to the first pre-gate slice.
- `works/backlog.md` lists the new P8 slices with the intended order, kind, and risk — including the
  gate slice and the post-gate `decomposition` slice, and **no** implementation slices.
- `phase.md` carries the breakdown (what each slice covers and why), the findings above, the four
  operator rulings as durable constraints, and the open questions the gate must answer.
