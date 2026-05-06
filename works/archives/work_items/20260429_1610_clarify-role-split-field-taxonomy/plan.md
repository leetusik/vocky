# Plan

- Work item: works/current/20260429_1610_clarify-role-split-field-taxonomy
- Created at: 20260429_1610
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.S1
- Slice: clarify role split and field taxonomy

## Goal

- Clarify the current MCP, public REST, and Admin REST responsibility split in durable docs.
- Define a compact taxonomy for existing feedback fields without introducing new fields or runtime behavior.

## Scope

- Update only `docs/product.md`, `docs/architecture.md`, `docs/api.md`, this work item, and `works/backlog.md`.
- Keep one canonical feedback store and shared capture field set across MCP and REST capture.
- Keep `P1.S2`/`P1.S3` identity and trigger fields out of this slice.
- Do not edit source code, migrations, README, Admin UI docs/assets, `docs/action-feedback-integration.md`, or `works/later_concerns.md`.

## Context

- `P1.DECOMP` decomposed the phase into documentation, contract-definition, implementation, integration-guidance, and review slices.
- Current implementation already exposes MCP capture/read tools, capture-only public REST, and Admin REST review/management over one PostgreSQL feedback store.
- This slice documents the current field responsibilities only; later slices define and implement identity/trigger expansion.

## Milestones

1. Mark `P1.S1` in progress in `works/backlog.md`.
2. Add product-level role split and current field taxonomy to `docs/product.md`.
3. Add architecture field responsibility mapping under API/runtime/data expectations in `docs/architecture.md`.
4. Clarify MCP capture, REST capture, and Admin REST integration intent in `docs/api.md`.
5. Validate wording and forbidden future-field leakage, then close and archive the work item.

## Validation

- Inspect edited docs for consistent role language:
  - MCP = agent/runtime capture and MCP reads.
  - REST = trusted server-to-server capture-only product/UI feedback.
  - Admin REST = human/operator review and management.
- Run `rg -n "user_id|trigger_type|trigger_message|trigger metadata" docs/product.md docs/architecture.md docs/api.md` and confirm no future identity/trigger contract leaked into this slice.
- No `uv run pytest` is planned because this is docs/backlog-only work.

## Risks / open questions

- Risk: Wording could imply new runtime fields or transport-specific payload split. Keep language anchored to current fields and shared capture schema.
- Risk: Docs could blur Admin REST with public REST. Keep Admin REST explicitly review/management-oriented and public REST capture-only.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
