# Phase P8: Design Gate: Brand, App UI & Landing

_Intent: see [intent.md](intent.md)._

## Objective

Seed vocky's design canvas from live code, run the Claude Design gate for the brand, the app UI and the landing, and capture the signed-off design as an implementable spec. Implementation is P9.

## Context

P8 runs the **real Claude design gate** that P4 deliberately deferred (decision **D-P4-3**). P4.S1
shipped the design-system *mechanism* — the Tailwind v4 `@theme` block in `web/src/app/globals.css`,
the CVA primitives in `web/src/components/ui/`, and the `web/design/canvas/` mirror — at a knowingly
**placeholder palette**, reusing hi2vi_web's token *names* 1:1 so a later gate could swap values
without touching call sites. **No vocky brand exists yet.**

**This phase is the design only.** The apply half is **P9** (order 4.6), whose `DECOMP` cannot run
until this gate closes and sizes the work from the returned `build-prompt.md`. That split is v12's
prescription for a big design change, and it is what lets this phase close cleanly at signoff.

> **This phase was re-created on 2026-07-17.** An earlier P8 ran under rules that did not exist yet
> and was fully reverted at `c9102e3`. Everything below marked *harvested* was measured by that
> phase (or by the `/design-sync` run it spawned) and is carried forward so no slice re-derives it.
> The originals are in git: `0007184`, `97ad6a8`, `0c794bb`, `301ab32`.

**Live claude.ai target:** `1eaa0803-46e3-426a-ab04-17a802170234` — `vocky design system`,
`PROJECT_TYPE_DESIGN_SYSTEM` (verified). **Nothing has been pushed to it yet.**
**ABANDONED — do not target:** `2d64ae63-5b35-41a8-9090-c3f3eeed0b99`. Same name, still returned by
`list_projects`, invisible in the operator's UI, emptied of all 23 files at the revert, and
undeletable (DesignSync has no `delete_project`). **Target by id, never by name.**

## Decomposition

_Slice breakdown and rationale — filled by the `P8.DECOMP` slice (2026-07-17)._

> Two v12 rules bind the shape and must survive into that breakdown:
>
> - **The gate slice is `--kind co-work --risk high` and is NEVER dispatched** — a deliberate
>   exception to the contract's "every slice is delegated", because executors have no `DesignSync`
>   tool. Push, STOP, and read-back all live in that one slice (two commits, with the `pending`
>   window between them). Never rate a design gate `low`.
> - **Do not over-plan before the gate** — *"you do not know what the operator will design."* Create
>   round 1 only. If the session needs a round 2, cut it at a fractional order afterward.
>
> **Both survived: `P8.S6` is `co-work`/`high` and is round 1's only gate; nothing beyond `S7` exists.**

`intent.md`'s four stages — **seed → brief → gate → synthesis** — with **seed** split three ways on
measured size (~11 cards at 100–330 lines each, plus a machine-produced render). `P8.REVIEW` sits at
order 9999, so 1–7 slot in cleanly.

| Slice | Name | Kind | Risk | Order | Depends on |
|---|---|---|---|---|---|
| `P8.S1` | Frozen baseline render of the 6 shipped surfaces | `implementation` | `medium` | 1 | — |
| `P8.S2` | DS cards: foundations completion, DataTable card, `Reference — hi2vi vibe`; drop the fictional placeholder | `implementation` | `high` | 2 | — |
| `P8.S3` | Surface mirror cards A: app shell, login/signup, dashboard | `implementation` | `high` | 3 | `P8.S1` |
| `P8.S4` | Surface mirror cards B: project detail, feedback list, feedback detail | `implementation` | `high` | 4 | `P8.S1` |
| `P8.S5` | Gate brief card + `_ds_manifest.json` regen + P6→P8 source fixes | `implementation` | `high` | 5 | `P8.S2`, `P8.S3`, `P8.S4` |
| `P8.S6` | **The design gate: push → STOP → read-back** | **`co-work`** | **`high`** | 6 | `P8.S5` |
| `P8.S7` | Synthesis: capture the spec into `phase.md` + write the SIGNOFF | `implementation` | `high` | 7 | `P8.S6` |

