# P11.S10 result — design-fidelity pass

**Outcome: zero code changes.** Every §11 acceptance check, the §8 no-JS floor, the §9 a11y floor and the
whole-round consistency checks were verified against the tree and passed as shipped. The one open
question (`Section` padding) is adjudicated below — the shipped default is kept, with a strengthened
argument. This is exactly the "fidelity pass that proves the round correct" outcome the plan called the
best case, not the worst.

## Validation (repo root unless noted; run from `web/` where stated)

1. `pnpm typecheck` → **exit 0**, no output.
2. `pnpm lint` → **exit 0**, no output.
3. `pnpm test` → **78/78 passed**, 10 files, `Duration 254ms`.
4. `pnpm build` → succeeds, **zero warnings**, `Route (app)` table shows `ƒ /` (dynamic, unchanged).
5. `python3 scripts/skill_parity.py` → `PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.`
6. `bash -n web/public/install.sh` → exit 0.
7. `python3 scripts/workflow.py validate` (repo root) → `Workflow validation passed.`
8. Every §11 check below, with evidence.

Nothing failed, so steps 1–4 were not re-run after a fix — except for the temporary probe in check 2,
after which 1–4 (plus 5 and the final `git status`) were re-run to confirm a clean restore (see check 2).

## The seven §11 acceptance checks

**1. Install command pastes as one unbroken line from any width.**
`web/src/components/ui/snippet.tsx` puts `whitespace-pre overflow-x-auto` on both the `row` `<code>`
(`min-w-0 flex-1 overflow-x-auto … whitespace-pre`, line 304) and the `block` `<pre>`
(`overflow-x-auto p-3.5 … whitespace-pre`, line 290). Both the hero row (`hero.tsx:121-125`) and the
quickstart's step 1 (`agent-quickstart.tsx:124-134`, `steps.install`) render `Snippet variant="row"` with
the identical `heroInstall.command` / `steps.install.command` string. **PASS.**

**2. Preview counts change automatically when the skill changes.** Re-ran the S9 probe, this time against
a real `next start` server rather than only source-reading:
- Backed up `web/public/SKILL.md`, appended one blank line (`119/7975` → `120/7976`).
- `pnpm build` (clean), started `next start -p 3411`, fetched `/`: the served HTML's meta line read
  **`120 lines · 7976 bytes`** — the computed values, not a hardcode.
- Restored the file byte-for-byte from the backup (`wc -l -c` back to `119 7975`), rebuilt, started
  `next start -p 3412`, fetched `/` again: **`119 lines · 7975 bytes`**.
- `git status --short web/public/SKILL.md skills/vocky-feedback/SKILL.md web/` → **no output** — the
  restore left zero diff.
- `python3 scripts/skill_parity.py` → `PASS` again, post-restore.
- Re-ran `pnpm typecheck` / `pnpm lint` / `pnpm test` / `pnpm build` after the restore — all clean (see
  Validation 1–4 above; those are the post-restore readings).
**PASS.** No hardcode, no forked excerpt.

**3. With JS disabled: no copy button anywhere, the pane still shows the file and scrolls, `Download
SKILL.md` downloads it.** This is the composite check no earlier slice could make alone, so it needed a
real render of the whole page rather than a per-component `renderToStaticMarkup` (the landing page is an
`async` server component reading a session cookie — not reachable by that technique). Ran `next build` +
`next start` and fetched `/` (pre-hydration server HTML, i.e. the no-JS frame):
```
grep -o '<button[^>]*>[^<]*' page.html
<button type="button" class="… disabled:opacity-50 …" disabled="">Not yet — vocky is free today
```
**Exactly one `<button` in the entire document**, and it is P9's pre-existing disabled Pricing CTA (the
`disabled=""` attribute and the exact copy confirm it — matches S9's own identification of it as the sole
legitimate button). No copy button — hero, quickstart's four snippets, or skill pane — appears anywhere in
the server HTML. The skill pane's frontmatter + body were both present in the same fetch (confirmed via the
`#skill` section text and the computed meta line above), and `Download SKILL.md` / `Open the raw file` are
plain `<a href="/SKILL.md" download>` anchors unconditionally in the markup (`skill-section.tsx:77-86`,
`skill-preview-body.tsx:126-128`) — no JS required for either. **PASS.**

