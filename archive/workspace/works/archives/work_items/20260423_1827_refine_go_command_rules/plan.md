# Plan

- Work item: works/current/20260423_1827_refine_go_command_rules
- Created at: 20260423_1827
- Phase ID: P6
- Phase: Refine go-command workflow navigation
- Slice ID: P6.S1
- Slice: refine go command rules

## Context

The current workflow only defines a generic `go` shortcut. It does not explicitly define `go next slice`, `go next phase`, or state that bare `go` should default to slice-level behavior.

## Goal

Update `AGENTS.md` so `go`, `go next slice`, and `go next phase` have explicit, deterministic meanings.

## Scope

- In scope:
  - Replace the generic `Go Shortcut` wording in `AGENTS.md` with explicit command variants
  - Define how `go next phase` selects the target phase and its default slice
  - Update `works/backlog.md` to record the active `P6.S1` work item
- Out of scope:
  - Changing backlog formatting rules
  - Starting `P2`

## Approach

Make the command rules operational: define the current phase, define how each command chooses its phase and slice, and keep Plan-mode behavior aligned with the existing workflow constraints.

## Affected Files

- AGENTS.md
- works/backlog.md

## Reference Docs To Review

- AGENTS.md
- works/backlog.md

## Risks and Open Questions

- `go next phase` must jump exactly one phase ahead from the current active phase, not skip multiple phases or fall back silently.

## Verification Plan

- Review `AGENTS.md` to confirm all three command forms are explicit and non-overlapping.
- Confirm `works/backlog.md` records this slice correctly.

## Planned Commits

- docs(workflow): refine go command semantics
