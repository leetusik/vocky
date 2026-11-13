# Result

- Work item: works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime
- Created at: 20260424_1144
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S2
- Slice: add Redis queue and dedicated worker runtime
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.S3` to move `capture_feedback` onto the new queue and return the receipt-based MCP response.

## Summary

Added the Redis-backed runtime pieces required for async capture: a narrow queue module, a dedicated worker entrypoint, Redis configuration, and Compose or Make surfaces for the expanded topology.

## Changes Made

- Added Redis runtime and fakeredis test dependencies plus the `vocky-worker` CLI entrypoint in `pyproject.toml`.
- Added `REDIS_URL` and `REDIS_PORT` to the environment surface and updated Compose or Make to launch `redis`, `app`, `worker`, and `postgres`.
- Implemented the shared Redis client helper, capture queue serialization layer, and background worker loop with bounded retries plus dead-letter handling.
- Added focused tests for queue round-tripping and worker retry/dead-letter behavior.

## Files Changed

- `pyproject.toml`
- `uv.lock`
- `.env.example`
- `docker-compose.yml`
- `Makefile`
- `src/vocky/config.py`
- `src/vocky/app.py`
- `src/vocky/redis_client.py`
- `src/vocky/capture_queue.py`
- `src/vocky/worker.py`
- `tests/test_capture_queue.py`
- `tests/test_worker.py`
- `works/backlog.md`
- `works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime/plan.md`
- `works/current/20260424_1144_add_redis_queue_and_dedicated_worker_runtime/result.md`

## Verification Performed

- Ran `uv run pytest tests/test_capture_queue.py tests/test_worker.py`.
- Ran `docker compose config`.
- Ran `uv run python -c "from vocky.worker import CaptureWorker, main; from vocky.capture_queue import CaptureQueue; print('worker imports ok')"` to verify the new entrypoint imports cleanly.

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Switch `capture_feedback` from direct persistence to queue acceptance in `P1.S3`.
- Update the smoke flow, README, and durable docs for the eventual-consistency path in `P1.S4`.

## Commit References

- None.
