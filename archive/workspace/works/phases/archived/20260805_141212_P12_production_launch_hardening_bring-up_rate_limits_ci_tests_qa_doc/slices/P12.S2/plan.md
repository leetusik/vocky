# Plan — P12.S2: Repo hygiene sweep

Mode: `/do-whole-phase auto` (orchestrator planned inline; no operator plan gate).
Executor: `slice-executor-low` (risk `low` — fully mechanical; every edit below is spelled out).

**This is a literal-execution slice.** Every file, line, old string and new string is given. Make no other
change, invent no names, fix no unrelated thing you notice, and do not "improve" anything. If any step
does not match what is written here — a line has moved, a target name already exists, a command fails —
**stop and escalate** with what you saw. Do not improvise a repair.

Zero behaviour change and zero visual change is the acceptance bar. Every hex value stays byte-identical.

---

## Edit 1 — `Makefile:15`: drop the retired capture token

`EXPORTED_ENV_VARS` still exports `VOCKY_API_AUTH_TOKEN`, a global capture token that was retired
(P10/P11 replaced it with per-project `vk_` credentials and `VOCKY_API_TOKEN`).

Remove exactly the one token ` VOCKY_API_AUTH_TOKEN` from the list on line 15, leaving the surrounding
names and single-space separators intact.

**Keep `VOCKY_ADMIN_AUTH_TOKEN`** — it is a different, still-live variable that `P12.S1` just made
mandatory. Confusing the two is the one trap in this edit.

After: `grep -n "VOCKY_API_AUTH_TOKEN" Makefile` returns nothing, and
`grep -n "VOCKY_ADMIN_AUTH_TOKEN" Makefile` still returns line 15.

---

## Edit 2 — retire the five vestigial hi2vi design-token names

All five live in the `@theme` block of `web/src/app/globals.css`. Three are renamed (same hex, same
comment); two are **deleted** because nothing in `web/` references them and P8's audit already recorded
both as exact duplicates of existing tokens (`--color-archive-olive` == `muted`, `--color-archive-cream`
== `surface-soft`).

### 2a. `web/src/app/globals.css` — the declarations (lines 36–44)

| Line | Old | New |
|---|---|---|
| 37 | `--color-security-mint: #bee9d5;` | `--color-mint: #bee9d5;` |
| 38 | `--color-security-teal: #2fa477;` | `--color-teal: #2fa477;` |
| 42 | `--color-victory-lime: #9ad4a8;` | `--color-lime: #9ad4a8;` |
| 43 | `--color-archive-olive: #8a968f;` | **delete the whole line** |
| 44 | `--color-archive-cream: #f1f4f0;` | **delete the whole line** |

Keep each surviving line's trailing `/* … */` comment exactly as it is. Do not touch
`--color-trust-sage` (line 39) or any other token.

The section comment on **line 41** currently reads `/* Soft positive + muted neutral tints */`. After the
two deletions only the soft-positive tint remains — change it to `/* Soft positive tint */`.

### 2b. `web/src/app/globals.css` — the header comment (around lines 12–16)

The file header currently ends with **"Do not rename tokens."** and explains that names are ported 1:1
from hi2vi_web. That instruction is what this slice is deliberately retiring, so the file must not
contradict itself. Replace that sentence (keep the rest of the paragraph) with wording to this effect:

> Names are otherwise still 1:1 with hi2vi_web; P12.S2 retired the five vestigial hi2vi-section names
> (`security-mint`, `security-teal`, `victory-lime`, and the unused `archive-olive` / `archive-cream`)
> in favour of role names. Do not rename the remaining tokens.

Match the file's existing comment style and line width. This is the only prose you write in this slice.

### 2c. The six usage sites — exact, and there are no others

Each is a Tailwind utility class in a `className` / CVA variant string:

