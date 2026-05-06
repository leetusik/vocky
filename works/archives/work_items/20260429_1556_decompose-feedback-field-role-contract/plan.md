# Plan

- Work item: works/current/20260429_1556_decompose-feedback-field-role-contract
- Created at: 20260429_1556
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Break `P1` into concrete middle slices that clarify the MCP, REST, and Admin REST role split and organize feedback capture field responsibilities while preserving one shared canonical schema and store.

## Scope

- Update `works/backlog.md` to move `P1` into progress, mark this decomposition slice complete, and add the implementation/documentation slices needed before phase review.
- Keep the decomposition focused on field and role clarity from `works/later_concerns.md` concern `C2`.
- Do not edit source code, migrations, reference docs, integration docs, or `works/later_concerns.md` in this slice.

## Context

- `P1` currently has only the mandatory `decompose phase` and `phase review` slices.
- The phase notes lock the shared-schema role split: MCP for agent/runtime capture and MCP reads, REST for trusted server-to-server capture-only product/UI feedback, and Admin REST for human/operator review and management.
- `works/later_concerns.md` has an existing user-owned modification and should not be touched by this slice.

## Milestones

1. Confirm the next slice is `P1.DECOMP` and no active work item exists.
2. Add middle slices `P1.S1` through `P1.S4` before `P1.REVIEW`.
3. Link this work item in the backlog and mark `P1.DECOMP` done.
4. Fill `result.md` and archive the work item.

## Validation

- Inspect `works/backlog.md` to confirm `P1.DECOMP` is done, `P1.S1` through `P1.S4` are present and todo, and `P1.REVIEW` remains todo after the new slices.
- No test run is required because this slice only decomposes backlog scheduling.

## Risks / open questions

- Keep later trajectory export, framework adapters, privacy/export controls, and richer Admin context UX out of this phase unless explicitly promoted later.

## Docs to update

- None in this decomposition slice.
