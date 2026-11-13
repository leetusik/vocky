# Plan

- Work item: works/current/20260424_0859_verify_query_api_behavior_and_docs
- Created at: 20260424_0859
- Phase ID: P3
- Phase: Build MCP review/query tools
- Slice ID: P3.S4
- Slice: verify query API behavior and docs

## Context

- `P3.S2` and `P3.S3` implemented the `list_feedback` and `summarize_feedback` MCP tools plus focused unit, persistence, and integration coverage.
- The durable docs still need to reflect the implemented read surface rather than the earlier contract-lock wording, and the README still says the review/query API is only planned.
- The local smoke path currently exercises only `capture_feedback`; `P3.S4` needs to extend it so the self-hosted verification story covers the full MCP read/write loop.

## Goal

Finish the query-tool phase by aligning the README and durable docs with the shipped MCP read surface, extending smoke coverage, and running the full query-focused verification set.

## Scope

- In scope:
  - Update `README.md`, `docs/api.md`, and `docs/architecture.md` so they describe the implemented MCP read tools and concrete list limit behavior.
  - Extend `src/vocky/smoke.py` to capture feedback and then verify both `list_feedback` and `summarize_feedback`.
  - Run the query-focused pytest suite and the smoke flow against the local app/Postgres stack.
  - Mark `P3.S4` active in `works/backlog.md` and capture the result here.
- Out of scope:
  - New product scope or architecture beyond the implemented `P3` surface.
  - Phase review or fix-slice handling, which belongs to `P3.REVIEW`.
  - `P4` hardening work.

## Approach

Update the consumer-facing docs to describe the actual `capture_feedback`, `list_feedback`, and `summarize_feedback` MCP surface, then extend the smoke script so it proves the write/read loop through the running app. After that, run the full query-related pytest set plus the smoke target against the compose stack.

## Affected Files

- `README.md`
- `docs/api.md`
- `docs/architecture.md`
- `src/vocky/smoke.py`
- `works/backlog.md`
- `works/current/20260424_0859_verify_query_api_behavior_and_docs/plan.md`
- `works/current/20260424_0859_verify_query_api_behavior_and_docs/result.md`

## Reference Docs To Review

- `README.md`
- `docs/api.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- The smoke flow needs stable assertions that tolerate server-generated timestamps while still proving the list and summary tools are wired correctly.
- The docs should distinguish contract-locked behavior from fully implemented behavior now that the read tools exist.
- The list limit bounds should be documented clearly enough that future consumers can page predictably.

## Verification Plan

- Run the full query unit, persistence, and MCP integration subset with explicit database env vars.
- Start the local compose app stack, migrate, and run the smoke script against it.

## Planned Commits

- `docs(readme): document MCP review query tools`
