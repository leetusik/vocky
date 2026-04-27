# Plan

- Work item: works/current/20260427_2322_lock_rest_try_docs_behavior
- Created at: 20260427_2322
- Phase ID: P4
- Phase: Working REST capture Try docs
- Slice ID: P4.S1
- Slice: lock REST Try docs behavior

## Goal

Define the behavior and boundaries for the Admin Docs REST capture try-it flow before implementation.

## Scope

- Update durable docs and README only.
- Specify that the try flow is an operator Admin UI convenience for same-origin `POST /api/feedback`.
- Capture auth behavior, real queued-feedback side effects, and the fact that no public REST review/query endpoint is added.

## Context

- `/api/feedback` already exists as the capture-only REST endpoint.
- `/api/*` uses `VOCKY_API_AUTH_TOKEN`, which is separate from `VOCKY_ADMIN_AUTH_TOKEN`.
- The browser Admin UI can load without server-side auth, but protected data and capture endpoints enforce their own tokens when configured.

## Milestones

1. Update README operator guidance for the Docs Try flow.
2. Update product, architecture, and API reference docs with the operator-only behavior.
3. Mark the backlog slice complete and archive the work item.

## Validation

- `rg -n "Try|try-it|VOCKY_API_AUTH_TOKEN|/api/feedback" README.md docs/product.md docs/architecture.md docs/api.md`

## Risks / open questions

- Avoid implying browser-direct unauthenticated ingestion is a recommended product integration pattern.
- Avoid creating or documenting a new public review/query contract.

## Docs to update

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
