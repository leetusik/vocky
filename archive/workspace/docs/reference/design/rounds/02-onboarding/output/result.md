# Round 02 — result: onboarding on the landing page

**Round:** 02 · **Phase:** P11 · **Slice:** P11.S5 · **Design session:** Claude Design + operator (sugang)
**Repo:** `github.com/leetusik/vocky` — read via a **local-directory connection**, not GitHub
**Companion:** `build-prompt.md` (the implementation contract the build slices size from)
**Round 01's record** is preserved in this project at `output/round-01/` (unchanged).

This file records *what was designed and why*, and logs every departure from the handoff.
`build-prompt.md` is the buildable spec — exact values, copy strings, states, breakpoints, no-JS behaviour.

---

## 0. Repo currency — how this round read the repo

The handoff flagged GitHub `main` as **45 commits behind** local, with everything this round is about unpushed.
**Resolved by attaching the local `vocky` directory.** No push happened, `ci.yml` did not fire, and every
artifact this round designs against was read from the local working tree:

| Read | Path | Used for |
|---|---|---|
| The skill, in full (119 lines) | `skills/vocky-feedback/SKILL.md` | preview content, verify readings, trap wording, TOC |
| The installer (62 lines) | `web/public/install.sh` | prerequisite claims (`uv` bootstrap, no sudo, re-run to upgrade) |
| Round 01's applied brand | this project's `tokens.css`, `card-kit.css` | every value used below |

Nothing was designed against the stale remote.

---

## 1. The round in one paragraph

The landing page explained vocky and then stopped. This round gives it a **spine of action** that runs from
the fold to the middle of the page: an install line at the hero's foot, a four-step agent quickstart, and the
published skill readable in place. The through-line is **the two-variable contract** — the one genuinely
unusual thing about vocky's onboarding — and the design's whole job is to make two `export` lines feel like
the product feature they are, not like setup chores. Nothing is decorated. The new vocabulary is three
primitives (snippet, trap, preview pane) and one inversion nobody expects: **on this page, `400` is success.**

---

## 2. Every §6 question — answered by the operator

The operator answered **"Decide for me" to all thirteen**, delegating each decision to this session. Recorded
as delegated, with the decision and its reasoning below. No question was left to an implementer.

### 6.1 The hero — where the install line goes
**Decided: a full-width row at the hero's foot, spanning both columns, above the trust strip.**
The left column already carries eyebrow → h1 → sub → two CTAs → four proof ticks; a fifth block inside it
makes a wall, and the right column's two layered panels can't take a third element without losing the
"request → record" reading. A row across the foot, separated by a hairline and 44px, is the only place that
adds a path without competing with one. It also reads correctly on a phone, where the columns stack and the
row simply keeps its place.

### 6.1b Is `curl | bash` the primary CTA?
**Decided: no — `Start free` stays primary.** A key is a precondition for the CLI (the install line's own
next step is `vocky signup`), so promoting install above signup would sequence the page wrong. The install
row is **prominent by position, quiet by weight**: a mono row with a secondary copy button, not a filled
button. To keep it from reading as an afterthought, it carries a hard peer statement — *"Or skip it — the
same capture is one REST call."*

### 6.2 Two sections or one?
**Decided: two.** They answer different questions ("how do I start?" vs. "what do I hand my agent?") and
they have different shapes — one is a numbered procedure, the other is a document reader. Fusing them would
have produced exactly the monolith the handoff forbids at card level, and the same objection applies on the
page. Two sections also let the tone ramp alternate properly (canvas → surfaceSoft).

### 6.2b Page order
**Decided: positions 4 and 5 — directly after `How it works`, before `Showcase`.**
`How it works` ends with the reader understanding the mechanism; the honest next beat is *do it*. Placing
onboarding after `Features`/`Pricing` would make it a footnote to a sales page, and placing it above
`How it works` would ask for a shell command before the mechanism was explained. Full order:
Hero (+install) · Trust strip · How it works · **Agent quickstart** · **The skill** · Showcase · Features ·
Pricing · Closing CTA.

### 6.3 The nav
**Decided: one new entry — `Get started` → `#quickstart`, placed second.** Five links is the ceiling this nav
can hold at 14px without crowding the two right-hand buttons. The skill takes an anchor (`#skill`) and an
in-page link from the end of the quickstart, but does not spend a nav slot: nobody arrives looking for a
skill file by name, they arrive looking for how to start.

