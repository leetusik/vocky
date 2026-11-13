# Result

- Work item: works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs
- Created at: 20260424_1151
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S4
- Slice: verify async capture flow and update operator docs
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.REVIEW` to review the completed async-capture phase and close it if no fix slices are needed.

## Summary

Updated the verification path and operator docs for the implemented async topology, and verified the full Compose-based self-hosted workflow plus the full pytest suite.

## Changes Made

- Added an end-to-end async MCP integration test that proves accepted captures are not queryable until the worker persists them.
- Updated `src/vocky/smoke.py` to treat `capture_feedback` as a receipt-based API and poll `list_feedback` until the worker-produced record appears.
- Refreshed `README.md`, `docs/product.md`, and `docs/architecture.md` so they describe the implemented Redis plus worker topology, the lack of UI, direct-run usage, and self-hosted integration examples.

## Files Changed

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `src/vocky/smoke.py`
- `tests/test_mcp_integration.py`
- `works/backlog.md`
- `works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs/plan.md`
- `works/current/20260424_1151_verify_async_capture_flow_and_update_operator_docs/result.md`

## Verification Performed

- Ran `uv run pytest tests/test_capture_queue.py tests/test_worker.py tests/test_capture_validation.py`.
- Ran `VOCKY_BASE_URL=http://127.0.0.1:8000 uv run vocky-smoke` against the Compose stack after bringing up `redis`, `postgres`, `app`, and `worker` and applying migrations.
- Ran `DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky TEST_DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky_test REDIS_URL=redis://127.0.0.1:56379/0 uv run pytest`.

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `docs/product.md`
- `docs/architecture.md`

## Follow-Ups

- Run the dedicated `P1.REVIEW` slice and close the phase if no further issues are found.

## Commit References

- None.
