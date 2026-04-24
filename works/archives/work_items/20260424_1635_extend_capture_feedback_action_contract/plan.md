# Plan

- Work item: works/current/20260424_1635_extend_capture_feedback_action_contract
- Created at: 20260424_1635
- Phase ID: P1
- Phase: Explicit action feedback capture
- Slice ID: P1.S2
- Slice: extend capture_feedback action contract

## Context

P1.S1 added persisted fields for explicit user actions. The existing `capture_feedback` MCP tool still accepts only the original generic fields, and the Redis queue serializer still omits the new action/context fields.

## Goal

Extend the existing `capture_feedback` tool so clients can submit like/dislike action feedback, optional comments, channel, messages, and used context through the async capture path.

## Scope

- In scope: MCP input normalization, validation for `feedback_value`, optional comment/channel normalization, JSON array validation for `messages` and `used_context`, queue serialization/deserialization, and integration tests.
- Out of scope: Liked-only read tool, Admin REST routes, and docs.

## Approach

Preserve the existing tool name and all existing fields. Add optional fields with conservative validation: `feedback_value` must be `1` or `2` when provided; `comment` and `channel` trim blanks to null; `messages` and `used_context` must be arrays and are stored as supplied. Dislikes may omit comments.

## Affected Files

- `src/vocky/tools/capture_feedback.py`
- `src/vocky/capture_queue.py`
- `tests/test_capture_validation.py`
- `tests/test_capture_queue.py`
- `tests/test_mcp_integration.py`

## Reference Docs To Review

- `docs/api.md`

## Risks and Open Questions

- Keep backward compatibility for existing `capture_feedback` callers that send none of the action fields.
- Pydantic/FastMCP must expose the new fields without changing the existing nested `source` object.

## Verification Plan

- Run focused capture validation, queue, MCP integration, and persistence tests.

## Planned Commits

- Not committing unless requested.