### Why this split

- **`S1` first, and it is not optional.** v12 requires *"a frozen baseline render of today's look…
  that survives token changes — the before/after reference at sign-off."* The harvested finding proves
  why it must precede the gate: utilities compile to `var(--color-*)` references, **so the instant the
  gate swaps `--color-green`, every live artifact re-themes and "before" is destroyed.** Its output is
  also the real paint `S3`/`S4` mirror against — hence the `depends_on`.
- **`S2` is design-system vocabulary; `S3`/`S4` are product surfaces.** Different work, different
  reference material. `S2` needs no baseline, so it can run before or beside `S1`.
- **`S3`/`S4` split 3/3 by measured weight.** Feedback detail alone is ~2–3× the dashboard (5 sections,
  a 14-cell `<dl>`, tag pills, comment cards, attachment rows, collapsible JSON), and project detail is
  a 6-column table plus the show-once key panel. One slice of six cards is ~1200 lines of hand-authored
  HTML; two of three is reviewable.
- **`S5` last before the gate** because the manifest **does not rebuild on upload** — it can only be
  regenerated once every card exists. It also carries the brief (the "say what to design" job) and the
  P6→P8 source fixes, both of which want the final card set in hand.
- **`S6` is the gate and is never dispatched** — push, STOP (`pending`), read-back, orchestrator-inline.
- **`S7` closes the phase** at the synthesis + SIGNOFF; the apply is P9.

### Risk rationale — why nothing is `low`

`executors.toml` is all-defaults → **flex mode**: `low` = sonnet@xhigh, `mid`/`high` = opus@xhigh. So
`medium` vs `high` **costs nothing extra**, and `low` is the only real cost lever — but nothing here is
mechanical enough for it.

- **`high` on every card-authoring slice** (`S2`–`S5`, `S7`) deliberately: the constraint these slices
  can most easily break — **zero brand decisions** — is exactly the kind a literal plan-follower crosses
  without noticing (it "helpfully" picks a color, drafts a headline, answers a question the brief was
  supposed to pose back). That judgment is the whole job.
- **`S1` is `medium`:** a build/curl/inline chain with real environment surprise (auth, fonts, the stack)
  but **no design judgment** in it.
- **`S6` is `high` and `co-work`:** v12 — *"never rate a design gate `low`."*
- **Nothing is `low`.** Deliberate, not an oversight.

### What is deliberately NOT sliced

- **No landing mirror cards.** The landing does not exist in code (`web/src/app/page.tsx` is a pure
  redirect), so authoring hero/features/pricing/footer cards would be **invention, not mirroring** — the
  exact trap constraint 6 and the fictional `dashboard-placeholder.html` both name. The landing reaches
  the session **through the brief, as questions** (*"a card can be a question"*). Claude Design designs
  it; we ask for it. This is not a coverage gap against `intent.md`'s "landing sections" line — it is how
  a first-time surface enters a gate.
- **No loading / error / 404 cards.** Cards for these would be net-new design, not mirroring. They are
  already an Open Question for the brief.
- **No round 2, no apply slices.** Round 1 only — *"expect the gate to re-shape the phase."* If the
  session needs another round, cut it at a fractional order **after** the read-back. P9 owns the apply.

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

### Harvested — measured facts about the codebase (do NOT re-derive)

Re-extracted mechanically from both `tokens.css` files with an assert that all 41 tokens are covered
exactly once — generated, not hand-transcribed.

- **"Inherit hi2vi vibe" reduces to 39 color values + 2 typefaces.**
  - `--color-*`: **41/41 names shared, 2/41 values identical** (`canvas`, `on-dark` — both `#ffffff`,
    i.e. agreeing by triviality).
  - `--text-*` (48 incl. bundled), `--radius*` (8), `--spacing-*` (4), `--container-*` (2),
    `--breakpoint-xs` (1): **names 100% shared, zero differing values — byte-identical.**
  - **No structural gap; the gap is chromatic and typographic.** `--font-mono` is *already the same
    face* (JetBrains Mono) — only the internal root var name differs. The real type gap is 2 tokens:
    `--font-sans` (Noto Sans KR vs Pretendard — both Korean-capable) and `--font-en`.
