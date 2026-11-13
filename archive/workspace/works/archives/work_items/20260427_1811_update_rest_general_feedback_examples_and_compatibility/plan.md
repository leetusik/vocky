# Plan

- Work item: works/current/20260427_1811_update_rest_general_feedback_examples_and_compatibility
- Created at: 20260427_1811
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.S3
- Slice: update REST general-feedback examples and compatibility coverage

## Goal

Update user-facing REST guidance to show general website/product surface feedback through the existing `POST /api/feedback` fields, and add compatibility coverage proving both legacy REST message/action payloads and broader REST surface payloads are accepted.

## Scope

- Update REST examples in `README.md`, `docs/action-feedback-integration.md`, and packaged Admin UI docs JSON.
- Add REST API test coverage for a broader surface/product payload that omits action and conversation-only fields.
- Preserve existing REST compatibility coverage for message/action feedback payloads.
- Do not change application behavior, storage, endpoint paths, auth, or read/review surfaces in this slice.

## Context

- `P2.S1` documented the REST/MCP intent split.
- `P2.S2` added explicit REST and MCP adapter input paths.
- REST broadening uses existing fields only, with `target_type="surface"` for known product surfaces and `source_metadata`/`attributes` for context.

## Milestones

1. Mark `P2.S3` in progress and link this work item from `works/backlog.md`.
2. Update README and action-feedback guidance with separate MCP and REST examples.
3. Update packaged Admin UI docs JSON with a REST surface-feedback example.
4. Add REST API compatibility coverage for current message/action payloads and broader surface payloads.
5. Run focused REST capture and Admin UI docs tests, then close the slice.

## Validation

- `uv run pytest tests/test_capture_api.py tests/test_admin_ui.py`
- `uv run pytest tests/test_capture_validation.py tests/test_capture_api.py tests/test_mcp_integration.py`

## Risks / open questions

- Risk: JSON escaping in `docs.json` can break packaged docs rendering. Run Admin UI tests.
- Risk: Examples could imply browser-direct ingestion. Keep wording server-side/server-to-server.

## Docs to update

- `README.md`
- `docs/action-feedback-integration.md`
- `src/vocky/admin_assets/docs.json`
