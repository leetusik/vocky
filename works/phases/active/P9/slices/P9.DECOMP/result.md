# P9.DECOMP — result: sized the apply phase from `build-prompt.md`

## What this slice did

Sized P9 (the apply half of P8's closed design gate) from the read-only implementation contract at
`docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md`. Re-read the full design record
(`build-prompt.md` primary; `result.md` §7 departures + §9 apply-time to-dos; `SIGNOFF.md` token delta) as
read-only source of truth, referenced P8's measured codebase facts (did not re-derive them), created the
seven middle slices as bare folders, and seeded `phase.md`. **No implementation code was written; nothing
under `web/` or under the design `output/` record was touched.**

## Slices created (7 bare folders, `slice.json` only, no `plan.md`)

| Slice | Name | Kind | Risk | Order | Depends on |
|---|---|---|---|---|---|
| `P9.S1` | Foundations: `@theme` swap + Pretendard loader | implementation | medium | 1 | — |
| `P9.S2` | Primitives: button/card/badge/field + new Select/Chip + barrel | implementation | medium | 2 | P9.S1 |
| `P9.S3` | App components + brand mark | implementation | medium | 3 | P9.S2 |
| `P9.S4` | App surfaces (all six) | implementation | medium | 4 | P9.S3 |
| `P9.S5` | Net-new states: loading/error/not-found/global-error | implementation | medium | 5 | P9.S2 |
| `P9.S6` | Landing: reclaim `/`, `landing.ts`, `components/landing/*` | implementation | **high** | 6 | P9.S3 |
| `P9.S7` | Consistency & DoD sweep + design-fidelity fixes | implementation | **high** | 7 | P9.S4, P9.S5, P9.S6 |

Verified: each folder holds only `slice.json` (no `plan.md`); S7's `depends_on` array holds the three deps
as separate entries (the `--depends-on` append flag was repeated per dep, not comma-joined). Risks/orders
match the manifest; S6 and S7 are `high`, the rest `medium`.

## Rationale (full detail in `phase.md` → Decomposition)

- **Foundation-first, faithful to `build-prompt.md §1`.** `1→2→3` strictly ordered (the `@theme` value swap
  re-themes every surface → primitives consume the tokens → app components compose the primitives). S4
  composes S3. **S5 and S6 are independent of each other and of most of S4** (`§1`: "steps 5–6 are
  independent of each other and of most of 4"). S7 is the closing sweep over all three leaf slices.
- **Risk is the cost lever.** Flex mode: `low`=sonnet, `mid`/`high`=opus. No P9 slice is fully mechanical —
  RESPECT-THE-DESIGN demands "closest-to-designed-intent, never a plainer fallback" (a judgment call
  everywhere) — so every slice is ≥ `medium` (opus). S6 (largest net-new surface + grounded copy) and S7
  (last line of defense against cross-slice drift) are `high`. Spending opus across this brand-defining
  phase is the intended trade.
- **File-ownership boundaries prevent any file being edited twice** (`globals.css`/`fonts.ts`→S1; §2.5
  literal fixes subsumed into S2's `button.tsx`/`card.tsx` rewrites; new components owned once; the
  `min-[900px]:`→`app:` migration distributed per-file with S7 as the DoD backstop).

## Deviation from the proposed manifest

**None.** The `P9.DECOMP` plan's 7-slice cut was executed verbatim — names, kinds, risks, orders, and every
dependency edge. My full independent re-read of `build-prompt.md` (§1 build order, §8 per-file manifest, §10
DoD) confirmed the cut maps faithfully to the contract and the intent's expected shape, so no merge, split,
or risk change was warranted.

One dependency nuance was **surfaced as a Finding rather than changed**: S5's `error.tsx`/`global-error.tsx`
compose the brand mark created in S3, but S5's recorded dep was left at **S2** (its foundational
primitive need). `depends_on` is advisory and existence-only; S5's order (5) already sequences it after S3
(3), so the mark exists at S5's turn. Moving the edge to S3 would not change execution and would blur the
plan's "S5 is primitive-level, independent of S4/S6" framing. The S5 planner is told (in `phase.md` →
Findings) to compose the S3 mark, not re-create it.

## `phase.md` seeded

Filled all stub sections in place:
- **Context** — what P9 applies (P8's signed-off round 01) and the on-disk source of truth
  (`build-prompt.md`; executors have no DesignSync; record is read-only).
- **Decomposition** — the 7-slice table + ordering/risk/file-ownership rationale + the "no deviation" note.
- **Findings & Notes** — carried forward the load-bearing traps: the re-theme property, §2.5 literals owned
  by S2, the distributed breakpoint migration verified in S7, backend-none, Pretendard vendoring as the one
  named build cost, the S5→brand-mark dependency nuance, the file-ownership boundaries, known record
  staleness, reactive fidelity fixes, and the `--depends-on` append rule.
- **Constraints** — the RESPECT-THE-DESIGN block verbatim, the locked-floors list, backend-none, read-only
  record, docs-versioned-once-at-`P9.REVIEW`, keep-tests-terse, do-not-touch-P6.
- **Doc impact** — pre-recorded the durable-truth areas P9 will make concrete (frontend/experience/decisions
  `D-P8-1` applied) for `P9.REVIEW` to consolidate; backend docs need no change.
- **Open Questions** — recorded that none block P9; the two apply-time choices (Pretendard mechanism,
  optional token rename) are named with cost as slice-level decisions.

## Doc impact (this slice)

No `doc-new-version` in DECOMP (docs are versioned once, at `P9.REVIEW`). Appended a pre-recorded Doc-impact
line to `phase.md` naming the durable-truth areas P9 will touch (`frontend.md`, `experience.md`,
`decisions.md`'s `D-P8-1` applied) for the review to consolidate; backend docs need no change.

## Validation

- `python3 scripts/workflow.py validate` — **passed** (clean, both before and after slice creation). The
  seven new bare folders are `todo` with no `plan.md`, which is correct and expected for freshly-created
  middle slices (they are not `ready`, so the plan-integrity check does not flag them).
- Confirmed via `ls` + `cat slice.json`: seven slice folders exist, each with only `slice.json`, correct
  kinds/risks/orders/deps.
- No changes under `web/` or `docs/reference/design/.../output/` or `SIGNOFF.md` — DECOMP wrote no code and
  did not edit the read-only record.
