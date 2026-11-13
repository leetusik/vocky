# P11.S6 result — primitives + copy landed

`Snippet`, `Trap`, the pure copy helper, the two `section-ids` entries and all four `landing.ts`
copy blocks are in. Nothing consumes them yet: `page.tsx`, `hero.tsx` and `landing-nav.tsx` are
untouched, so this slice is additive and the shipped landing renders exactly as before.

The three mechanics with no precedent in this repo — a mount gate, a revert timer, programmatic
text selection — are all implemented, and **the mount gate turned out to be provable in the
Node-env suite after all** (see "What tests do and do not cover").

## Files

| File | Change |
|---|---|
| `web/src/lib/clipboard.ts` | **new** — `CopyState` + the pure `attemptCopy(getText, write)` |
| `web/src/lib/use-is-hydrated.ts` | **new** — the mount gate, as a `useSyncExternalStore` hook |
| `web/src/components/ui/snippet.tsx` | **new** — `Snippet` + `snippetVariants` + `SnippetCopy` |
| `web/src/components/ui/trap.tsx` | **new** — `Trap` (no CVA; no variants) |
| `web/src/components/ui/index.ts` | barrel: both primitives + their types |
| `web/src/content/section-ids.ts` | `+quickstart`, `+skill` |
| `web/src/content/landing.ts` | `+snippet`, `+heroInstall`, `+quickstart`, `+skill` |
| `web/tests/clipboard.test.ts` | **new** — 3 cases |
| `web/tests/landing-copy.test.ts` | **new** — 3 cases, byte-lock |
| `web/tests/snippet-ssr.test.ts` | **new** — 3 cases, the §8 no-JS floor |

## The two primitives' final prop shapes

```ts
// @/components/ui — snippet.tsx
export interface SnippetCopy {
  copyLabel: string;        // "Copy"
  copiedLabel: string;      // "✓ Copied"  (the ✓ is a character, not an icon)
  copyFailedLabel: string;  // "Copy failed"
  selectionHint: string;    // shown under the snippet on failure only
  announcement: string;     // per-snippet, polite live region, success only
}

export interface SnippetProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "children">,
    VariantProps<typeof snippetVariants> {   // variant?: "row" | "block", default "row"
  label?: ReactNode;   // block: the bar label (always pass one). row: optional leading tag.
  command: string;     // the exact bytes shown AND copied
  copy: SnippetCopy;
}

// @/components/ui — trap.tsx
export interface TrapProps extends HTMLAttributes<HTMLElement> {
  label: ReactNode;      // "Known trap · Codex only"
  children: ReactNode;   // body prose; inline <code> is styled by the primitive
}
```

Call shape for S7–S9 — the four universal labels live once, the announcement is per snippet:

```tsx
<Snippet
  variant="row"
  command={heroInstall.command}
  copy={{ ...LANDING.snippet, announcement: heroInstall.copyAnnouncement }}
/>
```

`Snippet`'s root is an **unstyled wrapper**; `className` and any spread props land there, and the
bordered row/block frame is inside it. That is forced by the design: the failure hint sits *below*
the frame and the live region must not be inside a `whitespace-pre` scroller. So a consumer's
`className` is for layout (`mt-3`, `w-full`), not for restyling the frame.

## The three net-new mechanics

**1 · Mount gate (§8 — no button at all without JS).** The plan's spelling
(`useState(false)` + `useEffect(() => setMounted(true), [])`) **fails `pnpm lint`**: the React
Compiler rule `react-hooks/set-state-in-effect` rejects a synchronous `setState` in an effect body,
and it is an *error*, not a warning. Rather than suppress it I used the officially-blessed
hydration probe, extracted so S9's expand toggle can reuse it verbatim:

```ts
// web/src/lib/use-is-hydrated.ts
const subscribe = () => () => {};
export const useIsHydrated = () =>
  useSyncExternalStore(subscribe, () => true, () => false);
```

