# Plan

- Work item: works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime
- Created at: 20260424_1144
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S2
- Slice: add Redis queue and dedicated worker runtime

## Context

- The durable docs now assume Redis-backed enqueueing, a separate worker process, and a `REDIS_URL` config surface.
- The current runtime still consists of a single app process with synchronous Postgres writes in `capture_feedback`.
- The next slice needs to add the queue and worker infrastructure without changing the public `capture_feedback` behavior yet.

## Goal

Add the runtime pieces required for async capture: Redis configuration, queue primitives, a worker entrypoint, and self-hosted topology updates that the later capture-tool slice can use.

## Scope

- In scope:
  - Add Redis client dependency and runtime settings.
  - Implement a narrow queue module and worker loop for capture jobs.
  - Add a worker CLI entrypoint and update Compose / env / Make surfaces for Redis plus worker runtime.
- Out of scope:
  - Switching the `capture_feedback` MCP contract or response shape.
  - Updating smoke tests and operator docs beyond the runtime surfaces needed to launch the new topology.

## Approach

Introduce a small capture-job serialization layer backed by Redis lists, create a dedicated worker module that reads jobs and persists them through the existing feedback service with bounded retries and dead-letter handling, and expose the new runtime through config, package scripts, Compose, and Make targets.

## Affected Files

- `pyproject.toml`
- `.env.example`
- `docker-compose.yml`
- `Makefile`
- `src/vocky/config.py`
- `src/vocky/`
- `works/backlog.md`
- `works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime/plan.md`
- `works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime/result.md`

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`
- `README.md`
- `docker-compose.yml`
- `Makefile`

## Risks and Open Questions

- Keep the queue implementation intentionally small so the app and worker share only the minimum serialization and retry policy needed for v1.
- Ensure the new worker path can be exercised in tests without forcing every unit test to depend on a live Redis process.

## Verification Plan

- Run focused tests for queue serialization and worker processing.
- Validate the updated runtime surfaces compile and the new worker entrypoint imports cleanly.

## Planned Commits

- `feat(runtime): add Redis queue and worker`
