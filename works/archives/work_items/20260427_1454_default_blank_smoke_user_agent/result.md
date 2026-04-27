# Result

- Work item: works/current/20260427_1454_default_blank_smoke_user_agent
- Created at: 20260427_1454
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.F1
- Slice: default blank smoke user agent
- Review status: not reviewed
- Reviewer: n/a
- Next action: Rerun `P5.REVIEW` with `scripts/start_work.sh P5 P5.REVIEW review_self_hosted_packaging_polish_rerun`.

## Outcome

Updated smoke and readiness user-agent helpers so blank or whitespace-only `VOCKY_HTTP_USER_AGENT` values fall back to `VockySmoke/0.1`. Added focused test coverage for unset, blank, and custom user-agent behavior while preserving bearer-token handling.

## Deviations from plan

None.

## Validation run

- `VOCKY_HTTP_USER_AGENT= uv run pytest tests/test_public_access.py::test_smoke_mcp_client_headers_use_optional_bearer_token`

## Files changed

- `src/vocky/smoke.py`
- `scripts/wait_for_health.py`
- `tests/test_public_access.py`
- `works/backlog.md`
- `works/current/20260427_1454_default_blank_smoke_user_agent/plan.md`
- `works/current/20260427_1454_default_blank_smoke_user_agent/result.md`

## Docs updated

- None.

## Roadmap updates

- `P5.F1` moved to `done`.

## Retrospective

- Normalizing blank environment values keeps Make-exported optional settings from changing smoke defaults.