React renders and hydrates with the server snapshot (`false`), then re-renders with `true` once
hydration finishes. Identical observable behaviour to the mount effect, no hydration mismatch, no
lint suppression — and `renderToStaticMarkup` reproduces the pre-hydration frame exactly, which is
what made the floor testable.

**2 · Revert timer, and the asymmetry.** `copied` schedules a 2000ms revert to `idle`; `failed`
schedules nothing and persists until the next attempt. The handle lives in a ref, is cleared at the
top of every attempt, and is cleared again in a `useEffect` cleanup so it can never fire into an
unmounted tree. (The cleanup effect returns *only* a cleanup — no `setState` — so it is lint-clean.)

**3 · Programmatic selection.** On failure, `Range.selectNodeContents(commandNode)` +
`Selection.removeAllRanges/addRange`, then the mono `text-[11.5px] text-caution-deep` hint naming
`⌘C (Ctrl+C)`. Deliberately **not** in `lib/clipboard.ts`: that module stays DOM-free so it can be
tested in Node. Nothing is announced on failure — per §7 the selection plus the visible hint is the
whole affordance, and there is no `role="alert"` anywhere in this slice.

**Clipboard rule.** `attemptCopy`'s first argument is a *callback* that reads
`commandRef.current.textContent`, never the `command` prop. Block comment lines are recoloured with
a `<span class="text-trust-sage">`, which does not change `textContent`, so they are copied verbatim
(they are valid shell) — asserted in `snippet-ssr.test.ts`.

## `landing.ts` copy-block keys (S7–S9 consume these by name)

```
LANDING.snippet          copyLabel · copiedLabel · copyFailedLabel · selectionHint

LANDING.heroInstall      label · sub · command · caption · captionNarrow · copyAnnouncement

LANDING.quickstart       eyebrow · heading · lede
  .steps.install         n · title · sub · command · copyAnnouncement
  .steps.env             n · title · snippetLabel · command · copyAnnouncement
                         note{ text, code[] } · trap{ label, body{ text, code[] } }
  .steps.verify          n · title · sub · snippetLabel · command · copyAnnouncement
                         readings[]{ code, verdict, body }        // 400 / 401 / else
  .steps.capture         n · title · command · copyAnnouncement · resultBadge · resultText
  .peer                  before · linkLabel · after · href        // href = "#skill"
  .aside                 contractLabel · contractRows[]{ name, value } · contractBody
                         worksWithLabel · worksWith[]

LANDING.skill            eyebrow · heading · lede{ text, code[] } · copyAction · copyAnnouncement
                         downloadAction · downloadHref · served · insideLabel · inside[]
  .preview               filename · meta · downloadLabel · collapsedLines
                         footerCollapsed · footerExpanded · footerNoJs
                         expandLabel · collapseLabel · rawLabel · rawHref
```

Two shape decisions S7–S9 need to know about:

- **`quickstart.steps` is an object, not an array.** The four steps carry four different content
  shapes (row vs block snippet, note+trap vs reading list), so a `.map()` would not typecheck
  usefully; `steps.verify.readings` reads better than `steps[2].readings`. The `<ol>` ordering lives
  in the component and `n` is the numeral the design paints in the marker.
- **Rich strings are `{ text, code[] }`.** `text` is the verbatim sentence; every occurrence of each
  `code` token renders as an inline `<code>`. §5.1/§6 name exactly which tokens those are, and this
  keeps the copy one byte-checkable string instead of a segment array where a missing space at a
  boundary would be invisible. Three strings use it: `quickstart.steps.env.note`,
  `quickstart.steps.env.trap.body`, `skill.lede`. Checked: no token is a substring of another in the
  same string, so a straight split is safe.
- **`skill.preview.meta` / the three footers are templates** with `{lines}`, `{bytes}`,
  `{collapsed}`. Hardcoding a count is forbidden (§11.2); `collapsedLines: 22` is the design's window
  and correction 6 says keep it 22.

## Validation — verbatim

