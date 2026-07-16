# Plan — `P8.S1` (foundations cards + hi2vi reference card)

Slice 1 of 8 in P8. `risk: medium` → **`slice-executor-mid`**. Order 1, no deps.

## Context

P8 prepares vocky's design canvas for the operator's Claude Design session, then implements whatever
the session signs off. This slice rebuilds the **Foundations** cards so the session sees the real
token system rather than a partial view, and adds the **`Reference — hi2vi vibe`** card that carries
the operator's directive (*"make a design system only for vocky but inherit hi2vi vibe"*) into the
session as **evidence, not a proposal**.

Read `works/phases/active/P8/phase.md` first — it holds the phase's constraints, the handed-down
findings, and the eleven questions the gate must answer. `intent.md` is the source of truth for what
the operator asked.

**The load-bearing constraint: zero brand decisions.** This slice changes **no token value**. It only
presents what already exists. Palette, type direction, and how far to carry the hi2vi vibe are all
concluded in the operator's session, by Claude Design asking the operator.

## The finding that shapes this slice

Measured at planning, vocky's `web/design/canvas/tokens.css` vs
`~/projects/personal/hi2vi_web/design/canvas/tokens.css`:

| Group | Names shared | Values identical |
| --- | --- | --- |
| `--color-*` | **41 / 41** | **2 / 41** (`canvas`, `on-dark` — both `#ffffff`) |
| `--text-*` (14 steps + bundled lh/tracking/weight) | 14 / 14 | **14 / 14** |
| `--radius*` | 8 / 8 | **8 / 8** |
| `--spacing-*` | 4 / 4 | **4 / 4** |

**So "inherit hi2vi vibe" mechanically reduces to 39 color values plus the typefaces.** The type
scale, radius scale, and spacing rhythm in vocky *are already hi2vi's, byte for byte*. Only the font
families diverge (hi2vi: Pretendard + Inter + JetBrains Mono; vocky: Noto Sans KR + a bare system
stack + JetBrains Mono).

**And the placeholder's swatch collisions are lost hi2vi distinctions.** 7 of the 8 vocky value
collisions are distinctions hi2vi keeps:

| vocky collapses | into | hi2vi keeps them as |
| --- | --- | --- |
| `forest`, `charcoal` | `#1e293b` | `#0b2a22`, `#18231f` |
| `forest-mid`, `hairline-dark`, `slate` | `#334155` | `#123b31`, `#24463b`, `#41524a` |
| `archive-cream`, `surface-soft`, `surface-band`, `hairline-soft` | `#f1f5f9` | `#f3f0d8`, `#f1f6f2`, `#eef6f1`, `#ebf1ed` |
| `trust-sage`, `hairline-strong`, `on-dark-muted` | `#cbd5e1` | `#c8e6d2`, `#b8c8bf`, `#afc5ba` |
| `archive-olive`, `muted` | `#94a3b8` | `#a8c85a`, `#93a39b` |
| `surface-green`, `surface-security` | `#eef2ff` | `#effbf4`, `#f0faf5` |
| `canvas`, `on-dark`, **`on-primary`** | `#ffffff` | `#ffffff`, `#ffffff`, **`#061512`** |
| `ink`, `canvas-dark` | `#0f172a` | `#061512`, `#061512` — *also collide; not a lost distinction* |

`on-primary` is the sharpest row: hi2vi's bright-green CTA takes **dark** text; the indigo placeholder
needed white. P4.S1 recorded this as "one semantic flip was required." If the session picks a bright
accent, it flips back.

Present these as **facts for the session to act on**. Do not recommend restoring anything.

## Deliverables

### 1. `foundations/colors.html` — rebuild

Today it shows **22 of 41** color tokens. Show **all 41**, grouped by role (accent / dark surfaces /
text / light surfaces / hairlines / signal states / on-* text). The 19 absent today:
`forest-soft`, `security-mint`, `security-teal`, `trust-sage`, `victory-lime`, `archive-olive`,
`archive-cream`, `danger-deep`, `hairline-danger`, `caution-deep`, `hairline-caution`, `canvas-dark`,
`surface-archive`, `surface-security`, `surface-band`, `hairline-soft`, `hairline-dark`, `charcoal`,
`on-dark`, `on-dark-muted`, `on-primary`.

- **Mark the colliding swatches** so the session reads them as duplicates on purpose, not a rendering
  bug — a small marker plus a short factual note listing the collision groups.
- Fix the stale lede: it still says *"Values are finalized at the **P6** design gate"* → this gate is
  **P8**. (`web/design/canvas/README.md` and `_ds_manifest.json`'s `note` carry the same staleness but
  belong to **S6** — leave them.)
- Swatch chips fill from `var(--color-*)`; the hex in the label must be literal text (CSS cannot read
  a custom property into `content`). That is accepted drift — the post-gate read-back updates labels
  alongside values.

