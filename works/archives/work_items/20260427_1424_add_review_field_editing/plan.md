# Plan

- Work item: works/current/20260427_1424_add_review_field_editing
- Created at: 20260427_1424
- Phase ID: P4
- Phase: Feedback review and management
- Slice ID: P4.S3
- Slice: add review-field editing

## Goal

Add edit, save, and cancel flows using
`PATCH /admin/api/feedback/{feedback_id}` for the browser-approved review
fields.

## Scope

- Add an edit form for `feedback_value`, `comment`, `channel`, and `tags`.
- Preserve captured evidence and JSON metadata as read-only UI content.
- Update selected detail and current list state after a successful save.
- Add saving, validation-error, unauthorized, missing, and storage-error states.
- Keep delete flow and docs polish out of this slice.

## Context

- Admin REST can patch more fields, but the browser workflow intentionally
  exposes only review fields in this slice.
- `P4.S2` detail rendering loads canonical records through Admin REST.

## Milestones

1. Add detail edit controls and CSS.
2. Add PATCH request helpers, payload normalization, save/cancel state handling,
   and list/detail refresh behavior.
3. Update static UI tests and run focused UI plus Admin REST tests.

## Validation

- `uv run pytest tests/test_admin_ui.py`
- `uv run pytest tests/test_admin_api.py`

## Risks / open questions

- Tags need predictable browser normalization while still relying on server
  validation for duplicates or blanks.

## Docs to update

- None planned for this slice.