**4. Zero literal copy in the new components.** Read every file under `web/src/components/landing/` and
`web/src/components/ui/` added or touched by round 02 (`snippet.tsx`, `trap.tsx`, `agent-quickstart.tsx`,
`skill-section.tsx`, `skill-preview.tsx`, `skill-preview-body.tsx`, `skill-copy-button.tsx`,
`skill-shared.ts`, `inline-code.tsx`, plus `hero.tsx`/`landing-nav.tsx`'s touched regions). Every rendered
string is a prop or a `LANDING.*` reference; the only string literals in these files are Tailwind class
lists, one internal invariant-error message (`Snippet: command node is not mounted` /
`SkillCopyButton: skill pane is not mounted` — developer errors, never user-facing), an element id
(`SKILL_FILE_DOM_ID`), and a shared class constant (`SKILL_CONTROL_CLASS`, `INLINE_CODE_CLASS`) — none of
which is prose a visitor reads. **PASS.**

**5. No `vk_live_` anywhere; no flat `source_product`; the hero payload diff is empty.**
**Scoped correctly per the plan's warning:** `grep -rn "vk_live_" web/ src/` → **zero matches** (exit 1).
The repo-wide grep (excluding `node_modules`/`.next`) matches only `docs/reference/design/rounds/…`'s three
read-only round-02 record files plus this phase's own `works/phases/active/P11/**` planning files — all in
negation form, documenting the correction; expected and unrelated to `web/`/`src/`.
`grep -rn "source_product" web/ src/` → every hit is a legitimate **read-path** use: the feedback list/detail
pages, `lib/vocky/types.ts`'s stored-record types, `smoke.py:141`'s `GET` query filter, the backend's
read/query modules (`api.py`, `feedback/*`, `capture_queue.py`, `admin_api.py`, `persistence/models.py`),
`web/tests/vocky-app.test.ts:416`'s pre-existing read-record fixture, `web/public/SKILL.md:63` (documents
in prose that a top-level `source_product` is *rejected*), and `landing.ts:14`'s own comment explaining why
the read shape is flat while the capture request nests it. **No capture-request occurrence anywhere.**
`git log -p -- web/src/content/landing.ts | grep source` shows the hero's `source` field changed only once,
in `0192ea4 fix(P11.S1)` (flat → nested); zero diffs to it in any of S6–S9's commits. **The hero payload
diff is empty since S1. PASS**, with the scoping stated per the plan.

**6. The trap block has no `role="alert"` and no `aria-live`.**
`grep -rn 'role="alert"|aria-live="assertive"' web/src/components/` → the only real attribute usages in the
whole `components/` tree are `show-once-key.tsx:55` and `field.tsx:98` — both pre-existing, unrelated
components from before this round. Every hit inside round 02's own files (`trap.tsx`, `snippet.tsx`) is a
**comment** documenting the prohibition, not an attribute. `ui/trap.tsx`'s `<aside>` carries no `role` and
no `aria-live` attribute at all. **PASS.**

**7. Nav has exactly five links; `#quickstart` and `#skill` both scroll to their sections.**
`landing.ts:52-56` → `How it works` · `Get started` (`#quickstart`) · `Features` · `Pricing` · `Docs` —
five links, in that order (confirmed by S7's own `renderToStaticMarkup` check, re-confirmed here by
reading the array). `agent-quickstart.tsx:108` → `Section … id="quickstart"`; `skill-section.tsx:42` →
`Section … id="skill"`. `Section` bakes `scroll-mt-24` onto any element with an `id`
(`ui/section.tsx:69`), and `globals.css:257` sets `html { scroll-behavior: smooth }` globally, so both
anchors are native in-page smooth-scroll targets with no per-section JS. `section-ids.ts` has exactly the
five ids (`features`, `how`, `pricing`, `quickstart`, `skill`) and all five are consumed (three pre-existing
sections, `quickstart`/`skill` by the two new sections plus the peer link and nav entry). **PASS.**

## The padding adjudication — decided, applies to both sections identically

