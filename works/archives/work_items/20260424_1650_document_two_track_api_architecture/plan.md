# Plan

- Work item: works/current/20260424_1650_document_two_track_api_architecture
- Created at: 20260424_1650
- Phase ID: P3
- Phase: Admin REST API for human review
- Slice ID: P3.S4
- Slice: document two-track API architecture

## Context

P3 added Admin REST routes, auth, query endpoints, and management endpoints. Public docs still need to describe the two-track split and Admin REST contract.

## Goal

Document the Admin REST API and the two-track MCP-for-AI / REST-for-humans architecture.

## Scope

- In scope: README, reference docs, and environment template updates.
- Out of scope: New endpoint behavior.

## Approach

Update `docs/architecture.md` with the two-track shape, `docs/api.md` with Admin REST contracts, README with operator-facing summary, and `.env.example` with `VOCKY_ADMIN_AUTH_TOKEN`.

## Affected Files

- `.env.example`
- `README.md`
- `docs/architecture.md`
- `docs/api.md`

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Admin REST docs should make clear this is for human/operator workflows and is separate from AI few-shot MCP retrieval.

## Verification Plan

- Run Admin API tests after doc/config updates.

## Planned Commits

- Not committing unless requested.
