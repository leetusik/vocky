# Plan

- Work item: works/current/20260424_1142_async_capture_pipeline_and_self_hosted_operator_runbook
- Created at: 20260424_1142
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

- The active backlog had been rotated back to the template and needs a real execution phase before implementation can proceed.
- The approved phase plan calls for Redis-backed async capture, a dedicated worker runtime, a receipt-based `capture_feedback` response, and updated self-hosted operator docs.
- `AGENTS.md` requires a tracked work item for each slice and requires decomposition to finish before implementation slices begin.

## Goal

Replace the placeholder phase with the concrete implementation slices needed to ship async capture and its operator workflow, and move `P1` into active execution.

## Scope

- In scope:
  - Update `works/backlog.md` with the approved `P1` slice sequence and execution metadata.
  - Record the decomposition work in this work item's `plan.md` and `result.md`.
- Out of scope:
  - Application runtime changes, tests, or docs outside the backlog and work-item artifacts.
  - Any follow-on fix slices that may be discovered during later review.

## Approach

Use the approved phase plan as the source of truth, define the `P1.S1` through `P1.S4` implementation slices plus the mandatory review slice, and mark `P1` as `in_progress` with this work item attached to `P1.DECOMP`.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1142_async_capture_pipeline_and_self_hosted_operator_runbook/plan.md`
- `works/current/20260424_1142_async_capture_pipeline_and_self_hosted_operator_runbook/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- Keep the slices specific enough to drive implementation while staying within the agreed async-capture and self-hosting scope.

## Verification Plan

- Review the updated backlog entry for correct slice ordering, stable IDs, and the expected phase / slice status transitions.

## Planned Commits

- `feat(workflow): decompose async capture phase`