**Kept `Section`'s shipped default (`py-section` / `md:py-section-lg` = 72/104px, plus the standard
`px-5 md:px-14` gutter) for both `AgentQuickstart` and `SkillSection`. §5/§6's literal `Padding: 84px 28px`
is not applied to either.** This is the same call S8 and S9 already made; I re-derived it independently
rather than just re-stamping their conclusion, and I'm recording a stronger version of the argument because
one of their two supporting points doesn't actually hold up:

- **Their weaker point — "84px isn't on the token scale, and §1 forbids a new/renamed token" — is not a
  real blocker and I'm dropping it as a reason.** Using an *arbitrary* Tailwind value (`py-[84px]`) does not
  add or rename a token; it's the exact technique this same round already uses in a dozen other places for
  spec values that don't land on the scale (`rounded-[12px]`, `text-[13.5px]`, `size-[34px]`, `text-[15px]`,
  `mt-[22px]`, `max-w-[70ch]`, …). If token-scale purity were the only issue, 84px could be applied today
  with zero risk to §1. So the real question is horizontal, not vertical.
- **The stronger, load-bearing point is the horizontal one, and it's a real visible defect, not a
  preference.** The landing's shared gutter is `px-5 md:px-14` (20px / 56px) — confirmed identical across
  every other `Section`-based band on the page (Hero, HowItWorks, Showcase, Features, Pricing, ClosingCTA).
  Taking §5/§6's literal `28px` as these two sections' *own* horizontal padding, at every breakpoint, would
  put their content's left/right edges at a different distance from the viewport than every neighbouring
  section's — a visible seam a visitor would notice scrolling past the boundary, exactly where RESPECT THE
  DESIGN's own "never a plainer fallback" concern cuts the other way: literal-here is the choice that reads
  wrong, not the safe one.
- **A new, better-supported argument for why the whole line is not meant literally: the "Padding: 84px
  28px" line is identical, word-for-word, across two structurally different sections** (a four-step
  procedure vs. a two-column pitch-plus-preview), always paired with the same "container 1180px" line. Every
  *other* explicit value in `build-prompt.md` varies meaningfully with what it describes (gap widths, font
  sizes, colours per state); a padding spec that is bit-for-bit identical for two dissimilar surfaces reads
  as the design tool's own generic Section-wrapper boilerplate — the same class of artifact `P11.DECOMP2`'s
  correction 3 already identified for `.eyebrow`/`.note`/`.tag`/`.card` (card-kit specimen classes, not a
  bespoke decision for this content). `container: 1180px` is the one number in that pair that *does* match
  a real, load-bearing repo token (`max-w-page`) and is honoured exactly for that reason — it survives
  because it happens to coincide with product truth, not because every number on that line is normative.
