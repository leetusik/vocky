# Plan

- Work item: works/current/20260423_1816_lock_mvp_product_scope
- Created at: 20260423_1816
- Phase ID: P1
- Phase: Lock MVP scope and draft contracts
- Slice ID: P1.S1
- Slice: lock MVP product scope

## Context

The backlog now defines the first MVP as self-hosted, MCP-only, and intentionally narrow. `docs/product.md` and `README.md` still describe a broader first release that includes classification, which no longer matches the approved plan.

## Goal

Update the product-facing documents so they describe the actual first-MVP scope and explicit deferrals.

## Scope

- In scope:
  - Update `docs/product.md` with the first-MVP definition, goals, and non-goals
  - Update `README.md` so the public project overview matches the narrowed MVP
  - Update `works/backlog.md` to reflect the active `P1.S1` work item and slice status
- Out of scope:
  - Architecture details or API contract drafting
  - Any implementation work beyond documentation and backlog status updates

## Approach

Add explicit MVP boundary language instead of leaving the scope implied. Keep the messaging honest about what Vocky will do first versus what remains post-MVP.

## Affected Files

- docs/product.md
- README.md
- works/backlog.md

## Reference Docs To Review

- docs/product.md
- README.md
- works/backlog.md
- docs/architecture.md
- docs/api.md

## Risks and Open Questions

- The docs need to stay aligned with the backlog without implying stability for contracts that are still drafts.

## Verification Plan

- Review the updated docs for consistent MVP terminology and deferrals.
- Confirm the backlog points to the active `P1.S1` work item and slice status.

## Planned Commits

- docs(product): lock first MVP scope