- **`--font-en` has exactly one call site** — `web/src/components/ui/button.tsx:18`, the
  `buttonVariants` base. Every button renders in the *visitor's system font* while its surroundings
  are Noto Sans KR. **No face is vendored for it.**
- **`--breakpoint-xs` has zero consumers** — declared `globals.css:176`, no `xs:` variant anywhere in
  `web/src/`, against **11** hardcoded `min-[900px]:`. vocky's one declared breakpoint is unused; its
  one real breakpoint is untokenized.
- **8 palette collision groups** (swatch cards render these as duplicates): `ink` == `canvas-dark` ·
  `forest` == `charcoal` · `forest-mid` == `slate` == `hairline-dark` · `surface-soft` ==
  `hairline-soft` == `archive-cream` == `surface-band` · `trust-sage` == `hairline-strong` ==
  `on-dark-muted` · `archive-olive` == `muted` · `surface-green` == `surface-security`.
- **Token-drift traps — hardcoded literals a palette swap leaves stale:** `rgba(79,70,229,…)`
  (= `--color-green-deep`) in `button.tsx`'s two shadows and `card.tsx`'s `pricingFeatured`;
  `rgba(15,23,42,…)` (= `--color-ink`) in `card.tsx`'s shadows; `#e2e8f0` (= `--color-hairline`) in
  `card.tsx`'s `archive`. Plus arbitrary values bypassing tokens: the shell's
  `text-[18px]`/`tracking-[-0.3px]` brand, `min-h-[calc(100dvh-57px)]`, `max-w-[420px]`, and the
  pervasive `min-[900px]:`.
- **5 primitives are dead in shipped code:** `Section`, `Reveal`, `EndpointCard`, `Checkbox`,
  `Textarea`. Also unused: `Card` variants `dark`/`archive`/`security`/`pricing`/`pricingFeatured`;
  `Badge` variants `signal` (the *default*)/`security`/`dark`; `Button` `secondaryOnDark` + size
  `lg`; `Grid cols={2|3}`; the whole `--spacing-section*`/`--spacing-hero` group; `--container-wide`;
  `--breakpoint-xs`; 6 of 14 type steps (`hero-display`, `display-lg`, `heading-1`, `heading-2`,
  `body-lg`, `code-md`). **Mark inherited-but-unused, not equal billing — several are exactly what
  the landing will need.**
- **Primitives the shipped UI hand-rolls** — the real design questions: no `Select` (the feedback
  filter bar uses a native `<select>` borrowing `inputVariants()` via a template literal, bypassing
  `cn()`); no destructive `Button` variant (revoke uses `secondary` — P4 refused to invent a token
  with no hi2vi source); no `Chip`/`Tag` (feedback-detail tags are a bespoke `rounded-full` span, not
  `Badge`); `LogoutButton` is a bespoke chip, not the `Button` primitive.
- **`Badge variant="archive"` carries two opposite meanings** — Revoked *and* Disliked.
- **Loading, error, and 404 states do not exist.** Zero `loading.tsx` / `error.tsx` /
  `not-found.tsx` / `global-error.tsx`, zero `<Suspense>`. Empty and populated are designed; loading
  is a blank blocked render, error is Next's default overlay, `notFound()` (3 call sites) is Next's
  default 404. **Cards for these would be net-new design, not mirroring.**
- **`TrendChart`** is ~140 lines of dependency-free inline SVG. D-P4-3 records "a real chart library
  is a P6 design-gate question" — i.e. **this gate's**.
- **The landing must reclaim `/`.** `web/src/app/page.tsx` is a pure redirect today; its own comment
  states the intended pattern: the landing takes `/` and *"this bounce moves behind the landing's
  CTA."*
