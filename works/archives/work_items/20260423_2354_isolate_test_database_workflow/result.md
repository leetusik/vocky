# Result

- Work item: works/current/20260423_2354_isolate_test_database_workflow
- Created at: 20260423_2354
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.F1
- Slice: isolate test database workflow
- Review status: passed
- Reviewer: Codex
- Next action: Rerun `P2.REVIEW` to confirm the phase can now close.

## Summary

Isolated the destructive pytest database setup onto a dedicated test database workflow, auto-created that database when possible, and updated the developer docs so the main application `DATABASE_URL` is no longer the reset target for the capture test suite.

## Changes Made

- Updated `tests/conftest.py` so persistence and MCP integration tests use `TEST_DATABASE_URL` or a derived `*_test` database instead of the main application database.
- Added safety checks that reject using the same database for `DATABASE_URL` and `TEST_DATABASE_URL`.
- Added automatic test-database creation when the configured role can create databases through the application connection.
- Updated `.env.example` and `README.md` to document the dedicated test-database workflow.
- Marked `P2.F1` active in the backlog.

## Files Changed

- `.env.example`
- `README.md`
- `tests/conftest.py`
- `works/backlog.md`
- `works/current/20260423_2354_isolate_test_database_workflow/plan.md`
- `works/current/20260423_2354_isolate_test_database_workflow/result.md`

## Verification Performed

- `POSTGRES_PORT=55432 VOCKY_PORT=8011 make compose-up`
- `DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky make migrate`
- `DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky TEST_DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky_test uv run pytest`
- `APP_BASE_URL=http://127.0.0.1:8011 make smoke`
- `POSTGRES_PORT=55432 VOCKY_PORT=8011 make compose-down`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`

## Follow-Ups

- Rerun the phase review slice and close `P2` if no additional issues remain.

## Commit References

- None.
