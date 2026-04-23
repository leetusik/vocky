# AGENTS.md

## Purpose

This repository defaults to agentic delivery. Use planning, tracked work items, and review gates for almost all coding work.

## Commit Convention

- Preferred format: `type(scope): summary`
- `scope` is optional.
- Use imperative summaries without a trailing period.
- Keep commits focused on one logical change when practical.

Supported types:

- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `ci`
- `build`
- `perf`
- `revert`

Examples:

- `feat(mcp): add feedback capture tool skeleton`
- `fix(storage): handle empty sentiment values`
- `docs(workflow): document review loop rules`

## Working Model

1. Almost all coding is done through a planning and implementation workflow, not direct edits.
2. `works/backlog.md` is the active queue of phases and slices.
3. Active work-item folders live under `works/current/`.
4. Completed work-item folders move to `works/archives/work_items/`.
5. Archived backlog snapshots move to `works/archives/backlogs/`.
6. Every work item contains `plan.md` and `result.md`.
7. Long-lived reference docs live under `docs/` and transient execution notes live under `works/`.

## Stable IDs

- Every phase must have a stable phase ID such as `P1`, `P2`, or `P3`.
- Every slice must have a stable slice ID tied to its phase.
- Use these slice ID patterns:
  - `P1.DECOMP` for the mandatory `decompose phase` slice
  - `P1.REVIEW` for the mandatory `phase review` slice
  - `P1.S1`, `P1.S2`, `P1.S3` for normal middle slices
  - `P1.F1`, `P1.F2` for review-driven fix slices
- Reference phases and slices by ID in backlog entries, work-item files, and agent updates.

## Required Flow

1. Read `docs/product.md`, `docs/architecture.md`, `docs/api.md`, and `works/backlog.md`.
2. Choose or create the active phase in `works/backlog.md`.
3. Ensure the phase starts with the two mandatory slices:
   - `decompose phase`
   - `phase review`
4. Run `scripts/start_work.sh <phase_id> <slice_id> <slug>` to create a timestamped work-item folder bound to the chosen phase and slice.
5. Fill `plan.md` before making code changes.
6. Implement the slice.
7. Fill `result.md` when implementation ends.
8. Run the `phase review` slice.
9. If review finds problems, create dedicated fix slices, implement them, and rerun `phase review`.
10. Mark the phase done only when review passes.
11. Run `scripts/archive_work.sh <work_dir_name>` after the work item is complete.
12. Run `scripts/rotate_backlog.sh` when the active backlog cycle is finished and a fresh backlog should start.

## Status Model

Phase statuses:

- `planned`
- `in_progress`
- `in_review`
- `blocked`
- `done`

Slice statuses:

- `todo`
- `in_progress`
- `in_review`
- `changes_requested`
- `done`

Rules:

- `phase review` cannot be marked `done` until the phase actually passes review.
- If review fails, keep the phase open, add explicit fix slices, complete them, and rerun review.
- Use `changes_requested` when review found issues that must be handled before closure.

## Backlog Rules

- Organize the backlog by phase, not as a flat task list.
- Every phase must include an objective, status, review outcome, work items, and slices.
- `decompose phase` creates the middle slices needed to finish the phase.
- `phase review` validates the phase and stays open until the bar is met.
- Re-review is mandatory after fixes.

## Fast-Path Exceptions

The full workflow is the default. A fast path is acceptable only for very small changes such as:

- typo-only edits
- one-line wording fixes
- metadata-only changes
- tiny documentation-only adjustments with no workflow impact

Do not use the fast path when a change affects:

- code behavior
- tests
- public or MCP-facing contracts
- architecture or repository workflow
- multiple files with nontrivial intent

If there is any doubt, use the full workflow.

## Reference Doc Update Triggers

- Update `docs/product.md` when goals, users, terminology, scope, or product direction changes.
- Update `docs/architecture.md` when component boundaries, data flow, storage shape, runtime choices, or repo structure changes.
- Update `docs/api.md` when a public-facing or MCP-facing contract is introduced, changed, stabilized, or deprecated.
- Record planned reference-doc updates in `plan.md` and actual reference-doc updates in `result.md`.

## Reference Files

- `docs/product.md`: problem, users, goals, and terminology
- `docs/architecture.md`: current repo shape and intended system design
- `docs/api.md`: current and planned public-facing contracts
- `works/templates/backlog.md`: fresh backlog template
- `works/templates/plan.md`: work-item plan template
- `works/templates/result.md`: work-item result template

## Notes

- Keep product-facing messaging in `README.md`.
- Keep durable workflow rules in `AGENTS.md`.
- Keep stable technical truth in `docs/`.
- Keep execution artifacts in `works/`.