### 6.4 Traps and caveats
**Decided: two distinct weights, and a trap is amber — never red.**
- **Weight 1 — note** (the shipped `.note`: 2px green left rule): the `~/.zshenv` reasoning. It is
  *rationale*, not a hazard; it explains why a repo `.env` cannot work.
- **Weight 2 — trap** (net-new, built entirely on round 01's shipped caution tokens): the Codex
  `network_access` gap. A bordered amber block, mono uppercase label naming its scope
  (**Known trap · Codex only**), preceded by a 7px rotated square — no warning glyph, no emoji.

It avoids reading as an error three ways: **hue** (caution amber vs. danger red, both already in the system),
**tense** (it describes something to add before anything breaks, not something that broke), and **semantics**
(a plain `<aside>` with no `role="alert"` — nothing is announced on load). Card *Components / Note vs. trap
vs. error* shows all three weights adjacent so the distinction is reviewable, not asserted.

### 6.5 How much of the 119 lines shows
**Decided: the first 22 lines — frontmatter band plus the lede, `## 1`, and the two-export block — in a
380px scroller with a bottom fade and a `Show the whole file` toggle that raises the cap to 640px.**
Twenty-two lines is the smallest excerpt that proves the file's *character*: a reader sees the trigger
description, the section numbering, prose density, and a real fenced command. A scroller (rather than a hard
clip) means a no-JS visitor can still read all 119 lines. Expanded caps at 640px rather than going unbounded —
the page must not grow by a screen and a half.

### 6.5b Treatment inside the preview
**Decided: frontmatter distinct, body plain — no syntax colouring at all.**
The frontmatter is split at the closing `---` and given a tinted band; that is the *only* structural
distinction. The repo ships no highlighter, and hand-rolled colouring for a markdown file that contains bash
*and* json fences would be wrong in a way readers can see. Plain mono at 12.5px/1.62 also removes any
temptation to transform the text — which matters, because the parity gate means the bytes on screen must be
the bytes served.

### 6.6 Copy affordances
**Decided: one primitive, two sizes.** `Snippet` (row: one line, 48px, inline button) and `Snippet` (block:
multi-line, dark, label + button in a bar). The block deliberately inherits the shipped `EndpointCard`
palette so a terminal on this page looks like a request panel elsewhere on it. Four copyable things, one
mechanism, one clipboard rule: **the clipboard gets the element's `textContent`, never a re-typed string.**

### 6.6b Copied, and copy failure
**Decided: label swap with a 2s revert; failure selects the text and names the shortcut.**
Copied → `✓ Copied` on green-soft/mint, announced once through a polite live region, back to idle after 2s.
Failure → the button becomes `Copy failed` in caution tones, the border goes caution, **the command text is
programmatically selected**, and a mono hint appears: *"The command is selected for you — press ⌘C (Ctrl+C)."*
The failure state persists until the next attempt; it is the one case where a state that fixed nothing must
not disappear on a timer.

### 6.7 Download vs. Copy
**Decided: Copy primary, Download a secondary text link.** The skill's destination is an agent's skills
directory or a chat window — both are paste targets. `Copy the skill` is the filled button; `Download SKILL.md`
is a plain anchor beside it (and is also the no-JS survivor, per the locked floor). The byte/line meta lives
in the pane header, where it informs the read rather than decorating the button.

### 6.8 Two audiences, one page
**Decided: one continuous story, with the agent path clearly recommended and REST named as its equal
alternative.** No tabs, no split. The quickstart is labelled *"Get started · for agents"* and ends with a
peer line — *"No install, or not zsh? The same capture is one `POST /api/feedback` with the same bearer key"*
— pointing at the skill, which documents Path B in full. The backend integrator was never orphaned: the hero
still shows a raw request, and the install row says out loud that the CLI is optional.

### 6.9 Prerequisites
**Decided: bare command, one mono caption under it.** `no sudo · installs uv if it's missing · re-run any
time to upgrade` — twelve words, all three verified in `install.sh`. A prerequisites *list* would imply
friction the installer removes; silence would leave the reader wondering whether they need `uv` first.

### Reference / variations
No reference was supplied. Variations were delegated too; **one committed direction per surface** was
designed rather than parallel options, since every §6 answer was delegated and diverging on all of them at
once would produce a matrix to arbitrate rather than a design to land.

---

## 3. What was designed — the card set

Thirteen cards, one per reviewable unit, in three groups. All link `tokens.css` (which imports `card-kit.css`).

**Landing** — `Hero + install row` (desktop) · `Hero + install row · narrow` (440px) ·
`Agent quickstart` · `Skill on the landing` · `Page order + anchors`
**Components** — `Snippet — row + block` · `Note vs. trap vs. error` · `Nav — one new entry` ·
`Preview pane — collapsed`
**States** — `Preview pane — expanded` · `Copy — idle / copied / failed` ·
`Verify — success & failure readings` · `No JavaScript`

## 4. Token delta

**None.** Every value used already exists in round 01's `tokens.css` — including the whole caution family
(`--color-caution`, `--color-caution-deep`, `--color-surface-caution`, `--color-hairline-caution`), which had
no consumer until this round and now carries the trap treatment. The new vocabulary is *composition*, not new
tokens: it is expressed as specimen classes in `card-kit.css` under a `Round 02 additions` heading, and as
three real components in `build-prompt.md` §3.

## 5. Locked floors — each one, verified

- **`VOCKY_BASE_URL` / `VOCKY_API_TOKEN`** — used verbatim everywhere they appear; never abbreviated,
  never re-cased, never wrapped mid-name.
- **The install command** — `curl -fsSL https://vocky.hi2vi.com/install.sh | bash`, one line, `white-space: pre`,
  horizontal scroll on overflow. It never reflows, at any width, and the clipboard takes the node's text.
- **No `vk_live_`** — the only key shown anywhere is `vk_...` (and `vk_…` in the contract aside).
- **Nested `source.product`** — the hero payload is reproduced byte-for-byte from the corrected version;
  no new payload was introduced that could regress it.
- **Preview derives from the served file** — designed as a *server read* of `/SKILL.md` at request time
  (§3.4 of `build-prompt.md`), never a pasted excerpt. The card's text is a specimen of that read.
- **a11y / reduced motion** — `word-break: keep-all` inherited from the kit; the only motion is a 150ms
  colour transition on buttons and a `max-height` change on expand, both of which drop to instant under
  `prefers-reduced-motion`. Amber and green are never the sole carrier of meaning.
- **No-JS stated** — its own card, and §7 of `build-prompt.md`.

## 6. Departures from the handoff — logged

1. **`output/` collision.** Round 01's `result.md` / `build-prompt.md` occupied this project's `output/`.
   They were **copied to `output/round-01/` unchanged** before round 02 was written to the canonical
   `output/result.md` / `output/build-prompt.md`. Nothing was edited or deleted.
2. **Cards this round did not draw.** The handoff's starting list included *"the install row / snippet
   primitive on its own"* (drawn), and implied a separate card for the verify snippet (drawn) — but no card
   was made for a *narrow* quickstart or skill section. Their stacking is specified numerically in
   `build-prompt.md` §6 instead; both are single-column reflows with no reordering, and a card would have
   added review surface without a decision in it.
3. **A statement the handoff did not ask for.** Card *States / No JavaScript* asserts a server-render
   (not client-fetch) for the preview. That is arguably an implementation choice, but it is stated in the
   design because it is the only shape that keeps *both* the no-JS floor and the parity gate.
4. **Line/byte figures.** The handoff cites *119 lines, 7,975 bytes*; the local file measures 120 lines by
   `wc -l` convention (119 content lines + trailing newline). Cards display `119 lines · 7,975 bytes`, and
   `build-prompt.md` requires both numbers be **computed from the served file**, never hardcoded — so the
   discrepancy cannot ship.
5. **Nothing in the existing landing copy was touched**, and no shipped component was restyled.

## 7. What this round did not decide

- Whether `/install.sh` and `/SKILL.md` get a cache policy — a production bring-up question.
- Whether the dashboard's key-mint flow should link back to `#quickstart` (plausible, out of scope).
- Korean copy for the three new surfaces. The page is bilingual-capable and the new strings are English-only,
  same as the shipped landing; if the next phase localizes, these strings localize with it.
