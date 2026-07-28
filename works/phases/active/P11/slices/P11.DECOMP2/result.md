# P11.DECOMP2 — result

**The five-slice cut in `plan.md` survived verification and was created unchanged in shape.** Orders 7–11,
all `kind: implementation`, all `risk: medium`, dependencies as planned. What changed is the *content* of
three slices, driven by nine corrections found by checking `build-prompt.md` against the working tree
rather than taking it on trust. Every correction is recorded in `phase.md`; **the design record was not
edited.**

## Slices created

```
P11.S6   order 7   implementation  medium  —         Primitives + copy: Snippet, Trap, pure copy helper, section-ids, landing.ts blocks
P11.S7   order 8   implementation  medium  P11.S6    Hero install row + nav (one new link, nav order per build-prompt 2)
P11.S8   order 9   implementation  medium  P11.S6    AgentQuickstart section + ReadingList + page.tsx insertion
P11.S9   order 10  implementation  medium  P11.S6    SkillSection + SkillPreview server read + page.tsx insertion
P11.S10  order 11  implementation  medium  P11.S9    Design-fidelity pass: acceptance checks, no-JS, a11y and reduced-motion floors
```

All five are **bare folders holding only `slice.json`** — no `plan.md` was pre-filled anywhere.

Two names differ slightly from the plan's, to surface scope the plan understated: S7 says "nav order per
build-prompt 2" (it is a reorder, not just an insert — finding 1) and S8 adds "ReadingList" (§3.3 was
unassigned in the plan — finding 3).

## Where reading the contract changed the cut

**It did not change the slice boundaries.** I considered splitting S6 (it carries two primitives, a pure
helper, two `landing.ts`-adjacent test surfaces and three large copy blocks) and rejected it: the copy
blocks' shape is exactly what `Snippet`'s props consume, and copy-as-data makes them one unit rather than
three fragments. Every file in the §10 change manifest is assigned to exactly one slice, plus two barrel
files the manifest omits (`ui/index.ts` → S6, `landing/index.ts` → S8 and S9).

It changed the *content* of three slices. The nine corrections are written out in full in `phase.md`; the
four that actually move work are:

1. **The nav is a reorder (S7).** §2 writes the final nav as `How it works · Get started · Features ·
   Pricing · Docs`, but `landing.ts:35-40` ships `Features · How it works · Pricing · Docs` — `Features`
   is *first* today. Inserting `Get started` at "second position" into the shipped array produces
   `Features · Get started · How it works · …`, contradicting both the written string and `result.md`
   §6.3's rationale. Acceptance check 7 only counts to five, so it would never catch this. The plan's
   "exactly one new link, second position" is true about the addition and silent about the reorder.
2. **The `.note` treatment does not exist in the repo (S8).** `build-prompt.md` §3.2 calls it "the existing
   note treatment", and `result.md` §6.4 calls it "the shipped `.note`". `grep -rn "border-l-2\|border-l "`
   over `web/src` returns **zero hits**, and `globals.css` has no `.note`, `.eyebrow`, `.tag` or `.card`
   class at all — those are card-kit specimen classes from the design project, not repo CSS. `.card` and
   `.tag` do have real repo equivalents (the `Card` and `Chip` primitives); the note must be **built**.
   It is used only in quickstart step 2, so S8 builds it inline — it does not become a `ui/` primitive.
3. **§3.3's `ReadingList` was unassigned (S8).** The spec says it "may live inside `AgentQuickstart`"; the
   plan's intents never named it. Assigned to S8 explicitly, and reflected in the slice name.
4. **The collapsed/no-JS tension in `SkillPreview` (S9).** §3.4 reads as if the collapsed pane's DOM is
   truncated to 22 lines; §8 requires all 119 lines to be readable without JS; `result.md` §6.5 settles it
   ("*a scroller rather than a hard clip means a no-JS visitor can still read all 119 lines*"). The full
   file is always in the server HTML and "collapsed" is a visual 380px window with a fade. This is the one
   place where a plausible-looking implementation breaks a locked floor with every CI check green — it is
   why I flagged S9 as the phase's strongest tier-bump candidate.

The remaining five corrections (the two shipped eyebrows and which one §5 means; §5.1's step marker
contradicting the shipped `HowItWorks` numeral it cites; the wrong "through the `Put these in ~/.zshenv`
line" parenthetical, where `22` is nonetheless normative; `result.md` §6.4's line-count discrepancy that
does not exist in the tree — both copies measure exactly 119 lines / 7,975 bytes; and the focus-ring +
reduced-motion floors already being global CSS) are apply-time to-dos that do not move work between
slices. All nine are catalogued in `phase.md` with their resolutions.

