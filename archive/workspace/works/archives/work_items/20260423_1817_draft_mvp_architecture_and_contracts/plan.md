# Plan

- Work item: works/current/20260423_1817_draft_mvp_architecture_and_contracts
- Created at: 20260423_1817
- Phase ID: P1
- Phase: Lock MVP scope and draft contracts
- Slice ID: P1.S2
- Slice: draft MVP architecture and contracts

## Context

The product docs now describe a narrow first MVP, but the architecture and API references still describe the system at a much broader pre-MVP level and do not capture the agreed draft surfaces.

## Goal

Update the architecture and API docs so they define the MVP system shape and draft public surfaces needed by the next implementation phases.

## Scope

- In scope:
  - Update `docs/architecture.md` with the first-MVP component boundaries and constraints
  - Update `docs/api.md` with draft contracts for MCP capture and the review/query API
  - Update `works/backlog.md` to reflect the active `P1.S2` work item and slice status
- Out of scope:
  - Implementing any runtime or storage code
  - Declaring the draft contracts stable

## Approach

Document the MVP at the behavior level: what surfaces exist, what they are for, and the minimum data they need. Keep exact field names and runtime choices open where they have not been decided yet.

## Affected Files

- docs/architecture.md
- docs/api.md
- works/backlog.md

## Reference Docs To Review

- docs/product.md
- docs/architecture.md
- docs/api.md
- works/backlog.md

## Risks and Open Questions

- The draft contracts need to be concrete enough to guide `P2` and `P3` without freezing details that should be refined during implementation.

## Verification Plan

- Review the architecture and API docs for alignment with the MVP scope in `docs/product.md`.
- Confirm the backlog records `P1.S2` as the active or completed slice with the correct work item path.

## Planned Commits

- docs(api): draft first MVP contracts
