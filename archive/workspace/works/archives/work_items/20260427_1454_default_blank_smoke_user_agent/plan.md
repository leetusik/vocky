# Plan

- Work item: works/current/20260427_1454_default_blank_smoke_user_agent
- Created at: 20260427_1454
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.F1
- Slice: default blank smoke user agent

## Goal

Treat blank `VOCKY_HTTP_USER_AGENT` values as unset so Make-exported empty values still use the default `VockySmoke/0.1` user agent.

## Scope

- Update smoke and readiness user-agent helpers.
- Add or adjust focused tests for blank/custom user-agent behavior.
- Do not change bearer-token behavior.

## Context

- The first `P5.REVIEW` run failed during `make verify`.
- `Makefile` exports `VOCKY_HTTP_USER_AGENT`, which means child processes can see it as an empty string even when users did not configure it.
- `os.getenv("VOCKY_HTTP_USER_AGENT", DEFAULT_USER_AGENT)` does not apply the default when the variable is present but blank.

## Milestones

1. Normalize blank or whitespace-only user-agent env values to the default.
2. Cover the behavior in focused tests.
3. Run the failing focused test and close the fix slice.

## Validation

- `uv run pytest tests/test_public_access.py::test_smoke_mcp_client_headers_use_optional_bearer_token`

## Risks / open questions

- Keep custom non-blank user-agent values working for external proxy compatibility.

## Docs to update

- None.
