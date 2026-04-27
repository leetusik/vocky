# Result

- Work item: works/current/20260427_1808_separate_transport_capture_input_paths
- Created at: 20260427_1808
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.S2
- Slice: separate transport capture input paths
- Review status: completed
- Reviewer: Codex
- Next action: Start `P2.S3` to update REST examples and compatibility coverage.

## Outcome

Split capture adapter inputs into explicit MCP and REST models and normalizers while preserving the shared service payload, queue, persistence path, validation behavior, endpoint paths, and receipt shape.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_capture_validation.py tests/test_capture_api.py tests/test_mcp_integration.py` - passed, 29 tests.

## Files changed

- `src/vocky/capture.py`
- `src/vocky/api.py`
- `src/vocky/tools/capture_feedback.py`
- `tests/test_capture_validation.py`
- `works/backlog.md`
- `works/current/20260427_1808_separate_transport_capture_input_paths/plan.md`
- `works/current/20260427_1808_separate_transport_capture_input_paths/result.md`

## Docs updated

- None. Durable docs were updated in `P2.S1`.

## Roadmap updates

- Marked `P2.S2` complete in `works/backlog.md`.

## Retrospective

- Keeping one shared private normalization implementation made the transport split explicit without increasing behavior drift between REST and MCP.
