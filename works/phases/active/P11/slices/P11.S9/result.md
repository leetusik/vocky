# P11.S9 — result: `SkillSection` + `SkillPreview` landed at page position 5

The landing's third round-02 surface is live in the composition: `AgentQuickstart` → **`SkillSection`** →
`Showcase`. S8's peer link to `#skill` now resolves. The pane reads the **served** `web/public/SKILL.md`
at request time, computes its own line/byte counts, and ships **every one of its 119 lines in the server
HTML** with **zero `<button>` elements** anywhere in the section.

Nothing here was checked against a live origin: `https://vocky.hi2vi.com/SKILL.md` still 404s and does so
until P12 deploys. Everything below was proven against a local `next start` production server instead.

---

## 1. What landed

| File | Kind | What it is |
|---|---|---|
| `web/src/components/landing/skill-section.tsx` | **new**, server | §6 — the section: sticky left column + the pane |
| `web/src/components/landing/skill-preview.tsx` | **new**, server | §3.4 — reads + parses + measures the served file, renders header/band/body |
| `web/src/components/landing/skill-preview-body.tsx` | **new**, client | the scroller + fade + footer; owns `expanded` |
| `web/src/components/landing/skill-copy-button.tsx` | **new**, client | "copy the whole served file", used twice |
| `web/src/components/landing/skill-shared.ts` | **new**, plain | the pane's DOM id + the shared small-control class |
| `web/src/components/landing/inline-code.tsx` | **new**, plain | S8's `withInlineCode` + `INLINE_CODE_CLASS`, **lifted** |
| `web/src/components/landing/agent-quickstart.tsx` | edited | now imports the lifted helper (behaviour unchanged) |
| `web/src/components/landing/index.ts` | edited | exports `SkillSection` |
| `web/src/app/page.tsx` | edited | `<SkillSection />` at position 5 + comment |
| `web/tests/skill-preview-ssr.test.ts` | **new** | 5 tests; the permanent CI proof of the no-JS floor |

`web/public/SKILL.md`, the canonical skill, `globals.css`, `ui/*` and the backend are all **untouched**.
No token was added or renamed. No `doc-new-version` was run.

## 2. The server/client split as it landed

```
SkillSection (server)
└─ SkillPreview (server, async)          ← fs.readFile("public/SKILL.md"), parse, measure
   ├─ header (server)  filename · "119 lines · 7975 bytes" · [Copy] · <a download>
   │   └─ SkillCopyButton (client, mount-gated → renders NOTHING pre-hydration)
   └─ SkillPreviewBody (client)          ← owns useState(expanded) + useIsHydrated()
      ├─ <div id="skill-file-content">   ← textContent === the served file, byte for byte
      │   ├─ {frontmatter}  server-rendered band  (prop, not children)
      │   └─ <div relative> <div tabIndex=0 max-h-…> {body} </div> <fade/> </div>
      └─ footer  (hydrated ? footerCollapsed/footerExpanded + toggle
                           : footerNoJs + "Open the raw file" anchor)
```

Both the frontmatter band and the body arrive as **`ReactNode` props rendered on the server**, so the
client island only ever flips a `max-height` and an opacity. That is what keeps the whole file in the HTML.

