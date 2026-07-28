# P11.S7 — Hero install row + the nav reorder

> ## RESPECT THE DESIGN
> **Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
> failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
> intent, never a plainer fallback.**

## Scope

Two changes, both small, both in shipped above-the-fold code. That narrow blast radius is exactly why this
is its own slice.

1. **The hero install row** — `build-prompt.md` §4.
2. **The nav** — `build-prompt.md` §2, as corrected by **correction 1** in `phase.md`.

Source of truth: `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` §2 and §4. Read
`works/phases/active/P11/phase.md`'s "DECOMP2 done" corrections and its "S6 done" notes first — S6's
primitives and copy blocks are what this slice consumes.

## Everything you need already exists

S6 shipped these; **consume them, do not re-create anything**:

- `Snippet` from `@/components/ui` — `<Snippet variant="row" command={…} copy={…} />`. `SnippetProps`
  takes `command: string`, `copy: SnippetCopy`, and an optional `label`. The copy object carries
  `copyLabel` / `copiedLabel` / `copyFailedLabel` / `selectionHint`.
- `LANDING.snippet` — the four shared copy-button labels.
- `LANDING.heroInstall` — already final copy, verbatim:
  ```
  label:            "Install the CLI"
  sub:              "Or skip it — the same capture is one REST call."
  command:          "curl -fsSL https://vocky.hi2vi.com/install.sh | bash"
  caption:          "no sudo · installs uv if it's missing · re-run any time to upgrade"
  captionNarrow:    "no sudo · installs uv if it's missing"
  copyAnnouncement: "Copied the install command."
  ```
- `SECTION_IDS.quickstart` / `SECTION_IDS.skill` — added by S6.

**Write no new copy.** Every string is in `landing.ts`; `build-prompt.md` §11.4 makes "zero literal strings
in the new components" an acceptance check.

## Part 1 — the hero install row (`web/src/components/landing/hero.tsx`)

### What must not change

**Nothing inside the existing two-column grid.** The eyebrow pill, the `h1`, the sub-paragraph, both CTAs,
the proof ticks, the `EndpointCard` and the layered captured-record `Card` all stay exactly as shipped.

**The `EndpointCard` payload must not be edited.** `P11.S1` corrected it — nested `source.product`, no
`vk_live_` — and that correction is the reason this phase's first slice existed. A `git diff` touching
`hero.request` in `landing.ts` is a failure of this slice.

**`Start free` stays the primary CTA.** The install row is prominent by position and quiet by weight — a
mono row with a secondary copy button, **never a filled button**. (`result.md` §6.1b: promoting install
above signup would sequence the page wrong, since a key is a precondition for the CLI.)

### What to add

Append **below** the two-column grid, still inside the hero container:

- Separator: `margin-top:44px; padding-top:26px; border-top:1px solid var(--color-hairline)`.
- Then a two-column grid: `grid-template-columns:auto minmax(0,1fr); gap:28px; align-items:center`.
- **Left** — the micro label `Install the CLI`: uppercase, 11px, weight 700, `letter-spacing:.8px`,
  `var(--color-green-dark)`. Under it the sub, 13px `var(--color-steel)`, `max-width:22ch`.
- **Right** — `<Snippet variant="row">` carrying `heroInstall.command`, and beneath it the caption in mono
  11.5px `var(--color-steel)`.

**Narrow (< 900px)** — single column, `gap:10px`, the label block above the snippet; the caption drops to
`captionNarrow`. The row itself is unchanged and the command still scrolls rather than wraps.

### Translating to classes

The repo's breakpoint for this is **`--breakpoint-app` (56.25rem = 900px)**, so the `app:` variant is the
right tool and the narrow case is the base style (mobile-first). Useful exact landings: **44px = `mt-11`**,
**28px = `app:gap-7`**, `gap-[10px]` at base, `border-t border-hairline`, `pt-[26px]`, `max-w-[22ch]`.

**The caption swap must be CSS-only, not JS** — render both strings and toggle with `app:hidden` /
`hidden app:block`. A JS-driven swap would break the no-JS floor and cause a hydration mismatch.

