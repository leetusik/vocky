# P11.S8 result — `AgentQuickstart` section + `page.tsx` insertion

## What landed

- **`web/src/components/landing/agent-quickstart.tsx`** (new) — the whole surface: header
  (dotted-pill eyebrow + `h2` + lede), four numbered steps (`install` / `env` / `verify` /
  `capture`, each a different shape per `LANDING.quickstart.steps`), the peer row linking to
  `#skill`, and the sticky contract aside (two cards). Server component; the only client
  islands are the four `Snippet` copy buttons it composes.
- **`web/src/app/page.tsx`** — `<AgentQuickstart />` inserted between `<HowItWorks />` and
  `<Showcase />` (position 4), plus a two-line comment noting the insertion and that
  `SkillSection` (position 5) is S9's job.
- **`web/src/components/landing/index.ts`** — `export { AgentQuickstart } from "./agent-quickstart"`
  added after `HowItWorks`, with a `// P11.S8 — …` comment line, matching `ui/index.ts`'s style.
- **`web/tests/agent-quickstart-ssr.test.ts`** (new, permanent) — a terse `renderToStaticMarkup`
  suite (same technique as S6's `snippet-ssr.test.ts`) asserting: no `<button` anywhere in the
  section's server HTML (the no-JS floor held across all four snippets at once, not just one in
  isolation); every step's command still ships as selectable text (checked via safe,
  quote-free substrings — full strings for the install command, `VOCKY_API_TOKEN` /
  `%{http_code}` / `acme-web` for the others, since the block-command lines get HTML-entity-escaped
  quotes and the env block's comment line is wrapped in its own `<span>`); and the section
  renders `id="quickstart"` with the peer row's `href="#skill"`.

Wrote no new copy anywhere — every string comes from `LANDING.quickstart` (spread/reference
only); `LANDING.snippet` supplies the four shared button labels.

## How the four corrections were applied

1. **Correction 3 — the `.note` treatment, built inline.** No `Note` primitive exists or was
   created; it's a single `<div className="border-l-2 border-green pl-3 text-body-sm text-steel …">`
   inside step 2's content block, reusing `Trap`'s own inline-`<code>` descendant-utility recipe
   (`[&_code]:rounded-xs [&_code]:bg-[rgba(14,26,22,0.055)] [&_code]:px-[5px] [&_code]:py-px
   [&_code]:font-mono [&_code]:text-[12.5px]`, hoisted into a shared `INLINE_CODE_CLASS` constant)
   so the page's two "rich string" treatments read as one system. Order in the JSX is
   Snippet → note → Trap, matching "note before trap."
2. **Correction 4 — hero's dotted eyebrow, not `how-it-works.tsx`'s.** The header eyebrow is a
   byte-for-byte copy of `hero.tsx`'s `bg-green-soft` pill + `size-1.5 bg-green` dot markup.
   `how-it-works.tsx` was not touched.
3. **Correction 5 — the 34px ink circle, not the shipped 36px numeral.** `StepMarker` renders
   `size-[34px] rounded-full bg-ink text-on-dark font-mono text-[15px] font-bold` — the explicit
   values §5.1 gives — never the actually-shipped `size-9 bg-green-soft text-green-dark` numeral
   `how-it-works.tsx` uses. Neither file was restyled to match the other.
4. **The two content floors held verbatim, unrelabelled, unreordered:** `400`'s reading renders
   first in `readings[]` (as authored in `landing.ts`) with the green-soft/green-dark tone, and
   `401`'s reading renders with no additional copy beyond `LANDING.quickstart.steps.verify.readings[1].body`
   — no retry advice was added anywhere near it.

## The inline-code helper

`withInlineCode(text, code)` — sorts `code` longest-first, builds one alternation regex (each
token regex-escaped), splits the sentence on it, and maps matched segments to plain `<code>{part}</code>`
(no className on the `<code>` itself — the *container* supplies the `[&_code]:…` descendant
styling, mirroring how `Trap` already treats its own children). Used for `steps.env.note.text`
and `steps.env.trap.body.text`. Verified by hand that `~/.zshenv`, `.env`, and `exec` each occur
as intended in the note (`.env` does not accidentally match inside `~/.zshenv`, since it requires
a literal `.` immediately followed by `env` — `~/.zshenv`'s only `.` is followed by `zshenv`, not
`env`), and the trap's four tokens (`workspace-write`, `network_access = true`,
`[sandbox_workspace_write]`, `~/.codex/config.toml`) are non-overlapping substrings of its body.

## `ReadingList`, built inline (§3.3)

