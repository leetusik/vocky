# Plan

- Work item: works/current/20260423_2254_update_commands_and_deferred_queue
- Created at: 20260423_2254
- Phase ID: P7
- Phase: Revise workflow commands and deferred queue
- Slice ID: P7.S1
- Slice: update commands and deferred queue

## Context

The durable workflow rules still use `go`, even though the intended behavior is to either do the next slice in the current phase or finish the whole current phase. The active backlog also shows `P3` as `in_progress`, which makes the planning state misleading because `P2` is still the next implementation phase in backlog order.

## Goal

Replace the old `go` wording with explicit slice and whole-phase triggers, add a dedicated deferred-jobs queue file, and reset the active backlog so `P2` is clearly next.

## Scope

- In scope:
  - Update `AGENTS.md` to retire `go` and define `do the next slice` plus `do the whole phase`
  - Create `works/deferred.md` for intentionally postponed work
  - Update `works/backlog.md` and `works/templates/backlog.md` so the active backlog is limited to scheduled phases
  - Update `docs/architecture.md` for the new repo structure
  - Reset `P3` from `in_progress` to `planned`
- Out of scope:
  - Implementing `P2`
  - Changing product or API scope
  - Moving any concrete jobs into the deferred queue yet

## Approach

Make the command language explicit and current-phase oriented. Keep `works/backlog.md` as the active execution queue, add `works/deferred.md` for parked work, and normalize the backlog state so `P7` can review out cleanly and `P2` becomes the next non-done implementation phase afterward.

## Affected Files

- AGENTS.md
- docs/architecture.md
- works/backlog.md
- works/templates/backlog.md
- works/deferred.md
- works/current/20260423_2254_update_commands_and_deferred_queue/plan.md
- works/current/20260423_2254_update_commands_and_deferred_queue/result.md

## Reference Docs To Review

- docs/product.md
- docs/architecture.md
- docs/api.md
- AGENTS.md
- works/backlog.md

## Risks and Open Questions

- The whole-phase command needs to be explicit that it stays in the current phase instead of advancing to the next one.
- The deferred queue should not become a second active backlog with conflicting priority rules.

## Verification Plan

- Confirm `AGENTS.md` no longer defines `go`, `go next slice`, or `go next phase` as active triggers.
- Confirm `works/deferred.md` exists and documents how deferred jobs should be tracked.
- Confirm `P3` is back to `planned` and that `P2` remains the first non-done implementation phase after `P7` is done.
- Confirm the backlog template reflects the active-backlog versus deferred-queue split.

## Planned Commits

- docs(workflow): revise commands and add deferred queue
