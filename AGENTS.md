# AGENTS.md

## Purpose

This repository defaults to agentic delivery. Use planning, tracked work items, and review gates for almost all coding work.
Backlog-scheduled work uses the full phase/slice workflow. Unrelated user requests may use the standalone path described below.

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
3. Standalone unrelated requests are not part of the active backlog queue and do not require a phase, slice, or work-item folder.
4. `works/deferred.md` is the deferred-jobs queue for work intentionally parked outside the active execution order.
5. Active work-item folders live under `works/current/`.
6. Completed work-item folders move to `works/archives/work_items/`.
7. Archived backlog snapshots move to `works/archives/backlogs/`.
8. Every backlog work item contains `plan.md` and `result.md`.
9. Long-lived reference docs live under `docs/` and transient execution notes live under `works/`.

## Python Development

- Use `uv` for Python development in this repository.
- Prefer `uv run` for Python commands such as tests, scripts, and CLIs.
- Prefer `uv add`, `uv remove`, `uv lock`, and `uv sync` for Python dependency management.
- Do not introduce `pip`, `venv`, or bare `python` workflows unless an existing repo constraint requires them.

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
2. Before selecting backlog work, check whether the documented backlog cycle is complete. If every documented phase has `Status: done` and every documented slice has `Status: done`, run `scripts/rotate_backlog.sh`.
3. If the user request qualifies as Standalone Work, follow that section and do not choose or create a backlog phase for the request.
4. Choose or create the active phase in `works/backlog.md`.
5. If `works/backlog.md` is still a placeholder or the requested work is to create a dedicated backlog from scratch, treat backlog creation as its own complete job:
   - Create only the phase entries and their mandatory `decompose phase` and `phase review` slices.
   - Add phase-level notes where useful to capture intent, constraints, assumptions, or handoff context.
   - Do not add phase-specific middle slices during backlog creation.
   - Do not start implementation, code edits, docs edits, tests, review, or the first `decompose phase` slice in the same job.
   - Stop after the backlog creation job is complete and report the new backlog.
6. Ensure every newly created phase initially contains only the two mandatory slices:
   - `decompose phase`
   - `phase review`
7. Run `scripts/start_work.sh <phase_id> <slice_id> <slug>` to create a timestamped work-item folder bound to the chosen phase and slice.
8. Fill `plan.md` before making code changes.
9. Implement the slice.
10. Fill `result.md` when implementation ends.
11. Run the `phase review` slice.
12. If review finds problems, create dedicated fix slices, implement them, and rerun `phase review`.
13. Mark the phase done only when review passes.
14. Run `scripts/archive_work.sh <work_dir_name>` after the work item is complete.
15. Run `scripts/rotate_backlog.sh` when the active backlog cycle is finished and a fresh backlog should start.

## Standalone Work

- Standalone Work applies when the user request is unrelated to active backlog execution and does not explicitly ask to create or update backlog scheduling.
- Standalone Work does not require a phase, slice, or `works/current/` work-item folder.
- Do not run `scripts/start_work.sh` for Standalone Work, and do not add backlog entries just to track it.
- If the current backlog is already complete, run `scripts/rotate_backlog.sh` first as housekeeping. Rotation archives `works/backlog.md` to `works/archives/backlogs/<timestamp>_backlog.md` and copies `works/templates/backlog.md` to `works/backlog.md`.
- If the next request is standalone, completed-backlog rotation remains housekeeping only; do not create a fresh phase or slice for that standalone request.
- Still inspect the relevant docs and code, make focused changes, run appropriate verification, and report the result.
- For standalone changes that trigger reference-doc updates, update the relevant `docs/` files and summarize the planned and completed doc changes in agent updates and the final report instead of `plan.md` and `result.md`.

## Deferred Work

- `works/deferred.md` is the explicit parking lot for later jobs that should not affect active backlog ordering yet.
- If the user asks to save tasks, follow-ups, later work, or ideas to `works/deferred.md`, add them to that file immediately.
- A direct user request to save items to `works/deferred.md` does not require creating a phase, slice, or work-item folder.
- During slice implementation, add a deferred job when a substantial or necessary later job is discovered and it is not appropriate to add it to the current backlog as a slice, fix slice, or new phase.
- Do not defer work that is required for the current slice or required for the current phase to pass review. Track that work in the active slice or add a review-driven fix slice instead.
- Use the next stable deferred ID by scanning existing `D*` entries, then record title, status, source, reason, and trigger for re-entry.
- Keep deferred entries concise and actionable. If the source is a user request, say so. If the source is implementation work, include the phase/slice or work item when available.
- Deferred jobs are not part of `do the next slice` or `do the whole phase` selection until they are promoted into `works/backlog.md`.

