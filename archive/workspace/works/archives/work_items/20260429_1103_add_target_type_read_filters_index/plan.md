# Plan

- Work item: works/current/20260429_1103_add_target_type_read_filters_index
- Created at: 20260429_1103
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S2
- Slice: add target_type read filters and index

## Goal

Implement exact `target_type` read filtering for MCP and Admin feedback list paths, add the PostgreSQL index for the stored discriminator, and update reference docs so the accepted P1.S2 behavior is documented as implemented.

## Scope

- Add `target_type` to transport-neutral read filters and repository query predicates.
- Normalize and validate `target_type` query inputs for `list_feedback`, `summarize_feedback`, `list_liked_conversations`, and `GET /admin/api/feedback`.
- Add an Alembic migration and ORM index for `feedback_events.target_type`.
- Add focused query, persistence, MCP, and Admin REST coverage for valid, blank, invalid, filtered, and unfiltered behavior.
- Update stable docs that currently describe P1.S2 as future/accepted.

## Context

- Existing capture writes already validate and persist `target_type`.
- Existing response serializers already return `target_type`.
- This slice must not add split feedback tables, renamed tools, new feedback-kind fields, capture contract changes, or new REST review endpoints.
- Admin dashboard metrics remain time-window-only and should not gain a `target_type` filter.
- Existing rows with `target_type = null` remain readable when no type filter is supplied; there is no explicit null-type filter in this slice.

## Milestones

1. Add shared target-type filter normalization and wire it through MCP/Admin query inputs.
2. Apply repository/schema/index changes and persistence coverage.
3. Add MCP/Admin tests and update reference docs.
4. Run targeted validation for the changed slice.

## Validation

- `uv run pytest tests/test_query_validation.py tests/test_persistence.py tests/test_mcp_integration.py tests/test_admin_api.py`
- `git diff --check`

## Risks / open questions

- Alembic head changes must update tests that assert the current migration version and index list.
- The query helper should produce consistent error wording across MCP tool errors and Admin REST `400` responses.

## Docs to update

- `docs/api.md`
- `docs/architecture.md`
- `docs/product.md` if any implemented/future wording remains stale after the code change
