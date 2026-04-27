# Plan

- Work item: works/current/20260427_1829_decompose_channel_categories_admin_adjustability
- Created at: 20260427_1829
- Phase ID: P3
- Phase: Channel categories and Admin adjustability
- Slice ID: P3.DECOMP
- Slice: decompose phase

## Goal

Decompose P3 into concrete, ordered middle slices so channel handling can move from free text to nullable category semantics with Admin adjustability.

## Scope

- Update `works/backlog.md` only for P3 scheduling metadata.
- Set P3 to `in_progress`.
- Mark `P3.DECOMP` complete and link this work item.
- Add concrete P3 middle slices before `P3.REVIEW`.
- Keep `P3.REVIEW` as the final P3 slice.
- Do not change runtime code, API behavior, schemas, migrations, tests, durable reference docs, README, or packaged Admin assets in this decomposition slice.

## Context

- P3 currently contains only the required `decompose phase` and `phase review` slices.
- The phase objective is to replace free-text-only `channel` handling with nullable default-none category behavior that operators can adjust in Admin.
- Current channel handling is free text across capture validation, read filters, Admin REST patching, persistence, and Admin UI filter/edit controls.
- Later slices should lock the category contract in durable docs before implementation, then apply validation/storage policy, update Admin workflows, and add example/test coverage.

## Milestones

1. Confirm the active backlog state and current P3 slice order.
2. Add P3 middle slices with stable IDs, concise names, statuses, and notes.
3. Mark `P3.DECOMP` done and link this work item.
4. Validate the updated backlog shape and complete the work-item result.

## Validation

- Inspect `works/backlog.md` after editing.
- Confirm P3 is `in_progress`.
- Confirm `P3.DECOMP` is done and links this work item.
- Confirm `P3.S1` through `P3.S4` are todo and ordered before `P3.REVIEW`.
- Confirm `P3.REVIEW` remains todo and last.
- No test suite run is required because this slice changes workflow artifacts only.

## Risks / open questions

- Later slices must choose the allowed category representation or management model before code changes.
- Existing records may contain arbitrary channel text; compatibility and migration behavior must be decided in `P3.S1`.
- Admin UI changes should preserve nullable "none" behavior and avoid making browser editing more powerful than the Admin REST contract.

## Docs to update

- None for this slice. Durable product, API, and architecture documentation updates are scheduled for `P3.S1`.
