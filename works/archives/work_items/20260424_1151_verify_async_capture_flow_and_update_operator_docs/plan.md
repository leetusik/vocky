# Plan

- Work item: works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs
- Created at: 20260424_1151
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S4
- Slice: verify async capture flow and update operator docs

## Context

- The runtime now includes Redis plus the worker and `capture_feedback` now returns a receipt instead of a persisted record ID.
- The current smoke script and README still assume immediate read-after-write persistence and do not document the worker process or Redis clearly.
- The phase still needs one verification slice that proves the eventual path works and updates the operator guidance to match the implemented topology.

## Goal

Update verification and operator docs so the repo demonstrates the async capture flow end to end and clearly explains how self-hosted users run and integrate the app today.

## Scope

- In scope:
  - Update smoke and test coverage for eventual worker persistence.
  - Update `README.md` and any affected durable docs so they describe the implemented async topology and usage flow.
  - Add a concrete MCP client example and a concrete reverse-proxy example for self-hosted operators.
- Out of scope:
  - New public APIs beyond the existing MCP tools.
  - Full auth, TLS, or deployment automation beyond documentation examples.

## Approach

Add an end-to-end async test that proves a capture receipt becomes queryable only after worker processing, change the smoke flow to poll for the persisted record, and refresh the README plus status-bearing docs to match the new Redis-plus-worker deployment and usage pattern.

## Affected Files

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `src/vocky/smoke.py`
- `tests/test_mcp_integration.py`
- `works/backlog.md`
- `works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs/plan.md`
- `works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs/result.md`

## Reference Docs To Review

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `src/vocky/smoke.py`

## Risks and Open Questions

- Keep the docs honest about the current MVP boundary: async capture is implemented, but there is still no UI or public job-status surface.
- Ensure the smoke flow tolerates worker latency without becoming flaky or unbounded.

## Verification Plan

- Run the async end-to-end pytest coverage that exercises capture acceptance, worker persistence, list visibility, and summary counts.
- Run the full test suite.
- Run the live smoke or verify workflow against the Compose stack if the environment permits.

## Planned Commits

- `docs(self-host): update async operator runbook`
