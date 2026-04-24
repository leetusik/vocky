# Plan

- Work item: works/current/20260424_0856_implement_summary_counts_and_trends
- Created at: 20260424_0856
- Phase ID: P3
- Phase: Build MCP review/query tools
- Slice ID: P3.S3
- Slice: implement summary counts and trends

## Context

- `P3.S2` completed the shared query normalization helpers plus the listing read path through the repository, service, and MCP layers.
- `P3.S3` adds the second locked read contract, `summarize_feedback`, using the same core filters but a required ingest-time window and UTC daily-count aggregation.
- The architecture and API docs already constrain the summary output to `total_count` plus zero-filled UTC `daily_counts`, with no extra breakdown dimensions in this phase.

## Goal

Implement `summarize_feedback` end to end so callers can retrieve total matching feedback volume and UTC day counts for an explicit ingest-time window.

## Scope

- In scope:
  - Extend feedback query/result types with summary aggregate outputs.
  - Add repository and service read methods for filtered total-count and per-day aggregation.
  - Implement the `summarize_feedback` MCP tool on top of the shared query normalization helpers.
  - Add focused tests for required timestamps, invalid time windows, zero-filled day series, and MCP integration behavior.
  - Mark `P3.S3` active in `works/backlog.md` and capture the result here.
- Out of scope:
  - README and smoke updates reserved for `P3.S4`.
  - New aggregate dimensions such as by-product or by-tag breakdowns.
  - New storage indexes, schema changes, or non-MCP transports.

## Approach

Reuse the shared filter normalization helpers from `P3.S2`, add transport-neutral summary result types, aggregate matching rows by UTC day in the repository, zero-fill the requested day window in the service or repository result shaping, and expose the result through a dedicated `summarize_feedback` MCP tool with the same tool-execution error model as the other MCP tools.

## Affected Files

- `src/vocky/feedback/...`
- `src/vocky/mcp_server.py`
- `src/vocky/tools/...`
- `tests/...`
- `works/backlog.md`
- `works/current/20260424_0856_implement_summary_counts_and_trends/plan.md`
- `works/current/20260424_0856_implement_summary_counts_and_trends/result.md`

## Reference Docs To Review

- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- The UTC day bucketing logic needs to stay correct across arbitrary timezone offsets in the input window and in stored `ingested_at` values.
- The summary output must zero-fill the requested window without silently widening it past the requested exclusive end timestamp.
- The repository query should preserve the same supported filter set as `list_feedback` so the two read tools do not drift.

## Verification Plan

- Run focused pytest coverage for summary validation, persistence behavior, and MCP integration once the slice is implemented.

## Planned Commits

- `feat(mcp): implement feedback summary tool`
