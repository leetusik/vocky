# P11.S7 result — hero install row + the nav reorder

## What landed

### Part 1 — hero install row (`web/src/components/landing/hero.tsx`)

Appended below the existing two-column grid, still inside the `<Section>`. Nothing inside the grid
changed (verified below). Structure and class translation:

```tsx
<div className="mt-11 grid grid-cols-1 items-center gap-[10px] border-t border-hairline pt-[26px] app:grid-cols-[auto_minmax(0,1fr)] app:gap-7">
  <div>
    <p className="font-mono text-micro text-green-dark uppercase">{heroInstall.label}</p>
    <p className="mt-1 max-w-[22ch] text-body-sm text-steel">{heroInstall.sub}</p>
  </div>
  <div className="min-w-0">
    <Snippet
      variant="row"
      command={heroInstall.command}
      copy={{ ...LANDING.snippet, announcement: heroInstall.copyAnnouncement }}
    />
    <p className="mt-2 font-mono text-[11.5px] text-steel">
      <span className="app:hidden">{heroInstall.captionNarrow}</span>
      <span className="hidden app:block">{heroInstall.caption}</span>
    </p>
  </div>
</div>
```

Translation notes, in the order §4's landings were followed:

- `mt-11` = 44px, `pt-[26px]`, `border-t border-hairline` — all exact per §4.
- Base (narrow, mobile-first) is `grid-cols-1 gap-[10px]`; `app:grid-cols-[auto_minmax(0,1fr)] app:gap-7`
  (28px) switches in at `--breakpoint-app` (900px). DOM order (label block, then snippet) is unchanged
  between the two layouts — a single-column grid stacks it top-to-bottom at narrow widths and the same
  two children land left/right once the grid gains its second track, so no conditional rendering or
  reordering was needed.
