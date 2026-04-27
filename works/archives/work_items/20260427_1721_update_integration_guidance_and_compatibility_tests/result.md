# Result

- Work item: works/current/20260427_1721_update_integration_guidance_and_compatibility_tests
- Created at: 20260427_1721
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S4
- Slice: update integration guidance and compatibility tests
- Review status: completed
- Reviewer: Codex
- Next action: Continue with `P1.REVIEW`.

## Outcome

Updated the integration guide, README examples, packaged Admin UI docs, smoke path, and integration tests to show exact message targeting. Added worker round-trip coverage that captures target fields, persists them, and reads them back through `list_feedback`.

## Deviations from plan

None.

## Validation run

- `jq empty src/vocky/admin_assets/docs.json`
- `uv run pytest tests/test_mcp_integration.py::test_capture_feedback_becomes_queryable_after_worker_processing tests/test_admin_ui.py::test_admin_ui_assets_serve_packaged_resources`

## Files changed

- `docs/action-feedback-integration.md`
- `README.md`
- `src/vocky/admin_assets/docs.json`
- `src/vocky/smoke.py`
- `tests/test_mcp_integration.py`
- `tests/test_admin_ui.py`
- `works/backlog.md`
- `works/current/20260427_1721_update_integration_guidance_and_compatibility_tests/plan.md`
- `works/current/20260427_1721_update_integration_guidance_and_compatibility_tests/result.md`

## Docs updated

- `docs/action-feedback-integration.md`
- `README.md`
- `src/vocky/admin_assets/docs.json`

## Roadmap updates

- Marked `P1.S4` complete in `works/backlog.md`.

## Retrospective

- Smoke verification now checks target context, which keeps the public self-hosted path aligned with the new semantics.
