# Plan

- Work item: works/current/20260424_1142_lock_async_capture_contract_and_operator_topology
- Created at: 20260424_1142
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S1
- Slice: lock async capture contract and operator topology

## Context

- `capture_feedback` currently writes directly to PostgreSQL and returns a final `feedback_id` / `ingested_at` response even though the next slices will move persistence to a background worker.
- The approved direction is Redis-backed queueing with a dedicated worker, a receipt-style capture response, and eventual consistency between capture acceptance and review queries.
- The self-hosted workflow and durable docs need to reflect the new topology before the runtime changes land.

## Goal

Update the durable product, architecture, and API docs so the async capture design, runtime topology, and operator-facing expectations are explicit before implementation begins.

## Scope

- In scope:
  - Update `docs/product.md`, `docs/architecture.md`, and `docs/api.md` for the async capture design.
  - Record the planned operator topology, config surface, and capture contract changes.
  - Track the slice in backlog and work-item artifacts.
- Out of scope:
  - Runtime code, dependency changes, or tests.
  - Full README or runbook edits for operator commands; those land in later slices after implementation stabilizes.

## Approach

Revise the reference docs from synchronous storage language to enqueue-first capture language, specify the Redis plus worker topology, document the receipt-based MCP contract, and describe the eventual consistency boundary for read tools.

## Affected Files

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`
- `works/current/20260424_1142_lock_async_capture_contract_and_operator_topology/plan.md`
- `works/current/20260424_1142_lock_async_capture_contract_and_operator_topology/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`

## Risks and Open Questions

- Keep the docs precise about the chosen v1 boundary: accepted capture receipts are public, queue or failure state is operational only, and read tools continue to surface completed records only.

## Verification Plan

- Review the docs together to confirm the runtime topology, config surface, and MCP contract all describe the same async behavior and operator expectations.

## Planned Commits

- `docs(async): lock capture contract and topology`
