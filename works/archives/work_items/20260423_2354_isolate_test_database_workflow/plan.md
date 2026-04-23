# Plan

- Work item: works/current/20260423_2354_isolate_test_database_workflow
- Created at: 20260423_2354
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.F1
- Slice: isolate test database workflow

## Context

- `P2.REVIEW` found a blocking issue: the persistence and MCP integration tests currently reset the database pointed to by `DATABASE_URL`.
- The phase otherwise passes its functional checks, so this fix should stay focused on test isolation and the developer workflow around it.
- The compose-backed local Postgres workflow already provides the credentials needed to create and use a disposable test database.

## Goal

Move destructive test setup onto a dedicated test database path and document that workflow so `uv run pytest` no longer risks wiping the main application database.

## Scope

- In scope:
  - Update the pytest database fixtures to use a dedicated test database path.
  - Auto-create the test database when possible.
  - Update `.env.example` and README instructions for the test database variable.
  - Rerun the pytest and smoke verification flow.
- Out of scope:
  - New production features or wider refactors.

## Approach

Add a `TEST_DATABASE_URL` workflow, derive a safe default test database name from `DATABASE_URL` when needed, create that database from the application connection if it does not exist, and keep all schema resets confined to the test database.

## Affected Files

- `.env.example`
- `README.md`
- `tests/conftest.py`
- `works/backlog.md`
- `works/current/20260423_2354_isolate_test_database_workflow/plan.md`
- `works/current/20260423_2354_isolate_test_database_workflow/result.md`

## Reference Docs To Review

- `README.md`
- `works/backlog.md`

## Risks and Open Questions

- Database creation privileges may differ outside the compose stack, so the fixture should fail with a clear message if it cannot create the derived test database.

## Verification Plan

- Bring the compose stack back up.
- Run pytest with both `DATABASE_URL` and `TEST_DATABASE_URL`.
- Re-run the smoke target and shut the stack back down.

## Planned Commits

- `fix(test): isolate capture test database workflow`