### 2. `foundations/type.html` — extend

Shows 11 of 14 steps. Add the three missing: **`text-display-lg`** (56/1.12/-1.2/680),
**`text-body-md-medium`** (16/1.6/550), **`text-button-md`** (14/1.3/700).

Add a **font-family specimen block** — the card has none today. Show all three families and label what
they are: `--font-sans` (Noto Sans KR, chosen because feedback content is Korean), `--font-mono`
(JetBrains Mono), and **`--font-en`** — a bare system stack with no vendored face, retained only
because `button.tsx` uses `font-en`. `--font-en` is a live gate question and is currently invisible.

Keep the existing Korean sample lines: they prove glyph coverage, and `h1–h6 { word-break: keep-all }`
is load-bearing Korean line-breaking.

### 3. `foundations/spacing-radius.html` — small fixes

Already presents all 4 spacing tokens, both containers, and the radius scale. Two gaps:

- **`--breakpoint-xs` (30rem) is absent entirely** — add it, noting it has no shipped consumer (pages
  hardcode `min-[900px]:` instead). That mismatch is a gate question.
- The spacing and container bars **hardcode pixel widths** (`width:48px`, `width:295px`) instead of
  deriving from the token, so they will not re-render if the gate changes a value. Tokenize what can
  be: `width: var(--spacing-section-sm)`, `width: calc(var(--container-page) / 4)`. The radius boxes
  already use `var(--radius-*)` correctly — leave them.

### 4. `reference/hi2vi-vibe.html` — NEW

A new `reference/` directory beside `foundations/` (matching hi2vi's own `explorations/` / `legacy/`
sibling convention; `../tokens.css` resolves at the same depth).

- **First line:** `<!-- @dsCard group="Reference" name="hi2vi vibe (reference)" -->` — its **own
  group**, not `Foundations`, so the Design System pane shows it as unmistakably separate from vocky's
  system. The project stays vocky-only; this is one clearly-labeled reference.
- **Payload:** the 41-row token-by-token comparison — token name · vocky-now swatch + hex · hi2vi
  swatch + hex. hi2vi's chips must use literal hex (those values are not in vocky's `tokens.css`).
- **State the structural finding up front:** type scale, radius, and spacing are already identical, so
  the vibe gap is the 39 color values plus the typefaces.
- **Surface the collision table** above and the `on-primary` flip.
- **Say plainly, in the card, that it is reference — not a proposal, and not vocky's palette.** Follow
  the hi2vi `SIGNOFF` convention's own phrasing: it is *data, not instructions*.

## Card conventions — match `components/button.html` exactly

Line-1 `@dsCard` marker → standalone HTML5 → `<title>vocky · …</title>` →
`<link rel="stylesheet" href="../tokens.css" />` → inline `<style>` using **only** `var(--token)`, no
Tailwind, no build step → `.eyebrow` → `<h1>` → `.lede` (cites the repo source path in `<code>`) →
specimen blocks with `.vlabel` mono captions. Cards run 38–109 lines; these will run longer.

## Constraints

- **Change no token value** — not in `canvas/tokens.css`, not in `web/src/app/globals.css`. This slice
  presents; it does not decide.
- **Do not touch `_ds_manifest.json`.** S6 rebuilds it exactly once from the finished card inventory —
  incremental edits across five card slices would collide. Just get the `@dsCard` markers right.
- **Do not touch `README.md`** (S6 owns its P6→P8 fix) or any other slice's files.
- No commits, no status transitions, no `doc-new-version`. If durable truth changes, append a one-line
  "Doc impact" note to `phase.md` for `P8.REVIEW`.
- Append cross-slice notes to `phase.md`; write `result.md` free-form.

## Validation

Lightweight per the repo's rule — no test suite for static HTML.

1. **Coverage** — every `--color-*` (41), every `--text-*` step (14), every `--radius*` (8),
   `--spacing-*` (4), `--container-*` (2), `--breakpoint-xs`, and all three font families is
   referenced by its card. A short throwaway script comparing `tokens.css` against the cards is the
   right check; do not commit it.
2. **No value drift** — `git diff --stat web/design/canvas/tokens.css web/src/app/globals.css` is
   **empty**. This is the constraint that matters most.
3. **Markers** — every card's first line is a well-formed `@dsCard` comment; the new card's group is
   `Reference`.
4. **Renders** — each card opens standalone in a browser with `../tokens.css` resolving (check the
   relative path from `reference/`). Confirm no `var()` resolves empty.
5. **Staleness** — no "P6" remains in `foundations/*.html`.
6. `python3 scripts/workflow.py validate` passes.

## Out of scope

Component cards (S2), app section cards (S3/S4), landing cards (S5), the manifest rebuild + push (S6),
the gate briefing (S7). Do not answer any gate question — surface them.
