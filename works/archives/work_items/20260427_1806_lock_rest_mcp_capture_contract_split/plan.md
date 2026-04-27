# Plan

- Work item: works/current/20260427_1806_lock_rest_mcp_capture_contract_split
- Created at: 20260427_1806
- Phase ID: P2
- Phase: Separate REST and MCP capture intent
- Slice ID: P2.S1
- Slice: lock REST and MCP capture contract split

## Goal

Lock the durable product, architecture, and API direction for P2 before code changes: REST capture should support general server-to-server website/product feedback through the existing `POST /api/feedback` field set, while MCP capture remains optimized for agent/message workflows.

## Scope

- Update `docs/product.md`, `docs/architecture.md`, and `docs/api.md`.
- Update `works/backlog.md` to mark `P2.S1` in progress, then done after validation.
- Do not change application code, tests, README examples, or packaged Admin UI docs in this slice.
- Do not add REST-only aliases, new public fields, new endpoints, migrations, or browser-direct ingestion.

## Context

- P2 was decomposed after P1 completed target semantics.
- The chosen REST broadening strategy is existing fields only.
- REST remains server-to-server and capture-only.
- MCP and REST should keep sharing the async receipt shape, queue, worker, service, and PostgreSQL storage model.
- Existing accepted REST message/action payloads must remain valid.

## Milestones

1. Mark `P2.S1` in progress and link this work item from `works/backlog.md`.
2. Update product docs to distinguish MCP agent/message capture from broader REST product/surface capture.
3. Update architecture docs to define transport-specific adapter intent over shared storage and queueing.
4. Update API docs to describe REST general-feedback semantics without changing the endpoint or field set.
5. Validate the changed docs and close the slice.

## Validation

- Inspect the edited docs for consistent REST/MCP wording.
- Inspect `works/backlog.md` after updates.
- No code tests are required for this docs-only slice.

## Risks / open questions

- Risk: Wording could imply a new REST API shape. Avoid that by explicitly saying existing fields only.
- Risk: REST could be described as browser-direct. Keep it server-to-server only.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
