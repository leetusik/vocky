# Plan

- Work item: works/archives/work_items/20260429_1052_lock_capture_boundary_type_contract
- Created at: 20260429_1052
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S1
- Slice: lock capture boundary and type contract

## Goal

Lock the durable product, architecture, and API direction for capture-surface boundaries and `target_type` feedback separation before implementation begins.

## Scope

- Update `docs/product.md`, `docs/architecture.md`, and `docs/api.md`.
- Define MCP capture as agent-decided VoC capture for agent workflows.
- Define REST capture as the preferred server-to-server path for explicit product/UI-triggered feedback.
- Preserve the existing single `feedback_events` storage model, tool names, REST endpoint paths, and capture fields.
- Prepare `target_type` as the next exact-match read filter and indexed review dimension without implementing it in this slice.
- Leave README, packaged Admin docs, Admin UI, migrations, service code, and tests to later P1 slices.

## Context

- P1 was decomposed to clarify MCP versus REST capture intent and make message versus non-message feedback separately reviewable through `target_type`.
- Existing docs already describe `target_type` capture values, but some architecture/API text still says target fields are not filters or indexes in this phase.
- `P1.S2` is responsible for implementing `target_type` filtering and the PostgreSQL index after this contract slice is complete.

## Milestones

1. Link this work item from `works/backlog.md` and mark `P1.S1` in progress.
2. Update durable docs to distinguish MCP agent-decided capture from REST explicit product/UI capture.
3. Clarify `target_type` semantics for `message`, `conversation`, `surface`, and `null`.
4. Reframe stale "not filters" wording so the contract points to `P1.S2` for implementation.
5. Mark the slice done, record the result, and archive the work item.

## Validation

- Run `git diff --check`.
- Search durable docs for stale target-field filter/index wording.
- Inspect the edited docs for consistent capture-boundary and `target_type` contract language.

## Risks / open questions

- Avoid overpromising implemented behavior before `P1.S2`; docs should distinguish intended contract direction from current implementation where necessary.
- Do not introduce new storage-table, endpoint, tool-name, or capture-field commitments.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
