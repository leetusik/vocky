# Plan

- Work item: works/current/20260423_1821_workflow_rule_updates
- Created at: 20260423_1821
- Phase ID: P5
- Phase: Update workflow rules for execution and slice tracking
- Slice ID: P5.DECOMP
- Slice: decompose phase

## Context

The repository workflow needs three durable changes before implementation continues: Python development should use `uv`, bare `go` should resolve to the next actionable slice, and backlog slices should be visually explicit with checkbox markers.

## Goal

Decompose the workflow-update phase into the concrete rule and review slices needed to implement those changes cleanly.

## Scope

- In scope:
  - Update `works/backlog.md` to set `P5` as the active phase
  - Add the phase-specific middle slices for the workflow-rule updates
- Out of scope:
  - Implementing the rule changes themselves
  - Reviewing or closing the phase

## Approach

Keep the phase small: one slice for the AGENTS workflow rules, one slice for backlog presentation and template updates, and one review slice.

## Affected Files

- works/backlog.md

## Reference Docs To Review

- AGENTS.md
- works/backlog.md
- works/templates/backlog.md

## Risks and Open Questions

- The rule wording needs to be specific enough that future agents can follow it deterministically from the repo alone.

## Verification Plan

- Confirm `P5` is the active phase and includes the correct stable slice IDs and ordering.
- Confirm the middle slices map cleanly to the requested workflow changes.

## Planned Commits

- docs(workflow): decompose workflow rule update phase
