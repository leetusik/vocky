# Plan

- Work item: works/current/20260424_1148_switch_capture_to_enqueue_first_behavior
- Created at: 20260424_1148
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S3
- Slice: switch capture to enqueue-first behavior

## Context

- `P1.S2` added the Redis queue module, the background worker, and the runtime configuration needed for async capture.
- `capture_feedback` still validates and persists synchronously, so the public tool contract and current tests do not match the new topology yet.
- The next slice needs to switch only the capture write path, while leaving the read tools focused on completed records in PostgreSQL.

## Goal

Move `capture_feedback` from direct persistence to queue acceptance, return the receipt-based response contract, and update the capture-focused tests to match the new behavior.

## Scope

- In scope:
  - Update `capture_feedback` to enqueue validated jobs and return `request_id`, `accepted_at`, and `status`.
  - Map queue failures to MCP tool execution errors.
  - Update capture validation or MCP integration tests for the new contract.
- Out of scope:
  - README or operator-doc changes for self-hosting.
  - Eventual-consistency smoke behavior or full end-to-end live verification; those belong to `P1.S4`.

## Approach

Keep the existing normalization path intact, replace the direct feedback-service call with the capture queue facade, return an acceptance receipt from the queue layer, and update capture-focused tests to use a fake Redis-backed queue or queue stubs where appropriate.

## Affected Files

- `src/vocky/tools/capture_feedback.py`
- `tests/test_mcp_integration.py`
- `works/backlog.md`
- `works/current/20260424_1148_switch_capture_to_enqueue_first_behavior/plan.md`
- `works/current/20260424_1148_switch_capture_to_enqueue_first_behavior/result.md`

## Reference Docs To Review

- `docs/api.md`
- `src/vocky/tools/capture_feedback.py`
- `tests/test_mcp_integration.py`

## Risks and Open Questions

- Keep the validation behavior unchanged so the only public behavioral change is acceptance semantics and the new success payload.
- Ensure capture tests do not accidentally depend on a live Redis service when a fake queue or fake Redis instance will do.

## Verification Plan

- Run focused MCP integration tests for successful acceptance, validation errors, missing required fields, and queue failure handling.

## Planned Commits

- `feat(capture): enqueue accepted feedback`