**`useIsHydrated()` was reused** for both islands (S6's `useSyncExternalStore` hook) — no
`useEffect(() => setMounted(true), [])` anywhere; `pnpm lint` is clean.

## 3. The two things that must not go wrong — how each is now nailed down

### 3.1 The full file is ALWAYS in the server HTML (correction 7)

Nothing is truncated at any layer. "Collapsed" is a **visual window only**:

| | collapsed | expanded |
|---|---|---|
| < 900px | `max-h-[300px]` + fade | `max-h-[480px]`, fade at `opacity-0` |
| ≥ 900px (`app:`) | `max-h-[380px]` + fade | `max-h-[640px]`, fade at `opacity-0` |
| body text | **the whole file** | **the whole file** (identical DOM) |

Proven three ways, two of them permanent:

1. `web/tests/skill-preview-ssr.test.ts` asserts on **`## 7. Report back`** — the file's *last* section —
   and on its final sentence, plus `expect(html).not.toContain("<button")`. A future truncation fails CI.
2. Against a real `next start` server: **all 119 non-blank lines** of `public/SKILL.md` were found inside
   the `#skill` section of the served HTML (`0` missing), and the section contained `0` `<button` elements.
3. The one `<button` on the whole page is the pre-existing **disabled Pricing CTA** from P9 — outside both
   new sections.

The fade is `pointer-events-none`, so the native scroller still scrolls without JS, and the footer's no-JS
sentence (`119 lines · scroll to read · served verbatim at /SKILL.md`) is **true as written**.

### 3.2 The preview reads the SERVED file and computes its counts

`readServedSkill()` does `fs.readFile(path.join(process.cwd(), "public", "SKILL.md"), "utf8")` at request
time; `lines = content.split("\n").length - 1`, `bytes = Buffer.byteLength(content)`. No excerpt, no
constant. `grep -n "119\|7975\|7,975"` over every new file → **no matches** (comments were reworded so the
grep stays mechanical for S10).

**Count-probe readings (validation step 6), verbatim:**

```
=== BASELINE ===           wc -l -c → 119 7975 public/SKILL.md
HEADER META : 119 lines · 7975 bytes
FOOTER      : 119 lines · scroll to read · served verbatim at /SKILL.md

=== PERTURBED (one line appended to web/public/SKILL.md, NO code change) ===
                           wc -l -c → 120 8029 public/SKILL.md
scripts/skill_parity.py → FAIL — web/public/SKILL.md is not a byte-for-byte copy … (exit 1)
HEADER META : 120 lines · 8029 bytes
FOOTER      : 120 lines · scroll to read · served verbatim at /SKILL.md

=== RESTORED ===           wc -l -c → 119 7975 public/SKILL.md
cmp public/SKILL.md ../skills/vocky-feedback/SKILL.md → identical
scripts/skill_parity.py → PASS — … matches the canonical skill byte-for-byte. (exit 0)
HEADER META : 119 lines · 7975 bytes
```

The probe harness (`tests/tmp-count-probe.test.ts`, `probe-out.txt`) was deleted afterwards;
`git status` shows `web/public/SKILL.md` unmodified.

**Bytes render raw (`7975`), not `7,975`** — §3.4 gives the formula `Buffer.byteLength(content)` with no
formatting, and `toLocaleString()` would be a locale-dependent value in server-rendered HTML.

## 4. The 22-line window, and the "does the blank line count as body line 1?" question

**Decision: the body is rendered VERBATIM — the blank line after the closing `---` is kept — and the `22`
is read as counting the PANE from the file's first line (frontmatter band included), not the body.**

The plan asked me to decide the body-line-1 convention deliberately. Working it through, the question
mostly dissolves, and the part that survives is forced by the clipboard rule rather than by taste:

**(a) The rendering half is not a choice.** The pane's `textContent` is the clipboard payload (§3.1's
locked rule), and the split is lossless by construction — `frontmatter + body === content`, asserted in
the test. Stripping the body's leading blank line would make what a visitor copies **differ by one byte
from what `/SKILL.md` serves and what `scripts/skill_parity.py` gates** — the exact class of silent fork
this slice exists to prevent. So the blank line stays, in the DOM and in the clipboard.

*(Implementation note for anyone who edits the `<pre>`: HTML drops a newline immediately after a `<pre>`
start tag, and React's server renderer emits a compensating extra `\n` for exactly that reason. That is
why the raw HTML shows one more newline than the file and the parsed `textContent` shows exactly the
file's. Verified with `renderToStaticMarkup`. Do not "clean up" that leading newline.)*

**(b) The counting half: `22` counts the pane from file line 1.** Four pieces of evidence, all pointing
the same way:

1. `result.md` §6.5 spells out what collapsed shows: *"the first 22 lines — **frontmatter band** plus the
   lede, `## 1`, and the two-export block"*. The frontmatter band is **inside** the excerpt, and the
   two-export block closes at **file line 18**.
2. The footer says `Showing the first {collapsed} of {lines} lines`, and `{lines}` is **119 — the file's
   line count**. Two numbers in one sentence must share a denominator or the sentence is false. Under the
   body-line reading it would mean "the first 22 body lines of 119 file lines".
3. §3.4's parenthetical ("through the `Put these in ~/.zshenv, never a repo .env:` line" = **file line
   20**) is off by 2 under the pane reading, versus off by 7 under the body reading (DECOMP2 correction 6
   established body line 22 = file line 27, deep into `## 2`).
