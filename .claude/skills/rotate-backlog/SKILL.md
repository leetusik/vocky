---
name: rotate-backlog
description: "One invocation pays the doc debt, then archives: check the debt first, create and run the docs phase that pays it, then archive every done phase. The word archive-only keeps the plain archive-and-report path; the word gate restores the approval loop."
argument-hint: "[archive-only] [gate]"
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit, Write, Glob, Grep, Bash, Agent
disable-model-invocation: true
---

# rotate-backlog

One invocation does the whole clean-up. It checks the doc debt **first** and archives nothing while any stands. When some phase owes consolidation it creates the docs phase that pays it (the invocation is the operator's yes), runs that phase end to end on the default stream, and only then archives every done phase, the docs phase included. When nothing owes, it archives the done phases right away. It is safe to re-run at any point of the chain: a stop (a `pending`, `blocked` or `needs_operator` slice, a failed review) ends the run, and the next `/rotate-backlog` resumes from the live docs phase.

The engine decides; this skill runs the chain. `python3 scripts/workflow.py rotate-backlog` prints one decision as its **first stdout line**, `rotate=<branch>`, and the branches below follow it. Archiving stays whole-phase only and never uses `--force`: to archive an unfinished phase, use `archive-phase <P> --force` by hand.

## Procedure

1. **`archive-only` in the invocation args:** run `python3 scripts/workflow.py rotate-backlog --archive-only`, relay its report, and **STOP**. That is the plain archive-and-report path: it creates, reorders and runs nothing, and it is not refused on a parallel stream.

2. **Otherwise run the engine** and read its **stdout before its exit code** (`refused` exits 1):

   ```sh
   python3 scripts/workflow.py rotate-backlog
   ```

   Branch on the first line as a prefix:

   - **`rotate=refused`** (`rotate=refused stream=<branch>`): this checkout is a parallel stream. Relay the line and the stderr message, tell the operator to run `/rotate-backlog` from the main checkout, and **STOP**. Nothing was written.

   - **`rotate=archive`**: nothing owes and no docs phase is live. Relay the sweep report verbatim (`rotated <n> done phase(s) to archived:` with its `- <P>: <path>` lines, or `no done phases to rotate…`, or `no active phases to rotate`), plus any `docs_phase_elsewhere=` line (a docs phase on another stream that is not resumed here). Commit the archive (`chore(works): archive <ids> with rotate-backlog`), or commit nothing when nothing was rotated. Report and **STOP**.

   - **`rotate=stop_midflight`**: the debt stands, but default-stream work is off a boundary. Relay the `midflight=<id>:<status>, …` list, the `stopped_before=` line and the closing line. Nothing was archived, created or reordered. **STOP**; a re-run after those slices are `todo`, `ready` or `done` (and no listed phase is `pending`, `blocked` or `in_review`) goes on.

   - **`rotate=create`**: a docs phase is owed and none is live.
     1. **Show the proposal** so the operator sees what is being created: `docs_phase_proposal=`, `phase=`, `name=`, `objective=`, and the `scope:` line's `python3 scripts/workflow.py docs-debt` in a few lines (the phases, the note count, the docs). Relay any `docs_phase_covered=` line.
     2. **Run the printed `create:` line exactly as printed.** Its `--order` is the queue jump ahead of planned work. The `/rotate-backlog` invocation is the operator's yes for the engine-drafted name, objective and scope: no pause, no narrowing, no editing. Read the new phase id `<P>` from the `phase=` line. Relay any parallel `hint:` the engine prints; never act on it.
     3. **Fill `works/phases/active/<P>/intent.md`** as the `create-phase` skill's *docs-phase route* says, which stays the source of truth: origin `operator`; under *Original Input (verbatim)*, the `/rotate-backlog` invocation; under *Confirmed Intent*, the engine-drafted name and objective and the `docs-debt` scope; and the cut the phase's `DECOMP` will make, written down and not made: one `--kind docs` slice per doc, `doc-new-version` then `rebuild-docs` per note, and the payment per covered phase as `docs-debt`'s `pay:` line says (`docs-consolidated <P>`, or `parallel-consolidated <P>`), with the acceptance gate `--waive`d at the `DECOMP` boundary.
     4. **Commit** (`chore(works): create <P> with rotate-backlog`), then continue as `resume`.

   - **`rotate=resume`** (`rotate=resume docs_phase=<P>`): a docs phase is live.
     1. If a `docs_phase_order=<P> <old> -> <new>` line was printed, the engine re-asserted the queue jump: `phase.json` and the regenerated `works/` files changed. Commit them (`chore(works): move <P> ahead with rotate-backlog`) before anything else. Relay any `docs_phase_covered=` and `docs_debt_waiting=` lines.
     2. **Run the docs phase `<P>` end to end per the `do-whole-phase` skill, in `auto`.** `python3 scripts/workflow.py next` now points at it (it sorts first by order). The `/rotate-backlog` invocation is the explicit `auto` that the contract's decomposition carve-out requires, so the docs phase's `DECOMP` plans inline; `gate` in the invocation args restores the approval loop instead. Its acceptance gate is normally `--waive`d at the `DECOMP` boundary. Every normal stop ends the run (`pending`, `needs_operator`, `blocked`, a failed or empty high return, a non-passing review): report where it stopped and that the next `/rotate-backlog` resumes from there.
     3. When the docs phase is `done`, run `python3 scripts/workflow.py rotate-backlog` **once more**. On `rotate=archive`, relay the sweep, commit it (`chore(works): archive <ids> with rotate-backlog`) and report. **On anything else, relay it and STOP**: one docs phase per invocation keeps the chain finite, and the next `/rotate-backlog` takes the next step.

## Rules

- The docs phase runs on the **default stream** only, like every docs phase: `doc-new-version` and the payment commands run nowhere else. Never ask for a worktree, and relay without acting on any parallel-run hint `new-phase` or `next` prints.
- Create the docs phase only through the printed `create:` line, as printed. Never narrow, edit or re-word it, and never run `--force`, `archive-phase` or `archive-all` on the operator's behalf.
- Every stop is reported with the exact engine line that caused it.
- `archive-only` never creates or runs anything.
