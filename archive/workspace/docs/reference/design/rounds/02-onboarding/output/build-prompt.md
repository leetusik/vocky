# Round 02 — build-prompt: the implementation contract

**Round:** 02 · **Phase:** P11 · designed at **P11.S5**, built by the slices **P11.DECOMP2** cuts
**Repo:** `github.com/leetusik/vocky` · **Companion:** `result.md` (decisions & rationale)
**This file is self-sufficient.** Executors have no access to the design project — every value, string,
state and breakpoint needed to build these three surfaces is below.

> ## RESPECT THE DESIGN — put this in every slice plan and executor prompt
> Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> **Do not drop, simplify, restyle, or "improve" a designed element to save effort** — that is a correctness
> failure, not a shortcut. Where an exact value isn't specified here, pick the option closest to the designed
> intent, **never a plainer fallback**. This round implies **no backend change** and **no new token** (§1).

---

## 1. Token delta

**None.** Every value below resolves to an existing `@theme` token in `web/src/app/globals.css`. The caution
family (`--color-caution` `#C6820E`, `--color-caution-deep` `#8F5C06`, `--color-surface-caution` `#FBF3E3`,
`--color-hairline-caution` `#EEDCB2`) is shipped but previously unused on the landing; it now carries the trap
treatment. **Do not add a token. Do not rename one.**

## 2. Page composition — `web/src/app/page.tsx`

Insert two sections between `HowItWorks` and `Showcase`:

| # | Component | Tone | Reveal | id |
|---|---|---|---|---|
| 1 | `Hero` *(modified — §3.1)* | `default` | no | — |
| 2 | `TrustStrip` | `surfaceSoft` | — | — |
| 3 | `HowItWorks` | `surface` | — | `how` |
| **4** | **`AgentQuickstart`** *(new)* | **`default`** | **yes** | **`quickstart`** |
| **5** | **`SkillSection`** *(new)* | **`surfaceSoft`** | **yes** | **`skill`** |
| 6 | `Showcase` | `default` | — | — |
| 7 | `Features` | `surface` | — | `features` |
| 8 | `Pricing` | `default` | — | `pricing` |
| 9 | `ClosingCTA` | `forest` | — | — |

`web/src/content/section-ids.ts` — add exactly two entries: `quickstart`, `skill`. (`SectionId` is typed;
the sections cannot compile without them.)

`landing-nav.tsx` — add **one** link, in second position:
`How it works · Get started · Features · Pricing · Docs`. `Get started` → `#quickstart`.
Active state (reader inside the section, same mechanism the existing nav uses if any; otherwise none):
`color: var(--color-green-dark); background: var(--color-green-soft); font-weight: 600`.
`#skill` gets **no** nav link.

## 3. New components