4. Empirically, the collapsed pane shows the 5-line band in full plus ~18 body lines in a 380px scroller
   at 12.5px/1.62 (~20.25px/line, the last ~5 under the fade) — i.e. **about the first 22 lines of the
   file**, which is what the design's own description says.

**`collapsedLines: 22` is kept exactly as authored** (correction 6) and was not "corrected" to 15.

**What this decision does and does not change:** because nothing is truncated, `collapsedLines` is used in
exactly one place — filling `{collapsed}` in the footer template. If **S10 prefers DECOMP2's body-line
reading, no code changes**: the DOM, the counts and the window are identical either way. The only thing
that would change is this paragraph.

## 5. The section-padding question S8 left open (§5/§6's literal `84px 28px`) — the argument, for S10

**Decision: same as S8 — `Section`'s shipped default (`py-section` / `md:py-section-lg` = 72/104px), no
override.** The reasoning, since S10 adjudicates both sections together and needs the argument:

- **Correction 5's rule does apply, but this is a different conflict.** Correction 5 ("explicit values are
  normative, descriptive labels are not") settled a spec value contradicting *a mislabelled shipped
  component*. Here the explicit value contradicts **the design system's own locked spacing scale**: there
  is no 84px token, and §1 forbids adding one. Honouring `84px` literally means shipping an off-system
  value on a page whose entire vertical rhythm is 72/104.
- **The horizontal half is the tell.** `28px` is not the landing's gutter: every shipped `Section` uses
  `px-5 md:px-14` (20/56px). Adopting 28px for one section would leave this section's content edge
  **misaligned with the hero, quickstart and showcase directly above and below it** — a *visible* fidelity
  failure, where 84-vs-72/104 is invisible in isolation. A designed page whose sections do not share a
  left edge is worse than one whose band heights differ from a spec sheet by 12px.
- **`84px 28px` looks like a card-kit specimen frame, not a page instruction** — the same class of artifact
  DECOMP2's correction 3 already identified for `.eyebrow` / `.note` / `.tag` / `.card`, which turned out
  to be the design tool's own specimen classes with zero counterparts in this repo. Both new sections
  carry the *identical* padding string, which is what you would expect from a kit default rather than from
  a per-section decision.
- **The container half of §6 IS honoured exactly**: `Section`'s inner container is `max-w-page` = **1180px**,
  precisely the "container 1180px" §6 asks for. Only the padding differs.
- **Page-wide precedent**: `HowItWorks`, `Showcase`, `Features`, `Pricing`, `ClosingCTA` and now
  `AgentQuickstart` all use the default. Overriding here alone would make `SkillSection` the single
  exception on the page.

**If S10 disagrees, it must flip both new sections together** (and accept a gutter that differs from every
other section) — never one, which would be strictly worse than either consistent choice.

## 6. Other design-fidelity judgment calls (S10 should not "fix" these back)

1. **The fade's containing block is a non-scrolling wrapper, not the scroller.** §3.4 puts
   `position:relative` on the body and the fade at `inset:auto 0 0 0`. Taken literally, an absolutely
   positioned child of a *scrolling* box anchors to the scrolled **content**, so the fade would sit at the
   very bottom of the whole file and be invisible in the collapsed window — the designed element would be
   effectively dropped. So the scroller is wrapped in a `relative` div and the fade is positioned against
   that: the same painted result, at the collapsed window's bottom edge, where the design puts it.
2. **The fade fades out (`opacity-0`) instead of unmounting** on expand, so the two 150ms transitions
   (`max-height`, opacity) run together rather than one popping. Reduced motion makes both instant via the
   existing global rule (correction 9 — no CSS added).
3. **The gradient is an arbitrary class**, `bg-[linear-gradient(to_bottom,rgba(255,255,255,0),var(--color-canvas)_78%)]`
   — the exact spec value, and a class rather than `style={{}}`. **Verified compiled** into
   `.next/static/chunks/*.css`, as were `max-height:380px/640px/300px/480px`, `height:110px`,
   `transition-property:max-height` and `grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr)` (the
   `app:` ones correctly nested under `@media (min-width:56.25rem)` = 900px).
