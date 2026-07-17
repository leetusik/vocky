# P9.DECOMP — Plan: decompose "Apply the Design: App UI, Landing & Feature Changes"

## Context — why this slice exists

P9 is the **apply half** of P8's now-closed design gate. P8 landed a complete, verbatim,
**read-only** implementation contract at
`docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md` — exact token values,
component APIs with class strings, per-surface changes, a per-file manifest (§8), and a DoD (§10).
P9's whole job is to build that faithfully.

`P9.DECOMP` is the **native decomposition** the workspace deliberately could not run until the gate
closed (there was nothing to size from). Its only job is to **size the phase from `build-prompt.md`**:
create the middle-slice folders and seed `phase.md`. **It writes no implementation code** and does not
pre-fill any slice's `plan.md`.

- **Executor:** `slice-executor-high` (decomposition always routes to the top tier).
- **Source of truth on disk:** `build-prompt.md` is the complete spec — **P9's implement executors have
  no `DesignSync`**, so what's on disk is all they get. `result.md` (departures + §9 apply-time to-dos)
  and `SIGNOFF.md` (the token delta) are companions. The 30-card set stays in the design project; do
  **not** copy it down. Treat everything under `output/` as read-only data.

## What the executor must do (and only this)

1. **Re-read the design record** (`build-prompt.md` primary; `result.md` §7 departures + §9 to-dos;
   `SIGNOFF.md`) as read-only source of truth. Do not re-derive codebase facts — they're measured in
   `works/phases/active/P8/phase.md` → *Findings & Notes*; reference them, don't re-measure.
2. **Create the 7 middle slices below** with `new-slice` — **bare folders only** (never pre-fill their
   `plan.md`). `--depends-on` is `action="append"`: **repeat the flag per dep**, never comma-separate
   (a comma-joined value stores as one literal dep and fails `validate`).
3. **Seed `phase.md`**: Context, the Decomposition table + rationale, Findings & Notes (carry forward
   the load-bearing traps below), Constraints (the RESPECT-THE-DESIGN block verbatim + locked floors +
   backend-none + docs-versioned-once-at-REVIEW + keep-tests-terse), and Open Questions (none block —
   the apply-time choices are named).
4. **Return `done`.** No code, no commits, no status transitions (the orchestrator does those).

## Proposed middle-slice breakdown

Follows `build-prompt.md §1` (foundation-first build order) and the phase intent's expected shape
(*foundation first → net-new capabilities isolated → design-fidelity fix → consistency/DoD sweep last*).
`1→2→3` are strictly ordered; **S5 and S6 are independent of each other and of most of S4**.

| Slice | Name | Kind | Risk | Order | Depends on | Scope (build-prompt §) |
|---|---|---|---|---|---|---|
| `P9.S1` | Foundations: `@theme` swap + Pretendard loader | implementation | medium | 1 | — | §2 color, §3 type+`fonts.ts`, §4.1 radius, §4.2 spacing/containers, §4.3 breakpoint token, header comment; verify shadcn aliases (§2.5 last bullet) |
| `P9.S2` | Primitives: button/card/badge/field + new Select/Chip + barrel | implementation | medium | 2 | S1 | §4.4–4.12 rewrites incl. the §2.5 button/card literal fixes; new `select.tsx`/`chip.tsx`; `ui/index.ts` |
| `P9.S3` | App components + brand mark | implementation | medium | 3 | S2 | §4.5 logout→Button, §4.13 StatTiles, §4.14 area TrendChart, §5 app-shell/rail-nav, §7.1 new `brand/{mark,wordmark}` |
| `P9.S4` | App surfaces (all six) | implementation | medium | 4 | S3 | §5 auth-card, dashboard, project detail (breadcrumb/badges/revoke/key panel), feedback list (Select/Chip), feedback-fields, feedback detail (Chip), island forms |
| `P9.S5` | Net-new states | implementation | medium | 5 | S2 | §6 `loading`/`error`/`not-found`/`global-error` |
| `P9.S6` | Landing — reclaim `/` | implementation | **high** | 6 | S3 | §7 `page.tsx`, new `content/landing.ts`, new `components/landing/*` |
| `P9.S7` | Consistency & DoD sweep + design-fidelity fixes | implementation | **high** | 7 | S4, S5, S6 | §10 DoD checklist; kill any residual `min-[900px]:` / `--breakpoint-xs` / `inputVariants()` `<select>`; retire dead `content/nav.ts`/`section-ids.ts` if unused; fix drift from build-prompt exact specs |

Exact `new-slice` manifest for the executor to run:

```
new-slice --phase P9 --slice P9.S1 --name "Foundations: @theme swap + Pretendard loader" --kind implementation --risk medium --order 1
new-slice --phase P9 --slice P9.S2 --name "Primitives: button/card/badge/field + new Select/Chip + barrel" --kind implementation --risk medium --order 2 --depends-on P9.S1
new-slice --phase P9 --slice P9.S3 --name "App components + brand mark" --kind implementation --risk medium --order 3 --depends-on P9.S2
new-slice --phase P9 --slice P9.S4 --name "App surfaces (all six)" --kind implementation --risk medium --order 4 --depends-on P9.S3
new-slice --phase P9 --slice P9.S5 --name "Net-new states: loading/error/not-found/global-error" --kind implementation --risk medium --order 5 --depends-on P9.S2
new-slice --phase P9 --slice P9.S6 --name "Landing: reclaim /, landing.ts, components/landing/*" --kind implementation --risk high --order 6 --depends-on P9.S3
new-slice --phase P9 --slice P9.S7 --name "Consistency & DoD sweep + design-fidelity fixes" --kind implementation --risk high --order 7 --depends-on P9.S4 --depends-on P9.S5 --depends-on P9.S6
```

