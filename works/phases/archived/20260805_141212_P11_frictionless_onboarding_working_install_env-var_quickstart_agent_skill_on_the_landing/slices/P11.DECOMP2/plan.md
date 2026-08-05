# P11.DECOMP2 — decompose the build from the landed design

## Why this slice exists

P11 both designs and builds, so it decomposed in **two passes**. The first `DECOMP` could not cut the build
slices — the design decides what gets built, and features appear and disappear at the gate. The gate is now
closed: round 02 landed on 2026-07-29 with a **token delta of `None`** and **no backend change**. This slice
cuts the build slices from the landed spec.

**Read these two before anything else** — they are the contract, and they are self-sufficient by design
because the build executors have no `DesignSync` and the card set stays in the design project:

- `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` — the implementation contract:
  exact values, final copy strings, a normative state table, breakpoints, the no-JS floor, an a11y floor,
  a per-file change manifest (§10), and seven acceptance checks (§11).
- `docs/reference/design/rounds/02-onboarding/output/result.md` — the decisions and their reasoning.

Also read `works/phases/active/P11/phase.md`'s **"S5 done"** section, which summarizes the spec, and
`intent.md` if intent is ever unclear.

## The rule that governs every slice you cut

**RESPECT THE DESIGN.** Ship every designed element as designed — layout, density, hierarchy, tokens,
states, no-JS behaviour. **Do not drop, simplify, restyle, or "improve" a designed element to save effort**
— that is a correctness failure, not a shortcut. Where an exact value is unspecified, pick the option
closest to the designed intent, **never a plainer fallback**.

Record this in `phase.md` as a standing instruction, and note that it must appear in **every build slice's
`plan.md` and in every executor dispatch prompt**. That is the `design-cowork` requirement, and it exists
because a spec this precise is easy to quietly round off.

## The cut

Five build slices, at orders after this one. **Backing work first, the design implementation after, the
fidelity pass last** — here "backing work" is the shared primitives and copy, since the design implies no
backend at all.

| Slice | Order | Kind | Risk | Depends on | Name |
|---|---|---|---|---|---|
| `P11.S6` | 7 | implementation | medium | — | Primitives + copy: `Snippet`, `Trap`, the pure copy helper, `section-ids`, all `landing.ts` blocks |
| `P11.S7` | 8 | implementation | medium | `P11.S6` | Hero install row + the one new nav link |
| `P11.S8` | 9 | implementation | medium | `P11.S6` | `AgentQuickstart` section + its `page.tsx` insertion |
| `P11.S9` | 10 | implementation | medium | `P11.S6` | `SkillSection` + `SkillPreview` (server read of the served file) + its `page.tsx` insertion |
| `P11.S10` | 11 | implementation | medium | `P11.S9` | Design-fidelity pass: the seven acceptance checks, no-JS, a11y and reduced-motion floors |

```sh
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S6 \
  --name "Primitives + copy: Snippet, Trap, pure copy helper, section-ids, landing.ts blocks" \
  --kind implementation --risk medium --order 7
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S7 \
  --name "Hero install row + the one new nav link" \
  --kind implementation --risk medium --order 8 --depends-on P11.S6
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S8 \
  --name "AgentQuickstart section + page.tsx insertion" \
  --kind implementation --risk medium --order 9 --depends-on P11.S6
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S9 \
  --name "SkillSection + SkillPreview server read + page.tsx insertion" \
  --kind implementation --risk medium --order 10 --depends-on P11.S6
python3 scripts/workflow.py new-slice --phase P11 --slice P11.S10 \
  --name "Design-fidelity pass: acceptance checks, no-JS, a11y and reduced-motion floors" \
  --kind implementation --risk medium --order 11 --depends-on P11.S9
```

**Bare folders only** — never pre-fill any `plan.md`. Verify each new folder holds only `slice.json`.

### Why this cut

- **S6 is the spine.** `Snippet` is used by the hero row and by three of the quickstart's four steps;
  `Trap` and the copy mechanics are shared. Building them once, first, is what keeps S7–S9 from each
  inventing their own. It also carries all the copy, because the house rule is copy-as-data: `landing.ts`
  holds every string and the components hold none, so the copy blocks are a single coherent unit rather
  than three fragments. `section-ids.ts` goes here too — `SectionId` is typed, so **S8 and S9 cannot
  compile without their entries existing first**.