Follow S6's translation order: token utility → exact numeric scale → arbitrary value. Note that
`hero.tsx` already uses arbitrary values (`w-[88%]`, the layered card's `shadow-[…]`), so this is house
style. Do not introduce `style={{…}}` in a landing component.

## Part 2 — the nav (`web/src/content/landing.ts`)

**This is a reorder, not just an insert** — correction 1, verified against the tree.

The nav links are **data**, not markup: they live in `LANDING.nav.links` and `landing-nav.tsx` maps over
them. So this is a `landing.ts` edit, and `landing-nav.tsx` may well need **no change at all** — check
before touching it.

Today:

```
Features · How it works · Pricing · Docs
```

`build-prompt.md` §2 writes the final nav as:

```
How it works · Get started · Features · Pricing · Docs
```

So `How it works` moves to **first** and `Get started` → `#quickstart` becomes **second**. Inserting
"at second position" into today's array would yield `Features · Get started · How it works · …`, which
contradicts both the spec's own written string and `result.md` §6.3's rationale — `Get started` sits second
*because it follows* `How it works`, mirroring the §6.2b page order. **Acceptance check 7 only counts to
five, so nothing downstream will catch this — get it right here.**

Build the href from `SECTION_IDS.quickstart`, never a hardcoded `"#quickstart"` — anchors derive from the
map so they cannot drift.

**`#skill` gets NO nav link** (§2, explicit). Five links is the ceiling.

**Do not touch the footer** — correction 2. `landing.ts`'s footer Product column carries the same three
anchors; the design says nothing about it, so adding `Get started` there would be an undesigned change.

### Active state

§2 specifies `color: var(--color-green-dark); background: var(--color-green-soft); font-weight: 600` for
the reader-inside-the-section state, and qualifies it: *"same mechanism the existing nav uses if any;
otherwise none."* **Check whether `landing-nav.tsx` has any scroll-spy mechanism today. It almost certainly
does not — and if it does not, do not build one.** The spec explicitly makes this conditional, so shipping
no active state is the designed outcome, not a shortcut. Say which case you found in `result.md`.

## Validation

From `web/` unless noted:

1. `pnpm typecheck` → exit 0.
2. `pnpm lint` → exit 0.
3. `pnpm test` → the **70** tests S6 left green all still pass. S6's `landing-copy.test.ts` byte-locks the
   install command, so a reflow here fails loudly — that is intended.
4. `pnpm build` → succeeds. `/` stays `ƒ` (dynamic) — it has been dynamic since P9.S6 because `page.tsx`
   reads the session cookie. **That is expected, not a regression.**
5. **The hero payload is untouched**: `git diff -- web/src/content/landing.ts` shows changes **only** in
   `nav.links` — no hunk anywhere near `hero.request`. Paste the diff of that region (or state it is empty)
   in `result.md`.
6. From the repo root: `grep -rn "vk_live_" web/ src/ docs/ --exclude-dir=node_modules` → **no matches**;
   `grep -n "source_product" web/src/content/landing.ts` → exactly the one comment-line occurrence S1 left.
7. `grep -rn "style={{" web/src/components/landing/hero.tsx` → **no matches**.
8. Confirm the final nav order renders as `How it works · Get started · Features · Pricing · Docs` — read it
   out of the built markup or the content array and quote it in `result.md`.
9. **No copy button in the server HTML.** S6 proved this technique works without jsdom
   (`web/tests/snippet-ssr.test.ts` uses `renderToStaticMarkup`). Either extend that test or run the same
   check by hand against the hero row, and report which.
10. `python3 scripts/workflow.py validate` → passes.

Nothing here can be checked against a live origin — the site is not deployed until P12, so
`https://vocky.hi2vi.com/install.sh` still 404s. Say so in `result.md`.

## Out of scope

- No `AgentQuickstart`, no `SkillSection`, no `page.tsx` change — S8 and S9 insert their own sections.
- No footer change (correction 2).
- No scroll-spy machinery unless one already exists.
- **No `globals.css` change, no new or renamed token** — the design's delta is `None.`
- No new primitive; `Snippet` already exists.
- No backend change, no `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S7/result.md` from scratch (free-form): the row as it landed with
its class translation, the final nav array, which active-state case you found, verbatim validation output,
and the hero-payload diff evidence. Append durable cross-slice notes to
`works/phases/active/P11/phase.md`; if this changes durable truth append one line to `## Doc impact` —
do not run `doc-new-version`. Do not commit and do not change any slice or phase status.