- **`Section` is itself a shared design primitive whose whole job is one consistent padding rhythm across
  every band on the page** (`ui/section.tsx`'s own doc comment: "Full-bleed tonal band that hosts a page
  section"). Every pre-existing landing section already relies on that shared rhythm rather than a
  per-section override. Introducing a one-off override for exactly these two new sections would be the
  actual design-fidelity violation here — it breaks a page-wide consistency this round's own design record
  never asked to change (§10's change manifest lists no edit to `Section` or `globals.css` at all).

**This is a deliberate, argued departure from two explicit values in the contract, made once here and
applying to both sections identically — not an oversight.** No code change follows from it (S8/S9 already
implemented the default); if a future round wants an intentional 84px vertical rhythm break for these two
sections specifically, that is a design decision to make explicitly next round, not something to infer from
this line.

## The §9 a11y floor — verified, not rebuilt

- **Focus ring**: `globals.css:276-279` — `:focus-visible { outline: 2px solid var(--color-green-deep);
  outline-offset: 2px }` — is global `@layer base`, so every new button and anchor gets it automatically
  with zero component-level CSS.
- **The two scrollers**: the round added exactly one `overflow-auto` region —
  `skill-preview-body.tsx:84-95`'s pane body — and it carries `tabIndex={0}` (line 88), so it is
  keyboard-focusable and keyboard-scrollable in both its collapsed (300/380px) and expanded (480/640px)
  states. Read `build-prompt.md` §9's "the two scrollers (the pane body is focusable…)" as describing that
  one element's two visual states, not two separate DOM nodes — there is no second `overflow-auto` (or
  `overflow-y-auto`) element anywhere in `landing/` or `ui/snippet.tsx`/`ui/trap.tsx`; `Snippet`'s
  `overflow-x-auto` is a single-line horizontal scroll whose entire content is already present as static,
  selectable text (no vertical clipping, nothing hidden from a screen reader), and no earlier slice's notes
  (S6–S9) ever named it as a second scroller needing `tabIndex`. **No change made here** — it already holds.
- **Semantics**: `AgentQuickstart` and `SkillSection` both render `<Section>` with no `as` override, so both
  are `<section>` (`ui/section.tsx:60`); both have an `<h2>` (`agent-quickstart.tsx:116`,
  `skill-section.tsx:55`). The quickstart's four steps + peer row are an `<ol>`
  (`agent-quickstart.tsx:122`); the skill section's "What's inside" list is also an `<ol>`
  (`skill-section.tsx:97`).
- **Colour is never the sole carrier**: `ReadingList`'s chip always renders the literal `reading.code`
  (`"400"`/`"401"`/`"else"`) alongside its colour (`agent-quickstart.tsx:76`); the trap's label is
  `"Known trap · Codex only"` — the literal word "trap" is in the copy itself (`landing.ts:198`), not just
  implied by the amber styling.
- **No load-time interruption**: repo-wide `grep -rn 'role="alert"|aria-live="assertive"'` under
  `web/src/components/` returns only two pre-existing, unrelated components (`show-once-key.tsx`,
  `field.tsx`); zero in round 02's own files. Every copy button's success announcement is
  `aria-live="polite"` (`snippet.tsx:320`, `skill-copy-button.tsx:198`), and nothing is announced on
  failure beyond the visible hint, matching §7 exactly.
- **Reduced motion**: `globals.css:282-291` forces `transition-duration: 0.01ms !important` (plus
  `animation-*` and `scroll-behavior: auto`) under `prefers-reduced-motion: reduce`, globally — the copy
  buttons' 150ms colour transitions and the preview's `max-height`/opacity transitions all inherit this
  with no component-level media query.

None of the above needed a `globals.css` change or a new token — confirmed by `git log` showing no P11
commit has ever touched `web/src/app/globals.css`.

## §7 state table + §8 no-JS floor — verified by reading the code (no jsdom in this repo)

There is no jsdom/RTL in this repo's vitest config (`environment: "node"`), so the interactive states below
cannot be driven through a DOM in an automated test here, and per the plan I did **not** add a browser test
runner for this slice. Verified instead by reading each implementation against §7's table:

- **Success reverts after 2000ms**: `Snippet` and `SkillCopyButton` both define
  `const COPIED_REVERT_MS = 2000` and `setTimeout(() => setState("idle"), COPIED_REVERT_MS)` on a successful
  `attemptCopy`, with the timer cleared on unmount (`useEffect` cleanup) and cleared again at the start of
  the next attempt (`clearRevert()` / the inline `clearTimeout` at the top of `handleCopy`).
- **Failure persists**: the `else` branch of `handleCopy` sets `state` to `"failed"` and starts **no**
  revert timer — it only clears on the *next* `handleCopy` call (`clearRevert()` at the top). Matches "until
  the next attempt" exactly.
- **Failure selects the command programmatically**: `selectCommandText()` / `selectSkillText()` build a
  `Range` over the ref'd/DOM-id'd node and call `Selection.addRange`, invoked from the `else` branch of
  `handleCopy`; the visible hint (`copy.selectionHint` / `selectionHint` prop) renders only in the `failed`
  branch, right below the row.
- **Preview collapsed/expanded**: `skill-preview-body.tsx:89-94` — `max-h-[300px] app:max-h-[380px]`
  collapsed, `max-h-[480px] app:max-h-[640px]` expanded — both bounded (`overflow-auto`, never
  `overflow-visible`/unbounded), fade only shown collapsed (`opacity-0` when `isExpanded`).
- **No-JS**: `useIsHydrated()` returns `false` through server render and hydration and only flips after —
  `Snippet`'s and `SkillCopyButton`'s buttons render as `null`/absent (not `disabled`) while unhydrated
  (`snippet.tsx:258-269`, `skill-copy-button.tsx:176`); the pane's body is a plain server-rendered
  `overflow-auto` `<pre>`, no JS required to scroll it; the footer's ternary falls to `footerNoJs` when
  `!hydrated` (`skill-preview-body.tsx:110-114`); `Download SKILL.md` is an unconditional `<a … download>`
  in both `skill-section.tsx` and the pane header, never gated on hydration.

This reading is corroborated by three permanent, DOM-free regression tests that already assert the no-JS
half of this table in CI without jsdom: `web/tests/snippet-ssr.test.ts`,
`web/tests/agent-quickstart-ssr.test.ts`, and `web/tests/skill-preview-ssr.test.ts` (all pass, see
Validation 3 above). **Still unverified by any automated means in this repo, and not verifiable without a
browser**: the actual 2000ms timer firing, the `Range`/`Selection` becoming the real OS selection, the
`aria-live="polite"` announcement actually being spoken, and any focus/hover pixel-level check. Stated
plainly, per the plan, rather than asserted as proven.

## Whole-round consistency (§5 of the plan)

- **Install command identical everywhere**: `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` appears
  verbatim in `web/public/install.sh:5` (header comment), `docs/cli.md:15`, `README.md:54`, and twice in
  `web/src/content/landing.ts` (`heroInstall.command` line 120, `quickstart.steps.install.command` line
  189) — all five `grep -Fn` hits match character-for-character.
- **`page.tsx` section order** matches §2 exactly: `Hero · TrustStrip · HowItWorks · AgentQuickstart ·
  SkillSection · Showcase · Features · Pricing · ClosingCTA` (`page.tsx:44-52`).
- **`section-ids.ts`** has exactly five ids (`features`, `how`, `pricing`, `quickstart`, `skill`) — no
  orphan; all five are referenced somewhere (three pre-existing sections' own `id`, `quickstart`/`skill` by
  the two new sections' `id` plus the nav entry and peer link).
- **Tone alternation**: `agent-quickstart.tsx:108` `tone="default"`, `skill-section.tsx:42`
  `tone="surfaceSoft"` — matches §2 exactly, continuing the page's alternating tonal ramp.

## What I did not change, and why

Nothing. Every check above passed on the first read; the only "action" taken was the check-2 probe (append
a byte to the served `SKILL.md`, observe the counts change, restore byte-for-byte, re-verify). I looked
specifically for the kind of gap the plan warned about — a hardcode, a forked excerpt, a silently-dropped
`tabIndex`, a stray `role="alert"`, a nav-order slip, a diverged install line — and found none. This matches
the plan's own framing: corrections 1–9 were all caught and closed at DECOMP2/S7/S8/S9 time; S10's job was
to prove that held across the whole round, not to find new problems for their own sake.

## A note on `format:check` (not a validation step, not fixed)

Not part of this slice's required validation (it is not in the plan's numbered list and is deliberately not
in CI). Ran it anyway out of curiosity: **14 files** now fail `pnpm format:check`, not the 12 the plan's
"out of scope" note names. The 2 extra are `agent-quickstart.tsx` (net-new, S8) and `hero.tsx` (touched by
S7) — both fail purely because `prettier-plugin-tailwindcss` reorders class lists differently from how they
were hand-written, the exact non-issue S8's own notes already named ("that is not a CI failure"). Confirmed
`hero.tsx` was prettier-clean at the P10.REVIEW baseline (`git show 880bc93:web/src/components/landing/hero.tsx`
passes `prettier --check` clean today), so this specific file's failure is new to this round, not inherited —
worth recording precisely for whichever P12 slice eventually runs `prettier --write` across the repo, so it
doesn't mistake the count. **Not fixed here**, per the plan's explicit instruction; `format:check` stays out
of CI and this is P12's call.

## For the phase review

- The padding adjudication above is the one open decision this slice was asked to make; it applies
  identically to both sections and requires no code change.
- Doc impact: see the addendum I added to `phase.md`'s "## Doc impact" section — `P11.S7` had not recorded
  an entry (its nav reorder + hero install row do touch `docs/current/frontend.md`'s landing narrative),
  so I added one addressing that gap. No new doc impact from this slice itself (no source changed).
- Nothing here required a `globals.css` edit, a new/renamed token, a change to the canonical skill or
  `web/public/SKILL.md` beyond the temporary, fully-restored count probe, a fix to the 12 (now 14, see
  above) prettier failures, a backend change, or a doc version — all per the plan's stated boundaries.
