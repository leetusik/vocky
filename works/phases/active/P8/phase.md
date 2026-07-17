# Phase P8: Design Gate: Brand, App UI & Landing

_Intent: see [intent.md](intent.md)._

## Objective

Run the Claude Design gate for vocky's brand, the app UI and the landing: write the handoff, hold the operator's design session, read the design back, and land the signed-off design as an implementable spec. Implementation is P9.

## Context

P8 runs the **real Claude design gate** that P4 deliberately deferred (decision **D-P4-3**). P4.S1
shipped the design-system *mechanism* — the Tailwind v4 `@theme` block in `web/src/app/globals.css` and
the CVA primitives in `web/src/components/ui/` — at a knowingly **placeholder palette**, reusing
hi2vi_web's token *names* 1:1 so a later gate could swap values without touching call sites. **No vocky
brand exists yet.**

**This phase is the design only.** The apply half is **P9** (order 4.6), whose `DECOMP` cannot run
until this gate closes and sizes the work from the returned `build-prompt.md`. v13 prescribes that split
for a big design change, and it is what lets this phase close cleanly at signoff.

> **This phase has been re-shaped twice.** An earlier P8 ran under rules that did not exist yet and was
> fully reverted at `c9102e3`; the phase was re-created under **v12**, whose seeded-canvas mechanism
> **v13** then retired. Everything below marked *harvested* was measured by that reverted work (or by
> the `/design-sync` run it spawned) and is carried forward so no slice re-derives it. The originals are
> in git: `0007184`, `97ad6a8`, `0c794bb`, `301ab32`, `d20badf`.

**Live claude.ai target:** `1eaa0803-46e3-426a-ab04-17a802170234` — `vocky design system`,
`PROJECT_TYPE_DESIGN_SYSTEM` (verified). **Nothing was ever pushed to it.** **Target by id, never by
name** — a second project (`2d64ae63-…`) shares the name, is still returned by `list_projects`, and is
invisible in the operator's UI. Confirm the target against the operator's screen at the gate, not the
API.

## Decomposition

Cut by `P8.DECOMP` (2026-07-17). **Round 1 only — two middle slices.** Bare folders; each slice's
`plan.md` is written by the orchestrator at that slice's own turn.

| Slice | Name | Kind / Risk / Order | Depends on |
|---|---|---|---|
| `P8.S1` | Retire the `web/design/canvas/` mirror | `implementation` / `low` / 1 | — |
| `P8.S2` | Design gate round 1: brand, app UI & landing | `co-work` / `high` / 2 | `P8.S1` |

**`P8.S1` — constraint 8's cleanup.** Deletes the 13-file mirror (`tokens.css`, `_ds_manifest.json`,
9 component/foundation/section cards, `README.md`), which has no job under v13 and can only drift.
Verified inert: nothing in `web/src/`, `next.config.*`, `tsconfig.json`, or `postcss.config.*` imports
or globs it; git history keeps it. Rated **`low`** — a pure deletion plus one exactly-specified comment
edit, genuine `slice-executor-low` (sonnet) territory. Under flex mode `mid` and `high` are both
opus@xhigh, so `low` is this phase's **only real cost lever**. Its one dangling code reference is
`web/src/app/page.tsx:11` (*"The `design/canvas/` mirror remains the design-gate artifact."*); the same
comment block's line 6 (*"P6 replaces this with the public landing page"*) is now false — **P9** builds
the landing. Doc references to the canvas (`frontend.md`, `decisions.md`) are **not** S1's job: they are
pre-recorded in *Doc impact* for `P8.REVIEW` (constraint 10).

**`P8.S2` — the gate itself.** `co-work` / `high`, and **never dispatched** (v13's deliberate exception:
executors have no `DesignSync` tool, so the read-back is orchestrator-inline). Two commits bracket the
`pending` window; it ends at the landed design + SIGNOFF and **writes no implementation code** — that is
P9. Its shape, for the record (its `plan.md` gets written at its turn, not now):

