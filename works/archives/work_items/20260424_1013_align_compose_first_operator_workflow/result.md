# Result

- Work item: works/current/20260424_1013_align_compose_first_operator_workflow
- Created at: 20260424_1013
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S1
- Slice: align compose-first operator workflow
- Review status: passed
- Reviewer: Codex
- Next action: Start `P4.S2` to update the self-hosted runbook and durable config notes around the new Compose-first defaults.

## Summary

Aligned the local operator workflow around the copied root `.env`, added stable `bootstrap` and `verify` helper targets, and made the smoke path wait for service readiness before exercising the MCP loop.

## Changes Made

- Updated `Makefile` so the supported local targets import the root `.env` when present and export the relevant runtime and Compose variables to `uv`-driven commands.
- Added `bootstrap`, `verify`, and `wait-ready` targets while keeping the granular workflow targets intact.
- Added a safety guard before `make test` so it refuses to run when `TEST_DATABASE_URL` is missing or points at the same database as `DATABASE_URL`.
- Added `scripts/wait_for_health.py` so readiness polling is explicit and reusable from the Make-based operator flow.
- Marked `P4.S1` active in `works/backlog.md`.

## Files Changed

- `Makefile`
- `scripts/wait_for_health.py`
- `works/backlog.md`
- `works/current/20260424_1013_align_compose_first_operator_workflow/plan.md`
- `works/current/20260424_1013_align_compose_first_operator_workflow/result.md`

## Verification Performed

- `make -n bootstrap`
- `make -n verify`
- `WAIT_READY_TIMEOUT=1 VOCKY_BASE_URL=http://127.0.0.1:9 uv run python scripts/wait_for_health.py`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Update `README.md` and durable architecture notes so the documented self-hosted flow matches the `.env`-driven Compose-first workflow.

## Commit References

- None.