| File | Line | Old | New |
|---|---|---|---|
| `web/src/components/show-once-key.tsx` | 56 | `border-security-mint` | `border-mint` |
| `web/src/components/ui/chip.tsx` | 19 | `border-security-mint` | `border-mint` |
| `web/src/components/ui/snippet.tsx` | 110 | `border-security-mint` | `border-mint` |
| `web/src/components/ui/snippet.tsx` | 116 | `border-security-teal` | `border-teal` |
| `web/src/components/ui/snippet.tsx` | 116 | `text-victory-lime` | `text-lime` |
| `web/src/components/ui/endpoint-card.tsx` | 36 | `text-security-teal` | `text-teal` |
| `web/src/components/landing/skill-copy-button.tsx` | 77 | `border-security-mint` | `border-mint` |

**Line 116 of `snippet.tsx` also contains `bg-[rgba(190,233,213,0.16)]` — leave that arbitrary value
exactly as it is.** It is the mint hex written inline; changing it would change a rendered colour.

No collision check is needed: `--color-mint`, `--color-teal` and `--color-lime` do not exist in the file
today, and Tailwind's defaults expose only numbered shades (`teal-500`, …), never the bare name.

---

## Edit 3 — clear the 14 `prettier --check` failures

Run this **last**, after edits 1 and 2, so it also formats anything those edits touched:

```sh
cd web && pnpm exec prettier --write .
```

The 14 files it will rewrite (all pre-existing P4-era drift, none of them a file edit 2 touches):

```
README.md
src/app/(app)/projects/[projectId]/actions.ts
src/app/apple-icon.tsx
src/app/opengraph-image.tsx
src/components/landing/agent-quickstart.tsx
src/components/landing/hero.tsx
src/lib/bff.ts
src/lib/env.ts
src/lib/session.ts
src/lib/vocky/auth.ts
tests/auth-routes.test.ts
tests/session-guards.test.ts
tests/session.test.ts
tests/vocky-auth.test.ts
```

This is **formatting only** — never hand-edit these files, never change logic while you are in them, and
do not run prettier from the repo root. `web/.prettierignore` excludes `public/`, so `install.sh` and the
served `SKILL.md` are untouchable by this step; the CI byte-parity gate must stay green.

If prettier rewrites a file **not** on that list, or rewrites `web/public/**`, stop and escalate.

---

## Boundaries

- Nothing outside `Makefile` and `web/` changes. No Python, no `compose*.yml`, no `.github/`, no `deploy/`.
- Do **not** edit anything under `docs/`, do **not** run `doc-new-version`, do **not** commit, and do
  **not** run any `scripts/workflow.py` state command.
- Do not add, remove or reorder any other design token, and do not touch `web/public/`.
- This slice changes no rendered pixel. If any check suggests a visual change, that is a failure, not a
  finding to accept.

## Validation — run all of these and report the actual output

1. `grep -rn "security-mint\|security-teal\|victory-lime\|archive-olive\|archive-cream" web/ --exclude-dir=node_modules --exclude-dir=.next` → **no matches**.
2. `grep -n "VOCKY_API_AUTH_TOKEN" Makefile` → **no matches**; `grep -n "VOCKY_ADMIN_AUTH_TOKEN" Makefile` → still present.
3. `grep -n "#bee9d5\|#2fa477\|#9ad4a8" web/src/app/globals.css` → the same **three** lines as before, values unchanged; and `grep -n "archive-olive\|archive-cream" web/src/app/globals.css` → no matches. (Do **not** assert on the hexes `#8a968f` / `#f1f4f0` — they legitimately survive as `--color-muted` and `--color-surface-soft`.)
4. `cd web && pnpm exec prettier --check .` → **clean, 0 files**.
5. `cd web && pnpm lint && pnpm typecheck && pnpm test && pnpm build` → all green. `pnpm build` is the real proof that every renamed utility class still resolves.

Any failure in step 5 that you cannot attribute to a line in this plan → stop and escalate; do not fix it.

## Deliverables

- `result.md` in this slice folder (free-form): the edits made, the verbatim output of the five checks,
  and a one-line confirmation that no hex value changed.