```
write docs/reference/design/rounds/01-brand-app-landing/handoff.md
  → commit "feat(design): P8.S2 handoff — ..."
  → operator pushes + runs Connect GitHub   [the agent cannot push: settings.json denies Bash(git push:*)]
  → set-slice-status P8.S2 pending → STOP; the operator designs in Claude Design
  → operator clears pending → read back [DesignSync, orchestrator-inline] → concreteness check
  → land the design AS-IS into output/ + the spec into phase.md → write SIGNOFF.md
  → commit "feat(design): P8.S2 read-back — ..."
```

**Why S1 must land before S2 — load-bearing, not cosmetic.** S2 pushes the branch so Claude Design can
read current code via Connect GitHub. A stale placeholder-palette mirror sitting in the repo at push
time is exactly the drift hazard v13 names: it would read to the session as authoritative, competing
with the real `globals.css` tokens it contradicts. Delete first, then publish.

**Why seven slices collapse to two.** The reverted v12 decomposition (`d20badf`) cut **seven** middle
slices: seed → brief → gate → synthesis, where the seed alone split three ways (baseline render, DS
cards, six surface mirrors). **v13 retires that entire seeding arm** — Claude Design reads the real repo
itself, so Claude Code authors no cards, no canvas, no token mirror. Its one output is `handoff.md`.
Those seven collapse to **one** design slice; the only other round-1 work is constraint 8's cleanup.

**This is round 1 only — deliberately.** v13: *"you do not know what the operator will design."* The
read-back is **expected** to re-shape the phase. Round 2 — and any design-fidelity fix slice, which is
part of the normal shape, not a failure — gets cut at a **fractional order** (2.5, …) after the gate
closes, between `P8.S2`@2 and `P8.REVIEW`@9999. Creating more now would be guessing at a design that
does not exist yet.

The v13 loop this phase implements:

```
handoff.md → push → PENDING: the operator designs in Claude Design
  → read back [DesignSync, ORCHESTRATOR-inline] → concreteness check
  → land the design AS-IS → SIGNOFF → implement [P9]
```

> Three v13 rules bind the shape and must survive into that breakdown:
>
> - **The design slice is `--kind co-work --risk high` and is NEVER dispatched** — a deliberate
>   exception to the contract's "every slice is delegated", because executors have no `DesignSync`
>   tool, so the read-back is orchestrator-inline. Two commits (`feat(design): <slice> handoff — …`
>   then `feat(design): <slice> read-back — …`), with the `pending` window between them. Never rate a
>   design slice `low`.
> - **A design slice never writes implementation code.** It ends at the landed design + SIGNOFF.
>   Landing the design is not implementing it — it is what makes P9 easy.
> - **Do not over-plan before the gate** — *"you do not know what the operator will design."* Create
>   round 1 only. Expect the read-back to re-shape the phase; cut round 2 at a fractional order
>   afterward. A design-fidelity fix slice is part of the normal shape, not a failure.

**The design record** lives at `docs/reference/design/` — **it does not exist yet and this phase creates
it.** Durable and outside `works/` on purpose: P8 archives before P9 runs.

```
docs/reference/design/
├── rounds/<NN>-<slug>/
│   ├── handoff.md          # OUT — we write it
│   └── output/             # IN — Claude Design returns it; READ-ONLY
│       ├── result.md       #   what was designed; every departure logged
│       └── build-prompt.md #   the implementation contract
└── SIGNOFF.md
```

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

### `P8.S2` — GATE CLOSED: round 01 landed. The spec P9 builds from.

The design gate is closed. The design record is durable at **`docs/reference/design/`**, outside `works/`
so it survives P8's archive:

- **`docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md`** — **the implementation
  contract. P9 decomposes and sizes every slice from this file.** Exact token values (all 41 colors, 14
  type steps, radii, spacing, breakpoints), component APIs with class strings, per-surface changes, a
  per-file change manifest (§8), and a DoD (§10). It opens with a **RESPECT THE DESIGN** block that must go
  into every P9 slice plan and executor prompt.