- **`h1–h6 { word-break: keep-all }`** is Korean line-breaking and **must survive any type change**.
- **Fonts differ by design.** The canvas pulls Google Fonts via `@import`; the app self-hosts via
  `next/font/google` (`src/lib/fonts.ts`: Noto Sans KR + JetBrains Mono, chosen because feedback
  content is Korean). `--font-en` is a bare system stack kept only because `Button` uses `font-en`.
  A type change lands in **both**.
- **Token renames cost call-site churn.** Names were kept hi2vi-identical *so the gate swaps values
  only*. A rename is possible but not free — a read-back decision, not a default.
- **Usage is not a separate surface.** `StatTiles` + `TrendChart` are consumed by `dashboard/page.tsx`
  and `projects/[projectId]/page.tsx` only — so the intent's "usage" is covered inside those two
  section cards, not as a seventh surface.
- **From `P4.REVIEW`:** on `/projects/[id]` **no rail item is marked current** (projects aren't a rail
  item) — flagged there as "worth a deliberate call when the rail grows."
- **Canvas card format** (`components/button.html` is the reference): line-1 `@dsCard` marker →
  standalone HTML5 → `<link rel="stylesheet" href="../tokens.css" />` → inline `<style>` using
  **only** `var(--token)`, no Tailwind → `.eyebrow` → `<h1>` → `.lede` (cites the repo source path) →
  `.specimen` blocks with `.vlabel` mono captions. Cards may run 100–330 lines.
- **Copy is data** (`src/content/`). Mirror cards must use the **exact shipped strings** so the canvas
  reads as the real product, not lorem.
- **Path mapping:** `_ds_manifest.json` declares cards as `design/canvas/…` while files live at
  `web/design/canvas/…` → `finalize_plan` takes `localDir: web/` and writes `design/canvas/**`.
  hi2vi's project uses the identical mapping.
- **`--depends-on` is `action="append"`** — repeat the flag per dep. A comma-separated string is
  stored as one literal dep and fails `validate` with `missing dependency`. (Found the hard way at the
  first `P8.DECOMP`.)

### Harvested from the reverted `/design-sync` run — machine-measured, mechanism wrong, facts real

- **Utilities compile to `var(--color-*)` references, not baked hex** — verified in the compiled
  bundle, not inferred: `.bg-green { background-color: var(--color-green); }`, and the tokens ride in
  the same file. **So a token value change rethemes every component.** This is the property the whole
  design gate depends on — and precisely **why a frozen baseline render is mandatory**: the instant
  the gate swaps `--color-green`, every live artifact re-themes and "before" is destroyed.
- **`Grid`'s `gap?: string` takes a raw class string, not a token**, and Tailwind's content scan
  covers `web/` only. `web/` uses exactly `gap-1`, `gap-2`, `gap-3`, `gap-3.5`, `gap-4` today — so
  `gap="gap-8"` **does not fail, does not warn, and renders with no gap at all.** A silent no-op
  through a component's own public API.
- **`Grid`'s `cols={3}` and `cols={4}` are pixel-identical below 1024px** — Tailwind's `lg` is
  64rem/1024px, verified in the compiled bundle. vocky's real breakpoint is `min-[900px]:`.
  Reinforces the `--breakpoint-xs` finding.
