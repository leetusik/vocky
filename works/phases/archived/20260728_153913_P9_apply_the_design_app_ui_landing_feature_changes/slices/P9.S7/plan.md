# P9.S7 — Plan: Consistency & DoD sweep + design-fidelity fixes

## Context — why this slice exists

The closing slice (v13's expected shape: a consistency/DoD sweep last, with the design-fidelity fix folded
in). S1–S6 applied the design surface-by-surface; S7 verifies the **whole app** against `build-prompt.md
§10`'s Definition of Done, catches any cross-slice drift or fidelity gap and **fixes it inline**, and
retires the dead nav/section-id leftovers the landing made removable. It is the last gate before
`P9.REVIEW`. Depends on S4+S5+S6 (all done).

Source of truth on disk (no DesignSync): `build-prompt.md §10` (the DoD) + §2–§7 (the exact specs to check
drift against). Read `works/phases/active/P9/phase.md` (Findings & Constraints) first.

## RESPECT THE DESIGN — the load-bearing constraint (verbatim; in every P9 plan + dispatch)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; §9 confirms it.)

## The work

### 1. Verify the DoD §10 checklist (fix any drift inline)
Walk every §10 item across the built app; for each, confirm it holds and **fix in place** if it drifted:
1. `globals.css` holds the §2/§3/§4 values, no accidental palette duplicates, header comment updated.
2. Pretendard loads (Korean renders) with a Korean-capable fallback; `--font-en` not a bare system stack.
3. Buttons `rounded-md`; `ghost`/`destructive`/`destructiveOutline` exist; LogoutButton is a `Button`.
4. `Select` + `Chip` exist and are **used** (feedback filters `Select`, feedback tags `Chip`); no
   `inputVariants()`-template `<select>` remains.
5. Badge `archive` split; credential status `active`/`revoked`; rating `liked`/`disliked`/`unrated`.
6. TrendChart is the dependency-free area redesign with the a11y summary + both empty shapes.
7. All six app surfaces render the new system at compact density; project detail has a breadcrumb.
8. `/` serves the landing to signed-out visitors, bounces signed-in to `/dashboard`; landing copy from `content/landing.ts`.
9. `loading`/`error`/`not-found`/`global-error` exist and match; 404 copy is generic (404-never-403).
10. `--breakpoint-xs` gone; `--breakpoint-app` used; **no `min-[900px]:` literals remain**.
11. **Locked floors intact:** identical login error, 404-never-403, show-once key warning + revoked-stays-listed,
    download-only attachments, UTC labels, `word-break: keep-all`, Korean-capable `--font-sans`, `FieldError`
    `aria-live`, distinct empty states.
12. **No `src/vocky/**` change; all data maps to existing serializers.**

### 2. Cross-slice consistency + design-fidelity spot-check
Grep-assert the negative-space invariants (all should already hold — this is the backstop): zero
`min-[900px]:`, zero `--breakpoint-xs`, zero `inputVariants()`-template `<select>`, zero old Badge/Button/
Card variant names (`softGreen`/`secondaryOnDark`/Card `security`/`archive`, etc.). Spot-check fidelity
against `build-prompt.md` exact specs: a sample of the §2.1 token values in `globals.css`, button base
`rounded-md`, the §4.7 badge variants, the landing composing real primitives. Fix any mismatch to the spec.

### 3. Retire the dead nav/section-id leftovers (confirmed safe)
`NAV_LINKS`/`SKIP_TO_CONTENT` are exported but never rendered; `overview`/`primitives` have no references
outside the dead nav files (both grep-verified). Retire them:
- Delete `web/src/content/nav.ts` (`NAV_LINKS`, `SKIP_TO_CONTENT`, the `section()` helper).
- Remove `overview`/`primitives` from `SECTION_IDS` (`content/section-ids.ts`) — leaving only the live
  landing anchors `features`/`how`/`pricing`.
- Remove the `NAV_LINKS`/`SKIP_TO_CONTENT` exports from `content/index.ts`.
- If `NavLink`/`Cta`/the `sectionId` field in `content/types.ts` become fully unused after this, remove them
  too (grep-confirm first; leave anything still referenced). **Re-grep after each deletion** — a red build
  means something still used it; do not leave the tree red.

### 4. Full verification + broad smoke
`pnpm typecheck` / `lint` / **`build`** / **`test`** (the vitest suite — P9 touched no backend/lib, so it
must stay green; fix or flag any break). Dev-server smoke of every surface: `/` (signed-out landing +
signed-in bounce), `/login`, `/dashboard`, a `/projects/[id]`, `/feedback` (+ a filtered query), a
`/feedback/[id]`, and an unknown URL (→ the vocky 404).

### 5. Pre-existing format debt — flag, do NOT fix
There are **20 pre-existing** `format:check` failures in P4-era files (unrelated to P9). Confirm P9
introduced **none** (all P9-touched files are prettier-clean). **Do NOT reformat those 20** — that's P4
debt, out of P9's charter; fixing them would muddy the phase diff. Record them in `result.md` as a flagged
follow-up (the orchestrator may open a defer-job); the review notes `format:check` fails only on
pre-existing files.

## Files S7 may touch

Only: (a) drift fixes the DoD walk surfaces (targeted, spec-conforming — expected to be few or none); (b)
the dead-content retirement (`content/nav.ts` delete, `section-ids.ts`, `content/index.ts`, maybe
`types.ts`). No wholesale rewrites.

## Boundary — do NOT

- Do **not** re-design or restyle a **correct** element — fix only genuine drift from `build-prompt.md`.
  A sweep is not a redesign pass.
- Do **not** touch backend / `src/vocky/**` / `lib/vocky/*`, or reformat the pre-existing P4 files.
- Do **not** run `doc-new-version` (docs are consolidated at `P9.REVIEW`).
- If the sweep uncovers **substantial** drift beyond a targeted fix, record it and return `needs_operator`/
  `blocked` rather than silently expanding scope.

## Verification

- `cd web && pnpm typecheck && pnpm lint && pnpm build && pnpm test` all green.
- `prettier --write` any file S7 touches (and confirm the P9-touched set is clean); the 20 pre-existing
  failures remain (flagged, not fixed).
- Greps: `content/nav.ts` gone; `SECTION_IDS` has only `features`/`how`/`pricing`; no `NAV_LINKS`/
  `SKIP_TO_CONTENT` exports; and the §1 negative-space invariants all hold.
- The DoD §10 walk recorded item-by-item in `result.md` (each ✓ or the fix applied).
- Dev-server smoke of all surfaces + the 404 passes.

## Doc impact (append to `phase.md` → Doc impact; do NOT version docs here)

DoD §10 fully met; dead nav/section-id leftovers retired (`content/nav.ts` gone, `SECTION_IDS` trimmed to
the landing anchors). This completes the P9 apply — `P9.REVIEW` consolidates the accumulated Doc-impact
notes into `frontend.md`/`experience.md`/`decisions.md` versions.
