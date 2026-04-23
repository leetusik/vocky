# Plan

- Work item: works/current/20260423_2257_review_workflow_commands_and_deferred_queue
- Created at: 20260423_2257
- Phase ID: P7
- Phase: Revise workflow commands and deferred queue
- Slice ID: P7.REVIEW
- Slice: phase review

## Context

`P7.S1` updated the workflow rules, created `works/deferred.md`, changed the backlog/template usage rules, updated architecture docs, and reset `P3` to `planned`. This review needs to confirm the new command semantics are unambiguous and that the active backlog now points back to `P2` once `P7` closes.

## Goal

Review the workflow change for correctness, consistency, and closure readiness, then either close `P7` or identify explicit fix work if something is wrong.

## Scope

- In scope:
  - Review the `P7` command-rule, deferred-queue, and backlog-state changes
  - Update `works/backlog.md` with the final `P7` review status
  - Close `P7` if the review passes
- Out of scope:
  - Additional workflow redesign beyond the requested command rename and deferred-queue split
  - Starting `P2`

## Approach

Inspect the edited workflow docs and backlog state directly, confirm the new commands behave as intended on paper, and verify that `P2` is again the first non-done implementation phase after `P7` is marked done.

## Affected Files

- works/backlog.md
- works/current/20260423_2257_review_workflow_commands_and_deferred_queue/plan.md
- works/current/20260423_2257_review_workflow_commands_and_deferred_queue/result.md

## Reference Docs To Review

- AGENTS.md
- docs/architecture.md
- works/backlog.md
- works/templates/backlog.md
- works/deferred.md

## Risks and Open Questions

- The main risk is accidental ambiguity: the rules need to make it obvious that `do the whole phase` stays in the current phase and that deferred jobs are not part of automatic selection.

## Verification Plan

- Confirm `P7` can be marked `done` with no open findings.
- Confirm `P2` is the first non-done phase in `works/backlog.md` after `P7` closes.
- Confirm `works/current/` only contains the active review work item before archive.
- Confirm the final backlog paths point at archived work items for completed `P7` slices.

## Planned Commits

- docs(workflow): close command and deferred queue update