- **`--color-surface-soft` == `--color-surface-band`** (both `#f1f5f9`) → `Section`'s `surfaceSoft`
  and `band` are two named API values with one value: **two bands stack into one unbroken block with
  no seam.** (`security` #eef2ff vs `archive` #f9fafb are close but genuinely distinguishable.)
- **`Section` is tall by construction** — `py-section md:py-section-lg` = 104px top and bottom at any
  viewport ≥768px, so the 72px `py-section` base is never what a short capture shows.
- **`Section`'s `id` is typed to `SECTION_IDS` = `{overview, primitives}`** — both leftovers from the
  dead P4.S1 preview page.
- **`FieldError` renders an empty `<p class="min-h-[1.25rem]">` when there is no error** — deliberate:
  reserves space and stays in the tree for `aria-live`. **An a11y floor for the brief's "locked" list.**
- **`web/src/lib/utils.ts` (`cn()`) is clean of `server-only`**; `lib/env`, `lib/session`, `lib/bff`,
  `lib/auth-guards`, `lib/vocky/*` are not.
- **`web/src/components/usage/` and `web/src/components/app-shell/` are app components, not the design
  system** — outside `src/components/ui`.
- **Playwright 1.61.1 + chromium 1228 are cached at `~/Library/Caches/ms-playwright`** on macOS, *not*
  `~/.cache/ms-playwright`. Outside the repo — survived the revert. Check the Library path before any
  tool re-downloads ~200MB.

### The anti-finding — why `/design-sync` is forbidden here (do not retry it)

> `/design-sync` on vocky required: a fabricated `web/package.json` `"types"` field (without it:
> `[ZERO_MATCH] no component exports — treating as tokens-only DS`, **0 components**); a
> **hand-written `dtsPropsFor.DataTable`** (extraction emitted a dangling generic `T` —
> `columns: DataTableColumn<T>[]; rows: T[]` with neither `T` nor `DataTableColumn` defined, i.e. a
> broken contract); an isolated **84MB** `.ds-sync/` dep tree (pnpm's strict isolation won't expose
> `postcss` from `web/`); a `typescript@^5` pin (TypeScript **7** is the native port — its
> `exports["."]` maps to `./lib/version.cjs`, exposing only the version string, so
> `package-validate.mjs`'s `await import('typescript')` throws inside a `try` and prints the
> misleading *"typescript not in node_modules"*, silently skipping the only check validating the
> hand-written `dtsPropsFor`); a symlink; and a Tailwind pre-compile step (`globals.css` is *source*,
> not a stylesheet).
>
> **It reached only 3 of 13 components.** Its README classified **195** custom properties where the
> design system has **125** — the extra ~70 are Tailwind internals (`--tw-space-y-reverse` filed
> under "spacing"). It also asserted a fiction: *"This design system is the published vocky-web React
> library… all 13 components are the real upstream code"* — `vocky-web` is `private: true` and has
> never been published.
>
> This is v12's **app-first trap**, observed end to end. Every symptom the skill predicts occurred.
> **Do not retry `/design-sync` until a real design system exists in code.** The `web/package.json`
> `"types"` patch is part of the trap, not a fix: it declares a `private: true` Next.js app to be a
> typed library. It was reverted; **do not restore it.**

### v12 seed requirements this phase must meet

- **Frozen baseline render** — v12 requires *"a faithful export of the current design, plus a frozen
  baseline render of today's look (CSS inlined, runtime stripped) that survives token changes — the
  before/after reference at sign-off."* **"CSS inlined" does not mean resolving every `var()` to
  hex**: the compiled stylesheet carries its own `:root{--color-green:…}`, so inlining the stylesheet
  freezes the values. Only 6 files are `"use client"` and Next SSRs their initial HTML, so `curl` on a
  `pnpm build && pnpm start` server captures the real paint — no Playwright, no new deps. The one
  client-only visual (`Reveal`, `opacity:0` until IntersectionObserver) is **dead in shipped code**,
  so there is no fidelity gap. `vocky-smoke` (`src/vocky/smoke.py`) already does signup → project →
  mint key → post feedback → poll read — **the real-data seeder exists**; `make bootstrap` brings the
  stack up.
- **vocky is BOTH a redesign and a first-time.** The 6 shipped app surfaces are a **redesign** (they
  exist; freeze them). The foundation round is **first-time** (no vocky brand exists → inventory +
  product context + real data shapes + existing tokens/fonts + the labeled hi2vi REFERENCE). Say so
  in the brief.
- **The brief must declare locked vs. in-play** — v12: *"This is how you shape a design session
  without deciding anything."* "Zero brand decisions" is a rule for **Claude Code**; nothing yet tells
  **Claude Design** what it may move. Needs, with dated exceptions: landing copy **in play this pass
  only** (app copy in `src/content/` stays locked); brand spirit **in play** (vocky has none);
  component vocabulary **in play** (this is a bootstrapping pass); data contracts **locked by default
  but reopenable if the design requires it — name the cost, don't assume it**. Locked floors:
  `word-break: keep-all`, `--font-sans` stays Korean-capable, the a11y floor incl. `FieldError`'s
  `aria-live`.
- **`build-prompt.md` must be a hard line-item in the required-output manifest.** v12: *"the
  implementation contract — a round is incomplete without it."* **P9's entire decomposition rests on
  it**; without it P9 sizes work from vibes.
- **Operator attachments: vocky has none.** No logo, no wordmark — the app-shell brand is literally
  `text-[18px] tracking-[-0.3px]` text. A real gate input the brief must **ask about, not answer**.
- **Uploading a card does not make it appear.** The pane indexes from `_ds_manifest.json`, which
  **does not rebuild on upload** — regenerate it after the last card exists and `write_files` it back.
  `register_assets` is legacy; skip it. The current manifest lists **10** cards and its `note` field
  still says the gate is "P6"; `web/design/canvas/README.md` says P6 in 5 places. Both are source and
  a slice may fix them.

### Established at `P8.DECOMP` (2026-07-17) — new facts, not harvested

- **The frozen baseline lands at `web/design/baseline/`** — beside the canvas mirror vocky already uses,
  inside `web/` so the `localDir: web/` mapping and Connect GitHub both reach it. v12's canonical
  `docs/reference/design/baseline/` **does not fit vocky**: there is no `docs/reference/` tree, and
  `docs/` is the versioned durable-truth machinery (generated `current/` + `versions/`) — a frozen render
  is neither. The skill explicitly permits the living `design/canvas/**` mirror as the alternative record;
  this is that record's baseline half. **Repo-only — NOT pushed as canvas cards**: the canvas is for live,
  re-themable cards, the baseline is the frozen "before". Pushing it would hand Claude Design a second,
  stale copy of every surface.
- **`data-table` has no card but is the most-used primitive** — 4 of the 6 shipped surfaces render it,
  and `intent.md` names it in the component list. → `S2` adds it. (Today's canvas: 3 foundations +
  6 components + the fictional placeholder = 10 cards, none mirroring a real surface.)
- **Baseline fidelity trap for `S1` — fonts.** The app self-hosts fonts via `next/font/google`
  (`src/lib/fonts.ts`), so a curl'd page references `/_next/static/media/*.woff2` — URLs that **die with
  the server**. Inlining only the stylesheet leaves the "frozen" render in system fonts, silently. `S1`
  must resolve this: inline the faces (base64) **or** record the gap explicitly. **A type change is one
  of the gate's two real questions** (`--font-sans`, `--font-en`), so font fidelity in the "before" is
  load-bearing, not cosmetic.
- **The 6 surfaces are behind auth.** `S1`'s curl chain must POST login, keep the session cookie, and
  reuse it across every capture — an unauthenticated curl captures redirects, not surfaces. Real data
  already exists to render: `make smoke` / `src/vocky/smoke.py` does signup → project → mint key → post
  feedback → poll read, and `make bootstrap` (compose-up + migrate + wait-ready) brings the stack up.
  `web` has `build` + `start` (`next start -H 127.0.0.1 -p 3030`). **No new deps, no Playwright.**
- **`S6` carries the one authorized `git push`** — an explicit `S6` obligation, **not a standing
  permission** (v12's words). It publishes ~340 files / +38k lines to the **public**
  `github.com/leetusik/vocky` — `main` is **38 commits ahead** of `origin/main` — including all of
  `works/`: every phase notebook and every verbatim operator message. No secrets travel (verified at
  phase creation). `intent.md`: *"Worth one deliberate look before the gate slice runs."*
- **The `--depends-on` append trap is real and was avoided here** — verified at `scripts/workflow.py:1066`
  (`action="append"`). `P8.S5`'s three deps stored as a 3-element array and `validate` passed clean.

## Constraints

Durable for every slice in this phase. The first five are operator rulings (`intent.md` is the source
of truth).

1. **Zero brand decisions — the load-bearing constraint.** The agent's scope is canvas prep. Palette,
   type, the landing's value prop and copy are all concluded in the operator's Claude Design session,
   **by Claude Design asking the operator**. No slice may propose a palette, a type direction, or
   draft landing copy. **Never answer a design question — pose it back.** Cards ship at today's
   placeholder values with placeholder copy slots.
2. **The mechanism is v12's default: Seeded canvas + Connect GitHub.** The `DesignSync` **tool** for
   push/read-back. **The `/design-sync` skill is forbidden** — see the anti-finding.
3. **Canvas coverage = every shipped surface** — login/signup, app shell, dashboard, project detail,
   feedback list, feedback detail.
4. **hi2vi vibe reaches the session as a reference card, not a proposal** — one clearly-labeled
   `Reference — hi2vi vibe` card, **data, not a proposal**. The claude.ai project stays **vocky-only**
   otherwise.
5. **One session covers app + landing together** — foundations, components, app sections, landing
   sections.
6. **Ground in real content and real data shapes — never lorem.** A card with nothing real to mirror
   is invention: don't author it, ask for it. **Delete the fictional
   `sections/dashboard-placeholder.html`** rather than push it.
7. **Implementation is P9.** This phase closes at the signoff. **Do not touch P6** — P8+P9 absorb the
   landing design and build, leaving P6 deploy-only; the operator reconciles it at `P6.DECOMP`.
8. **Docs are versioned once, at `P8.REVIEW`.** Slices append "Doc impact" notes below; no slice runs
   `doc-new-version`.
9. **Keep tests terse** per the repo's small-tests rule.

## Doc impact

_Running list for `P8.REVIEW` to consolidate into doc versions. Append one line per durable-truth change._

- **Pre-recorded at the phase's re-creation:** `docs/current/` universally still calls the design gate
  "P6" — `frontend.md` (§`design/canvas/`, lines ~57 + 74, and line ~205), `decisions.md` (**D-P4-3**,
  lines 130–134), `experience.md`, `architecture.md`, `product.md`. **P8 supersedes D-P4-3** and,
  with P9, absorbs the landing design + build, leaving P6 deploy-only. `frontend.md` also documents
  the canvas structure and card count, which this phase's seed will change. `P8.REVIEW` must
  consolidate the *final* structure once, not track it per slice.

## Open Questions

_Phase-level questions the gate session must answer. Listed so the brief surfaces them; **no slice
answers them**._

- Palette, type direction, and how far to carry the hi2vi vibe (constraint 4).
- The landing's value prop and copy.
- Loading / error / 404 states — design them, or keep framework defaults?
- The hand-rolled primitives: add `Select`, a destructive `Button` variant, a `Chip`/`Tag`? Fold
  `LogoutButton` into `Button`?
- The five dead primitives + unused variants/tokens/type steps: adopt (the landing likely wants
  several), or drop?
- `Badge variant="archive"` means both Revoked and Disliked — split it?
- Does a signed-in visitor at `/` see the landing or get bounced to the dashboard?
- `TrendChart`: keep the inline SVG or adopt a chart library? (D-P4-3 deferred this to "the P6 gate"
  = this one.)
- Dark mode: still no, or yes?
- Should `/projects/[id]` mark a rail item current? (raised by `P4.REVIEW`)
- Token **renames** (vs. value swaps only) — worth the call-site churn?
- **`--font-en` has no vendored face** — every button renders in the visitor's system font. Vendor a
  face, or drop the token?
- **`--breakpoint-xs` has no consumer** — adopt `xs`, drop it, or tokenize the real 900px breakpoint?
- **The `on-primary` flip** — follows from the accent choice (a bright accent flips it dark; a
  saturated mid-tone keeps it white). Presented as a dependency, not an independent question.
- **Brand assets** — vocky has no logo or wordmark. What should the brand mark be?