- A short note appended to `phase.md` § *Findings & Notes*: the three surviving tokens' new names
  (`mint`, `teal`, `lime`), the two deleted, and that `prettier --check` under `web/` is now clean — which
  is the precondition `P12.S6` needs before it can add that gate to `ci.yml`.
- **No "Doc impact" line is expected** — this slice changes no durable truth. If you believe it does, say
  so in `result.md` rather than editing any doc.

---

## Escalation 1: `slice-executor-low` → `slice-executor-mid`

The low tier executed all three edits correctly and reported every check green **except** two conflicts
that are defects in this plan, not in the work. Both are hereby resolved by the orchestrator. The tree as
the low tier left it is **correct and complete** — do not revert or redo any of it.

### The low tier's findings (verbatim in substance)

1. `pnpm exec prettier --write .` also reformatted `web/src/components/ui/snippet.tsx`, which is **not** on
   this plan's 14-file list and **is** a file Edit 2c modified. The plan named that exact situation as a
   hard escalation trigger.
2. Validation step 1 (`grep … → no matches`) **cannot pass** while Edit 2b requires writing the five
   retired token names verbatim into the `globals.css` header comment. The two instructions contradict
   each other in the same file.

Everything else was reported green: `Makefile` correct (retired token gone, `VOCKY_ADMIN_AUTH_TOKEN`
still on line 15); three hexes unchanged under the new names; `archive-olive` / `archive-cream`
declarations gone; `prettier --check` clean; `pnpm lint && typecheck && test (78 passed) && build` green.

### Resolution 1 — the `snippet.tsx` reflow is ACCEPTED

Verified from `git diff`: prettier collapsed a two-line string literal to one line **because Edit 2c's
rename made it shorter** (`border-security-teal … text-victory-lime` → `border-teal … text-lime`). Same
classes, same DOM, same rendered pixels, `bg-[rgba(190,233,213,0.16)]` untouched. This is a direct,
predictable consequence of an edit this plan ordered, so it is inside the slice's scope, not outside it.
The 14-file list was descriptive of the *pre-existing* drift, and should have said so.

### Resolution 2 — validation step 1 is REPLACED

The header comment is deliberate historical documentation and stays exactly as written. Step 1 is
replaced by these two checks, which say what was actually meant (that no **token declaration or utility
class** survives, prose aside):

```sh
# A. no declaration and no usage of any retired name — must return NOTHING (exit 1)
grep -rn -- "--color-security-mint\|--color-security-teal\|--color-victory-lime\|--color-archive-olive\|--color-archive-cream\|border-security-\|text-security-\|text-victory-\|bg-archive-" web/ --exclude-dir=node_modules --exclude-dir=.next

# B. the only surviving mentions are the three header-comment lines in globals.css
grep -rn "security-mint\|security-teal\|victory-lime\|archive-olive\|archive-cream" web/ --exclude-dir=node_modules --exclude-dir=.next
```

The orchestrator has already run both: **A returns nothing (exit 1)**, and **B returns exactly three
lines, all `web/src/app/globals.css:17-19`**, inside the header comment. That is the passing state.

### What the mid tier must actually do

The implementation is done. Your job is verification and bookkeeping only:

1. Re-run checks A and B above, plus this plan's original validation steps 2, 3, 4 and 5, and report the
   real output. If any of them now fails, that is a genuine regression — report it rather than patching.
2. Make **no further source edits** unless a check fails. In particular do not revert the `snippet.tsx`
   reflow and do not touch the header comment.
3. Write `result.md` for this slice (it was intentionally not written), covering all three edits, the
   verbatim check output, a confirmation that no hex value changed, and both escalation resolutions.
4. Append the short note to `phase.md` § *Findings & Notes* the original Deliverables section asks for:
   the three surviving tokens' new names (`mint`, `teal`, `lime`), the two deleted, that the retired names
   survive only in the `globals.css` header comment as history, and that `prettier --check` under `web/`
   is now clean — the precondition `P12.S6` needs before adding that gate to `ci.yml`.
5. Still no commit, no `workflow.py` state command, no `docs/` edit, no "Doc impact" line expected.
