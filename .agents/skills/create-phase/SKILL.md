---
name: create-phase
description: Capture operator intent (refine → clarify → confirm), then create one or more phases (intent.md + DECOMP/REVIEW only) or route to defer-job. Stops before decomposition.
---

# create-phase

Turn an operator request for new work into one or more phases — or a deferred job — with the operator's intent captured first. Explicit invocation only. **This skill creates phases; it never decomposes or implements them** (see *Making a phase ≠ executing it* in the contract — `AGENTS.md`/`CLAUDE.md`).

## Procedure

1. **Refine.** Restate the operator's request in clear language. Read `docs/current/*.md` and `works/backlog.md` for context if useful. Preserve the operator's exact words — you will record them verbatim later.

2. **Clarify.** Ask the operator about anything ambiguous before acting: scope and boundaries, whether this is one phase or several, a sensible name and objective for each, and whether the work should start now (a phase) or be parked for later (a deferred job). Wait for answers. Do not run any `workflow.py` command yet.

   **If the work touches product visual design, one of those questions is the design split** — read the `design-cowork` skill and ask whether this is **one phase** (a design slice, then the build, decomposed in two passes) or **two** (a *design* phase, then an *apply* phase — the shape a big design wants). This is the only place that call can be made: the `DECOMP` slice's executor is forbidden from running `new-phase`, so a two-phase split decided later cannot be created from inside decomposition.

3. **Confirm.** Present your refined understanding back to the operator — for each phase, the proposed **name** and **objective**; for deferred work, the title, reason, and trigger. Get explicit confirmation. Per the contract, do **not** run `new-phase` until the operator confirms.

4. **Route on the operator's choice:**

   **Defer for later** → fold the confirmed intent into the arguments and run:
   ```
   python3 scripts/workflow.py defer-job --title "..." --reason "..." --trigger "..." [--source ...]
   ```
   This parks the job under `works/deferred/open/<DID>/` and never affects next-slice selection until promoted (the same command the `defer-job` skill wraps). Report and STOP.

   **Make a phase (or several)** → for each phase, in operator-confirmed order:
   1. Create it:
      ```
      python3 scripts/workflow.py new-phase --phase P<N> --name "..." --objective "..."
      ```
      `new-phase` creates only `P<N>.DECOMP` and `P<N>.REVIEW`, scaffolds `intent.md`, and links it near the top of `phase.md`.
   2. Fill `works/phases/active/P<N>/intent.md`:
      - leave **Origin** as `operator`;
      - paste the operator's request **word-for-word** under *Original Input (verbatim)* — do not fix grammar or wording;
      - write the confirmed, refined wording under *Confirmed Intent (refined + clarified)*;
      - record any clarifying Q/A under *Clarifications Resolved*.

      (`new-phase` already filled the phase id and captured-at timestamp.)
   3. Confirm `phase.md` links `intent.md` near the top (the engine added `_Intent: see [intent.md](intent.md)._`).
   4. **Relay the parallel hint if `new-phase` printed one.** When another phase is already
      `in_progress`, the engine prints a `hint:` line offering
      `python3 scripts/workflow.py parallel-start P<N>` — surface it to the operator as a
      **suggestion, never a default**: this phase can run on its own branch and worktree instead of
      queueing behind the current one. **Now is the only moment to opt in** — `parallel-start`
      requires the phase to still be `planned`, so it must run before any decomposition or execution.
      If the operator says yes, run it and report the branch and worktree it created; the phase is
      then driven from a session opened in that worktree. See the `parallel-phase` skill for the full
      lifecycle (work, branch review, PR, merge, deferred doc consolidation, teardown).

5. **STOP and report.** List the phases created — IDs, names, and `intent.md` paths — or the deferred job created. Do **not** decompose into middle slices, write any slice's `plan.md`, or implement code. Decomposition is the `DECOMP` slice's own job, later, when the operator executes the phase (`/do-next-slice`, `/do-whole-phase`) or explicitly tells you to.
