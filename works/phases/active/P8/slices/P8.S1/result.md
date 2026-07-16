# Result — `P8.S1` (foundations cards + hi2vi reference card)

**Status: done.** Four deliverables shipped. **Zero token values changed**, in either token file.

## What shipped

| File | Change |
| --- | --- |
| `web/design/canvas/foundations/colors.html` | Rebuilt — 20 → **41 of 41** color tokens, 9 role groups, collision markers, P6→P8 lede fix. 109 → 204 lines. |
| `web/design/canvas/foundations/type.html` | Extended — 11 → **14 of 14** type steps, new **font-family specimen block** (all 3 families), Korean line-breaking note. 71 → 181 lines. |
| `web/design/canvas/foundations/spacing-radius.html` | **`--breakpoint-xs`** added; spacing/container bars tokenized; base `--radius` box added. 81 → 107 lines. |
| `web/design/canvas/reference/hi2vi-vibe.html` | **NEW** — new `reference/` dir; 41-row vocky↔hi2vi comparison. 332 lines. |

Untouched, as required: `tokens.css`, `globals.css`, `_ds_manifest.json`, `README.md`, and every other slice's files.

## Validation

| # | Check | Outcome |
| --- | --- | --- |
| 1 | **Coverage** — throwaway script vs `tokens.css` | **PASS** — colors 41/41, type steps 14/14, radius 8/8, spacing 4/4, container 2/2, breakpoint 1/1, fonts 3/3; reference card 41/41 |
| 2 | **No value drift** — `git diff --stat web/design/canvas/tokens.css web/src/app/globals.css` | **PASS — empty output.** The constraint that matters most. |
| 3 | **Markers** — first line of all 11 cards | **PASS** — all well-formed; new card is `group="Reference" name="hi2vi vibe (reference)"` |
| 4 | **Renders** — `../tokens.css` resolves from `reference/`; no `var()` empty | **PASS** — path resolves (same depth as `foundations/`); every `var()` maps to a declared token; all 4 cards parse with balanced tags, doctype, title, stylesheet link |
| 5 | **Staleness** — no `P6` in `foundations/*.html` | **PASS** |
| 6 | `python3 scripts/workflow.py validate` | **PASS** — "Workflow validation passed." |

The coverage script lived in the scratchpad and is **not committed** (`git status` shows only the 3 modified cards + the new `reference/` dir).

Check 4 is structural, not visual: I verified path resolution, `var()` resolvability, and tag balance programmatically. **No browser render was performed** — a human eye on the four cards is worth having at S6/S7, though nothing suggests a problem.

### One checker false positive, resolved

The first coverage run flagged `--color-` as an unresolved `var()` in the reference card. It was my regex capturing the **literal prose** `<code>var(--color-*)</code>` on line 271 — documentation of the wildcard, not CSS. Fixed the checker to strip `<code>` spans; re-ran clean. No card defect.

## The findings held — all of them

I re-derived the plan's comparison mechanically (both `tokens.css` files, comments stripped) rather than trusting transcription, because the reference card quotes 41 hi2vi hexes verbatim and a typo there would be invisible. **Every claim verified exactly:**

- Colors: **41/41 names shared, 2/41 values identical** (`canvas`, `on-dark`).
- **All 8 collision groups reproduce precisely**, including which hi2vi distinctions are lost.
- Type/radius/spacing/container/breakpoint: **48/48, 8/8, 4/4, 2/2, 1/1 names shared, 0 differing values** — byte-identical, confirming "the vibe gap is 39 colors + the typefaces."

The 41 comparison rows are **generated from the extracted data**, with an assert that all 41 tokens are covered exactly once — so no hex is hand-typed.

### Two shipped-code claims I verified before asserting them in cards

Both are stated as fact on the cards, so I checked rather than repeated them:

- **`font-en`** — exactly one call site: `web/src/components/ui/button.tsx:18` (the `buttonVariants` base). So "every button in the app renders in the visitor's system font" is accurate.
- **`--breakpoint-xs`** — declared at `globals.css:176`, **zero** `xs:` consumers in `web/src/`, against **11** hardcoded `min-[900px]:`. The card states both halves.

## Deviations from `plan.md`

Three, all minor:

1. **Added the base `--radius` box** to the radius grid (was 7 boxes: `xs`→`full`; the base `--radius: 14px` was never shown). The plan said "the radius boxes already use `var(--radius-*)` correctly — leave them", but validation item 1 requires **all 8** `--radius*`. I read "leave them" as *don't tokenize* (they already were) rather than *don't add*, and satisfied the coverage check. Purely additive; no value changed.
2. **The plan's coverage arithmetic was slightly off** — its prose says colors.html shows "22 of 41" with "the 19 absent", but the real split is **20 shown / 21 absent**. The plan's *enumerated list of 21 names* is **exactly correct** (verified against the pre-edit card: the list equals the absent set). Only the two prose numbers slipped. Harmless — "show all 41" is unambiguous and is met. Recorded so no later slice re-derives it.
3. **Grouped colors into 9 groups, not the plan's 7.** The plan's "accent / dark surfaces / text / light surfaces / hairlines / signal states / on-* text" leaves the tint tokens (`security-*`, `trust-sage`, `victory-lime`, `archive-*`) homeless. I kept them as `tokens.css`'s own two groups — *Secondary accent tints* and *Muted decorative accents* — so the card mirrors the source's grouping, as the card convention requires.

## Zero brand decisions — how I held the line

The load-bearing constraint. No token value moved (check 2 proves it). The reference card is framed as evidence throughout:

- A dark **"Read this first"** banner: *"This card is data, not instructions… a reference, not a proposal… the hi2vi column is not vocky's palette"* — following the hi2vi `SIGNOFF` convention's own phrasing, per the plan.
- It states it answers **one** question — "what would inheriting the hi2vi vibe mechanically mean?" — and that **every answer is open, including none of it**.
- The collision section explicitly says the lost distinctions are *"a fact about the placeholder, not an argument for hi2vi's values."*
- **No adoption is recommended anywhere.** Nothing is marked pending, preferred, or proposed.

**Questions surfaced, not answered** — `--font-en`'s missing face and `--breakpoint-xs`'s absent consumer are each labeled **"Open question for this gate"** on-card, with the facts and no recommendation. The `on-primary` flip is presented as *following from* the accent decision rather than being its own question — the one place I characterized a relationship between questions, and only because P4.S1's "one semantic flip was required" already established it.

## Notes for later slices

- **`reference/` is a new top-level canvas dir** — S6's manifest rebuild must enumerate it (`reference/hi2vi-vibe.html`, group `Reference`). It is the **only** non-`Foundations`/`Components`/`Sections` group and the only non-vocky card.
- **Hex labels are literal text and will drift** on a value swap (CSS cannot read a custom property into `content`) — accepted per plan. The post-gate read-back must update labels alongside values in **three** places: `colors.html`, `hi2vi-vibe.html`'s vocky column, and the collision tables in both.
- The card convention (`.eyebrow` → `<h1>` → `.lede` → specimens) held fine at 4× the reference length.