## Risk rationale — the phase's cost lever

Under flex mode `low`=sonnet@xhigh, `mid`/`high`=opus@xhigh, so **`low` is the only real cost saver**,
reserved for *fully mechanical, no-judgment* plans. **No P9 slice qualifies:** RESPECT-THE-DESIGN
requires "closest-to-designed-intent, never a plainer fallback" wherever a value isn't spelled out —
that is a judgment call in every slice. So every slice is **≥ medium** (opus). **S6 (landing)** and
**S7 (sweep/fidelity)** are rated **high**: S6 is the largest net-new surface with the most composition
and grounded copy; S7 must catch cross-slice drift and is the last line of defense before review. This
is the operator's brand-defining phase and the intent is emphatic about fidelity — spending opus across
the board is the intended trade.

## File-ownership boundaries (no file edited by two slices)

- **`globals.css` + `fonts.ts` → S1 only.** S1 does **not** touch `button.tsx`/`card.tsx`: their §2.5
  hardcoded-shadow/border literal fixes are subsumed by S2's wholesale rewrite of those files — fixing
  them in S1 would be thrown away. (Build-prompt §1.1 bundles §2.5 into "foundations"; we split it on
  file ownership so no file is edited twice.) S1 owns only the `globals.css` shadcn-alias verify (§2.5
  last bullet).
- **The `min-[900px]:` → `app:` migration is distributed, not one slice.** S1 defines
  `--breakpoint-app` and removes `--breakpoint-xs`; each slice migrates the literals in **its own**
  files (S3: app-shell/rail-nav; S4: feedback pages). **S7 verifies zero `min-[900px]:` remain** — the
  DoD backstop.
- **New components live where they're first needed but are owned once:** `select`/`chip` → S2;
  `brand/{mark,wordmark}` → S3; `content/landing.ts` + `components/landing/*` → S6.

## RESPECT THE DESIGN — record verbatim in phase.md Constraints (goes into every downstream slice plan + dispatch prompt)

> Ship every designed element as designed — layout, density, hierarchy, tokens, interactions,
> empty/error/loading states. **Do not drop, simplify, restyle, or "improve" a designed element to save
> effort** — that is a correctness failure, not a shortcut. Where an exact value isn't specified, pick
> the option closest to the designed intent, **never a plainer fallback**. Where the design implies
> backend/data work, **build the backing** and surface the choice — don't quietly drop the feature.
> (This round implies **no** backend change; build-prompt §9 confirms it.)

## Findings & traps DECOMP must carry into phase.md

- **The re-theme property:** utilities compile to `var(--color-*)`, so §2 is a value swap — S1's
  `globals.css` edit re-themes every surface at once. The literals a swap does **not** reach are §2.5
  (owned by S2, above).
- **Backend/data: no change required** (build-prompt §9 / SIGNOFF). No `src/vocky/**`, no P2/P3 contract
  reopening. The pricing "coming later" control is disabled copy — **no waitlist endpoint**.
- **The one named build cost is Pretendard vendoring** (`next/font/local` + woff2 **or**
  `@fontsource/pretendard`) — an S1 apply-time decision (result.md §9), not a DECOMP one. Fallback chain
  must keep a Korean-capable face (Noto Sans KR).
- **Locked floors (must survive every slice):** identical login error (401→one message), 404-never-403
  copy, show-once `vk_` key warning + revoked-stays-listed, download-only attachments, UTC labels,
  `h1–h6 { word-break: keep-all }`, Korean-capable `--font-sans`, `FieldError` empty `aria-live` region,
  distinct empty states.
- **Design-fidelity fixes are reactive, not pre-cut:** S7 folds the fidelity check into the DoD sweep;
  cut a separate `--kind fix` slice at a fractional order only if a slice reveals substantial drift
  (v13: *"part of the normal shape, not a failure"*).
- **Known record staleness (apply-time nit, do NOT edit the read-only record):** both returned files
  still name the two monolith HTMLs as "visual source of truth"; the card set superseded them.
  `build-prompt.md` is the on-disk truth P9 builds from.

## Docs

No `doc-new-version` in DECOMP or any middle slice (constraint: docs versioned **once, at `P9.REVIEW`**).
Durable-truth changes get a one-line "Doc impact" note in `phase.md` for the review to consolidate.

## Verification

- `python3 scripts/workflow.py validate` clean.
- Seven slice folders exist under `works/phases/active/P9/slices/` (`P9.S1`…`P9.S7`), each with a
  `slice.json` and **no** `plan.md`.
- `phase.md` seeded: Decomposition table + rationale, Findings & Notes, Constraints (RESPECT-THE-DESIGN
  block present), Open Questions.
- `git status` shows **no** change under `web/` or `docs/reference/design/output/` (DECOMP writes no code
  and never edits the read-only record).
