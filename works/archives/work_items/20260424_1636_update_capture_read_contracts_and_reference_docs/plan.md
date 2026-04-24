# Plan

- Work item: works/current/20260424_1636_update_capture_read_contracts_and_reference_docs
- Created at: 20260424_1636
- Phase ID: P1
- Phase: Explicit action feedback capture
- Slice ID: P1.S3
- Slice: update capture/read contracts and reference docs

## Context

P1.S1 and P1.S2 added action feedback storage and capture input support. The generic read tools and public reference docs still describe the pre-action-feedback shape.

## Goal

Expose the new action fields in read results and document the updated generic MCP contract without making tracked docs specific to Changple5.

## Scope

- In scope: `list_feedback`/`summarize_feedback` filters for feedback value and channel, list response fields, tests, README/reference doc updates.
- Out of scope: Liked-only MCP retrieval, Admin REST routes, and Changple-specific handoff docs.

## Approach

Add shared read validation for optional `feedback_value` and channel filters, serialize action/context fields in `list_feedback`, and update `docs/api.md`, `docs/architecture.md`, `docs/product.md`, and README language to describe explicit action feedback generally.

## Affected Files

- `src/vocky/tools/list_feedback.py`
- `src/vocky/tools/summarize_feedback.py`
- `src/vocky/tools/query_feedback_common.py`
- `tests/test_query_validation.py`
- `tests/test_mcp_integration.py`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Existing MCP read callers should continue to work when they omit the new filters.
- `list_feedback` output gains fields; clients should treat this MVP contract as early-stage.

## Verification Plan

- Run query validation and MCP integration tests.
- Run persistence tests to confirm the shared filter layer still works.

## Planned Commits

- Not committing unless requested.