4. **The pane frame is `rounded-xl border border-hairline bg-canvas`, no shadow.** §3.4 specifies the
   header/band/body/footer but never the enclosing frame; `hairline` matches the internal dividers it
   *does* specify, `rounded-xl` (14px) is the token this repo gives large panels (`Card` feature/pricing),
   and a flat panel suits a documentary artifact. Not a plainer fallback — just the unspecified edge.
5. **Header filename uses `text-caption`** (12px/500 — an exact token match for "mono 12px/500"); the meta
   uses `text-[11px]` because `text-micro` bundles 0.8px tracking + 700 weight, which the plain meta line
   must not have. This follows S8's warning about composite `--text-*` tokens: never stack a `font-*`
   override on one.
6. **One small-control treatment, three wearers** (`SKILL_CONTROL_CLASS`): the header's `Download`, the
   footer's toggle, and the footer's no-JS `Open the raw file` anchor. The footer therefore does not
   reflow when JS arrives and swaps the anchor for the button.
7. **`SkillCopyButton` carries §7's three states via its own CVA** rather than exporting
   `ui/snippet.tsx`'s private `copyButtonVariants`: that one is documented there as owned by `Snippet` and
   covers only the compact `cbtn`, while the section's action is the **primary filled button**. Colour
   lives entirely in compound variants (never stacked over a base `bg-*`) precisely because of the
   cascade trap S8 recorded.
8. **The §7 failure hint renders under the primary button only, not in the pane header** — a 9px-padded
   header bar has no room for a second line, and the failure's real affordance (the file selected
   programmatically via `Range`+`Selection`) is visible one line below either button. Both buttons still
   swap to `Copy failed` in caution tones and both select the file.
9. **The `<pre>` shows the body with no highlighting, no markdown rendering, no library** (§3.4,
   `result.md` §6.5b). The frontmatter band is the only structural distinction in the pane.
10. **`aria-expanded` on the toggle** — not specified, no copy, strictly additive a11y.

## 7. `withInlineCode` was lifted, not duplicated

S8 left `withInlineCode` / `INLINE_CODE_CLASS` file-private and explicitly deferred the decision to this
slice. `skill.lede` is the same `{ text, code[] }` shape, so they moved to
`web/src/components/landing/inline-code.tsx` **unchanged**, and `agent-quickstart.tsx` now imports them.
Two consumers is where two copies can start to drift, and the design wants both sentences to read as one
treatment. `agent-quickstart-ssr.test.ts` still passes untouched, and the quickstart's server HTML is
byte-identical in the live render.

## 8. Validation — every step, verbatim

**1. `pnpm typecheck`**
```
> vocky-web@0.1.0 typecheck /Users/sugang/projects/personal/vocky/web
> tsc --noEmit
exit=0
```

**2. `pnpm lint`**
```
> vocky-web@0.1.0 lint /Users/sugang/projects/personal/vocky/web
> eslint .
exit=0
```

