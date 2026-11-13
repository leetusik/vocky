# Plan

- Work item: works/current/20260424_1726_audit_mcp_feedback_contracts
- Created at: 20260424_1726
- Phase ID: P1
- Phase: Review fast-built feedback MCP/Admin backlog
- Slice ID: P1.S2
- Slice: audit MCP feedback contracts

## Context

P1 reviews the feedback MCP/Admin work that was built quickly before this review phase. P1.S2 focuses on the MCP-facing contracts and checks implementation, tests, README, and durable API/architecture docs for consistency.

## Goal

Validate that `capture_feedback`, `list_feedback`, `summarize_feedback`, `list_liked_conversations`, shared query normalization, and service/repository behavior match the documented MCP contracts. Identify required corrections as explicit follow-up fix slices rather than making unrelated changes inside the audit.

## Scope

- In scope:
  - MCP tool handlers and shared normalization code under `src/vocky/tools/`.
  - Feedback service/repository methods used by MCP capture and query tools.
  - Tests covering MCP validation, integration, persistence/query behavior, and public MCP access.
  - MCP sections in `README.md`, `docs/api.md`, and relevant architecture notes.
  - Backlog/work-item updates for this audit slice.
- Out of scope:
  - Admin REST-specific routing and behavior, which is covered by P1.S3.
  - Broad product or architecture rewrites not required by a contract mismatch.
  - Implementing optional enhancements beyond required corrections.

## Approach

1. Inspect MCP tool implementations and shared query normalization.
2. Inspect feedback service/repository behavior for capture, listing, summary, and liked-conversation retrieval.
3. Compare observed behavior with `docs/api.md`, `docs/architecture.md`, README MCP text, and test expectations.
4. Run focused tests if the audit suggests risk; otherwise rely on the phase-level test run planned in P1.S4.
5. Record findings in `result.md`, update `works/backlog.md`, and add fix slices only for required corrections.

## Affected Files

- `src/vocky/tools/capture_feedback.py`
- `src/vocky/tools/list_feedback.py`
- `src/vocky/tools/summarize_feedback.py`
- `src/vocky/tools/list_liked_conversations.py`
- `src/vocky/tools/query_feedback_common.py`
- `src/vocky/feedback/service.py`
- `src/vocky/feedback/repository.py`
- `tests/`
- `README.md`
- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1726_audit_mcp_feedback_contracts/plan.md`
- `works/current/20260424_1726_audit_mcp_feedback_contracts/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`

## Risks and Open Questions

- The review may find a real contract mismatch that requires a dedicated fix slice before final review.
- Cursor, timestamp, and zero-filled summary semantics are easy to document incorrectly; compare code and tests directly.
- Capture is async, so accepted receipts must not imply immediate queryability.

## Verification Plan

- Inspect source and test coverage for all MCP tools.
- Run focused pytest modules if code/docs changes are required or if a behavior is unclear.
- Record whether P1.F2+ slices are needed.

## Planned Commits

- None planned for this audit slice unless the user later asks for a commit.
