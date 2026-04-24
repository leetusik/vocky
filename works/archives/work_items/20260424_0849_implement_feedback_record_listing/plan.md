# Plan

- Work item: works/current/20260424_0849_implement_feedback_record_listing
- Created at: 20260424_0849
- Phase ID: P3
- Phase: Build MCP review/query tools
- Slice ID: P3.S2
- Slice: implement feedback record listing

## Context

- `P3.S1` locked the read contract as MCP tools, with `list_feedback` defined as the first implementation slice.
- The existing service already persists `FeedbackEventRecord` objects through a transport-neutral repository/service path that should be extended rather than bypassed.
- `P3.S2` needs cursor pagination, ingest-time filtering, newest-first ordering, and MCP tool execution errors aligned with the existing `capture_feedback` behavior.

## Goal

Implement `list_feedback` end to end through the repository, service, and MCP layers so stored feedback can be retrieved with the approved filters and cursor semantics.

## Scope

- In scope:
  - Extend feedback query types with list filters, cursor state, and list-page results.
  - Add repository and service read methods for newest-first filtered listing.
  - Implement the `list_feedback` MCP tool, including input normalization, cursor encode/decode, and error mapping.
  - Add focused tests for list input validation, cursor behavior, pagination, and MCP integration.
  - Mark `P3.S2` active in `works/backlog.md` and capture the result here.
- Out of scope:
  - The `summarize_feedback` aggregate read path from `P3.S3`.
  - README and smoke updates reserved for `P3.S4`.
  - New migrations, new indexes, or non-MCP transports.

## Approach

Add transport-neutral list query/result types, implement a repository query ordered by `(ingested_at desc, id desc)` with cursor filtering and one-row lookahead, expose it through `FeedbackService`, and register a new `list_feedback` MCP tool that normalizes inputs and converts opaque cursor strings into transport-neutral cursor objects.

## Affected Files

- `src/vocky/feedback/...`
- `src/vocky/mcp_server.py`
- `src/vocky/tools/...`
- `tests/...`
- `works/backlog.md`
- `works/current/20260424_0849_implement_feedback_record_listing/plan.md`
- `works/current/20260424_0849_implement_feedback_record_listing/result.md`

## Reference Docs To Review

- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- Cursor filtering must stay stable when multiple rows share the same `ingested_at`, so the `(ingested_at, id)` comparison logic needs to match the sort order exactly.
- The tool-layer cursor encoding should stay opaque and reject malformed payloads without leaking repository internals.
- Limit bounds are not yet spelled out in the docs, so the implementation needs explicit constants that can be documented in `P3.S4`.

## Verification Plan

- Run focused pytest coverage for list validation, persistence behavior, and MCP integration once the slice is implemented.

## Planned Commits

- `feat(mcp): implement feedback listing tool`