- **`output/result.md`** — decisions & rationale; answers every open question; logs 10 departures.
- **`docs/reference/design/SIGNOFF.md`** — authorization, supersessions, token delta.
- Both files landed **verbatim and read-only**. The 30-card set + `tokens.css` **stay in the design
  project** (project `1eaa0803-…`) and are deliberately **not** copied down — `build-prompt.md` is the
  complete on-disk source of truth, which matters because **P9's executors have no DesignSync**.

**The design at a glance** (authoritative detail is in `build-prompt.md`, do not re-derive here):

- **Brand:** "a quiet instrument for hearing your users." One deep-emerald green (`--color-green #0C7A52`,
  a **real value swap** off the indigo placeholder — names unchanged, so the swap re-themes every surface),
  on a green-cool neutral ramp. Light-only (no dark mode). Compact, data-dense. Pretendard + JetBrains Mono.
- **Every open question resolved:** on-primary stays white (AA-checked); `--breakpoint-xs` dropped for a
  real `--breakpoint-app` (900px); Select / Chip / destructive Button added; Badge `archive` split into
  rating + status; TrendChart → dependency-free area chart; loading/error/404 designed; the pricing-vs-free
  contradiction resolved as "Free now, paid later"; brand mark = three rising bars (a capture-volume
  waveform).
- **Net-new surfaces:** the public landing reclaiming `/` (the largest new build) and the four
  loading/error/not-found/global-error states.
- **Backend: no change required** (`build-prompt.md` §9) — everything maps to existing serializers. The one
  named non-trivial build cost is **Pretendard vendoring** (not on Google Fonts → `next/font/local`).
- **All nine locked floors honored**, including the five security ones (identical login error,
  404-never-403, show-once key warning, download-only attachments, UTC labels).

**Apply-time nits for P9 (catalogued, not blockers — the record is read-only so these were NOT edited into it):**

- Both returned files still name the two monolith HTMLs as "visual source of truth". Those were superseded
  by the card set and deleted from the project; **the card set is the visual source of truth now.**
- `result.md` §9 lists P9 apply-time to-dos: pick the Pretendard vendoring mechanism; the optional
  token-rename pass (costed, deferred); the waveform mark can seed the favicon/OG image (a P6 concern); the
  "coming later" pricing card's disabled control needs no backend unless a waitlist is ever wanted.

**Doc impact (for `P8.REVIEW` to consolidate — see the Doc impact section):** the design gate closed;
`decisions.md` should record round 01's resolutions as a decision (superseding D-P4-3), and `frontend.md`
/ `experience.md` now have a concrete target palette, type, component set, landing, and state design to
reference. No doc is versioned by this slice (constraint 10).

### `P8.S2` — the workspace moved to v14 mid-slice: the session must return a card set

**Constraint 2 below is now partly stale — read this first.** It says the mechanism is v13's and that
"we author no cards, no canvas, no token mirror". The **mirror ban on Claude Code is unchanged and
unweakened** — we still author no canvas, no cards, and no `tokens.css` of our own. What changed is the
**required-output manifest**: under **v14** the design session must return **a card set** alongside
`result.md` and `build-prompt.md`. **Markdown alone is not a round.** Requiring a card is not drawing
one — we say what must be reviewable; Claude Design decides what it looks like and authors `tokens.css`,
because the palette *is* the design.

**Why v14 exists — and it is this phase's own failure.** v13 retired the line-1 `@dsCard` contract *as
part of* retiring the mirror, reasoning that Connect GitHub makes mirroring unnecessary. That holds for
**input**. But the manifest was never only input: it is also **the render index for the Design System
pane**, and Connect GitHub does not populate that pane. So the card medium died with the mirror.

**What round 01 actually returned.** The design succeeded; the visibility failed. `output/result.md` and
`output/build-prompt.md` are complete and authoritative — but the round came back as **two monolithic
HTMLs** (`Vocky Round 01 - Design System.html`, `Vocky Round 01 - Landing.html`) with **no line-1
markers**, so **no `_ds_manifest.json` was ever compiled** and the operator's pane was empty. A complete
`build-prompt.md` they could not see, review, or fix. Root cause is ours: `handoff.md` §10 told Claude
Design "no cards" and §8 required only the two markdown files. The session delivered exactly what was
asked.

