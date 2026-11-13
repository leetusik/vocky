# P11.S8 — `AgentQuickstart` section + its `page.tsx` insertion

> ## RESPECT THE DESIGN
> **Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
> failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
> intent, never a plainer fallback.**

## Scope

Build `web/src/components/landing/agent-quickstart.tsx` and insert it into `web/src/app/page.tsx` at
**position 4**, between `HowItWorks` and `Showcase`.

Source of truth: `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` **§2, §3.3, §5**.
Read `works/phases/active/P11/phase.md` first — the "DECOMP2 done" corrections (**3, 4, 5** apply here) and
the "S6 done" / "S7 done" notes describing what already exists.

This is the biggest of the three surfaces: a header, four numbered steps, a peer line, and a sticky aside.

## What already exists — consume it, build nothing new

- **`Snippet`** (`@/components/ui`) — `variant="row"` and `variant="block"`, with the mount-gated copy
  button, the 2s revert, and the persisting failure state. Props: `command`, `copy: SnippetCopy`,
  optional `label`. Three of the four steps use it.
- **`Trap`** (`@/components/ui`) — the amber `<aside>` for step 2.
- **`Section`**, **`Card`**, **`Chip`**, **`Reveal`** — shipped primitives.
- **`LANDING.snippet`** — the four shared copy-button labels.
- **`LANDING.quickstart`** — **all copy for this section already exists and is final.** Its shape (note the
  steps are an *object keyed by name*, not an array — four heterogeneous shapes):
  - `eyebrow`, `heading`, `lede`
  - `steps.install` — `{ n, title, sub, command, copyAnnouncement }`
  - `steps.env` — `{ n, title, snippetLabel, command, copyAnnouncement, note: {text, code[]}, trap: {label, body:{text, code[]}} }`
  - `steps.verify` — `{ n, title, sub, snippetLabel, command, copyAnnouncement, readings: [{code, verdict, body}] }`
  - `steps.capture` — `{ n, title, command, copyAnnouncement, resultBadge, resultText }`
  - `peer` — `{ before, linkLabel, after, href }`
  - `aside` — `{ contractLabel, contractRows: [{name, value}], contractBody, worksWithLabel, … }`

**Write no new copy.** `build-prompt.md` §11.4 makes "zero literal strings in the new components" an
acceptance check. The `note.code` / `trap.body.code` arrays list the substrings that must render as inline
`<code>` inside their prose — implement a small helper that wraps those fragments rather than hand-splitting
the sentences.

## The four corrections that apply here

**Correction 3 — `.note` does not exist and must be built inline.** The spec calls it "the existing note
treatment" / "the shipped `.note`", but `grep` over `globals.css` and `web/src` finds no such class and no
`border-l-2` anywhere. Build it **inline in this component** (13px `text-steel`, `border-l-2 border-green`,
`pl-3`). **Do not create a `Note` primitive** — it has exactly one consumer.

**Correction 4 — use the hero's eyebrow, the one with the dot.** Two eyebrow treatments ship:
`how-it-works.tsx` uses `text-caption font-semibold tracking-[0.12em] text-green-dark uppercase` (no dot);
`hero.tsx` uses a `rounded-full bg-green-soft` pill with a `size-1.5 bg-green` dot. §5 explicitly says
"existing `.eyebrow` treatment, **green dot** + uppercase" — **the dot reading is explicit and wins.**

**Correction 5 — the step marker's explicit values are normative, its label is not.** §5.1 says "Step
marker = the shipped `HowItWorks` step numeral: 34px circle, `background:var(--color-ink)`, white mono 700
15px." The actually-shipped numeral is `size-9` (36px) `bg-green-soft` `text-green-dark`. **Build the 34px
ink circle with white mono 700 15px** — and **do not restyle `how-it-works.tsx`** to match.

