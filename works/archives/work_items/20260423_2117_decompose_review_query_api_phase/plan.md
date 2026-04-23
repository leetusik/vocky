# Plan

- Work item: works/current/20260423_2117_decompose_review_query_api_phase
- Created at: 20260423_2117
- Phase ID: P3
- Phase: Build review/query API
- Slice ID: P3.DECOMP
- Slice: decompose phase

## Context

`go next phase` from the current backlog order resolves from `P2` to `P3`. `P3` still contains only the placeholder decomposition and review slices, while the MVP docs already constrain this phase to a minimal review/query surface for stored feedback: filtered record retrieval plus simple counts or trends.

## Goal

Decompose `P3` into the concrete contract, implementation, verification, and review slices needed to build the review/query API without expanding scope beyond the current MVP docs.

## Scope

- In scope:
  - Create and fill this `P3.DECOMP` work item
  - Update `works/backlog.md` so `P3` becomes `in_progress`
  - Mark `P3.DECOMP` done against this work item
  - Replace the placeholder `P3` slice list with the concrete middle slices for contract lock, record listing, aggregate queries, and verification
- Out of scope:
  - Editing implementation code
  - Updating `docs/product.md`, `docs/architecture.md`, or `docs/api.md`
  - Changing `P2` or starting any `P3` implementation slice

## Approach

Keep `P3` narrowly aligned to the draft review/query surface already described in `docs/api.md`. Add only the slices needed to lock the contract, implement filtered record retrieval, implement simple counts or trends, verify behavior and docs, and then run the mandatory phase review.

## Affected Files

- works/backlog.md
- works/current/20260423_2117_decompose_review_query_api_phase/plan.md
- works/current/20260423_2117_decompose_review_query_api_phase/result.md

## Reference Docs To Review

- docs/product.md
- docs/architecture.md
- docs/api.md
- works/backlog.md

## Risks and Open Questions

- The slice notes must stay inside the current MVP scope and not imply dashboards, automated classification, non-MCP ingestion, or managed-cloud concerns.
- `P3.DECOMP` should not accidentally change `P2`; the request is to prepare the next phase, not reorder the backlog.

## Verification Plan

- Review `works/backlog.md` for stable IDs, required slice ordering, and status consistency within `P3`.
- Confirm the new slice notes map cleanly to the current MVP docs and keep the review/query scope narrow.
- Confirm the work-item metadata matches `P3` / `P3.DECOMP` exactly.

## Planned Commits

- docs(workflow): decompose review query api phase
