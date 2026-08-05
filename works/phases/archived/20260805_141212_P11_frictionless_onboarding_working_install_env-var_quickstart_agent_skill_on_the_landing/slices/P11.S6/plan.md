# P11.S6 — Primitives + copy: `Snippet`, `Trap`, the pure copy helper, `section-ids`, `landing.ts` blocks

> ## RESPECT THE DESIGN
> **Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
> Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
> failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
> intent, never a plainer fallback.**

## Why this slice is first, and why it is the risky one

`Snippet` is used by the hero install row and by three of the quickstart's four steps; `Trap` and the copy
mechanics are shared. Building them once, first, is what stops S7–S9 each inventing their own. `section-ids`
belongs here too: `SectionId` is a typed union, so **S8 and S9 cannot compile until their entries exist**.

**Three of this slice's mechanics have no precedent anywhere in the repo**, and all three are load-bearing
for the design's locked floors:

1. **A mount gate.** There is no `mounted` state anywhere in `web/src/` — I checked. §8 requires a no-JS
   visitor to see **no copy button at all**, never a present-but-inert one.
2. **A revert timer.** `show-once-key.tsx` latches `copied` one-way and never reverts; there is **no
   `setTimeout` anywhere in `web/src/`**. §7 requires 2000ms then back to idle.
3. **Programmatic text selection** (`Range` + `Selection`) on copy failure, with a state that
   **deliberately persists** rather than timing out.

Get the shape right here and the rest of the phase inherits it.

## Source of truth

`docs/reference/design/rounds/02-onboarding/output/build-prompt.md` **§3.1** (`Snippet`), **§3.2** (`Trap`),
**§7** (the normative state table) and **§8** (the no-JS floor). Read them before writing code. Also read
`works/phases/active/P11/phase.md`'s "DECOMP2 done" section — its **nine corrections** are apply-time
to-dos, and **correction 3** applies here.

## House conventions this must match

Verified against the tree; follow them rather than inventing:

- **`ui/` components are `export function Name({ className, ...props }: NameProps)`** — function
  declarations, never arrow consts. Props destructure `className` first and spread `...props` onto the root.
- **CVA when there are variants**: `export const snippetVariants = cva(base, { variants, defaultVariants })`,
  exported alongside the component; the props interface extends both the intrinsic attributes and
  `VariantProps<typeof snippetVariants>` (see `ui/button.tsx:48-51`). A no-variant primitive follows
  `ui/endpoint-card.tsx:11-19` instead.
- **`cn()` from `@/lib/utils`**, always last-arg: `cn(snippetVariants({ variant }), className)`.
- **Every `ui/` file opens with a block JSDoc** above the variants/interface stating the design intent and
  the a11y decision. This is uniform across `ui/` — match it, and use it to document the three net-new
  mechanics above.
- **Barrel**: add to `web/src/components/ui/index.ts` as a value export plus a `export type { … }` line,
  each preceded by a short `// P11.S6 — …` comment naming the slice, exactly as the existing entries do.
- **`web/src/content/landing.ts` is one `export const LANDING = { … } as const`** — no exported type, no
  `satisfies`. New top-level blocks get a box-rule comment (`// ── Hero install ────…`, padded to ~76 cols)
  like every existing block. Reuse the module-level `REPO_URL` / `DOCS_URL` consts rather than inlining URLs.
- Section components destructure **at module scope, outside the function**: `const { how } = LANDING;`
  (`how-it-works.tsx:9`).

### Tailwind translation — the one thing the spec cannot tell you

`build-prompt.md` writes raw CSS (`min-height:48px`, `font-size:13.5px`). **This repo has zero
`style={{…}}` occurrences.** Do not introduce inline styles — express every value as classes, in this order
of preference:

1. **A token utility** — `bg-canvas`, `text-ink`, `text-steel`, `border-hairline-strong`, `rounded-lg`,
   `font-mono`, `text-code-md`.
2. **The numeric scale where it lands exactly** — `min-height:48px` is **`min-h-12`** (see
   `ui/button.tsx:36-38`, where `size="lg"` is already `min-h-12`). Use it; do not write `min-h-[48px]`.
3. **An arbitrary value** where nothing lands — `text-[13.5px]`, `leading-[1.5]`,
   `px-[14px]`. Well precedented (~35 occurrences, e.g. `hero.tsx:76`, `how-it-works.tsx:15`).
   `text-[13.5px]` is correct here: the design says 13.5px, `text-code-md` is 13px, and **RESPECT THE
   DESIGN means shipping 13.5px, not rounding to the nearest token**. `cn()`'s font-size group is
   registered in `lib/utils.ts:19-44`, so the arbitrary value overrides cleanly.
4. `var(--color-*)` inside an arbitrary value when a token has no utility — precedent
   `shadow-[inset_2px_0_0_var(--color-green)]`.

