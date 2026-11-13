# Plan

- Work item: works/current/20260423_1814_mvp_phase_planning
- Created at: 20260423_1814
- Phase ID: P1
- Phase: Lock MVP scope and draft contracts
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

The backlog still contains a placeholder pre-MVP phase. The approved MVP direction is narrower: self-hosted, MCP-only ingestion, raw feedback storage, and a minimal review/query API with simple counts.

## Goal

Replace the placeholder backlog entry with a concrete four-phase MVP roadmap and decompose `P1` into explicit middle slices that can be implemented through tracked work items.

## Scope

- In scope:
  - Rewrite `works/backlog.md` to reflect phases `P1` through `P4`
  - Set `P1` to `in_progress` and mark `P1.DECOMP` as the active slice for this work item
  - Add the middle slices needed to complete `P1`
- Out of scope:
  - Updating reference docs outside backlog decomposition
  - Implementing later slices in `P1`, `P2`, `P3`, or `P4`

## Approach

Update the active backlog in place so it becomes the source of truth for the first MVP. Keep the slice set compact: one slice for product scope alignment, one for architecture and API contract drafting, and one phase review slice.

## Affected Files

- works/backlog.md

## Reference Docs To Review

- docs/product.md
- docs/architecture.md
- docs/api.md
- AGENTS.md

## Risks and Open Questions

- The wording needs to stay specific enough to guide implementation without overcommitting to details not yet designed.

## Verification Plan

- Review the rewritten backlog for status consistency, stable IDs, and required slice ordering.
- Confirm that `P1` through `P4` match the approved MVP scope.

## Planned Commits

- docs(workflow): define first MVP phases
