# Plan

- Work item: works/current/20260423_1826_refine_go_navigation
- Created at: 20260423_1826
- Phase ID: P6
- Phase: Refine go-command workflow navigation
- Slice ID: P6.DECOMP
- Slice: decompose phase

## Context

The repo already defines a generic `go` shortcut, but it does not yet distinguish `go next slice` from `go next phase`, and bare `go` is not explicitly documented as defaulting to slice-level behavior.

## Goal

Decompose this workflow phase into the concrete slice needed to update the navigation rules and then review them.

## Scope

- In scope:
  - Update `works/backlog.md` to set `P6` as the active workflow phase
  - Add the phase-specific middle slice for the navigation-rule change
- Out of scope:
  - Editing `AGENTS.md` in this slice
  - Reviewing or closing the phase

## Approach

Keep the phase minimal: one implementation slice to revise the `go` semantics in `AGENTS.md`, then the mandatory review slice.

## Affected Files

- works/backlog.md

## Reference Docs To Review

- AGENTS.md
- works/backlog.md

## Risks and Open Questions

- The updated command rules need to stay deterministic when no work item exists yet and when the next phase is already in progress.

## Verification Plan

- Confirm `P6` is the next active phase ahead of `P2`.
- Confirm the phase includes the correct stable IDs and the expected single middle slice.

## Planned Commits

- docs(workflow): decompose go navigation refinement
