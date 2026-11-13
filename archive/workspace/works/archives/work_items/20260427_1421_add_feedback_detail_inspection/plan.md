# Plan

- Work item: works/current/20260427_1421_add_feedback_detail_inspection
- Created at: 20260427_1421
- Phase ID: P4
- Phase: Feedback review and management
- Slice ID: P4.S2
- Slice: add feedback detail inspection

## Goal

Add record selection and full read-only detail inspection backed by
`GET /admin/api/feedback/{feedback_id}`.

## Scope

- Add a detail panel to the Feedback view.
- Make list records selectable and load the selected record from Admin REST.
- Render full record fields, including source fields, timestamps, tags,
  messages, used context, `source_metadata`, and `attributes`.
- Add detail loading, empty, missing, unauthorized, and error states.
- Keep editing and delete flows out of this slice.

## Context

- `P4.S1` added the filterable list and cursor paging.
- Admin REST returns detail payloads as `{ "record": ... }`.
- Captured messages, used context, metadata, and attributes must be read-only in
  this browser workflow.

## Milestones

1. Add detail panel markup and responsive styling.
2. Add selected-record state, fetch, and read-only rendering.
3. Update static UI tests and run focused validation.

## Validation

- `uv run pytest tests/test_admin_ui.py`

## Risks / open questions

- List refreshes can remove the selected record; detail state should clear when
  the selection is no longer in the current page.

## Docs to update

- None planned for this slice.