**The fix is v14's prescribed migration, not a redesign** — *"a round already handed off under v13 comes
back with no cards — it is not lost, just invisible. Re-hand-off for the card set against the existing
`result.md`/`build-prompt.md`."* That is `handoff-02-cards.md`: a **visibility pass** that decides nothing
new, keeps the two markdown files unedited and authoritative, and supersedes the monoliths so there is no
second source of truth.

**Two rules that bind the read-back when it eventually runs:**

- **`list_files` first.** No `_ds_manifest.json`, an empty `cards[]`, or a monolith → **`needs_operator`**
  with the card contract restated. It is explicitly **not** fixable by editing the artifacts, writing the
  cards ourselves, or hand-compiling the manifest — **`register_assets` and the write path stay closed.**
- **The cards stay in the design project — never copy them down.** The pane is their home and the operator
  keeps working in it; a local copy is a mirror again. **This is why `build-prompt.md` must be complete:**
  P9's implement slices are dispatched to executors with **no DesignSync**, so what we land is the whole
  source of truth they get. If the cards seem needed on disk to make a slice buildable, the real problem
  is that `build-prompt.md` is short — say so at read-back.

### `P8.S1` — two dangling references to `web/design/canvas/`, not one

The Decomposition section above recorded only one dangling code reference —
`web/src/app/page.tsx:11`. There was a second: **`web/.prettierignore:8-9`**, a comment
+ rule block (`# Design canvas artifacts — standalone HTML specimens, not in Prettier's
domain` / `design/`) whose only purpose was ignoring this tree. Both earlier sweeps
missed it for the same two reasons: it reads `design/`, not `design/canvas` (the string
every earlier grep searched for), and `.prettierignore` has no source extension, so a
`--include="*.ts,*.tsx,*.css,*.json"`-style grep never touches it. **Transferable lesson
for future dead-tree retirements:** also grep dotfiles/ignore files by bare directory
name, not just the fuller path used in code comments — an ignore rule degrades silently
(no build break, no lint error) when its target vanishes, so nothing forces it to
surface on its own.

Both references are now removed: `page.tsx`'s header comment dropped the canvas
sentence and corrected `P6` → `P9` (P8+P9 absorb the landing; P6 goes deploy-only per
`intent.md`), and `.prettierignore` dropped the dead `design/` block, ending the file at
`node_modules/`. `web/design/` (13 tracked files) is `git rm -r`'d and staged, not yet
committed — the orchestrator commits.

`pnpm format:check` fails in this tree independent of this slice — 20 pre-existing files
(`web/README.md`, `web/src/lib/env.ts`, several `web/tests/*.test.ts`, etc.) are already
unformatted; confirmed via `git diff`/`git status` that none of those files were touched
by this slice. Neither `page.tsx` nor `.prettierignore` appear in the warning list, which
is what this slice's edits are responsible for. Out of scope here; left as-is.

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
- **8 palette collision groups** — distinct token names holding identical values, so they render as
  duplicates wherever the palette is shown: `ink` == `canvas-dark` · `forest` == `charcoal` ·
  `forest-mid` == `slate` == `hairline-dark` · `surface-soft` == `hairline-soft` == `archive-cream` ==
  `surface-band` · `trust-sage` == `hairline-strong` == `on-dark-muted` · `archive-olive` == `muted` ·
  `surface-green` == `surface-security`.
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
  default 404. **These are net-new design, not documentation — the handoff asks for them, it does not
  describe them.**
- **`TrendChart`** is ~140 lines of dependency-free inline SVG. D-P4-3 records "a real chart library
  is a P6 design-gate question" — i.e. **this gate's**.
- **The landing must reclaim `/`.** `web/src/app/page.tsx` is a pure redirect today; its own comment
  states the intended pattern: the landing takes `/` and *"this bounce moves behind the landing's
  CTA."*
