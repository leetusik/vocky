# Result

- Work item: works/current/20260425_0050_web_capture_rest_api_auth
- Created at: 20260425_0050
- Phase ID: P1
- Phase: Public Web Capture REST API
- Slice ID: P1.S2
- Slice: add web capture REST route and API auth
- Review status: self-checked
- Reviewer: Codex
- Next action: Start `P1.S3` for docs and operator config examples.

## Outcome

- Added `POST /api/feedback` with shared capture validation, queue-backed `202 Accepted` responses, `400` validation/body-shape errors, and `503` queue failure mapping.
- Added `VOCKY_API_AUTH_TOKEN` runtime settings and optional bearer-token middleware scoped to `/api/*`.
- Mounted `/api/feedback` before the MCP catch-all and added REST capture plus `/api/*` auth tests.

## Deviations from plan

- Operator config example files remain scheduled for `P1.S3`; this slice added the runtime setting and behavior.

## Validation run

- `uv run pytest tests/test_capture_api.py tests/test_public_access.py tests/test_mcp_integration.py -q` - 29 passed

## Files changed

- `src/vocky/api.py`
- `src/vocky/app.py`
- `src/vocky/auth.py`
- `src/vocky/config.py`
- `tests/test_capture_api.py`
- `tests/test_public_access.py`
- `works/backlog.md`
- `works/current/20260425_0050_web_capture_rest_api_auth/plan.md`
- `works/current/20260425_0050_web_capture_rest_api_auth/result.md`

## Docs updated

- None. Durable docs and operator config examples are scheduled for `P1.S3`.

## Roadmap updates

- Mark `P1.S2` done and proceed to `P1.S3`.

## Retrospective

- Keeping REST ingestion as a separate route module preserved the existing MCP and Admin REST surfaces while sharing the same capture normalization and queue path.