Do not hand-tune class order — `prettier-plugin-tailwindcss` rewrites it.

## Deliverable 1 — the pure copy helper

The Node-env vitest has **no jsdom and no RTL**, so the testable logic must be genuinely pure. Put the
DOM-free part in a helper (a new `web/src/lib/clipboard.ts` is the natural home — there is no existing
`useCopy` hook or `lib/clipboard` to extend):

```ts
export type CopyState = "idle" | "copied" | "failed";

export async function attemptCopy(
  getText: () => string,
  write: (text: string) => Promise<void>,
): Promise<CopyState>
```

Returns `"copied"` when the write resolves, `"failed"` when either the read or the write throws. **The
`catch` must be valueless — never log the copied text** (`show-once-key.tsx:44-50` states this rule in a
comment; keep it). Reading `textContent` and calling `navigator.clipboard.writeText` stay in the component;
only this decision logic is extracted.

## Deliverable 2 — `web/src/components/ui/snippet.tsx`

`"use client"`. Two variants per §3.1 — `row` (one line, light) and `block` (multi-line, dark).

**Locked floors, non-negotiable:**

- **`white-space: pre` + `overflow-x: auto`** on the command element (`whitespace-pre overflow-x-auto`).
  The install command **must never wrap or truncate at any width** — horizontal scroll is correct, reflow
  is a bug. Also `flex-1 min-w-0` on the row's code element, or the flex parent will refuse to shrink it.
- **The clipboard gets the DOM node's `textContent`**, never a separately-typed string. Use a `ref` on the
  code/`<pre>` element. This is why block comment lines are *included* in the copy — they are valid shell.
- **The copy button renders only after mount.** `const [mounted, setMounted] = useState(false)` +
  `useEffect(() => setMounted(true), [])`, and return `null` for the button until `mounted`. A no-JS
  visitor gets the bordered, padded, **selectable** snippet with **no button element in the DOM**. This is
  net-new for this repo; document the contract in the JSDoc the way `ui/reveal.tsx:31-70` documents its own
  ("the static page is the guaranteed baseline").

**States, per the §7 table:**

| State | Presentation | Duration |
|---|---|---|
| idle | `Copy`, canvas bg, `border-hairline-strong` | — |
| copied | `✓ Copied`, `bg-green-soft`, `border-security-mint`, `text-green-dark`; on dark `bg-[rgba(190,233,213,.16)]`, `border-security-teal`, `text-victory-lime` | **2000ms**, then idle |
| failed | `Copy failed`, `bg-surface-caution`, `border-hairline-caution`, `text-caution-deep`; **the row's own border also goes `border-hairline-caution`**; the command text is **selected programmatically** (`Range` + `Selection`); a mono `text-[11.5px] text-caution-deep` hint appears | **persists** until the next attempt |

The asymmetry is deliberate and must be preserved: **success reverts on a timer, failure does not** — it is
the one case where a state that fixed nothing must not disappear on its own. Clear the timer in a `useEffect`
cleanup so it cannot fire after unmount.

**Announcement**: one **polite** live region per copy button; on success it receives the snippet's own
announcement string. Nothing is announced on failure — the selection plus the visible hint is the
affordance. **No `role="alert"` anywhere in this round.**

**Copy strings come in as props**, following the `ShowOnceKeyCopy` precedent
(`show-once-key.tsx:12-26`) — a `copy` prop object carrying the four labels (`copyLabel`, `copiedLabel`,
`copyFailedLabel`, `selectionHint`) plus the announcement. Components hold no literal strings.

## Deliverable 3 — `web/src/components/ui/trap.tsx`

Per §3.2. A plain `<aside>` — `border-hairline-caution`, `bg-surface-caution`, `rounded-lg`, `p-[14px_16px]`
equivalent.

- Label row: `flex items-center gap-2`, mono `text-[11px] tracking-[.8px] uppercase font-bold
  text-caution-deep`.
- The marker is a **7px square rotated 45°** in `bg-caution`. The spec writes it as a `::before`;
  pseudo-elements are not expressible here without arbitrary variants, so render a real
  `<span aria-hidden="true" className="size-[7px] rotate-45 bg-caution" />`. Same visual result, closest to
  the designed intent — **not** a plainer fallback like a bullet or an icon.
- **No icon component, no emoji, no `role="alert"`, no `aria-live`.** A trap is not an error, and nothing in
  this round may interrupt a screen reader on load. State this in the JSDoc — it is the kind of thing a
  future reader "fixes" into a bug.
- Body `text-[13.5px] leading-[1.6] text-slate`; inline `<code>` mono `text-[12.5px]` on
  `bg-[rgba(14,26,22,.055)]`, `rounded-xs`, `px-[5px] py-px`.

