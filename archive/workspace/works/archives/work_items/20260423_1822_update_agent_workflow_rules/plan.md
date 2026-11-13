# Plan

- Work item: works/current/20260423_1822_update_agent_workflow_rules
- Created at: 20260423_1822
- Phase ID: P5
- Phase: Update workflow rules for execution and slice tracking
- Slice ID: P5.S1
- Slice: update agent workflow rules

## Context

The repo needs durable rules for Python tooling, `go`-driven workflow advancement, and the visual interpretation of slice state so future agents can follow the backlog consistently.

## Goal

Update `AGENTS.md` so the repository itself defines how Python development should use `uv`, how bare `go` should resolve the next slice, and how slice checkboxes relate to backlog status.

## Scope

- In scope:
  - Add a Python tooling rule that standardizes on `uv`
  - Add a deterministic rule for handling user input of `go`
  - Add the durable rule for `[ ]` and `[x]` slice markers
  - Update `works/backlog.md` to point to the active `P5.S1` work item
- Out of scope:
  - Applying the checkbox format to the backlog file itself
  - Starting the next product implementation phase

## Approach

Keep the rules operational rather than aspirational so a future agent can execute them directly from `AGENTS.md` without guessing.

## Affected Files

- AGENTS.md
- works/backlog.md

## Reference Docs To Review

- AGENTS.md
- works/backlog.md
- works/templates/backlog.md

## Risks and Open Questions

- The `go` rule needs to be precise enough that the agent does not skip blocked work or jump ahead to a later phase.

## Verification Plan

- Review `AGENTS.md` for explicit, deterministic rules that cover all three requested changes.
- Confirm `works/backlog.md` records `P5.S1` as the active completed slice for this work item.

## Planned Commits

- docs(workflow): add go and uv rules
