# Result

- Work item: works/current/20260427_1712_add_explicit_feedback_target_capture_model
- Created at: 20260427_1712
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S2
- Slice: add explicit feedback target capture model
- Review status: completed
- Reviewer: Codex
- Next action: Continue with `P1.S3`.

## Outcome

Added optional `target_type`, `target_id`, `target_role`, and `target_text` capture persistence through validation, MCP tool input, REST input parsing, Redis job serialization/deserialization, service dataclasses, repository writes/reads, SQLAlchemy model, and Alembic migration.

Existing captures remain compatible because all target fields default to `None`, blank target strings normalize to `None`, and old queued jobs missing target keys deserialize with `None` values.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_capture_validation.py tests/test_capture_queue.py tests/test_capture_api.py tests/test_mcp_integration.py::test_capture_feedback_success`
- `uv run pytest tests/test_persistence.py::test_migration_applies_and_expected_indexes_exist tests/test_persistence.py::test_service_insert_persists_values_and_db_defaults`

## Files changed

- `alembic/versions/20260427_1600_add_feedback_target_fields.py`
- `src/vocky/capture.py`
- `src/vocky/capture_queue.py`
- `src/vocky/tools/capture_feedback.py`
- `src/vocky/feedback/types.py`
- `src/vocky/feedback/repository.py`
- `src/vocky/persistence/models.py`
- `tests/test_capture_validation.py`
- `tests/test_capture_queue.py`
- `tests/test_capture_api.py`
- `tests/test_mcp_integration.py`
- `tests/test_persistence.py`
- `works/backlog.md`
- `works/current/20260427_1712_add_explicit_feedback_target_capture_model/plan.md`
- `works/current/20260427_1712_add_explicit_feedback_target_capture_model/result.md`

## Docs updated

- None in this slice.

## Roadmap updates

- Marked `P1.S2` complete in `works/backlog.md`.

## Retrospective

- The queue compatibility test is the key guardrail for mixed old/new app-worker deployments.