**The `vk_live_` grep is no longer globally clean** (S7's finding): three read-only S5 design-record files
contain the literal in negation form, documenting the correction. Scope any such check to `web/` and `src/`.

## Layout — §5

`<Section tone="default" id="quickstart" reveal>`. Padding `84px 28px`; container `1180px` (there is a
`max-w-page` token — check whether `Section` already applies the container before adding your own).

**Header** (`max-width:70ch`): eyebrow → `h2` at `--text-heading-1` (38px) → lede 18px/1.6 `text-steel`.

**Body**: `grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr); gap:56px; margin-top:44px;
align-items:start`.

### Left — four steps

Step gap `16px`; each step's content block `padding-bottom:34px`; title at `--text-heading-4` (18px/700)
`text-charcoal`; sub 15px/1.6 `text-steel` `max-width:62ch`; content `margin-top:14px`.

1. **Install** — `<Snippet variant="row">`.
2. **Export the two variables** — `<Snippet variant="block" label="~/.zshenv">`, then the **note**
   (weight 1, built inline), then the **`Trap`** (weight 2). Order matters: note before trap.
3. **Verify** — `<Snippet variant="block" label="verify">`, then the `ReadingList` (below).
4. **Capture** — `<Snippet variant="row">`, then a result line: a `Captured` badge
   (`bg-green-soft text-green-dark`, mono 11px, pill) followed by mono 11.5px `text-steel` carrying
   `resultText`.

**Peer line** — a fifth row with a `·` marker instead of a numeral (`bg-surface-soft text-steel`), 15px
`text-steel`. `linkLabel` links to `peer.href` (`#skill`). **The anchor already exists in `SECTION_IDS`
(S6), so this compiles now and resolves once S9 lands its section** — that is by design; do not stub it.

### §3.3 `ReadingList` — build it here

Rows separated by `border-b border-hairline-soft`, `padding:11px 0`, 13.5px/1.55 `text-slate`. The status
chip is mono 12px/700, `rounded-md`, `px-2 py-[3px]`, `min-width:52px`, centred:

| code | chip |
|---|---|
| `400` | `bg-green-soft text-green-dark` |
| `401` | `bg-surface-danger text-danger-deep` |
| `else` | `bg-surface-caution text-caution-deep` |

**The chip always repeats the literal code — colour is never the sole signal.** This is an a11y floor, not
styling.

**Two content floors that are easy to soften and must not be:**

- **`400` is the success reading.** The token authenticated; a bare GET was rejected for a missing filter.
  Do not relabel it as an error or reorder it below `401`.
- **`401` says stop — no retry advice, ever.** The published skill (`skills/vocky-feedback/SKILL.md`) tells
  agents to stop on 401, and **the page must not contradict it.**

`ReadingList` may live inside this component (§3.3 says "may"); it has one consumer, so inline it rather
than adding a `ui/` primitive.

### Right — the contract aside

`position:sticky; top:24px`.

- **Card A** — `border-hairline-soft bg-surface rounded-xl p-5`: the micro label, two mono rows in the
  `Chip`-like treatment on `bg-canvas` with `justify-between`, a `border-hairline-soft` divider, then 13px
  `text-steel` carrying `contractBody`.
- **Card B** — a plain `Card`: the `Works with` label, then three `Chip`s.

Per correction 3, `.card` → the shipped `Card` primitive and `.tag` → the shipped `Chip` primitive
(`inline-flex rounded-sm border px-2 py-0.5 font-mono text-caption`). Use them.

**Narrow (< 900px)** — one column; the aside moves **below** the steps and loses `sticky`. Step numerals
stay 34px (they are not touch targets). **Nothing reorders.** Use the `app:` variant, mobile-first, as S7
did.

## Class translation

Follow the order S6 and S7 established: token utility → exact numeric scale → arbitrary value →
`var(--color-*)` inside an arbitrary value. `prettier-plugin-tailwindcss` rewrites class order, so do not
hand-tune it. Do not add `style={{…}}` to a landing component.

Useful exact landings: `gap-14` = 56px, `mt-11` = 44px, `gap-4` = 16px, `pb-[34px]`, `size-[34px]`,
`top-6` = 24px, `p-5` = 20px.

## Insertion — `web/src/app/page.tsx`

Insert `<AgentQuickstart />` between `<HowItWorks />` and `<Showcase />`. Add the export to
`web/src/components/landing/index.ts` following its existing comment style (a `// P11.S8 — …` line).

**`SkillSection` is S9's** — do not add it or a placeholder.

## Validation

From `web/` unless noted:

1. `pnpm typecheck` → exit 0.
2. `pnpm lint` → exit 0. (Note S6's finding: `react-hooks/set-state-in-effect` is an **error** here, so
   avoid `useEffect(() => setState(…))` patterns; this section should need no client state at all — it is a
   server component composing client `Snippet` islands.)
3. `pnpm test` → the **70** tests still pass.
4. `pnpm build` → succeeds; `/` stays `ƒ` (dynamic since P9.S6 — expected, not a regression).
5. **Zero literal copy** (acceptance check 4): `grep -nE '"[A-Za-z][A-Za-z ,.\x27—]{12,}"' web/src/components/landing/agent-quickstart.tsx`
   → no prose string literals; everything comes from `LANDING.quickstart`. Report what you grepped.
6. `grep -rn "style={{" web/src/components/landing/agent-quickstart.tsx` → no matches.
7. `grep -rn 'role="alert"\|aria-live="assertive"' web/src/components/landing/agent-quickstart.tsx` → no
   matches. Nothing in this round interrupts a screen reader on load.
8. **No copy button in the server HTML** — reuse S6's `renderToStaticMarkup` technique
   (`web/tests/snippet-ssr.test.ts`) against the real `AgentQuickstart`. Prefer adding a terse permanent
   assertion over a temp file this time: this section has **four** snippets, so the no-JS floor is worth
   holding in CI. Keep it small.
9. Confirm `#quickstart` resolves — the section renders with that id and the nav link S7 added points at it.
10. `python3 scripts/workflow.py validate` → passes.

Nothing can be verified against a live origin; the site is not deployed until P12.

## Out of scope

- No `SkillSection`, no `SkillPreview` — S9.
- No `Note` or `ReadingList` `ui/` primitive — both inline, one consumer each.
- No restyling of `how-it-works.tsx` (correction 5) and no footer change (correction 2).
- **No `globals.css` change, no new or renamed token** — the design's delta is `None.`
- No backend change, no `doc-new-version` (append one line to `## Doc impact` in `phase.md` instead).

## When done

Write `works/phases/active/P11/slices/P11.S8/result.md` from scratch (free-form): the section as it landed,
how the four corrections were applied, the inline-code helper's shape, verbatim validation output, and what
is not test-covered. Append durable cross-slice notes to `works/phases/active/P11/phase.md` — S9 builds the
sibling section and S10 verifies both, so record anything they should mirror. Do not commit and do not
change any slice or phase status.