```
$ pnpm typecheck          # in web/
> tsc --noEmit
exit=0

$ pnpm lint
> eslint .
exit=0

$ pnpm test
 Test Files  8 passed (8)
      Tests  70 passed (70)
   Duration  215ms

$ pnpm build
✓ Compiled successfully in 1599ms
✓ Generating static pages using 11 workers (13/13)
exit=0

$ grep -rn "style={{" web/src/components/ui/snippet.tsx web/src/components/ui/trap.tsx
(no matches; exit=1)

$ grep -rn 'role="alert"\|aria-live="assertive"' web/src/components/ui/trap.tsx
web/src/components/ui/trap.tsx:13: * DELIBERATELY NOT AN ALERT — do not "fix" this into one. No `role="alert"`, no
   ^ the ONLY match is the JSDoc prohibition. The element attributes are:
$ grep -n 'role=\|aria-' web/src/components/ui/trap.tsx | grep -v ': \*'
45:          aria-hidden="true"

$ python3 scripts/skill_parity.py        # repo root
PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.
exit=0

$ python3 scripts/workflow.py validate
Workflow validation passed.
exit=0
```

Test count: **61 → 70** (the phase's documented baseline of 61 was re-confirmed before any edit).
Nine new: 3 `attemptCopy`, 3 byte-lock, 3 server-HTML.

**Validation step 7, by hand** — `snippet.tsx:304` (row `<code>`)
`min-w-0 flex-1 overflow-x-auto … whitespace-pre` and `snippet.tsx:290` (block `<pre>`)
`overflow-x-auto … whitespace-pre`. Both floors present; `snippet-ssr.test.ts` asserts them too, so
a later slice cannot quietly drop them.

**The arbitrary utilities really compiled** — since this slice introduces the repo's first `[&_…]`
descendant variant and its first `ease-[…]`, I grepped the built CSS rather than assuming:

```
$ grep -cF <selector> .next/static/chunks/3kgq1wokh54yc.css
ease-[ease] 1 · rounded-[12px] 1 · size-[7px] 1 · text-[13.5px] 1 · text-[12.5px] 1
text-[11.5px] 1 · leading-[1.65] 1 · tracking-[.7px] 1 · text-[#DCEBE3] 1
py-[5px] 1 · py-[7px] 1 · px-[5px] 1 · bg-[rgba(190,233,213,0.16)] 1
[&_code]:text-[12.5px] 1
$ grep -o '\.ease-\\\[ease\\\][^}]*}' …
.ease-\[ease\]{--tw-ease:ease;transition-timing-function:ease}
```

## What tests do and do not cover

**Newly covered, beyond what the plan expected.** `renderToStaticMarkup` reaches the pre-hydration
frame with no DOM at all, so the §8 no-JS floor **is** asserted in CI: the server HTML contains no
`<button`, contains the command as selectable text, carries `whitespace-pre` + `min-w-0 flex-1`, and
wraps block comment lines in the sage span without altering the text. That is the single highest-risk
mechanic in the slice, now regression-proof.

**Still not covered — a browser is required, and this is S10's fidelity pass:**

- the 2000ms revert and its unmount cleanup (no fake timers without a component harness);
- the `Range` + `Selection` failure path, and the failure state persisting rather than timing out;
- the polite live-region announcement actually reaching a screen reader;
- hover/focus visuals, and the copy button's dark-tone treatment inside the block bar;
- that a copied install command pastes as one unbroken line at a narrow width (§11.1) — the
  *classes* are asserted, the rendered behaviour is not;
- everything below 900px (`app:`), since no consumer renders these primitives yet.

**Not behaviorally proven, per the phase's standing rule:** nothing here was exercised against a live
site. `https://vocky.hi2vi.com/install.sh` and `/SKILL.md` still 404 — the landing and the files it
names go live together in P12.

## Deviations from `plan.md`

1. **A fifth source file, `web/src/lib/use-is-hydrated.ts`.** Forced by the lint error above. Also
   extracted rather than inlined because S9's expand toggle needs the same gate, and the plan's own
   framing ("get the shape right here and the rest of the phase inherits it") argues for one named,
   documented hook over two copies.
2. **A third test file, `snippet-ssr.test.ts`** (the plan asked for two). It converts the mount gate
   from "unprovable here" to proven; three cases, in the plan's house shape.
3. **The plan's premise "this repo has zero `style={{…}}` occurrences" is wrong** — there are **15**:
   12 in `app/apple-icon.tsx` + `app/opengraph-image.tsx` (next/og `ImageResponse`, where Tailwind
   classes cannot apply at all) and 3 in `landing/features.tsx` (`style={{ height: "40%" }}` on a
   decorative bar). The *rule* still holds and was followed — the two new components have zero — but
   a later slice should not be surprised to find them.
4. **Validation step 4's expectation is wrong**: `/` does **not** prerender as static and never has.
   `app/page.tsx` reads the session cookie (`getSession()` + `redirect`) and its own P9.S6 comment
   says so — "reading the cookie makes `/` dynamic, so it is never prerendered". `page.tsx` is
   untouched by this slice and `/` is `ƒ` before and after; phase.md's DECOMP2 notes already record
   this correctly. The real intent of the check (nothing here made the landing *more* dynamic) holds.
5. **`skill.preview`'s copy is included**, though the plan's deliverable 5 named only the three
   blocks. §3.4/§7's preview strings are user-visible copy inside §6's surface, and acceptance check
   4 forbids literals in `SkillPreview` — leaving them out would have forced S9 to either add them
   anyway or inline them.
6. **Step 1's sub ships `uv` as plain text**, not inline `<code>`. The build-prompt marks inline code
   with an explicit parenthetical everywhere it wants it (the note, the trap, §6's lede); the
   backticks around `uv` inside step 1's sub are the document's own prose markup, and §5.1's sub
   styling names no code treatment.

## Judgment calls where the design left a value unspecified

Each picks the option closest to the designed intent, never a plainer fallback:

- **Radius 12px on the block** → `rounded-[12px]`. No token lands on 12 (`lg` is 10, `xl` is 14);
  rounding to a token would be exactly the quiet drift RESPECT forbids. Same reasoning keeps
  `text-[13.5px]` off the 13px `text-code-md` token.
- **`failed` on dark** → identical caution treatment to light. §7 supplies a dark override for
  `copied` only; the caution chip reads on the ink bar, and inventing a dark caution palette would
  mean a new colour the token delta forbids.
- **The block's border on failure** → also goes `hairline-caution`. §7 says "the row's border"; the
  failed state marks the whole snippet, and leaving the block alone would be the plainer reading.
- **Row `label?`** (in §3.1's signature, styled nowhere, and used by no consumer this round) →
  rendered as the block bar's label treatment translated to a light surface: mono `text-micro`
  `tracking-[.7px]` uppercase in `green-dark`, which is what §4's own micro label uses.
- **Trap label→body gap** → `mt-2` (8px), unspecified in §3.2.
- **The trap's inline `<code>`** → applied with `[&_code]:…` descendant utilities on the body, so
  consumers write plain `<code>` and cannot drift from the treatment. Repo's first arbitrary variant;
  verified present in the built CSS.
- **The 7px marker** → a real `aria-hidden` `<span class="size-[7px] rotate-45 bg-caution">`, as the
  plan directed, since a `::before` is not expressible here. Not a bullet, not an icon.
- **Announcements for the non-hero snippets** → §7 gives `Copied the install command.` and says to
  substitute the snippet's own label, so: `Copied the environment block.` /
  `Copied the verify command.` / `Copied the capture command.` / `Copied the skill file.`

## Formatting

`landing.ts`, `snippet.tsx` and `snippet-ssr.test.ts` were run through `prettier --write` after
writing (line wrapping only — no string content changed and `prettier-plugin-tailwindcss` reordered
nothing, so the hand-written class order already matched). All nine files this slice touches are
prettier-clean. The **12 pre-existing** repo-wide `format:check` failures were left alone per
phase.md, including 4 under `web/tests/`.

## Doc impact

One line appended to `phase.md`'s `## Doc impact` — no `doc-new-version` was run.
