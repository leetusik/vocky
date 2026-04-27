# Plan

- Work item: works/current/20260427_1427_add_delete_flow_and_docs_polish
- Created at: 20260427_1427
- Phase ID: P4
- Phase: Feedback review and management
- Slice ID: P4.S4
- Slice: add delete flow and docs polish

## Goal

Add a guarded browser delete flow backed by
`DELETE /admin/api/feedback/{feedback_id}` and update operator-facing docs for
the implemented review workflow.

## Scope

- Add guarded delete controls to the selected feedback detail.
- Refresh list/detail state after a successful delete.
- Handle deleting, unauthorized, missing, and storage-error states.
- Update README, durable docs, and in-app Docs wording for list/filter/detail,
  edit, and delete workflows.
- Do not add new Admin REST, MCP, database, or migration contracts.

## Context

- `P4.S1` through `P4.S3` added list/filter/detail/edit workflows.
- Admin REST delete already exists and returns `204 No Content` on success.
- Browser editing intentionally remains narrower than Admin REST.

## Milestones

1. Add guarded delete UI and state transitions.
2. Update docs and in-app docs payload.
3. Update tests and run focused UI/Admin REST validation.

## Validation

- `uv run pytest tests/test_admin_ui.py`
- `uv run pytest tests/test_admin_api.py`

## Risks / open questions

- Delete should avoid accidental activation and should clear stale selected
  state after success.

## Docs to update

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `src/vocky/admin_assets/docs.json`
