# Plan

- Work item: works/current/20260423_2253_revise_workflow_commands_and_deferred_queue
- Created at: 20260423_2253
- Phase ID: P7
- Phase: Revise workflow commands and deferred queue
- Slice ID: P7.DECOMP
- Slice: decompose phase

## Context

The current workflow rules use `go`, `go next slice`, and `go next phase`, but the intended behavior is different: the next-slice trigger should be explicit, and the whole-phase trigger should finish the current phase rather than jumping to a later one. The repo also needs a dedicated deferred-jobs queue so the active backlog stays focused on currently scheduled work.

## Goal

Add a dedicated workflow phase that decomposes the command rename, deferred-queue setup, and active-backlog cleanup into concrete implementation and review slices.

## Scope

- In scope:
  - Add a new phase before `P2` for the workflow change
  - Mark `P7.DECOMP` complete against this work item
  - Add the implementation and review slices needed to finish the workflow update
- Out of scope:
  - Editing `AGENTS.md`, `docs/architecture.md`, or templates in this slice
  - Creating the deferred queue file in this slice
  - Resetting `P3` status in this slice

## Approach

Insert `P7` ahead of the implementation phases so the workflow change lands before `P2` starts. Keep the phase compact: one implementation slice for the durable rule and queue updates, followed by the mandatory review slice.

## Affected Files

- works/backlog.md
- works/current/20260423_2253_revise_workflow_commands_and_deferred_queue/plan.md
- works/current/20260423_2253_revise_workflow_commands_and_deferred_queue/result.md

## Reference Docs To Review

- AGENTS.md
- docs/product.md
- docs/architecture.md
- docs/api.md
- works/backlog.md

## Risks and Open Questions

- The new command wording needs to be unambiguous about current-phase versus later-phase behavior.
- The deferred queue needs a narrow enough role that it does not conflict with the active backlog.

## Verification Plan

- Confirm `P7` is inserted before `P2` in backlog order.
- Confirm the new phase has the correct stable IDs and required slice ordering.
- Confirm `P2`, `P3`, and `P4` remain intact during decomposition.

## Planned Commits

- docs(workflow): decompose command and deferred queue update
