# Plan

- Work item: works/current/20260427_1417_build_feedback_list_and_filters
- Created at: 20260427_1417
- Phase ID: P4
- Phase: Feedback review and management
- Slice ID: P4.S1
- Slice: build feedback list and filters

## Goal

Replace the Feedback placeholder with a token-aware feedback list backed by
`GET /admin/api/feedback`.

## Scope

- Add list/filter controls for supported Admin REST list parameters.
- Add limit selection, cursor-based next/previous paging, and refresh behavior.
- Render list records with clear value, source, tags, and ingest-time summaries.
- Handle loading, empty, error, and unauthorized states.
- Keep detail, editing, and delete workflows out of this slice.

## Context

- Admin Web UI assets live under `src/vocky/admin_assets/`.
- Existing `adminFetch` and token storage should remain the only protected-data path.
- The Admin REST list endpoint already supports the target filters and cursor model.

## Milestones

1. Add Feedback list markup and CSS.
2. Add list state, query construction, fetch, render, and pagination logic.
3. Update focused UI tests for static asset hooks and run validation.

## Validation

- `uv run pytest tests/test_admin_ui.py`

## Risks / open questions

- Timestamp inputs must send timezone-aware UTC-capable ISO strings to match Admin REST validation.
- Cursor paging only returns a next cursor; previous paging will be maintained client-side from visited cursors.

## Docs to update

- None planned for this slice.
