# Result

- Work item: works/current/20260429_1103_add_target_type_read_filters_index
- Created at: 20260429_1103
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.S2
- Slice: add target_type read filters and index
- Review status: passed
- Reviewer: Codex
- Next action: Archive this work item and continue with `P1.S3`.

## Outcome

Implemented exact `target_type` filtering across MCP and Admin read paths. The transport-neutral query filter now includes `target_type`, shared query normalization accepts trimmed `message`, `conversation`, or `surface` values, invalid values return MCP tool errors or Admin REST `400`, and the repository applies an exact SQL predicate when the filter is present.

Added non-unique PostgreSQL index `ix_feedback_events_target_type` through Alembic revision `20260429_1103` and mirrored it in the ORM model. Existing `target_type = null` rows remain visible when no filter is supplied.

Updated stable product, architecture, and API docs from accepted/future wording to implemented read-filter behavior.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_query_validation.py tests/test_persistence.py tests/test_mcp_integration.py tests/test_admin_api.py` passed, 51 tests.
- `git diff --check` passed.

## Files changed

- `src/vocky/tools/query_feedback_common.py`
- `src/vocky/tools/list_feedback.py`
- `src/vocky/tools/summarize_feedback.py`
- `src/vocky/tools/list_liked_conversations.py`
- `src/vocky/admin_api.py`
- `src/vocky/feedback/types.py`
- `src/vocky/feedback/repository.py`
- `src/vocky/persistence/models.py`
- `alembic/versions/20260429_1103_add_feedback_target_type_index.py`
- `tests/test_query_validation.py`
- `tests/test_persistence.py`
- `tests/test_mcp_integration.py`
- `tests/test_admin_api.py`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Docs updated

- `docs/product.md`: describes `target_type` as an implemented exact-match review filter.
- `docs/architecture.md`: describes the implemented P1 read query model.
- `docs/api.md`: lists `target_type` filtering as implemented for MCP read tools and Admin list review.

## Roadmap updates

- `P1.S2` can be marked done. Continue with `P1.S3`.

## Retrospective

- The storage column and serializers already existed, so the slice stayed focused on query normalization, SQL filtering, indexing, and coverage.