One consumer (step 3's verify), not promoted to a `ui/` primitive. Rows are `<li>`s inside a
`divide-y divide-hairline-soft` list (`py-[11px]`, `text-[13.5px] leading-[1.55] text-slate`). The
status chip always renders the literal `reading.code` regardless of colour — the a11y floor from
the plan — coloured green-soft/green-dark for `"400"`, surface-danger/danger-deep for `"401"`, and
falling through to surface-caution/caution-deep for anything else (here, the literal `"else"`
value `landing.ts` itself uses for the third reading — copy is final, so this file renders it
as-is rather than second-guessing it). The (optional) `verdict` renders `font-semibold` ahead of
`body` when present; the third reading's `verdict` is `""` in the copy, so nothing renders before
its body — matches the design's own asymmetry.

## Deviations from `plan.md` (both are corrections toward the primary source-of-truth, not
departures from design intent)

1. **Reading-list chip radius: `rounded-sm` (6px), not the plan's literal `rounded-md`.**
   `plan.md` names the Tailwind class `rounded-md` directly, but the source-of-truth
   `build-prompt.md` §3.3 gives the raw value `border-radius:6px`. This repo's token scale
   (`globals.css`) redefines `--radius-sm: 6px` / `--radius-md: 8px` — different from stock
   Tailwind's own `md` (6px) — so `rounded-md` here would land at 8px, one step off the spec's
   explicit 6px. Per this same plan's own correction 5 ("the explicit values are normative, its
   descriptive label is not"), I followed the explicit pixel value over the class-name shorthand
   and used `rounded-sm`. `px-2 py-[3px]` (both sources agree) and `min-w-[52px]` are unchanged.
2. **Reading-list chip text: `text-[12px] font-bold`, not the `text-caption` token.** `text-caption`
   bundles `font-weight: 500` (see `globals.css` / `lib/utils.ts`'s own comment about this
   composite-token family), which would fight an added `font-bold` (700) for the same CSS
   property with no guaranteed winner in the compiled cascade. Using the arbitrary `text-[12px]`
   size alongside `font-bold` avoids the ambiguity entirely and still lands on the spec's exact
   "mono 12px/700."