**Not in scope: the `.note` treatment.** Per correction 3, the "existing `.note`" the spec cites **does not
exist in this repo** and is used only in quickstart step 2 — **S8 builds it inline**. Do not create a `Note`
primitive here.

## Deliverable 4 — `section-ids.ts`

Add exactly two entries to the `as const` map, camelCase key → kebab-case value, with a `// P11.S6` comment:
`quickstart: "quickstart"` and `skill: "skill"`. `SectionId` derives automatically, so `<Section id>` typing
updates for free. **Add nothing else** — an unused id is an anchor that goes nowhere.

## Deliverable 5 — the `landing.ts` copy blocks

Add `heroInstall`, `quickstart`, and `skill` blocks, plus a shared `snippet` block for the four universal
copy-button labels (so all consumers pass one object and no component holds a literal).

**Every string is final copy and appears verbatim in `build-prompt.md` §4, §5, §6 and §7.** Transcribe them
exactly — including the em-dashes, the `·` separators, the Korean in the capture example
(`vocky capture "결제를 못 했습니다" --product acme-web --value 2`), and `⌘C (Ctrl+C)` in the selection hint.
Multi-line snippet bodies use template literals with real embedded newlines, exactly as
`hero.request.body` does (`landing.ts:65-71`).

**The copyable payloads are byte-locked.** The install command in particular —
`curl -fsSL https://vocky.hi2vi.com/install.sh | bash` — must match `web/public/install.sh`'s header and
`docs/cli.md` character for character. Do not reflow, re-space, or re-quote any of them.

`landing.ts`'s header comment carries a **"GROUNDED, NOT LOREM"** rule and a locked floor that doc links
resolve to real targets. Both hold: every claim in these blocks is a real, shipped vocky fact, and the only
new link targets are the in-page anchors `#quickstart` / `#skill` and `/SKILL.md`.

## Deliverable 6 — tests, terse

Two small additions under `web/tests/` (`.ts`, not `.tsx`; node env; no DOM):

1. **`clipboard.test.ts`** — `attemptCopy` returns `"copied"` when the write resolves; `"failed"` when the
   write rejects (denied clipboard / insecure origin); `"failed"` when the text getter throws.
2. **A byte-lock test for the copyable payloads** — re-spell the install command and the `~/.zshenv` block
   as literals in the test and assert equality, so an accidental reflow fails CI. This is the repo's
   **first** test importing from `@/content` — it should work (no `server-only`, no JSX), but it is
   unproven; if the alias misbehaves, say so rather than deleting the test.

Keep both terse per `AGENTS.md`. Match `web/tests/vocky-auth.test.ts`'s shape: `vitest` import first, blank
line, `@/…` imports with type imports last, a slice-tagged block comment explaining *why the behavior
matters*, `describe` per exported function, full-sentence `it(…)` titles.

## Validation

From `web/` unless noted:

1. `pnpm typecheck` → exit 0.
2. `pnpm lint` → exit 0.
3. `pnpm test` → the existing **61** pass plus the new ones; report both numbers.
4. `pnpm build` → succeeds. `/` must still prerender as static; the new primitives must not accidentally
   make the landing dynamic.
5. `grep -rn "style={{" web/src/components/ui/snippet.tsx web/src/components/ui/trap.tsx` → **no matches**
   (the house has zero inline styles).
6. `grep -rn "role=\"alert\"\|aria-live=\"assertive\"" web/src/components/ui/trap.tsx` → **no matches**.
7. Confirm the snippet's command element carries both `whitespace-pre` and `overflow-x-auto`, and the row's
   code element also `flex-1 min-w-0`.
8. From the repo root: `python3 scripts/skill_parity.py` → still `PASS` (untouched, but it is cheap
   insurance that nothing disturbed `web/public/`).
9. `python3 scripts/workflow.py validate` → passes.

**Note what could not be proven**: there is no jsdom, so the mount gate, the 2s revert, the programmatic
selection, and the live-region announcement are **not** covered by automated tests. Say so plainly in
`result.md` — S10's fidelity pass is where they get checked, and `build-prompt.md` §11.3 (JS disabled → no
copy button visible anywhere) is the acceptance check that closes it.

## Out of scope

- No section components, no `page.tsx` change, no `hero.tsx` change, no `landing-nav.tsx` change — S7–S9.
- No `Note` primitive (correction 3 — S8 builds it inline).
- **No `globals.css` change. No new token. No token rename.** The design's delta is `None.`
- No backend change. No `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S6/result.md` from scratch (free-form): the two primitives' final
prop shapes, the copy-block keys added to `landing.ts` (S7–S9 consume them by name, so list them exactly),
how the three net-new mechanics were implemented, verbatim validation output, and what is not covered by
tests. Append durable cross-slice notes to `works/phases/active/P11/phase.md`. If this changes durable truth,
append one line to `## Doc impact` — do not run `doc-new-version`. Do not commit and do not change any slice
or phase status.
