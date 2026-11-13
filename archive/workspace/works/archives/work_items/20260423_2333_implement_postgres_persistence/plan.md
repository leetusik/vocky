# Plan

- Work item: works/current/20260423_2333_implement_postgres_persistence
- Created at: 20260423_2333
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.S3
- Slice: implement Postgres persistence

## Context

- `P2.S2` created the runnable app shell, project metadata, and container workflow.
- The architecture doc now fixes PostgreSQL, SQLAlchemy async sessions, and Alembic as the persistence approach.
- The next slice needs to add storage infrastructure that later MCP handlers can call through a transport-neutral service layer.

## Goal

Implement the PostgreSQL persistence core for feedback capture, including the initial schema, async session management, repository and service wiring, and migration tooling.

## Scope

- In scope:
  - Add SQLAlchemy metadata and the `feedback_events` ORM model.
  - Add async engine and sessionmaker wiring from `DATABASE_URL`.
  - Create the Alembic environment and initial migration for `feedback_events`.
  - Add repository and service code for creating feedback records.
  - Add baseline persistence-focused tests or smoke helpers as needed for this layer.
  - Update backlog state and record the slice result.
- Out of scope:
  - MCP request validation or tool error mapping.
  - README and broader consumer docs.
  - Query API reads for `P3`.

## Approach

Bootstrap Alembic from the async template, align it with the app settings and SQLAlchemy metadata, define the `feedback_events` model and create service/repository abstractions around async sessions, then verify the migration and write path against a real Postgres instance.

## Affected Files

- `alembic.ini`
- `alembic/...`
- `src/vocky/...`
- `tests/...`
- `works/backlog.md`
- `works/current/20260423_2333_implement_postgres_persistence/plan.md`
- `works/current/20260423_2333_implement_postgres_persistence/result.md`

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The migration defaults and ORM defaults need to match so persisted records behave consistently.
- The repository and service APIs should stay generic enough for the later MCP and HTTP transports to share them.

## Verification Plan

- Run the migration against Postgres.
- Execute a real insert path through the service or repository.
- Validate the expected indexes and default values from the created schema.

## Planned Commits

- `feat(storage): add postgres persistence core`