**3. `pnpm test` — 73 → 78** (S8's 73 all still green, +5 new)
```
 Test Files  10 passed (10)
      Tests  78 passed (78)
```
```
 ✓ tests/skill-preview-ssr.test.ts > SkillPreview server HTML > splits the frontmatter losslessly 1ms
 ✓ tests/skill-preview-ssr.test.ts > SkillPreview server HTML > ships the WHOLE file, through its last section 0ms
 ✓ tests/skill-preview-ssr.test.ts > SkillPreview server HTML > renders no button at all pre-hydration, and the no-JS footer instead 0ms
 ✓ tests/skill-preview-ssr.test.ts > SkillPreview server HTML > keeps Download as a plain anchor to the served file 0ms
 ✓ tests/skill-preview-ssr.test.ts > SkillPreview server HTML > computes the line and byte counts from the file it just read 0ms
```

**4. `pnpm build` — exit 0, `/` still `ƒ`, zero warnings**
```
✓ Compiled successfully in 1524ms
Route (app)
┌ ƒ /
```
The first attempt **did** emit one warning, and it was mine — see §9.1.

**5. The no-JS floor, in CI** — `web/tests/skill-preview-ssr.test.ts` (above), asserting the *last*
section of `SKILL.md`, `not.toContain("<button")`, the no-JS footer with its computed count, the raw
anchor, and `href="/SKILL.md"` + `download`.

**6. Counts computed, not hardcoded** — `grep -n "119\|7975\|7,975"` over
`skill-preview.tsx`, `skill-section.tsx`, `skill-preview-body.tsx`, `skill-copy-button.tsx`,
`skill-shared.ts` → **exit 1, no matches**. Behavioural probe readings in §3.2.

**7. `python3 scripts/skill_parity.py`**
```
PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.
parity exit=0
```

**8. `grep -rn "style={{" web/src/components/landing/skill-*.tsx`** → exit 1, no matches.

**9. `grep -rn 'role="alert"' web/src/components/landing/skill-*.tsx`** (and `aria-live="assertive"`) →
exit 1, no matches. One comment mentioning the attribute was reworded so the grep stays mechanical.

**10. `#skill` resolves and S8's peer link lands on it** — against a real `next start` production server
(`HTTP 200`, 124 018 bytes):
```
id="skill" present                                  PASS
href="#skill" (S8 peer link) present                PASS
id="quickstart" present                             PASS
header meta "119 lines · 7975 bytes"                PASS
no-JS footer text present                           PASS
"Open the raw file" anchor present                  PASS
LAST section "## 7. Report back" in served HTML     PASS
final line of the file in served HTML               PASS
frontmatter description in served HTML              PASS
href="/SKILL.md" present (×3)                        PASS
download attribute present                          PASS
all 119 file lines inside the #skill section: True | missing: []
buttons in #skill section: 0
section order: quickstart < skill < showcase: True
```

**11. `python3 scripts/workflow.py validate`**
```
Workflow validation passed.
validate exit=0
```

**Extra (not required):** `npx prettier --check` on the seven new/lifted files → *All matched files use
Prettier code style!* `format:check` is not in CI and its pre-existing failures (including
`agent-quickstart.tsx`, confirmed already failing at `HEAD` before this slice) were left alone.

## 9. Deviations from `plan.md`

1. **Two extra files beyond the plan's two.** The plan describes "a small client island" without naming
   it; `"use client"` cannot live in the file that calls `fs.readFile`, so the island is
   `skill-preview-body.tsx`, the shared copy affordance is `skill-copy-button.tsx`, and two constants both
   graphs need sit in `skill-shared.ts` (**every export of a `"use client"` module becomes a client
   reference in RSC, so a server component cannot import a bare string from one** — worth remembering).
   All are `skill-*`, so the plan's greps cover them.
2. **`path.join` had to be statically analyzable.** The first build emitted:
   *"Encountered unexpected file in NFT list … A file was traced that indicates that the whole project was
   traced unintentionally"*, tracing the entire project into the standalone output because the path was
   built from a spread array constant. Two literal segments
   (`path.join(process.cwd(), SERVED_SKILL_DIR, SERVED_SKILL_FILE)`) cleared it: build is now warning-free.
   **Any later request-time `fs` read must keep its path literal at the call site.**
3. **`withInlineCode` was lifted rather than duplicated**, which touched S8's `agent-quickstart.tsx`. The
   plan sanctioned either ("reuse or lift it"); §7 above gives the reasoning.
4. **Prettier was run on the new files only.** Not a plan step; it keeps net-new files off the repo's
   unformatted list without touching the pre-existing 12.

## 10. What is NOT proven

- **Nothing was checked against a live origin.** `/SKILL.md` is a 404 until P12 deploys; the flip probe
  stays armed in the phase's hand-off section. The pane was verified against a local `next start` only.
- **No hydrated behaviour is covered by a test.** The suite is Node-env vitest with no jsdom/RTL, so the
  expand/collapse toggle, the copy click, the 2000ms revert, the `Range`+`Selection` failure path, the
  polite announcement, hover/focus visuals, the `:focus-visible` ring on the focusable scroller, and every
  `< 900px` layout are **unverified by machine**. They are S10's fidelity pass (and the same gap S6 and S8
  recorded).
- **The clipboard payload's byte parity is proven structurally, not empirically**: the split is asserted
  lossless and the pane's subtree contains only those two nodes, but no browser was driven to read
  `textContent` back and `cmp` it against `SKILL.md`. Worth doing by hand in S10.
- **The standalone runtime path was not exercised** — the `fs` read was proven under `next start` from
  `web/`, and the Dockerfile's `WORKDIR /app` + `COPY … /app/public` + `node server.js` makes
  `process.cwd()/public/SKILL.md` correct there by construction, but no container was built.
