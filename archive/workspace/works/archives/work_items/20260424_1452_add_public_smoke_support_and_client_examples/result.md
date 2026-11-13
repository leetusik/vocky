# Result

- Work item: works/current/20260424_1452_add_public_smoke_support_and_client_examples
- Created at: 20260424_1452
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S3
- Slice: add public smoke support and client examples
- Review status: complete
- Reviewer: self
- Next action: Start `P1.S4` to document Cloudflare custom-domain setup and client usage.

## Summary

Updated the smoke MCP client so public smoke checks can authenticate with `Authorization: Bearer <token>` when `VOCKY_MCP_AUTH_TOKEN` is configured.

## Changes Made

- Added `make_mcp_client_headers()` to build optional bearer headers for smoke checks.
- Passed an authenticated `httpx.AsyncClient` into the MCP streamable HTTP client.
- Declared `httpx` as a direct runtime dependency because the smoke module imports it directly.
- Added tests for smoke header construction.
- Refreshed `uv.lock`.

## Files Changed

- `pyproject.toml`
- `uv.lock`
- `src/vocky/smoke.py`
- `tests/test_public_access.py`
- `works/backlog.md`
- `works/current/20260424_1452_add_public_smoke_support_and_client_examples/plan.md`
- `works/current/20260424_1452_add_public_smoke_support_and_client_examples/result.md`

## Verification Performed

- `uv lock`
- `uv lock --check`
- `uv run pytest tests/test_public_access.py -q`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None. Docs are planned for `P1.S4`.

## Follow-Ups

- Document the public client header and Cloudflare setup in `P1.S4`.

## Commit References

- Pending.
