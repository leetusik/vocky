# Plan

- Work item: works/current/20260429_1108_update_admin_type_filtering_operator_docs
- Created at: 20260429_1108
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S3
- Slice: update Admin type filtering and operator docs

## Goal

Expose the implemented `target_type` review filter in the Admin Web UI and update packaged operator documentation so operators can distinguish message, conversation, and surface feedback during review.

## Scope

- Add a feedback list filter select for `target_type` with `Any`, `message`, `conversation`, and `surface`.
- Include non-empty `target_type` values in Admin list query parameters.
- Keep unset/null `target_type` records visible under the default `Any` filter, without adding a dedicated unset filter.
- Update packaged Admin operator docs and tests to describe message/conversation/surface review filtering.
- Avoid Admin dashboard metrics changes and avoid new REST endpoints.

## Context

- `P1.S2` implemented server-side `target_type` filtering for `GET /admin/api/feedback`.
- The Admin UI already displays target type in list/detail views but does not yet let operators filter by it.
- Packaged docs live under `src/vocky/admin_assets/docs.json` and are verified by package/UI tests.

## Milestones

1. Locate Admin UI filter state, query construction, reset behavior, and tests.
2. Add the type filter control and request parameter wiring.
3. Refresh packaged operator docs and focused package/UI tests.
4. Run targeted Admin UI/package validation.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_admin_api.py`
- `make package-check`
- `git diff --check`

## Risks / open questions

- Admin assets are plain static files, so test coverage needs to confirm the packaged text and JS wiring directly.
- The UI must omit `target_type` from requests when `Any` is selected.

## Docs to update

- `src/vocky/admin_assets/docs.json`
