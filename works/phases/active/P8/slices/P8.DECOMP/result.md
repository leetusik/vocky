# P8.DECOMP — result

Cut P8 into **round-1 slices only**: two bare middle slices, plus the breakdown recorded in `phase.md`.
No design decisions, no code, no deletions, no doc versions — per the plan's *Out of scope*.

## What was created

Both via the plan's verbatim `new-slice` commands, as **bare folders** (only `slice.json`; no `plan.md`
pre-filled — each slice's plan is the orchestrator's job at that slice's own turn):

| Slice | Name | Kind / Risk / Order | Depends on |
|---|---|---|---|
| `P8.S1` | Retire the `web/design/canvas` mirror | `implementation` / `low` / 1 | — |
| `P8.S2` | Design gate round 1: brand, app UI & landing | `co-work` / `high` / 2 | `P8.S1` |

`--depends-on P8.S1` was passed as a single flag (the flag is `action="append"`); `P8.S2`'s `slice.json`
stores `"depends_on": ["P8.S1"]` — a real one-element list, not a comma-joined literal, so the
`missing dependency` trap recorded in *Findings & Notes* did not recur.

Order headroom is intact for the expected re-shape: `DECOMP`@0 · `S1`@1 · `S2`@2 · `REVIEW`@9999, so
round 2 and any design-fidelity fix slice cut cleanly at a fractional order (2.5, …) after the gate.

## Validation

| Command | Outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **pass** — `Workflow validation passed.` (also clean at baseline, before any change) |
| `python3 scripts/workflow.py next` | **pass** — `next_slice=P8.S1`. (`current_slice=P8.DECOMP` because this slice is still `in_progress`; the orchestrator owns that transition.) |
| `ls -A .../P8.S1/` | **pass** — `slice.json` only |
| `ls -A .../P8.S2/` | **pass** — `slice.json` only |
| `cat .../P8.S2/slice.json` | **pass** — `kind: co-work`, `risk: high`, `depends_on: ["P8.S1"]` |

## Recorded in `phase.md`

Filled the **Decomposition** section (the placeholder line replaced; the v13 loop, the three binding
rules, and the design-record layout below it left untouched) with: the two-slice table, the
S1-before-S2 ordering argument, the seven-to-two rationale, and the round-1-only scope.

The three load-bearing arguments captured there, for later slices:

- **S1 before S2 is load-bearing, not cosmetic.** S2 pushes the branch for Connect GitHub. A stale
  placeholder-palette mirror present at push time is precisely the drift hazard v13 names — it would
  read to the design session as authoritative while contradicting the real `globals.css` tokens.
- **Seven → two is v13 doing the work, not scope-cutting.** The reverted v12 cut (`d20badf`) needed
  seed → brief → gate → synthesis with a three-way seed split. v13 retires the whole seeding arm
  (Claude Design reads the repo itself), so Claude Code's one output is `handoff.md`: the design arm is
  one slice, and constraint 8's cleanup is the only other round-1 work.
- **Round 1 only is deliberate.** *"You do not know what the operator will design"* — the read-back is
  expected to re-shape the phase; more slices now would be guessing at a design that does not exist.

**Nothing appended to *Findings & Notes*.** The harvested facts were already complete and machine-measured;
this slice produced no genuinely new finding, and padding the section would dilute it. (The order-headroom
fact is recorded in *Decomposition*, where it belongs.)

## Deviations from `plan.md`

None.

## Doc impact

None — decomposition changed no durable truth. The phase's two pre-recorded *Doc impact* entries
(the "P6" → P8/P9 gate renaming, and `frontend.md`'s canvas section, which `P8.S1`'s deletion
invalidates) already stand for `P8.REVIEW` to consolidate; nothing was added or altered.

## Constraint check

- **Zero brand decisions** (constraint 1) — no palette, no type direction, no landing copy; the phase's
  *Open Questions* were neither answered nor narrowed.
- **No code, no deletions** — `web/design/canvas/` is untouched; `P8.S1` deletes it at its own turn.
- **No commits, no status transitions** — `new-slice` ×2 was the only workflow command run.
- **No `plan.md` pre-filled** for `P8.S1` or `P8.S2`.
