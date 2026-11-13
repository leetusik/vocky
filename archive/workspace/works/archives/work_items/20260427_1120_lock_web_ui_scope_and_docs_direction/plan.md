# Plan

- Work item: works/current/20260427_1120_lock_web_ui_scope_and_docs_direction
- Created at: 20260427_1120
- Phase ID: P1
- Phase: Self-hosted Web UI foundation
- Slice ID: P1.S1
- Slice: lock Web UI scope and docs direction

## Goal

Align durable product and architecture docs with the new self-hosted Admin Web UI foundation so later route/UI slices have clear scope and boundaries.

## Scope

- Update `docs/product.md` to include the self-hosted operator Admin Web UI foundation in MVP scope and remove stale "no dashboard UI" positioning.
- Update `docs/architecture.md` to describe the same-origin packaged static browser UI under `/admin`, backed by Admin REST under `/admin/api/*`.
- Make minimal README wording updates only where it contradicts the new UI foundation.
- Leave `docs/api.md` unchanged because this slice does not introduce or change a public REST/MCP contract.

## Context

- Current MVP has MCP, public REST capture, Admin REST, persistence, queueing, and worker pieces.
- P1 is adding the first browser surface for self-hosted operators without adding SaaS tenant concepts, a frontend build chain, or new API contracts.
- Later P1 slices will implement route/static serving and the initial operator shell.

## Milestones

1. Inspect README for stale no-UI/dashboard claims.
2. Update product and architecture references to the Web UI foundation and deferred richer workflows.
3. Update backlog status for P1.S1 completion and archive the work item after validation.

## Validation

- `rg -n "dashboard UI|human-facing dashboard|browser UI|Admin Web UI|no dashboard" README.md docs/product.md docs/architecture.md docs/api.md`

## Risks / open questions

- Keep the docs honest that this is a foundation/shell, not full dashboard metrics, docs pages, or feedback management workflows.
- Avoid changing `docs/api.md` unless a consumer-facing contract changes.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `README.md` only if stale wording is present
