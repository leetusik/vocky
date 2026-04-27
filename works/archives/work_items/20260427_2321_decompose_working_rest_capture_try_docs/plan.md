# Plan

- Work item: works/current/20260427_2321_decompose_working_rest_capture_try_docs
- Created at: 20260427_2321
- Phase ID: P4
- Phase: Working REST capture Try docs
- Slice ID: P4.DECOMP
- Slice: decompose phase

## Goal

Break P4 into concrete implementation slices for a working in-app REST capture try-it flow while keeping `P4.REVIEW` as the final gate.

## Scope

- Update `works/backlog.md` only.
- Add middle slices for contract/docs, Admin UI implementation, packaged docs/test coverage, and review sequencing.
- Mark `P4.DECOMP` complete when the backlog reflects the executable slice plan.

## Context

- The phase already exists with only the required `decompose phase` and `phase review` slices.
- The handoff plan defines the intended middle slices and the public-interface boundaries.
- The try flow must call the existing capture-only `POST /api/feedback` endpoint and must not introduce new backend contracts.

## Milestones

1. Update P4 metadata to show decomposition in progress.
2. Add `P4.S1`, `P4.S2`, and `P4.S3` before `P4.REVIEW`.
3. Mark `P4.DECOMP` done and record the work item.

## Validation

- Re-read the P4 backlog section after editing to verify slice order and statuses.

## Risks / open questions

- None for decomposition; implementation risks are assigned to the new middle slices.

## Docs to update

- No durable reference docs in this slice.