## Verified against the tree, not assumed

- **Token delta `None` holds.** Every token §3–§6 names exists in `globals.css`, including the full caution
  family at `:53-56`.
- **`Section` already supplies §2's needs** — `tone: default | surfaceSoft`, typed `id` with baked
  `scroll-mt-24`, and `reveal`. `html { scroll-behavior: smooth }` is global.
- **`--breakpoint-app` is 56.25rem = 900px** and Tailwind v4's `app:` variant is already in use across
  `src/components/app-shell/*` and the feedback pages — the design's `< 900px` maps to it exactly. No
  hand-rolled media query, and never `md:` (768px).
- **`:focus-visible` (`globals.css:276-279`) and the reduced-motion block (`:282-291`) already satisfy §9's
  focus ring and §7's "instant under reduced motion"** with zero new CSS. This is a real reason "no
  `globals.css` change" is achievable rather than aspirational; the only a11y work left is `tabIndex={0}`
  on the two scrollers.
- **`web/public/SKILL.md` and `skills/vocky-feedback/SKILL.md` are both 119 lines / 7,975 bytes**, and the
  frontmatter closes at line 5. Body line 15 is the `~/.zshenv` line; body line 22 falls just after the
  `## 2. Verify before you capture anything` heading.
- **vitest is `include: ["tests/**/*.test.ts"]` — `.ts` only.** Component tests are structurally
  impossible; `landing.ts` imports only `section-ids.ts` (no React), so the byte-lock copy test is
  feasible.
- **`page.tsx` is already dynamic** (`getSession()` + `redirect`), so `SkillPreview`'s request-time `fs`
  read is safe under `output: "standalone"`.

## Validation

| # | Command / check | Outcome |
|---|---|---|
| 1 | `python3 scripts/workflow.py validate` | **passed** (`Workflow validation passed.`), before and after slice creation |
| 2 | `python3 scripts/workflow.py next` | **`next_slice=P11.S6`** |
| 3 | `works/backlog.md` lists all five | **yes** — lines 63–67, all `todo`/`implementation`, `P11.REVIEW` still sorts last (order 9999) |
| 4 | Every new folder holds only `slice.json` | **yes** — `ls -A` on each of the five returns exactly `slice.json` |
| 5 | `git status --short` | **every change inside `works/`** (5 new slice folders, `phase.md`, this `result.md`, regenerated `backlog.md` / `index.json` / `state.json`) |
| 6 | `phase.md` carries the cut, rationale, intents, inherited facts, RESPECT THE DESIGN | **yes** — new `### DECOMP2 done` section, with the standing instruction and its "must appear in every build slice's `plan.md` **and** every executor dispatch prompt" note |

## For the orchestrator, before planning `P11.S6`

- **Put the RESPECT THE DESIGN paragraph in every one of S6–S10's `plan.md` *and* in every dispatch
  prompt.** It is quoted verbatim in `phase.md`'s new section.
- **Point every build slice at `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` as
  required reading**, and at `phase.md`'s nine corrections. The build-prompt is self-sufficient by design
  (the 43-card set stays in the design project and no executor has `DesignSync`) — but it is *not*
  self-correcting, and four of the nine corrections are places where following it literally produces a
  wrong result.
- **Tier bumps to consider** (never down): `P11.S9` first — correction 7 is a spec tension that silently
  breaks a locked floor while CI stays green. `P11.S6` second — the copy-failed state (programmatic
  `Range` + `Selection`, deliberately persistent rather than timed) on top of mount-gated client islands
  is the round's trickiest client mechanic, and three later slices inherit its shape.
- **S6 gates S8 and S9 at compile time**, not just logically: `SectionId` is a typed union, so neither
  section compiles until `quickstart` and `skill` exist in `section-ids.ts`.
- **Nothing is behaviorally provable against a live origin.** `/SKILL.md` and `/install.sh` still 404; each
  build slice's `result.md` must say plainly what was not proven, per the phase's standing rule.

## Deviations from `plan.md`

None in substance. The plan's cut, orders, kinds, risks and dependencies were all created as specified. Two
slice **names** were extended (S7, S8) to surface scope the plan understated — see above. No `plan.md` was
pre-filled, no source file outside `works/` was touched, no doc version was created, and no slice or phase
status was transitioned.