- **S7 is separated from S8/S9 because it touches shipped, above-the-fold code.** The hero's grid contents
  must not change — the corrected payload in particular. A small slice with a narrow blast radius is the
  right shape for that, even though the work is short.
- **S8 and S9 are independent of each other** and both depend only on S6. They are two different section
  builds with different shapes — a numbered procedure vs. a document reader — and each inserts itself into
  `page.tsx`. Cutting them apart keeps each reviewable; fusing them would rebuild the monolith the design
  deliberately split.
- **S9 carries the parity-critical work.** `SkillPreview` must be a **server** component reading the served
  file at request time, with line and byte counts **computed, never hardcoded**. A pasted excerpt forks
  silently from `scripts/skill_parity.py` and is a failure of intent even while CI stays green.
- **S10 is a design-fidelity slice, which `design-cowork` treats as part of the normal shape, not a
  failure.** It is the only slice positioned to run the acceptance checks, because several of them are
  cross-cutting: no-JS behaviour across every new component, focus rings on all buttons/anchors/scrollers,
  reduced-motion, and "grep the new components for literal copy → zero hits."

### Risk ratings

All five are `medium` → `slice-executor-mid`. The spec is exact enough that none requires architectural
judgment, and none is mechanical enough for `low` — every one carries the "respect the design" obligation,
which is a judgment call by nature. **The orchestrator may bump any of them one tier up at plan time**
(never down); `P11.S9` is the most likely candidate if planning reveals the server-read/no-JS interaction
is subtler than the spec makes it look.

## Slice intents to record in `phase.md`

Intents for the orchestrator to plan at each slice's turn — **not plans, and do not pre-fill any
`plan.md`.**

- **S6 — Primitives + copy.** `web/src/components/ui/snippet.tsx` (row + block variants per
  `build-prompt.md` §3.1; **`white-space:pre` + `overflow-x:auto` is a locked floor** — the install command
  must never wrap or truncate at any width) and `web/src/components/ui/trap.tsx` (§3.2 — an `<aside>`,
  deliberately **no** `role="alert"` and **no** `aria-live`, because a trap is not an error). The clipboard
  rule is locked: **copy the DOM node's `textContent`, never a separately-typed string**; reuse the proven
  mechanics in `web/src/components/show-once-key.tsx` but not its alert-box UI. Extract the copy logic into
  a **pure, DOM-free helper** so it is testable in this repo's Node-env vitest (there is no jsdom and no
  RTL). Add `quickstart` and `skill` to `web/src/content/section-ids.ts`. Add the `heroInstall`,
  `quickstart` and `skill` copy blocks to `web/src/content/landing.ts` as **byte-locked constants**, with a
  vitest that re-spells the copyable payloads so a reflow fails CI — vocky has no such test today and this
  would be its first.
- **S7 — Hero install row + nav.** `build-prompt.md` §4. Append the row **below** the existing two-column
  grid, inside the hero container. **Nothing inside the grid changes** — h1, sub, both CTAs, the proof
  ticks, the `EndpointCard` payload and the layered captured-record `Card` all stay exactly as shipped, and
  the corrected payload (nested `source.product`, no `vk_live_`) **must not be edited**. `Start free` stays
  the primary CTA; the install row is never a filled button. Then `landing-nav.tsx`: exactly **one** new
  link, second position, `Get started` → `#quickstart`. `#skill` gets **no** nav link. Honor the narrow
  (< 900px) behaviour in §4.
- **S8 — `AgentQuickstart`.** `build-prompt.md` §5, and insert at position 4 in `page.tsx` per §2. Four
  numbered steps plus the peer line, and the sticky contract aside. Two details the spec makes normative and
  that are easy to get wrong: **`400` is the success reading** on the verify step (the token authenticated;
  a bare GET was rejected for a missing filter), and **`401` says stop — never retry, never fall back**,
  because the published skill says so and the page must not contradict it. Every string is final copy in
  §5; use it verbatim.
