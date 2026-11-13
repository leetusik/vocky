# Plan

- Work item: works/current/20260423_2327_lock_capture_contract_and_storage_shape
- Created at: 20260423_2327
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.S1
- Slice: lock capture contract and storage shape

## Context

- `P2` is now decomposed and `P2.S1` is the first implementation slice.
- `docs/architecture.md` and `docs/api.md` still describe the MVP surfaces as draft and do not yet lock the runtime, schema, or error-model decisions this phase depends on.
- The handed-off phase plan specifies the concrete Python/ASGI/Postgres stack, `feedback_events` record shape, `capture_feedback` MCP contract, and validation rules to implement.

## Goal

Make the capture contract, storage shape, configuration surface, and phase notes explicit in the durable reference docs and backlog before runtime scaffolding begins.

## Scope

- In scope:
  - Update `docs/architecture.md` with the chosen runtime and persistence shape for `P2`.
  - Update `docs/api.md` with the concrete `capture_feedback` request, response, and error behavior.
  - Mark `P2.S1` active and record the work item in `works/backlog.md`.
  - Capture slice results in this work item.
- Out of scope:
  - Creating Python package files or runtime code.
  - Implementing migrations, repositories, MCP handlers, or tests.
  - README updates for local run instructions.

## Approach

Translate the approved `P2` plan into concrete architecture and API reference docs, including configuration keys, schema fields, UTC normalization rules, and tool execution error expectations for validation and storage failures.

## Affected Files

- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`
- `works/current/20260423_2327_lock_capture_contract_and_storage_shape/plan.md`
- `works/current/20260423_2327_lock_capture_contract_and_storage_shape/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The docs need to be concrete enough to guide implementation without pretending later `P3` query surfaces are already stable.
- The validation/error wording should align with MCP tool execution error guidance so later implementation can map failures cleanly.

## Verification Plan

- Re-read the updated architecture and API sections for contract completeness and consistency with the `P2` slice notes.

## Planned Commits

- `feat(docs): lock capture contract and storage shape`
