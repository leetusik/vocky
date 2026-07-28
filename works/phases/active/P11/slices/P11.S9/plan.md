# P11.S9 — `SkillSection` + `SkillPreview` + its `page.tsx` insertion

> ## RESPECT THE DESIGN
> **Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
> failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
> intent, never a plainer fallback.**

## Why this slice is bumped a tier

It carries the round's one genuine spec tension — a plausible, natural implementation **breaks a locked
floor while every CI check stays green** (correction 7, below). It is also the slice where a shortcut would
silently fork from the byte-parity gate S4 built. Read carefully before writing.

## Scope

Build `web/src/components/landing/skill-section.tsx` and `web/src/components/landing/skill-preview.tsx`,
and insert the section into `web/src/app/page.tsx` at **position 5**, between `AgentQuickstart` (S8) and
`Showcase`.

Source of truth: `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` **§2, §3.4, §6, §7,
§8**. Read `works/phases/active/P11/phase.md` first — corrections **6, 7, 8 and 9** all apply here, and the
"S6 done" / "S8 done" notes describe what to consume and mirror.

## The two things that must not go wrong

### 1. The full file is ALWAYS in the server HTML (correction 7)

§3.4 says collapsed "shows the first 22 lines of the body" and expanded's "body text = the whole file",
which reads like the collapsed DOM is truncated. **It is not.** §8 says the pane is "server-rendered with
the file already in the HTML… so all 119 lines are readable without JS", and `result.md` §6.5 settles it:
*"A scroller (rather than a hard clip) means a no-JS visitor can still read all 119 lines."*

→ **"Collapsed" is a *visual* window, not a content truncation.** The full body text is always rendered;
collapsed means a **380px scroller plus the fade overlay**. Expanding raises the cap to **640px** and drops
the fade — **it does not swap in new text.**

Truncating the server output to 22 lines would satisfy a literal reading of §3.4, pass every CI check, and
**break the no-JS floor** — while making the no-JS footer (`{lines} lines · scroll to read`) a lie. Do not
do it.

### 2. The preview reads the SERVED file, and its counts are computed

Read `web/public/SKILL.md` — the **served** copy — at request time (`fs.readFile`, or a same-origin fetch
of `/SKILL.md`). **Never a pasted excerpt.** A hand-copied excerpt forks silently from
`scripts/skill_parity.py` and is a failure of intent even while CI is green.

**Line and byte counts are computed from the file just read** — `content.split("\n").length - 1` and
`Buffer.byteLength(content)`. **Hardcoding them is forbidden** (acceptance check 2): they drift the moment
the skill is edited. Correction 8 confirms both files currently measure **119 lines, 7,975 bytes** and that
the formula yields 119 with no special handling — so a correct implementation needs no fudge factor.

`page.tsx` is already dynamic (`ƒ`) because it reads the session cookie, so a request-time `fs` read is
safe and changes nothing about the build output.

## What already exists — consume it

- **`useIsHydrated`** (`@/lib/use-is-hydrated`) — S6's mount gate. **Reuse it for the expand toggle.** Do
  not write `useEffect(() => setMounted(true), [])`: `react-hooks/set-state-in-effect` is an **error** in
  this repo's lint config and `pnpm lint` will fail.
- **`Snippet`**, **`Trap`**, **`Section`**, **`Card`**, **`Chip`**, **`Button`**, `buttonVariants`.
- **`LANDING.skill`** — all copy, final. Shape:
  - `eyebrow`, `heading`, `lede: {text, code[]}`
  - `copyAction`, `copyAnnouncement`, `downloadAction`, `downloadHref`, `served`
  - `insideLabel`, `inside: string[]` (7 items)
  - `preview`: `{ filename, meta, downloadLabel, collapsedLines: 22, footerCollapsed, footerExpanded, footerNoJs, expandLabel, collapseLabel, rawLabel, rawHref }`
- **`SECTION_IDS.skill`** — added by S6; S8's peer line already links to `#skill`, so **this slice is what
  makes that link resolve.**
