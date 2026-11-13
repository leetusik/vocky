# Plan

- Work item: works/current/20260424_0846_lock_review_query_contract
- Created at: 20260424_0846
- Phase ID: P3
- Phase: Build MCP review/query tools
- Slice ID: P3.S1
- Slice: lock review query contract

## Context

- `P3` is the first non-`done` phase in `works/backlog.md`, and `P3.S1` is the first incomplete slice.
- `P2` implemented `capture_feedback`, PostgreSQL persistence, and the transport-neutral feedback service, but the read surface is still described as a generic draft API.
- The approved phase plan narrows `P3` to MCP read tools, not HTTP routes: `list_feedback` for newest-first record retrieval and `summarize_feedback` for UTC daily counts over an explicit ingest window.

## Goal

Lock the concrete `P3` read-tool contract in the durable docs and backlog so implementation can proceed against explicit MCP inputs, outputs, sorting, pagination, and error rules.

## Scope

- In scope:
  - Update `docs/api.md` to replace the draft review/query API wording with the concrete `list_feedback` and `summarize_feedback` MCP contracts.
  - Update `docs/architecture.md` so the runtime and data-flow notes describe MCP read tools, ingest-time filtering, cursor pagination, and UTC summary bucketing.
  - Mark `P3` and `P3.S1` active in `works/backlog.md` and record this work item.
  - Capture the slice result in this work item.
- Out of scope:
  - Implementing repository, service, MCP tool, smoke, or test code.
  - Adding Starlette JSON routes, schema migrations, new indexes, or auth behavior.
  - README updates for end-user usage examples.

## Approach

Translate the approved phase plan into durable contract language, including the exact supported filters, inclusive/exclusive UTC ingest window semantics, cursor rules, record ordering, tag behavior, and MCP tool execution error expectations.

## Affected Files

- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_0846_lock_review_query_contract/plan.md`
- `works/current/20260424_0846_lock_review_query_contract/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The contract needs to be concrete enough for implementation and tests without overstating `P3` as already shipped.
- Cursor wording needs to be stable and transport-neutral so the repository, service, and MCP tools can all share the same semantics later.
- The docs should make it clear that time filtering is based on `ingested_at`, not `event_at`.

## Verification Plan

- Re-read the updated `docs/api.md`, `docs/architecture.md`, and `works/backlog.md` entries for consistency with the approved `P3` plan.

## Planned Commits

- `feat(docs): lock MCP review query contract`
