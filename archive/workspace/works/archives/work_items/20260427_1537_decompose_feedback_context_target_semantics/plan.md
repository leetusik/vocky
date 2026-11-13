# Plan

- Work item: works/current/20260427_1537_decompose_feedback_context_target_semantics
- Created at: 20260427_1537
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Break P1 into concrete, ordered middle slices that clarify feedback context terminology, add explicit target capture semantics, expose target context in review flows, and update integration guidance with compatibility coverage.

## Scope

- Update `works/backlog.md` only for P1 scheduling metadata.
- Set P1 to `in_progress`.
- Mark `P1.DECOMP` complete and link this work item.
- Add concrete P1 middle slices before `P1.REVIEW`.
- Keep `P1.REVIEW` as the final P1 slice.
- Do not change runtime code, API behavior, schemas, migrations, tests, or durable reference docs in this decomposition slice.

## Context

- P1 currently contains only the required `decompose phase` and `phase review` slices.
- The phase objective is to clarify `conversation_id` and `session_id` semantics and make the exact reviewed message or product surface explicit.
- Exact target field names should be decided in a later implementation slice before code changes.
- Existing capture clients must remain compatible until a later slice intentionally changes or versions the public contract.

## Milestones

1. Confirm the active backlog state and current P1 slice order.
2. Add P1 middle slices with stable IDs, concise names, statuses, and notes.
3. Mark `P1.DECOMP` done and link this work item.
4. Validate the updated backlog shape and complete the work-item result.

## Validation

- Inspect `works/backlog.md` after editing.
- Confirm P1 is `in_progress`.
- Confirm `P1.DECOMP` is done and links this work item.
- Confirm `P1.S1` through `P1.S4` are todo and ordered before `P1.REVIEW`.
- Confirm `P1.REVIEW` remains todo and last.
- No test suite run is required because this slice changes workflow artifacts only.

## Risks / open questions

- Slice descriptions must avoid prematurely locking exact target field names before the terminology slice.
- Later slices may need to adjust ordering if target semantics require API documentation before implementation.

## Docs to update

- None for this slice. Durable product/API/architecture documentation updates are scheduled into the new P1 middle slices.