## Execution Commands

- Use `do the next slice` to continue the current phase one slice at a time.
- Use `do the whole phase` to finish the current phase end-to-end.
- Do not use `go`, `go next slice`, or `go next phase`.
- These commands are backlog-driven only. Standalone Work does not change how they resolve the current phase or slice.
- Resolve the current phase by scanning `works/backlog.md` from top to bottom and selecting the first phase whose status is not `done`.
- If the current phase is `blocked`, stop and surface the blocker instead of skipping ahead.
- `do the next slice` selects the first slice in the current phase whose status is not `done`.
- Do not skip fix slices or `phase review` slices when they are the next non-done work in the current phase.
- Deferred jobs in `works/deferred.md` are not part of current-phase selection until they are promoted back into `works/backlog.md`.
- `do the whole phase` is limited to the current phase only. It must not continue into later phases or finish the whole backlog.
- `do the whole phase` stays in the current phase and works through each remaining slice in order until that phase is `done`, `blocked`, or paused for user input.
- If `do the whole phase` reaches review and the review finds problems, add explicit fix slices, complete them, and rerun review until the phase passes.
- A `do the whole phase` command may create one work item per slice as needed. The initial `do the whole phase` coordination work item, if one exists, must remain open until all slice work items it initiated are complete, then record the phase-level result last.
- If a matching active work item already exists for the selected phase and slice, continue it.
- If no matching active work item exists and execution is allowed, create one with `scripts/start_work.sh <phase_id> <slice_id> <slug>` before editing.
- If the agent is in Plan mode, do not implement the selected slice. Inspect the selected slice for `do the next slice`, or the full current phase for `do the whole phase`, then prepare the job plan. If no work item exists yet, say that it should be created when execution begins.
- If the agent is not in Plan mode, start or continue the selected scope through the normal workflow. `do the whole phase` may require multiple sequential work items.

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
- Keep `works/backlog.md` limited to actively scheduled phases and slices.
- Do not add standalone unrelated requests to `works/backlog.md`.
- Move intentionally deferred or parked work into `works/deferred.md` instead of leaving it in the active backlog, following the Deferred Work rules.
- Promote deferred work back into `works/backlog.md` when it is ready to re-enter execution order.
- When every documented phase is `done` and every slice is `done`, rotate the completed backlog with `scripts/rotate_backlog.sh` before starting new backlog-scheduled work.
- Rotation moves the completed backlog to `works/archives/backlogs/<timestamp>_backlog.md` and copies `works/templates/backlog.md` to `works/backlog.md`.
- Fresh backlog contents come from `works/templates/backlog.md`.
- If the next user request is standalone, rotate the completed backlog as housekeeping but do not create a new phase or slice for that standalone request.
- Every phase must include an objective, status, review outcome, work items, and slices.
- When a phase is first created, its slice list must contain only `decompose phase` and `phase review`; no phase-specific middle slices may pre-exist.
- Phase-level notes are allowed and encouraged when creating a phase. They do not count as slices and may capture constraints, intended decomposition direction, known risks, or handoff context.
- `decompose phase` is the only slice allowed to create the phase-specific middle slices needed to finish the phase.
- `phase review` must exist from phase creation so the review gate is visible, but it stays after the slices created by `decompose phase`.
- `phase review` validates the phase and stays open until the bar is met.
- Re-review is mandatory after fixes.
- Prefix every slice entry with `[ ]` while it is not done and with `[x]` once it is done.
- The checkbox marker is a visual summary only. The explicit `Status` field remains the source of truth.

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
- For backlog work items, record planned reference-doc updates in `plan.md` and actual reference-doc updates in `result.md`.
- For Standalone Work, record planned and actual reference-doc updates in agent updates and the final report.

## Reference Files

- `docs/product.md`: problem, users, goals, and terminology
- `docs/architecture.md`: current repo shape and intended system design
- `docs/api.md`: current and planned public-facing contracts
- `works/deferred.md`: deferred jobs intentionally parked outside the active backlog
- `works/templates/backlog.md`: fresh backlog template
- `works/templates/plan.md`: work-item plan template
- `works/templates/result.md`: work-item result template

## Notes

- Keep product-facing messaging in `README.md`.
- Keep durable workflow rules in `AGENTS.md`.
- Keep stable technical truth in `docs/`.
- Keep execution artifacts in `works/`.
