# Plan

- Work item: works/current/20260424_1452_add_public_smoke_support_and_client_examples
- Created at: 20260424_1452
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S3
- Slice: add public smoke support and client examples

## Context

The MCP endpoint now supports configured public hosts and optional bearer auth, but the smoke client still opens the streamable HTTP client without auth headers. Public verification against `https://vocky.example.com` would fail once the recommended token is configured.

## Goal

Allow the smoke script and existing Make targets to verify token-protected public MCP URLs without Host-header workarounds.

## Scope

- In scope:
  - Add bearer-header support to the smoke MCP client when `VOCKY_MCP_AUTH_TOKEN` is set.
  - Add focused tests for smoke auth header construction.
  - Ensure Make exports already pass the token into smoke targets.
  - Add client example details in docs during `P1.S4`, not this slice.
- Out of scope:
  - Cloudflare documentation text.
  - Running a live public smoke against `vocky.example.com` without confirmed external state.

## Approach

Use an `httpx.AsyncClient` with optional `Authorization` headers and pass it to `streamable_http_client`. Declare `httpx` as a direct runtime dependency because the smoke module imports it directly.

## Affected Files

- `src/vocky/smoke.py`
- `pyproject.toml`
- `uv.lock`
- `tests/test_public_access.py`
- `works/backlog.md`
- Work item plan/result files

## Reference Docs To Review

- `README.md`
- `docs/api.md`

## Risks and Open Questions

- Adding `httpx` as a direct dependency should be lockfile-only because it is already present through the MCP/client stack and dev dependencies.
- The public smoke target can only be fully live-tested after Cloudflare and tunnel setup exist.

## Verification Plan

- Run `uv run pytest tests/test_public_access.py -q`.
- Run `uv lock --check` or update the lock if needed after dependency metadata changes.

## Planned Commits

- `test(mcp): support authenticated public smoke checks`