- S8 built an inline-`<code>` helper for `lede.code`-style fragments — **mirror its approach** rather than
  inventing a second one. Check `agent-quickstart.tsx` and reuse or lift it.

**Write no new copy.** Acceptance check 4: zero literal strings in the new components.

The `meta` / footer strings carry `{lines}`, `{bytes}` and `{collapsed}` placeholders — write a tiny
formatter that substitutes them. Keep the strings in `landing.ts`; the substitution is code.

## Structure

### `SkillPreview` — a server component wrapping a small client island

Split the responsibility so the file stays server-rendered:

- **`skill-preview.tsx` (server)** — reads the file, computes counts, splits **once** on the closing
  frontmatter `---`, and renders the header / frontmatter band / body / footer. It passes the
  server-rendered body and the three footer strings to…
- **a small client island** that owns only `useState(false)` for expanded plus `useIsHydrated()`, toggling
  the body's `max-height` and the fade, and choosing the footer text. The **body content is `children`**,
  rendered on the server — this is what keeps all 119 lines in the HTML.

Per §3.4:

- **Header** — `bg-surface`, `border-b border-hairline`, `py-[9px] pr-[10px] pl-[14px]`. Left: filename
  `SKILL.md` mono 12px/500 `text-charcoal`, then the meta mono 11px `text-steel`. Right: `Copy` + `Download`.
- **Frontmatter band** — `bg-surface-archive`, `border-b border-hairline`, `p-[12px_16px]`, mono 12px/1.6
  `text-steel`, `whitespace-pre-wrap break-words`. **Include the `---` fences.** This is the **only**
  structural distinction in the pane.
- **Body** — `max-h-[380px] overflow-auto relative`; `<pre>` `p-[14px_16px]`, mono 12.5px/1.62
  `text-slate`, `whitespace-pre-wrap break-words`. **No syntax highlighting, no markdown rendering, no
  library.** Fade overlay: absolute, `inset:auto 0 0 0`, `height:110px`, `pointer-events-none`,
  `linear-gradient(to bottom, rgba(255,255,255,0), var(--color-canvas) 78%)`.
- **Footer** — `py-[9px] px-3`, `border-t border-hairline`, `bg-surface`. Left mono 11.5px `text-steel`
  using `footerCollapsed` / `footerExpanded` / `footerNoJs`; right the toggle.
- **Expanded** — body `max-h-[640px]` (**still a scroller**), fade removed, toggle label `Collapse`.
  **Never unbounded.**

**The `collapsedLines: 22` value is normative** (correction 6). The spec's parenthetical naming the
`~/.zshenv` line is wrong — that is body line 15 — but `22` appears in §3.4, the §7 state table, the footer
copy and `result.md` §6.5's rationale. **Keep 22; do not "correct" it to 15.** Since the body is not
truncated, 22 is what the footer *says* and what the 380px window shows — decide deliberately whether the
blank line right after the closing `---` counts as body line 1, and state your choice in `result.md`.

**No-JS** (§8): the toggle island never renders, so the footer uses `footerNoJs` and offers `rawLabel` →
`rawHref` as a plain anchor. The pane still scrolls natively.

### `SkillSection` — §6

`<Section tone="surfaceSoft" id="skill" reveal>`; grid
`minmax(0,.82fr) minmax(0,1.18fr); gap:56px; align-items:start`.