- Left micro label: `font-mono text-micro text-green-dark uppercase` — `text-micro` is 11px/1.4/**0.8px**
  tracking/700 (`globals.css:149-152`), matching the spec's "11px/700/letter-spacing:.8px" exactly with no
  override needed. This is the same token combination `ui/trap.tsx:43` already uses for its own
  11px/.8px/700/uppercase label, so it's house precedent, not a new interpretation.
- Sub: `text-body-sm` (13px/1.55/400) + `max-w-[22ch]` + `text-steel` — 13px is the only spec value; no
  other detail was given, so the token closest to "13px prose" was used (not `text-code-md`, which is also
  13px but a code-family token, wrong family for a sentence).
- Caption: `font-mono text-[11.5px] text-steel` — no token lands on 11.5px, same footing as S6's own
  `text-[13.5px]` arbitrary value (phase.md's "two plan facts" note), so an arbitrary value is house style
  here, not a shortcut.
- **Caption swap is CSS-only**: both strings render into the server HTML always; `app:hidden` /
  `hidden app:block` toggle visibility. No JS, no conditional render, no hydration mismatch.
- `Snippet` consumed exactly as S6 shipped it — `variant="row"`, `command={heroInstall.command}`,
  `copy={{ ...LANDING.snippet, announcement: heroInstall.copyAnnouncement }}`. No new primitive, no
  restyling of its frame (the wrapping `<div className="min-w-0">` only affects layout, per the
  "root is an unstyled wrapper, className is for layout" note in S6's phase notes).
- `Start free` was not touched; the install row has no button variant at all (a `Snippet` row's copy
  control is a secondary/ghost-styled `cbtn`, never `buttonVariants({variant:"primary"})`).

### Part 2 — nav reorder (`web/src/content/landing.ts`)

```ts
nav: {
  links: [
    { label: "How it works", href: `#${SECTION_IDS.how}` },
    { label: "Get started", href: `#${SECTION_IDS.quickstart}` },
    { label: "Features", href: `#${SECTION_IDS.features}` },
    { label: "Pricing", href: `#${SECTION_IDS.pricing}` },
    { label: "Docs", href: DOCS_URL, external: true },
  ],
  ...
}
```

Final array reads **`How it works · Get started · Features · Pricing · Docs`** — the whole array was
reordered (not "insert Get started at index 1 into today's order"), matching correction 1 and the design's
own written string exactly. `href` is `#${SECTION_IDS.quickstart}`, never a hardcoded `"#quickstart"`.
`#skill` gets no nav link. The footer's Product column (`landing.ts:449-459`, three anchors) was **not**
touched.

`landing-nav.tsx` needed **no change** — confirmed before touching anything: it already maps generically
over `nav.links` (`label`/`href`/optional `external`) with no hardcoded link count or index, so the reorder
+ new entry flowed through with zero component edits.

### Active nav state — which case was found

**No scroll-spy/active-state mechanism exists in `landing-nav.tsx` today.** It renders every link with the
same static class (`text-body-sm text-steel transition-colors hover:text-ink`); there is no scroll listener,
no `IntersectionObserver`, no "current section" state anywhere in the file or in `LANDING.nav`. Per the
spec's own qualifier — "same mechanism the existing nav uses if any; otherwise none" — **shipping no active
state is the designed outcome**, not a shortcut. No scroll-spy was built.

## Validation (from `web/` unless noted)

1. **`pnpm typecheck`** → exit 0, no output.
2. **`pnpm lint`** → exit 0, no output.
3. **`pnpm test`** → `Test Files 8 passed (8)`, `Tests 70 passed (70)` — the same 70 S6 left green, unchanged.
   `landing-copy.test.ts` (byte-locks the install command) still passes, confirming no reflow.
4. **`pnpm build`** → succeeds (`✓ Compiled successfully`, `✓ Generating static pages (13/13)`). Route table
   confirms `ƒ /` (dynamic) — expected, not a regression (dynamic since P9.S6 because `page.tsx` reads the
   session cookie).
5. **Hero payload untouched** — `git diff -- web/src/content/landing.ts` shows changes **only** in the
   `nav` block's comment + `links` array (7 added/changed lines around `nav.links`); no hunk anywhere near
   `hero.request`. Full diff:
   ```diff
   @@ -41,10 +41,17 @@ export const LANDING = {
      // In-page anchors derive from SECTION_IDS so they never drift from the
      // `<Section id>` targets. "Docs" is an EXTERNAL link (the repo README), not an
      // in-page anchor — vocky has no `/docs` route to fake.
   +  //
   +  // P11.S7 (round 02 build-prompt §2): "How it works" moves to first and "Get
   +  // started" -> #quickstart is inserted second — a REORDER of the whole array,
   +  // not an insert into today's order, so the final string reads
   +  // "How it works · Get started · Features · Pricing · Docs". #skill gets no
   +  // nav link. Five links is the ceiling.
      nav: {
        links: [
   -      { label: "Features", href: `#${SECTION_IDS.features}` },
          { label: "How it works", href: `#${SECTION_IDS.how}` },
   +      { label: "Get started", href: `#${SECTION_IDS.quickstart}` },
   +      { label: "Features", href: `#${SECTION_IDS.features}` },
          { label: "Pricing", href: `#${SECTION_IDS.pricing}` },
          { label: "Docs", href: DOCS_URL, external: true },
        ],
   ```
   `hero.request` (auth line, nested `source.product` body) is byte-for-byte what P11.S1 shipped.
6. **`grep -rn "vk_live_" web/ src/ docs/ --exclude-dir=node_modules`** — **not** empty; four matches, all
   pre-existing S5 design-record files (`docs/reference/design/rounds/02-onboarding/{output/result.md,
   output/build-prompt.md, handoff.md}`), all in negation form ("no `vk_live_`", "showed a `vk_live_` key
   tier [that is now corrected]") describing the correction, not a live key value. None are in `web/` or
   `src/`, and none were added or touched by this slice (confirmed `git log -1` on `build-prompt.md` shows
   it landed at S5's commit, before this slice existed). I deliberately worded my own new hero.tsx comment
   to say "no live-tier prefix" rather than quoting the literal string, so this slice adds zero new matches.
   `grep -n "source_product" web/src/content/landing.ts` → exactly the one expected comment-line occurrence
   (`:14`, the "stored/READ record... is flat" note), unchanged from S1.
7. **`grep -rn "style={{" web/src/components/landing/hero.tsx`** → no matches (exit 1).
8. **Final nav order** — confirmed twice: (a) the content array quoted above reads
   `How it works · Get started · Features · Pricing · Docs`; (b) rendered `LandingNav` via
   `renderToStaticMarkup` in a temporary (not committed) test and extracted the five in-page/`Docs` anchor
   labels — they render in that exact order, verbatim, in the actual DOM.
9. **No copy button in the server HTML** — ran the check by hand (a temporary, not-committed vitest test
   that rendered the actual `Hero` component with `renderToStaticMarkup`, same technique as S6's
   `snippet-ssr.test.ts`) rather than extending that file, since `Hero` composes several primitives and a
   dedicated hero-level check felt cleaner than growing a `Snippet`-scoped suite with a hero-shaped case.
   Confirmed: no `<button` anywhere in the rendered markup, the install command text is present, both
   caption variants (`caption` and `captionNarrow`) are present in the HTML (proving the swap is CSS-only,
   not a server-side branch), and the corrected hero payload (`checkout-web`, nested `source`, no
   `vk_live_`) is unchanged. Deleted the temp file after use — nothing was left in `web/tests/`.
10. **`python3 scripts/workflow.py validate`** → `Workflow validation passed.`

Also spot-verified the two `app:` breakpoint classes actually compiled (Tailwind can silently drop a
malformed arbitrary value): grepped the built `.next/static/chunks/*.css` and found
`.app\:grid-cols-\[auto_minmax\(0\,1fr\)\]{grid-template-columns:auto minmax(0,1fr)}` and `.app\:gap-7`
both correctly nested under `@media (min-width:56.25rem)` — the exact 900px breakpoint.

**Not behaviorally proven** (per the phase's standing note): nothing here can be checked against a live
origin — the site is not deployed until P12, so `https://vocky.hi2vi.com/install.sh` still 404s. All
validation above is against the local build/test/lint toolchain only.

## Deviations from `plan.md`

None in substance. One wording choice: my own explanatory comment in `hero.tsx` avoids literally spelling
`vk_live_` (writes "no live-tier prefix" instead) so this slice does not add a new match to validation
step 6's grep — the three matches that do exist are all pre-existing, read-only S5 design-record prose.

## Doc impact

None. This slice only reorders existing nav data and adds a new hero row built entirely from S6's
`Snippet` primitive and S6's `heroInstall` copy — no new section, no new primitive, no new anchor beyond
what S6 already added to `section-ids.ts`. `docs/current/frontend.md`'s stale section-inventory entries
(already flagged by S6's "Doc impact" note) will be updated once the review consolidates S6–S10 together;
this slice adds nothing new to that list.