- **`h1–h6 { word-break: keep-all }`** is Korean line-breaking and **must survive any type change**.
- **Fonts self-host.** The app uses `next/font/google` (`src/lib/fonts.ts`: Noto Sans KR + JetBrains
  Mono, chosen because feedback content is Korean). `--font-en` is a bare system stack kept only
  because `Button` uses `font-en`. A type change lands in `globals.css` **and** `src/lib/fonts.ts`.
- **Token renames cost call-site churn.** Names were kept hi2vi-identical *so the gate swaps values
  only*. A rename is possible but not free — a read-back decision, not a default.
- **Usage is not a separate surface.** `StatTiles` + `TrendChart` are consumed by `dashboard/page.tsx`
  and `projects/[projectId]/page.tsx` only — so the intent's "usage" is covered inside those two
  surfaces, not as a seventh one.
- **From `P4.REVIEW`:** on `/projects/[id]` **no rail item is marked current** (projects aren't a rail
  item) — flagged there as "worth a deliberate call when the rail grows."
- **Copy is data** (`src/content/`). Ground the handoff in the **exact shipped strings** — v13:
  *"Ground in real content — never lorem."*
- **`--depends-on` is `action="append"`** — repeat the flag per dep. A comma-separated string is
  stored as one literal dep and fails `validate` with `missing dependency`. (Found the hard way at the
  first `P8.DECOMP`.)

### Harvested from the reverted `/design-sync` run — machine-measured, mechanism wrong, facts real

- **Utilities compile to `var(--color-*)` references, not baked hex** — verified in the compiled
  bundle, not inferred: `.bg-green { background-color: var(--color-green); }`, and the tokens ride in
  the same file. **So a token value change rethemes every component.** This is the property the whole
  design gate depends on: the instant the gate swaps `--color-green`, every live artifact re-themes.
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
  reserves space and stays in the tree for `aria-live`. **An a11y floor for the handoff's "locked" list.**
- **`web/src/lib/utils.ts` (`cn()`) is clean of `server-only`**; `lib/env`, `lib/session`, `lib/bff`,
  `lib/auth-guards`, `lib/vocky/*` are not.
- **`web/src/components/usage/` and `web/src/components/app-shell/` are app components, not the design
  system** — outside `src/components/ui`.
- **Playwright 1.61.1 + chromium 1228 are cached at `~/Library/Caches/ms-playwright`** on macOS, *not*
  `~/.cache/ms-playwright`. Outside the repo — survived the revert. Check the Library path before any
  tool re-downloads ~200MB.

### What the handoff must carry

- **vocky is both a redesign and a first-time.** The 6 shipped app surfaces already exist — Claude
  Design reads them in the repo. The foundation is **first-time**: no vocky brand exists, so the handoff
  carries product context, real data shapes, the existing tokens/fonts, and the labeled hi2vi
  REFERENCE. Say so in the handoff.
- **The handoff must declare locked vs. in-play** — v13: *"This is how you shape a design session
  without deciding anything."* "Zero brand decisions" is a rule for **Claude Code**; nothing else tells
  **Claude Design** what it may move. Needs, with dated exceptions: landing copy **in play this pass
  only** (app copy in `src/content/` stays locked); brand spirit **in play** (vocky has none);
  component vocabulary **in play** (this is a bootstrapping pass); data contracts **locked by default
  but reopenable if the design requires it — name the cost, don't assume it**. Locked floors:
  `word-break: keep-all`, `--font-sans` stays Korean-capable, the a11y floor incl. `FieldError`'s
  `aria-live`.
- **The required-output manifest is strict, and always names both `result.md` and `build-prompt.md`.**
  v13: `build-prompt.md` is *"the implementation contract — a round is incomplete without it"*, and
  `result.md` logs what was designed and every departure. **P9's entire decomposition rests on
  `build-prompt.md`**; without it P9 sizes work from vibes.
- **Operator attachments: vocky has none.** No logo, no wordmark — the app-shell brand is literally
  `text-[18px] tracking-[-0.3px]` text. A real gate input the handoff must **ask about, not answer**.
- **Where to look** — real paths, real data shapes, drawn from the harvested facts above. Nothing real
  to point at → **ask for it; do not invent it.**

## Constraints

