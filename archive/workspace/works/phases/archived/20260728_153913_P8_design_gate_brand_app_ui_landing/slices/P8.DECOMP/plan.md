# P8.DECOMP — decompose the design gate into round-1 slices

## Context

P8 runs the real Claude Design gate that P4 deferred (**D-P4-3**): P4.S1 shipped the design-system
*mechanism* only — the Tailwind v4 `@theme` block in `web/src/app/globals.css` plus the CVA primitives in
`web/src/components/ui/` — at a knowingly placeholder palette. **No vocky brand exists yet.**

This slice's whole job is to cut the phase's middle slices. It writes no design and no code. **Round 1
only** — v13 is explicit that *you do not know what the operator will design*, so the read-back is
expected to re-shape the phase, and round 2 gets cut at a fractional order afterward.

Read `phase.md` first — its *Findings & Notes* are already fully harvested. **Do not re-derive them.**
`intent.md` is the source of truth for what the operator asked.

**Why this decomposition is small.** The reverted v12 decomposition (`d20badf`) cut **seven** middle
slices: seed → brief → gate → synthesis, where the seed split three ways (baseline render, DS cards, six
surface mirrors). **v13 retires that entire seeding arm** — Claude Design reads the real repo itself via
Connect GitHub, so Claude Code authors no cards, no canvas, no token mirror. Its one output is
`handoff.md`. Those seven collapse to **one** design slice, whose two commits (handoff, then read-back)
bracket the `pending` window. The only other round-1 work is constraint 8's cleanup.

## The two slices to create

Create them as **bare folders** — never pre-fill their `plan.md`. Each slice's plan is written by the
orchestrator at that slice's own turn.

### `P8.S1` — Retire the `web/design/canvas/` mirror · `implementation` / `low` / order 1

Constraint 8. The 13-file mirror (`tokens.css`, `_ds_manifest.json`, 9 component/foundation/section
cards, `README.md`) has no job under v13 and can only drift. Verified inert: nothing in `web/src/`,
`next.config.*`, `tsconfig.json`, or `postcss.config.*` imports or globs it; git history keeps it.

**It must land before P8.S2**, and that ordering is load-bearing: P8.S2 pushes the branch so Claude
Design can read current code. A stale placeholder-palette mirror sitting in the repo at push time is
exactly the drift hazard v13 names — it would read as authoritative to the session.

Rated `low` — a pure deletion plus one exactly-specified comment edit, genuine `slice-executor-low`
(sonnet) territory. Under flex mode `mid` and `high` are both opus@xhigh, so `low` is this phase's only
real cost lever.

Scope notes for when its plan is written (context, not a pre-filled plan): the one dangling code
reference is `web/src/app/page.tsx:11` — *"The `design/canvas/` mirror remains the design-gate
artifact."* The same comment block also says *"P6 replaces this with the public landing page"* (line 6),
now false: **P9** builds the landing. Doc references to the canvas (`frontend.md`, `decisions.md`) are
**not** that slice's job — they are pre-recorded in this phase's *Doc impact* list for `P8.REVIEW`
(constraint 10).

### `P8.S2` — Design gate round 1: brand, app UI & landing · `co-work` / `high` / order 2, depends on P8.S1

The gate itself. **Never dispatched** — a deliberate v13 exception to "every slice is delegated",
because executors have no `DesignSync` tool, so the read-back is orchestrator-inline. Never rated `low`.

Its shape, for the `phase.md` record (its own `plan.md` gets written at its turn, not now):

```
write docs/reference/design/rounds/01-brand-app-landing/handoff.md
  → commit "feat(design): P8.S2 handoff — ..."
  → operator pushes + runs Connect GitHub   [the agent cannot push: settings.json denies Bash(git push:*)]
  → set-slice-status P8.S2 pending → STOP; the operator designs in Claude Design
  → operator clears pending → read back [DesignSync, orchestrator-inline] → concreteness check
  → land the design AS-IS into output/ + the spec into phase.md → write SIGNOFF.md
  → commit "feat(design): P8.S2 read-back — ..."
```

It ends at the landed design + SIGNOFF. **It writes no implementation code** — that is P9.

## Commands

```bash
python3 scripts/workflow.py new-slice --phase P8 --slice P8.S1 \
  --name "Retire the web/design/canvas mirror" \
  --kind implementation --risk low --order 1

python3 scripts/workflow.py new-slice --phase P8 --slice P8.S2 \
  --name "Design gate round 1: brand, app UI & landing" \
  --kind co-work --risk high --order 2 --depends-on P8.S1
```

`--kind`/`--risk` are free-form strings in `scripts/workflow.py` (no `choices=`), so `co-work` and `high`
are accepted. `--depends-on` is `action="append"` — **one flag per dep**; a comma-separated string is
stored as a single literal dep and fails `validate` with `missing dependency`.

## Record in `phase.md`

Fill the **Decomposition** section with the breakdown and its rationale: the two slices, the
S1-before-S2 ordering argument, why v13's seven-to-two collapse is correct, and that this is round 1
only — with round 2 (and any design-fidelity fix) to be cut at fractional orders after the read-back.
Append any genuinely new findings to *Findings & Notes*; the harvested facts are already there.

## Verification

- `python3 scripts/workflow.py validate` — clean.
- `python3 scripts/workflow.py next` — reports `P8.S1` as the next slice.
- Both slice folders hold **only** `slice.json` (no pre-filled `plan.md`).
- `P8.S2`'s `slice.json` shows `kind: co-work`, `risk: high`, `depends_on: ["P8.S1"]`.

## Out of scope

No handoff, no code, no deletions, no doc versions, no `plan.md` for S1/S2. Decomposition creates bare
folders and records the breakdown, nothing more. Do not commit and do not transition slice/phase status —
the orchestrator does both.