- **S9 — `SkillSection` + `SkillPreview`.** `build-prompt.md` §6 and §3.4, inserted at position 5 per §2.
  `SkillPreview` is a **server component** that reads the served `/SKILL.md` at request time and splits it
  once at the closing frontmatter `---`. **Line and byte counts are computed from the file just read —
  hardcoding them is forbidden**, since they drift the moment the skill is edited. Collapsed shows the first
  22 body lines in a 380px scroller with a fade; expanded raises the cap to 640px and never goes unbounded.
  No syntax highlighting, no markdown rendering, no library. `Copy the skill` is primary; `Download
  SKILL.md` is a plain `<a href="/SKILL.md" download>` and is the no-JS survivor.
- **S10 — Fidelity pass.** Run `build-prompt.md` §11's seven acceptance checks and fix what fails. Also
  verify the §8 no-JS floor (copy buttons are client islands that render only after mount, so a no-JS
  visitor sees **no button at all** rather than an inert one; the preview still scrolls; Download still
  works), the §9 a11y floor (focus rings on every button, anchor, and both scrollers; the pane body
  focusable so it is keyboard-scrollable), and that motion drops to instant under
  `prefers-reduced-motion: reduce`. This slice may also close any fidelity gap earlier slices left.

## Facts every build slice inherits — record these in `phase.md`

- **Token delta: `None.`** `web/src/app/globals.css` requires **no change**. Round 01's caution family
  (`--color-caution` `#C6820E`, `--color-caution-deep` `#8F5C06`, `--color-surface-caution` `#FBF3E3`,
  `--color-hairline-caution` `#EEDCB2`) shipped but had no consumer; it now carries the trap treatment.
  **Do not add a token. Do not rename one.**
- **No backend change.** `POST /api/feedback` is untouched.
- **Copy-as-data is a hard rule** — zero literal strings in the new components; `build-prompt.md` §11.4
  makes it an acceptance check.
- **`section-ids.ts` is typed**, so anchors cannot be hardcoded and the two new entries gate compilation.
- **The web test suite is Node-env vitest** (`web/vitest.config.ts`), no jsdom and no RTL, 61 tests today
  across 5 files. Testable logic must be extracted into pure helpers. Keep new tests terse per `AGENTS.md`.
- **CI runs `pnpm lint`, `pnpm typecheck`, `pnpm test`** plus the skill-parity and installer checks
  (`.github/workflows/ci.yml`, added in S4). `prettier --check` is **not** in CI — it has 12 pre-existing
  failures — so do not assume formatting is gated, and do not "fix" those 12 files here.
- **`web/.prettierignore` now covers `public/`**, which is what keeps `web/public/SKILL.md` byte-identical
  to the canonical. Do not undo it.
- **The site is not deployed.** Nothing here can be verified against a live origin; `/SKILL.md` and
  `/install.sh` return 404 until P12. Verify locally with `next build` / the standalone server, and say
  plainly in each `result.md` what was **not** behaviorally proven.

## What this slice does NOT do

- **No implementation.** Decomposition writes only `works/` state and `phase.md`. Do not touch `web/`,
  `src/`, `docs/`, `scripts/`, or `.github/`.
- Do not pre-fill any slice's `plan.md`.
- Do not run `doc-new-version`, `new-phase`, `start-slice`, `finish-slice`, or any status transition.
- Do not edit the returned design record — it is read-only. Catalogue any nit as an apply-time to-do in
  `phase.md` instead.

## Validation

1. `python3 scripts/workflow.py validate` → passes.
2. `python3 scripts/workflow.py next` → reports `P11.S6`.
3. `works/backlog.md` lists all five new slices with the intended kinds, risks and orders, and `P11.REVIEW`
   still sorts last.
4. Every new slice folder contains **only** `slice.json`.
5. `git status --short` → every change inside `works/`.
6. `phase.md` carries: the cut with its rationale, the five slice intents, the inherited facts above, and
   the standing **RESPECT THE DESIGN** instruction with its "must appear in every build slice's `plan.md`
   and executor prompt" note.

## When done

Write `works/phases/active/P11/slices/P11.DECOMP2/result.md` from scratch (free-form): the slices created,
any place where reading `build-prompt.md` changed the cut and why, and anything the orchestrator must know
before planning `P11.S6`. Append the durable notes to `works/phases/active/P11/phase.md`. Do not commit and
do not change any slice or phase status.
