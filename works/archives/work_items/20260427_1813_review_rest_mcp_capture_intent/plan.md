# Plan

- Work item: works/current/20260427_1813_review_rest_mcp_capture_intent
- Created at: 20260427_1813
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.REVIEW
- Slice: phase review

## Goal

Review all P2 changes and close the phase only if REST capture now supports broader server-to-server website/product feedback while MCP capture remains agent/message-oriented, with compatibility preserved.

## Scope

- Review durable docs, user-facing examples, packaged Admin UI docs, adapter code, and REST/MCP tests touched by P2.
- Run broad validation for capture behavior and packaging where practical.
- If review finds a blocking issue, mark review `changes_requested`, add a fix slice, and do not close P2.
- If review passes, mark `P2.REVIEW` and P2 done.

## Context

- `P2.S1` locked REST/MCP intent in durable docs.
- `P2.S2` added explicit REST/MCP capture input models and normalizers.
- `P2.S3` updated examples and REST compatibility tests.
- No new REST endpoint, field alias, migration, auth path, or public review surface should exist in P2.

## Milestones

1. Mark P2 as in review and link this review work item.
2. Inspect P2 docs/code/tests for consistency and scope violations.
3. Run validation commands.
4. Record review outcome, add fix slices if needed, or close the phase if review passes.

## Validation

- `uv run pytest`
- `make package-check`
- `make verify` if the local Compose stack and environment are available.

## Risks / open questions

- Full `make verify` depends on a running local service stack and configured `.env`.
- The review should not rotate the backlog because later phases remain planned.

## Docs to update

- None expected unless review finds a mismatch.