3. **Section padding left at `Section`'s own defaults (`py-section md:py-section-lg`), not a
   custom `84px 28px` override.** No token in `globals.css` lands on 84px, and every other
   `Section`-based landing component (`HowItWorks`, `Showcase`, `Features`, `Pricing`,
   `ClosingCTA`) already ships with `Section`'s baked-in padding rather than a per-section
   pixel-exact override, despite round 01's build-prompt almost certainly giving equally exact
   numbers for those too. I followed that established, page-wide precedent rather than
   introducing the first per-section padding override on the landing. `container` (1180px) is
   unaffected — `Section`'s own container already lands exactly on `max-w-page`, confirmed before
   writing any code, so no second container was added (per the plan's own prompt to check this).
4. A handful of unspecified spacing values were judgment calls, all minor and all reversible if
   S10's fidelity pass disagrees: `mt-2` between a step's title and sub (matches `Features`'/
   `HowItWorks`' own h3→p precedent), `mt-3.5`/`space-y-3` inside each step's content block, `gap-4`
   between the aside's two cards, and `mt-3`/`mt-4` inside the header and Card A. None of these
   touch a value the build-prompt states explicitly.

Nothing else in the plan was skipped or altered. `Snippet`, `Trap`, `Card`, `Chip`, `Section` are
consumed unmodified; no `Note` or `ReadingList` `ui/` primitive was created; no `SkillSection`/
`SkillPreview` code or stub was added; `how-it-works.tsx`, `globals.css`, and the footer are
untouched; no backend change; no `doc-new-version` run.

## Validation — verbatim

1. **`pnpm typecheck`** — exit 0, no output.
2. **`pnpm lint`** — exit 0, no output (no `react-hooks/set-state-in-effect` risk: this section
   holds no client state at all — a server component composing client `Snippet`/`Trap` islands).
3. **`pnpm test`** — `Test Files 9 passed (9)` / `Tests 73 passed (73)` — the pre-existing 70 plus
   the 3 new `agent-quickstart-ssr.test.ts` cases. No regressions.
4. **`pnpm build`** — succeeded (`✓ Compiled successfully`, `✓ Generating static pages (13/13)`).
   Route table shows `ƒ /` — dynamic, as expected since P9.S6 (cookie read in `page.tsx`), not a
   regression.
5. **Zero literal copy** —
   `grep -nE '"[A-Za-z][A-Za-z ,.\x27—]{12,}"' web/src/components/landing/agent-quickstart.tsx`
   → initially found one false positive inside a doc-comment (`"fifth step row"`, a quoted phrase
   in prose, not a rendered string); reworded the comment to drop the quote marks and re-ran →
   **zero matches**. Every rendered string in the file comes from `LANDING.quickstart` /
   `LANDING.snippet` by reference.
6. **`grep -rn "style={{" web/src/components/landing/agent-quickstart.tsx`** → no matches.
7. **`grep -rn 'role="alert"\|aria-live="assertive"' web/src/components/landing/agent-quickstart.tsx`**
   → no matches.
8. **No copy button in the server HTML** — `web/tests/agent-quickstart-ssr.test.ts` (new,
   permanent; see above) — 3 assertions, all passing, covering all four snippets in one pass
   rather than one at a time.
9. **`#quickstart` resolves** — confirmed two ways: the SSR test asserts `id="quickstart"` appears
   in the rendered HTML, and `web/src/content/landing.ts:53` still reads
   `{ label: "Get started", href: `#${SECTION_IDS.quickstart}` }` (landed at S7, unchanged here) —
   so the nav link and the section id agree.
10. **`python3 scripts/workflow.py validate`** → `Workflow validation passed.`

**Extra confirmation beyond the plan's list** (following S6/S7's precedent of checking that
Tailwind actually compiled arbitrary/variant classes rather than silently dropping them): grepped
the built `.next/static/chunks/*.css` after `pnpm build` and found, compiled correctly:
`.app\:grid-cols-\[minmax(0,1.15fr)_minmax(0,0.85fr)\]{grid-template-columns:minmax(0,1.15fr) minmax(0,0.85fr)}`
and `.app\:sticky{position:sticky}` / `.app\:top-6{top:…}` all three nested under
`@media (min-width:56.25rem)` (900px) — the two-column grid and the sticky aside only ever apply
at `>=900px`, matching the narrow-viewport spec. Also confirmed: `.min-w-\[52px\]{min-width:52px}`, `.size-\[34px\]{width:34px;height:34px}`,
`.pb-\[34px\]{padding-bottom:34px}`, `.max-w-\[70ch\]{max-width:70ch}`, `.max-w-\[62ch\]{max-width:62ch}`,
and the `surface-danger`/`danger-deep` reading-chip colours. Nothing was silently dropped.

## Not test-covered (S10's fidelity pass owns these, same standing list S6/S7 already flagged)

- The 2000ms copy-revert timer, the `Range`+`Selection` failure-path selection, the persisting
  failure state, and the live-region announcement text — all inside `Snippet`, already exercised
  structurally by S6, not re-tested per-consumer here.
- Everything below the `app:` (900px) breakpoint: the single-column stack, the aside losing
  `sticky` and falling below the steps, and whether `app:top-6`/`app:sticky` actually produce the
  intended visual result in a real browser (only confirmed here that the CSS rules compiled with
  the right media-query nesting, not that a real narrow viewport renders as intended).
  `prefers-reduced-motion` and focus-ring behaviour for the two new copy buttons and the peer
  link (both already global per `phase.md`'s DECOMP2 correction 9 — no new CSS needed, but not
  re-verified in a browser here).
- The `#skill` anchor is a **transient dead link** until S9 lands (by design, per the plan and
  `phase.md`) — clicking "the skill" today scrolls to nothing. Acceptance check 7 (both anchors
  scroll) is S10's to prove once S9 exists.
- No live-origin check of any kind — the site is not deployed until P12, as every P11 slice's
  `result.md` states.

## For S9 / S10 to mirror or build on

- `AgentQuickstart` is a plain named function export, server component, zero props. `SkillSection`
  should follow the same shape (no props, pulls its own copy from `LANDING.skill`).
- The `withInlineCode(text, code)` helper (module-private to this file) is exactly what `S9`'s
  `skill.lede` (`{ text, code[] }`) needs too. It is **not exported** — if S9 wants it, either
  duplicate the ~12 lines (cheapest, matches this phase's "one consumer, build inline" pattern) or
  promote it to a shared `lib/` helper; I did not promote it since this slice has exactly one
  consumer and the plan's boundaries say nothing about a shared module. Worth a one-line note at
  S9's plan time.
- `INLINE_CODE_CLASS` (the note/trap inline-`<code>` recipe) is likewise file-private; if S9's
  `skill.lede` renders inline code outside of `Trap`, it will need the same descendant-utility
  string (or its own copy of it).
- The reading-list radius correction (`rounded-sm`, not `rounded-md`) is a repo-wide token-scale
  fact, not specific to this component — worth remembering if S9 or S10 encounters another
  "6px" spec value.
- `useIsHydrated()` was not imported directly here — `Snippet` already gates its own button on it,
  so this file needed no client state of any kind (confirmed by `pnpm lint` passing cleanly, per
  S6's flagged `react-hooks/set-state-in-effect` risk).