- **Left** (`sticky top-6`): eyebrow (the hero's dotted treatment, per correction 4) → `h2` at
  `--text-heading-2` (30px) → lede 15px/1.6 `text-steel` `max-w-[46ch]` with `vocky-feedback` as inline
  `<code>` → actions (`gap-3 mt-[22px]`): **`Copy the skill` is the primary filled button**, and
  **`Download SKILL.md` is a plain `<a href="/SKILL.md" download>`** beside it → the `served` line, mono
  11.5px `text-steel` → a `border-hairline-soft` divider, the `What's inside` micro label, and the 7-item
  list (mono tabular index + 13px `text-slate`).
- **Right** — `SkillPreview`, collapsed by default.
- **Narrow (< 900px)** — one column, left block first, `sticky` dropped; preview body `max-h-[300px]`
  collapsed / `480px` expanded; actions full-width stacked. Use the `app:` variant, mobile-first.

**`Download SKILL.md` must work with JavaScript disabled** — a plain anchor, always. It is the locked
no-JS survivor. `Copy the skill` is client-only and simply absent without JS; that is acceptable *because*
Download is durable.

## Correction 9 — two floors are already global

`globals.css:276-279` already ships `:focus-visible { outline: 2px solid var(--color-green-deep);
outline-offset: 2px }`, and `:282-291` already forces near-instant transitions under
`prefers-reduced-motion: reduce`. So §9's focus ring and §7's motion rule need **no new CSS**. The only
work here is **making the pane body focusable (`tabIndex={0}`) so it can receive the ring and be
keyboard-scrollable** — §9 requires exactly that.

## A fidelity item S8 left open — do not repeat it here

S8 chose `Section`'s shipped padding default (`py-section` / `md:py-section-lg` = 72/104px) over §5's
explicit `84px 28px`, reasoning that no other landing section overrides it. §6 gives this section the same
explicit `84px 28px`. **Correction 5 established the governing rule: explicit values are normative,
descriptive labels are not.** Make the same choice S8 made *only* if you conclude it is right, and either
way **state your reasoning in `result.md`** — S10 adjudicates both sections together, and it needs the
argument, not just the outcome.

## Validation

From `web/` unless noted:

1. `pnpm typecheck` → exit 0.
2. `pnpm lint` → exit 0.
3. `pnpm test` → the **73** tests S8 left green all pass, plus whatever you add.
4. `pnpm build` → succeeds; `/` stays `ƒ`.
5. **The no-JS floor, in CI.** Extend the `renderToStaticMarkup` technique (`web/tests/snippet-ssr.test.ts`,
   `agent-quickstart-ssr.test.ts`) to `SkillPreview` and assert, permanently:
   - the server HTML contains **no `<button`** anywhere in the pane;
   - it contains the **whole file** — assert on a string from the **last** section of `SKILL.md`
     (`## 7. Report back`), not just an early one. **This is the assertion that makes correction 7
     unbreakable**, so make it explicit;
   - the `Download` anchor is present with `href="/SKILL.md"` and `download`.
6. **Counts are computed, not hardcoded** (acceptance check 2): `grep -n "119\|7975\|7,975"` over the two
   new components → **no matches**. Then prove it behaviorally: temporarily append a line to
   `web/public/SKILL.md`, re-render, confirm the count changes, and **restore the file** so
   `python3 scripts/skill_parity.py` passes again. Report both readings.
7. `python3 scripts/skill_parity.py` → **PASS** (the served file must be byte-identical to the canonical
   when you finish).
8. `grep -rn "style={{" web/src/components/landing/skill-*.tsx` → no matches.
9. `grep -rn 'role="alert"' web/src/components/landing/skill-*.tsx` → no matches.
10. Confirm `#skill` resolves and **S8's peer link now lands on it**.
11. `python3 scripts/workflow.py validate` → passes.

Nothing can be checked against a live origin — `/SKILL.md` 404s until P12 deploys.

## Out of scope

- No fidelity sweep across the other sections — S10.
- **No `globals.css` change, no new or renamed token** — the design's delta is `None.`, and correction 9
  shows both floors are already global.
- No change to `web/public/SKILL.md` or the canonical skill (beyond the temporary, restored count probe).
- No new `ui/` primitive. No backend change. No `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S9/result.md` from scratch (free-form): the server/client split
as it landed, how you resolved the 22-line window and the body-line-1 question, the padding reasoning for
S10, the count-probe readings, verbatim validation output, and what is not test-covered. Append durable
cross-slice notes to `works/phases/active/P11/phase.md` — S10 verifies both sections, so record anything it
must check. Do not commit and do not change any slice or phase status.