All copy lives in `web/src/content/landing.ts` under a new `LANDING.quickstart` / `LANDING.skill` /
`LANDING.heroInstall` shape — **no literal strings in components** (round 01's house rule holds). Every string
below is final copy; use it verbatim.

### 3.1 `Snippet` — `web/src/components/ui/snippet.tsx`

One primitive, two variants. Server-rendered shell + a client copy button.

```
<Snippet variant="row"   label?  command />        // one line, light
<Snippet variant="block" label   command />        // multi-line, dark
```

**Row** — `display:flex; align-items:center; gap:10px; min-height:48px; padding:5px 6px 5px 14px;`
`border:1px solid var(--color-hairline-strong); background:var(--color-canvas); border-radius:10px`
The command: `<code>` — `font-family:var(--font-mono); font-size:13.5px; line-height:1.5;`
`color:var(--color-ink); white-space:pre; overflow-x:auto; flex:1; min-width:0`.
**`white-space:pre` + `overflow-x:auto` is a locked floor** — the command must never wrap or truncate, at any
width. Horizontal scroll is correct; reflow is a bug.

**Block** — `border:1px solid var(--color-forest-soft); background:var(--color-forest-mid);`
`border-radius:12px; overflow:hidden`.
Bar: `padding:7px 8px 7px 14px; background:var(--color-ink); border-bottom:1px solid var(--color-hairline-dark)`,
label mono 11px / `letter-spacing:.7px` / uppercase / 700 / `var(--color-trust-sage)`, button pushed right.
`<pre>`: `padding:14px; font:var(--font-mono) 13px/1.65; color:#DCEBE3; white-space:pre; overflow-x:auto`.
Comment lines inside a block render `var(--color-trust-sage)` and **are included in the copy** (valid shell).

**Copy button** (`cbtn`) — mono 12px/500, `letter-spacing:.3px`, `min-height:36px`, `padding:0 12px`,
`border-radius:8px`, `border:1px solid var(--color-hairline-strong)`, `background:var(--color-canvas)`,
`color:var(--color-slate)`; hover `background:var(--color-surface); color:var(--color-charcoal)`; 150ms ease.
On dark: `background:transparent; border-color:var(--color-hairline-dark); color:var(--color-on-dark-muted)`;
hover `background:rgba(255,255,255,.1); color:#fff`.

**Clipboard rule (locked):** copy the DOM node's `textContent`, never a separately-typed string. Reuse the
proven mechanics in `show-once-key.tsx` (`navigator.clipboard.writeText` + explicit failure branch); do not
lift its alert-box UI.

### 3.2 `Trap` — `web/src/components/ui/trap.tsx`

A `<aside>`. `border:1px solid var(--color-hairline-caution); background:var(--color-surface-caution);`
`border-radius:10px; padding:14px 16px`.
Label: `display:flex; align-items:center; gap:8px`, mono 11px, `letter-spacing:.8px`, uppercase, 700,
`var(--color-caution-deep)`, with a `::before` of `width/height:7px; background:var(--color-caution);`
`transform:rotate(45deg)`. **No icon component, no emoji, no `role="alert"`, no `aria-live`.**
Body: 13.5px/1.6 `var(--color-slate)`; inline `<code>` mono 12.5px on `rgba(14,26,22,.055)`, radius 4, `1px 5px`.

Rationale that is *not* a hazard uses the existing note treatment instead: 13px `var(--color-steel)`,
`border-left:2px solid var(--color-green)`, `padding-left:12px`.

### 3.3 `ReadingList` — the verify readings (may live inside `AgentQuickstart`)

Rows separated by `1px solid var(--color-hairline-soft)`, `padding:11px 0`, 13.5px/1.55 `var(--color-slate)`.
Status chip: mono 12px/700, `border-radius:6px`, `padding:3px 8px`, `min-width:52px`, centred —
`400` → `background:var(--color-green-soft); color:var(--color-green-dark)`;
`401` → `background:var(--color-surface-danger); color:var(--color-danger-deep)`;
`else` → `background:var(--color-surface-caution); color:var(--color-caution-deep)`.
The chip always repeats the literal code — colour is never the sole signal.

### 3.4 `SkillPreview` — `web/src/components/landing/skill-preview.tsx`

**Server component. Reads the served file at request time** — `fs.readFile` on
`public/SKILL.md` (or a fetch of `/SKILL.md` on the same origin), **never a pasted excerpt.** A hand-copied
excerpt forks silently from the byte-parity gate (`scripts/skill_parity.py`) and is a build failure of intent
even when CI is green.

Split the file once on the closing frontmatter `---`:

- **Header** — `padding:9px 10px 9px 14px; background:var(--color-surface); border-bottom:1px solid var(--color-hairline)`.
  Left: filename `SKILL.md`, mono 12px/500 `var(--color-charcoal)`. Then the meta, mono 11px
  `var(--color-steel)`: `<lines> lines · <bytes> bytes`. **Both numbers are computed from the file just read**
  (`content.split("\n").length - 1` and `Buffer.byteLength(content)`) — hardcoding them is forbidden; they
  drift the moment the skill is edited. Right: `Copy` button + `Download` anchor.
- **Frontmatter band** — `background:var(--color-surface-archive); border-bottom:1px solid var(--color-hairline);`
  `padding:12px 16px`; mono 12px/1.6 `var(--color-steel)`; `white-space:pre-wrap; word-break:break-word`.
  Include the `---` fences. This is the **only** structural distinction in the pane.
- **Body** — `max-height:380px; overflow:auto; position:relative`; `<pre>` `padding:14px 16px`, mono
  12.5px/1.62 `var(--color-slate)`, `white-space:pre-wrap; word-break:break-word`.
  **No syntax highlighting.** No markdown rendering. No library.
  Collapsed shows the **first 22 lines of the body** (through the `Put these in ~/.zshenv, never a repo .env:`
  line). Fade overlay: `position:absolute; inset:auto 0 0 0; height:110px; pointer-events:none;`
  `background:linear-gradient(to bottom, rgba(255,255,255,0), var(--color-canvas) 78%)`.
- **Footer** — `padding:9px 12px; border-top:1px solid var(--color-hairline); background:var(--color-surface)`.
  Left, mono 11.5px `var(--color-steel)`: collapsed `Showing the first 22 of <lines> lines`; expanded
  `Showing all <lines> lines · served verbatim at /SKILL.md`. Right: the toggle.

**Expanded** — body `max-height:640px` (still a scroller), fade removed, body text = the whole file,
toggle label `Collapse`. Never unbounded.

## 4. Surface 1 — the hero install row (`hero.tsx`)

**Nothing inside the existing hero grid changes.** The h1, sub, both CTAs, the four proof ticks, the
`EndpointCard` payload and the layered captured-record `Card` all stay exactly as shipped. The corrected
payload (nested `source.product`, no `vk_live_`) **must not be edited**.

Append, inside the hero container, below the two-column grid:

`margin-top:44px; padding-top:26px; border-top:1px solid var(--color-hairline)`, then a
`grid-template-columns:auto minmax(0,1fr); gap:28px; align-items:center`:

- **Left** — micro label, uppercase mono-ish 11px/700/`letter-spacing:.8px`, `var(--color-green-dark)`:
  **`Install the CLI`**. Under it, 13px `var(--color-steel)`, `max-width:22ch`:
  **`Or skip it — the same capture is one REST call.`**
- **Right** — `<Snippet variant="row">` with, verbatim:
  **`curl -fsSL https://vocky.hi2vi.com/install.sh | bash`**
  and beneath it a mono 11.5px `var(--color-steel)` caption:
  **`no sudo · installs uv if it's missing · re-run any time to upgrade`**

`Start free` stays the primary CTA. The install row is never a filled button.

**Narrow (< 900px, `--breakpoint-app`):** the label block sits above the snippet (single column, `gap:10px`);
the caption keeps only `no sudo · installs uv if it's missing`; the row itself is unchanged and the command
still scrolls rather than wraps. Hero CTAs go full-width stacked (existing behaviour).

## 5. Surface 2 — `AgentQuickstart` (`web/src/components/landing/agent-quickstart.tsx`)

`Section tone="default" id="quickstart" reveal`. Padding `84px 28px`; container `1180px`.

**Header** (`max-width:70ch`)
- Eyebrow (existing `.eyebrow` treatment, green dot + uppercase): **`Get started · for agents`**
- h2 at `--text-heading-1` (38px): **`Two variables, and your coding agent can capture.`**
- Lede 18px/1.6 `var(--color-steel)`: **`The whole agent contract is two environment variables — no plugin, no SDK, no config file. Export them once and every coding agent on the machine gets the same access.`**

**Body** — `grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr); gap:56px; margin-top:44px; align-items:start`.

### 5.1 Left: four steps
Step marker = the shipped `HowItWorks` step numeral: 34px circle, `background:var(--color-ink)`, white mono
700 15px. Step gap `16px`; each step's content block `padding-bottom:34px`. Step title at
`--text-heading-4` (18px/700) `var(--color-charcoal)`; step sub 15px/1.6 `var(--color-steel)`, `max-width:62ch`;
content `margin-top:14px`.

**1 · `Install the CLI`**
sub: **`One line. It bootstraps `uv` if you don't have it and needs no sudo.`**
`<Snippet variant="row">` `curl -fsSL https://vocky.hi2vi.com/install.sh | bash`

**2 · `Export the two variables`**
`<Snippet variant="block" label="~/.zshenv">` containing exactly:
```
# ~/.zshenv
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."
```
then the **note** (weight 1), verbatim:
**`Put them in ~/.zshenv, never a repo .env. A repo .env is never auto-loaded by Claude Code or Codex, so a resolver never sees it — and a key in a repo file is one commit away from leaking. ~/.zshenv is sourced by every zsh invocation, so every Bash call, every Codex exec, and every repo you work in inherits it.`**
(`~/.zshenv`, `.env`, `exec` as inline `<code>`.)
then the **trap** (weight 2), label **`Known trap · Codex only`**, body verbatim:
**`The workspace-write sandbox denies outbound network by default, so the capture POST fails silently. Add network_access = true under [sandbox_workspace_write] in ~/.codex/config.toml. Claude Code needs no equivalent change.`**
(`workspace-write`, `network_access = true`, `[sandbox_workspace_write]`, `~/.codex/config.toml` as inline `<code>`.)

**3 · `Verify before you capture anything`**
sub: **`This writes nothing. It only proves the two variables are right.`**
`<Snippet variant="block" label="verify">` containing exactly:
```
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $VOCKY_API_TOKEN" \
  "$VOCKY_BASE_URL/api/feedback"
```
then the `ReadingList`, verbatim:
- `400` — **`Ready.`** `The token authenticated; the endpoint only rejected a bare GET for a missing filter.`
- `401` — **`Stop.`** `The key is wrong, revoked, or VOCKY_API_TOKEN is unset. Fix the key — don't retry, don't fall back to another path.`
- `else` — `Connection refused, timeout, DNS failure — VOCKY_BASE_URL is wrong or the service is unreachable.`

**No retry advice on 401** — the published skill says stop; the page must not contradict it.

**4 · `Capture`**
`<Snippet variant="row">` `vocky capture "결제를 못 했습니다" --product acme-web --value 2`
then a result line, `margin-top:10px`, `display:flex; gap:8px; align-items:center`: a `Captured` badge
(`background:var(--color-green-soft); color:var(--color-green-dark)`, mono 11px, pill) followed by mono 11.5px
`var(--color-steel)`: **`request_id 8f3c1d2e-4a77-4b19-9f0c-2b7d5e6a1c34`**.

**Peer line** (a fifth step row with a `var(--color-surface-soft)` / `var(--color-steel)` `·` marker instead
of a numeral), 15px `var(--color-steel)`:
**`No install, or not zsh? The same capture is one POST /api/feedback with the same bearer key — the skill spells out the REST path.`**
"the skill" links to `#skill`.

### 5.2 Right: the contract aside (`position:sticky; top:24px`)
Card A — `border:1px solid var(--color-hairline-soft); background:var(--color-surface); border-radius:14px; padding:20px`:
- micro label `The contract`
- two mono rows (existing `.tag` treatment on `var(--color-canvas)`, `justify-content:space-between`):
  `VOCKY_BASE_URL` / `host` · `VOCKY_API_TOKEN` / `vk_…`
- hairline-soft divider, then 13px `var(--color-steel)`:
  **`Both are read by the CLI, the REST path and /mcp alike. A vk_ key has no test tier — mint one with vocky keys mint or take one from the dashboard.`**

Card B — plain `.card`: micro label `Works with`, then three `.tag` chips: `Claude Code`, `Codex`,
`any zsh shell`.

**Narrow (< 900px):** one column; the aside moves **below** the steps and loses `sticky`. Step numerals stay
34px (they are not touch targets). Nothing reorders.

## 6. Surface 3 — `SkillSection` (`web/src/components/landing/skill-section.tsx`)

`Section tone="surfaceSoft" id="skill" reveal`. Padding `84px 28px`; container `1180px`.
`grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr); gap:56px; align-items:start`.

**Left** (`position:sticky; top:24px`)
- Eyebrow: **`Agent skill`**
- h2 at `--text-heading-2` (30px): **`Hand your agent the whole procedure.`**
- 15px/1.6 `var(--color-steel)`, `max-width:46ch`: **`vocky-feedback is a published skill file: the two-variable setup, the verify step, three capture paths and an error table branch by branch — written to be followed verbatim, not interpreted.`** (`vocky-feedback` as inline `<code>`.)
- Actions, `gap:12px`, `margin-top:22px`: primary button **`Copy the skill`** (copies the whole served file);
  beside it a plain anchor **`Download SKILL.md`** → `href="/SKILL.md" download`.
- Mono 11.5px `var(--color-steel)`: **`served verbatim at vocky.hi2vi.com/SKILL.md · MIT`**
- hairline-soft divider, micro label **`What's inside`**, then a 7-item list (mono tabular index +
  13px `var(--color-slate)`), verbatim:
  1. `Set up the two-variable contract` 2. `Verify before you capture anything`
  3. `Path A — capture with the CLI` 4. `Path B — raw REST` 5. `Path C — /mcp`
  6. `Error handling — branch by branch` 7. `Report back`

**Right** — `SkillPreview` (§3.4), collapsed by default.

**Narrow (< 900px):** one column, left block first, `sticky` dropped; preview body `max-height:300px`
collapsed / `480px` expanded. Actions go full-width stacked.

## 7. States — normative

| State | Trigger | Presentation | Duration |
|---|---|---|---|
| Copy idle | — | `Copy`, canvas/hairline-strong | — |
| Copy done | `writeText` resolves | `✓ Copied`, `background:var(--color-green-soft)`, `border-color:var(--color-security-mint)`, `color:var(--color-green-dark)`; on dark `background:rgba(190,233,213,.16)`, `border-color:var(--color-security-teal)`, `color:var(--color-victory-lime)` | **2000ms**, then idle |
| Copy failed | `writeText` rejects / no secure context | `Copy failed`, `background:var(--color-surface-caution)`, `border-color:var(--color-hairline-caution)`, `color:var(--color-caution-deep)`; the row's border → `var(--color-hairline-caution)`; **the command text is selected programmatically** (`Range` + `Selection`); mono 11.5px `var(--color-caution-deep)` hint appears: **`The command is selected for you — press ⌘C (Ctrl+C).`** | **persists** until the next attempt |
| Preview collapsed | default | 380px scroller + fade, footer `Showing the first 22 of <n> lines`, toggle `Show the whole file` | — |
| Preview expanded | toggle | 640px scroller, no fade, footer `Showing all <n> lines · served verbatim at /SKILL.md`, toggle `Collapse` | — |

**Announcements:** one polite live region per copy button; on success it receives `Copied the install command.`
(substitute the snippet's own label). Nothing is announced on failure beyond the visible hint — the selection
plus the hint is the affordance. No `role="alert"` anywhere in this round.

**Motion:** the only transitions are 150ms colour on buttons and the `max-height` change on expand. Both
become instant under `prefers-reduced-motion: reduce`. The `Reveal` wrapper's existing reduced-motion
behaviour applies unchanged to both new sections.

## 8. No-JavaScript behaviour — locked

- **Copy buttons are client islands that render only after mount.** A no-JS visitor sees **no button at all** —
  never a present, inert control. The snippet row keeps its border, padding and selectable text; the block's
  bar keeps its label and simply has no button.
- **The preview pane is server-rendered with the file already in the HTML.** Its body is a native scroller
  (`max-height:380px; overflow:auto`), so all 119 lines are readable without JS. The expand toggle is a client
  island and is absent; the footer instead reads `<n> lines · scroll to read · served verbatim at /SKILL.md`
  and offers a plain anchor `Open the raw file` → `/SKILL.md`.
- **`Download SKILL.md` is a plain `<a download>`** and works with JS disabled, always. This is the locked
  floor from the handoff.
- `Copy the skill` (the section's primary button) is likewise client-only; with no JS the Download anchor is
  the sole action, and that is acceptable because it is the durable one.

## 9. A11y floor

- Both sections are `<section>` with an `<h2>`; steps are an ordered list semantically.
- `word-break: keep-all` on h1–h6 (global, round 01) — the new headings are English but the rule stays.
- Focus ring: `2px solid var(--color-green-deep)`, `offset 2px` on every button, anchor, and the two scrollers
  (the pane body is focusable so it is keyboard-scrollable).
- Contrast: `caution-deep` on `surface-caution` 6.1:1; `green-dark` on `green-soft` 6.9:1; `steel` on canvas
  6.4:1; `#DCEBE3` on `forest-mid` 9.4:1. The status chips carry their literal code, the trap carries the word
  "trap" — colour is never load-bearing alone.
- The trap is an `<aside>`, not an alert. Nothing in this round interrupts a screen reader on load.

## 10. Change manifest

| File | Change |
|---|---|
| `web/src/app/page.tsx` | insert `AgentQuickstart` + `SkillSection` at positions 4–5 |
| `web/src/content/section-ids.ts` | add `quickstart`, `skill` |
| `web/src/content/landing.ts` | add `heroInstall`, `quickstart`, `skill` copy blocks (every string in §4–§6) |
| `web/src/components/landing/hero.tsx` | append the install row below the grid; **grid contents untouched** |
| `web/src/components/landing/landing-nav.tsx` | one new link, second position |
| `web/src/components/landing/agent-quickstart.tsx` | **new** |
| `web/src/components/landing/skill-section.tsx` | **new** |
| `web/src/components/landing/skill-preview.tsx` | **new** — server read of `/SKILL.md`, split at frontmatter |
| `web/src/components/ui/snippet.tsx` | **new** — row + block, client copy island |
| `web/src/components/ui/trap.tsx` | **new** |
| `web/src/app/globals.css` | **no change** (no token delta) |
| backend / `POST /api/feedback` | **no change** |

## 11. Acceptance checks

1. `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` copied from any width pastes as one unbroken line.
2. The preview's line and byte counts change automatically when `skills/vocky-feedback/SKILL.md` changes
   (edit a line locally, rebuild, watch the header) — proving no hardcode and no forked excerpt.
3. With JS disabled: no copy button is visible anywhere, the pane still shows the file and scrolls, and
   `Download SKILL.md` downloads it.
4. `grep` the new components for literal copy → zero hits (all strings in `landing.ts`).
5. No `vk_live_` anywhere; no flat `source_product` anywhere; the hero payload diff is empty.
6. The trap block has no `role="alert"` and no `aria-live`.
7. Nav has exactly five links; `#quickstart` and `#skill` both scroll to their sections.
