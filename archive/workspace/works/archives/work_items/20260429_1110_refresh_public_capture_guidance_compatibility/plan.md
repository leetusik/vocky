# Plan

- Work item: works/current/20260429_1110_refresh_public_capture_guidance_compatibility
- Created at: 20260429_1110
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S4
- Slice: refresh public capture guidance and compatibility coverage

## Goal

Refresh public guidance so MCP is framed as agent-decided VoC capture, REST as explicit product/UI-triggered capture, and `target_type` as the review discriminator for message, conversation, and surface feedback without changing capture endpoints or tools.

## Scope

- Update `README.md` and `docs/action-feedback-integration.md` with MCP-versus-REST capture intent and `target_type` review guidance.
- Add or adjust message and surface feedback examples using existing tool and endpoint names.
- Add compatibility coverage showing older records or captures with `target_type = null` remain readable and unfiltered unless a type filter is provided.
- Avoid capture contract changes, renamed tools, new endpoints, split storage, or backfills.

## Context

- `P1.S2` implemented `target_type` read filters and index.
- `P1.S3` exposed the filter in Admin UI and packaged docs.
- Existing capture paths already accept optional `target_type`; public wording needs to make the intended integration split clear.

## Milestones

1. Inspect README, action integration guide, and existing capture/query compatibility tests.
2. Patch public docs and examples for agent-decided MCP capture and explicit REST product/UI capture.
3. Add focused compatibility tests for omitted/null `target_type` behavior.
4. Run targeted docs-adjacent and capture/query validation.

## Validation

- `uv run pytest tests/test_capture_validation.py tests/test_capture_api.py tests/test_mcp_integration.py tests/test_persistence.py`
- `git diff --check`

## Risks / open questions

- Public docs should not imply browser-direct unauthenticated REST capture or a new review API.
- Compatibility tests should verify behavior without introducing a dedicated null-target filter.

## Docs to update

- `README.md`
- `docs/action-feedback-integration.md`
