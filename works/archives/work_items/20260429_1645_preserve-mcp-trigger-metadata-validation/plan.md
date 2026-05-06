# Plan

- Work item: works/current/20260429_1645_preserve-mcp-trigger-metadata-validation
- Created at: 20260429_1645
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.F1
- Slice: preserve MCP trigger metadata validation

## Goal

Ensure MCP `capture_feedback` passes `trigger_metadata` through shared validation without falsey coercion, and cover invalid MCP trigger metadata.

## Scope

- Update only the MCP capture wrapper and targeted MCP integration tests.
- Do not change the public capture success response shape or REST behavior.

## Context

- P1.REVIEW found that `trigger_metadata or {}` could hide falsey non-object values before `normalize_json_object` validates them.
- REST and shared validation already handle invalid non-object trigger metadata.

## Milestones

1. Pass raw `trigger_metadata` through to `McpCaptureFeedbackInput`.
2. Add MCP integration coverage for invalid trigger metadata.
3. Run targeted MCP tests and diff check.

## Validation

- `uv run pytest tests/test_mcp_integration.py`
- `git diff --check`

## Risks / open questions

- The fix should not alter source metadata or attributes handling outside this trigger-specific path.

## Docs to update

- None.
