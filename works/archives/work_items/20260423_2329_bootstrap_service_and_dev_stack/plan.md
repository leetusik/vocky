# Plan

- Work item: works/current/20260423_2329_bootstrap_service_and_dev_stack
- Created at: 20260423_2329
- Phase ID: P2
- Phase: Build MCP capture and persistence core
- Slice ID: P2.S2
- Slice: bootstrap service and dev stack

## Context

- `P2.S1` locked the runtime, configuration, and contract decisions in the reference docs.
- The repo still has no Python package, dependency metadata, container config, or runnable ASGI app.
- The next slice needs to create the runnable shell without yet implementing persistence or the capture tool behavior.

## Goal

Create the initial `uv`-managed Python project, Starlette/FastMCP host app shell, configuration loading, container stack, and Make targets that later slices will build on.

## Scope

- In scope:
  - Create `pyproject.toml` and project package layout under `src/vocky`.
  - Add settings, Starlette app bootstrap, FastMCP mount, and `/healthz`.
  - Add Dockerfile, `docker-compose.yml`, `.env.example`, and Makefile.
  - Generate the initial `uv.lock`.
  - Update backlog state and record the work item result.
- Out of scope:
  - Database models, Alembic environment, or repository code.
  - The `capture_feedback` tool implementation.
  - README and reference-doc updates beyond what is necessary for the scaffold to run.

## Approach

Define the Python package and dependency metadata first, then add the transport shell and settings module, then add local/dev tooling around it, and finally run the scaffold-level checks (`uv sync`, import smoke, and container config validation).

## Affected Files

- `pyproject.toml`
- `uv.lock`
- `.gitignore`
- `.env.example`
- `Makefile`
- `Dockerfile`
- `docker-compose.yml`
- `src/vocky/...`
- `works/backlog.md`
- `works/current/20260423_2329_bootstrap_service_and_dev_stack/plan.md`
- `works/current/20260423_2329_bootstrap_service_and_dev_stack/result.md`

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The mounted FastMCP path and lifespan setup need to match the current MCP Python SDK expectations so the later integration tests do not fight the scaffold.
- The dev stack should not assume persistence exists yet, but it still needs a stable `DATABASE_URL` surface for the next slice.

## Verification Plan

- Run `uv sync`.
- Import and instantiate the ASGI app through `uv run`.
- Validate the compose file syntax and the Make targets that do not require persistence logic.

## Planned Commits

- `feat(app): bootstrap service and dev stack`