Durable for every slice in this phase. The first five are operator rulings (`intent.md` is the source
of truth).

1. **Zero brand decisions — the load-bearing constraint.** The agent's scope is the handoff. Palette,
   type, the landing's value prop and copy are all concluded in the operator's Claude Design session,
   **by Claude Design asking the operator**. No slice may propose a palette, a type direction, or
   draft landing copy. **Never answer a design question — pose it back.**
2. **The mechanism is v13's: handoff → STOP → read back → land as-is → implement (in P9).** Claude
   Design reads the real repo via **Connect GitHub**; we author **no cards, no canvas, no token
   mirror**. `DesignSync` is **read-back only** and **main-thread only**.
3. **Scope checklist = every shipped surface** — login/signup, app shell, dashboard, project detail,
   feedback list, feedback detail — plus the landing (hero, features, pricing, footer), foundations,
   and components.
4. **hi2vi vibe reaches the session as a clearly labeled `REFERENCE` section in the handoff, not a
   proposal** — **data, not a proposal**. The claude.ai project stays **vocky-only** otherwise.
5. **One session covers app + landing together** — foundations, components, app sections, landing
   sections.
6. **Ground in real content and real data shapes — never lorem.** Nothing real to point at is not an
   invitation to invent: ask for it.
7. **Implementation is P9.** This phase closes at the signoff. **Do not touch P6** — P8+P9 absorb the
   landing design and build, leaving P6 deploy-only; the operator reconciles it at `P6.DECOMP`.
8. **Retire `web/design/canvas/`.** The 13-file mirror (`tokens.css`, `_ds_manifest.json`, 10 cards,
   `README.md`) has no job under v13 and can only drift. A slice deletes it; it is inert today (nothing
   in the app or the build imports it) and git history keeps it.
9. **Never run `/design-sync`.** v13: it is a repo→component-bundle compiler, *"a different thing, and
   is not this workflow."* It was run here off-book, walked into the app-first trap, and reached only
   3 of 13 components before being reverted. The full measured post-mortem is in git —
   `git show c9102e3^:works/phases/active/P8/phase.md` → *The anti-finding*. **Do not retry it**, and
   do not restore the `web/package.json` `"types"` patch it required: that patch declares a
   `private: true` Next.js app to be a typed library, and is part of the trap, not a fix.
10. **Docs are versioned once, at `P8.REVIEW`.** Slices append "Doc impact" notes below; no slice runs
    `doc-new-version`.
11. **Keep tests terse** per the repo's small-tests rule.

## Doc impact

_Running list for `P8.REVIEW` to consolidate into doc versions. Append one line per durable-truth change._

- **Pre-recorded at the phase's re-creation:** `docs/current/` universally still calls the design gate
  "P6" — `frontend.md` (§`design/canvas/`, lines ~57 + 74, and line ~205), `decisions.md` (**D-P4-3**,
  lines 130–134), `experience.md`, `architecture.md`, `product.md`. **P8 supersedes D-P4-3** and,
  with P9, absorbs the landing design + build, leaving P6 deploy-only.
- **Pre-recorded at the v13 revision:** `frontend.md` documents the `design/canvas/` structure and card
  count. Constraint 8 **deletes that tree**, so `P8.REVIEW` must re-version `frontend.md` to drop the
  canvas section — consolidating the *final* state once, not tracking it per slice.
- **From `P8.S2` (gate close):** the design gate is closed and the durable record lives at
  `docs/reference/design/` (round 01 `output/` + `SIGNOFF.md`). `decisions.md` should record round 01's
  brand/UX resolutions as a decision that **supersedes D-P4-3**; `frontend.md` and `experience.md` now
  have a concrete target (deep-emerald palette with names-kept value swap, Pretendard, compact density,
  the new component vocabulary, the `/` landing, and the loading/error/404 states). The design specifies
  **no backend/data change**. `P8.REVIEW` consolidates these; no doc is versioned by an implementation or
  co-work slice (constraint 10).

## Open Questions

_Phase-level questions the gate session must answer. Listed so the handoff surfaces them; **no slice
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
