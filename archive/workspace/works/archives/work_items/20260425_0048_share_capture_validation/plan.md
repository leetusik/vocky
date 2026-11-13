# Plan

- Work item: works/current/20260425_0048_share_capture_validation
- Created at: 20260425_0048
- Phase ID: P1
- Phase: Public Web Capture REST API
- Slice ID: P1.S1
- Slice: share capture validation and receipt models

## Goal

Move capture payload validation, normalization, UTC timestamp serialization, and accepted receipt serialization out of the MCP tool adapter into a transport-neutral module that REST can reuse.

## Scope

- Add a shared capture module under `src/vocky/`.
- Keep MCP `capture_feedback` behavior and public response shape unchanged.
- Update capture validation tests to import the shared module.
- Do not add the REST route or API auth in this slice.

## Context

- The current MCP tool owns validation and response serialization directly in `src/vocky/tools/capture_feedback.py`.
- `P1.S2` needs the same JSON payload contract over REST without duplicating validation logic.
- Existing queue and worker behavior should not change.

## Milestones

1. Extract shared Pydantic input models, validation helpers, normalized payload dataclass, and accepted receipt model.
2. Refactor the MCP tool into a thin adapter that builds shared input, enqueues normalized payloads, and maps errors to MCP tool results.
3. Update targeted tests and run capture/MCP validation.

## Validation

- `uv run pytest tests/test_capture_validation.py tests/test_mcp_integration.py -q`

## Risks / open questions

- Pydantic validation errors for malformed MCP tool input should remain surfaced by the MCP SDK as they are today.
- The shared module should avoid importing MCP-specific types.

## Docs to update

- None in this slice; docs are scheduled for `P1.S3`.
