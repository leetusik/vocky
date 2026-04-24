# Result

- Work item: works/current/20260424_1451_add_bearer_token_protection_for_mcp_traffic
- Created at: 20260424_1451
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S2
- Slice: add bearer-token protection for MCP traffic
- Review status: complete
- Reviewer: self
- Next action: Start `P1.S3` to add public smoke auth support and client examples.

## Summary

Added optional bearer-token protection for MCP HTTP traffic. When `VOCKY_MCP_AUTH_TOKEN` is set, `/mcp` requires `Authorization: Bearer <token>` and `/healthz` remains open.

## Changes Made

- Added `VOCKY_MCP_AUTH_TOKEN` settings support with blank-token local default.
- Added `MCPBearerAuthMiddleware` with constant-time bearer-token comparison.
- Installed the middleware in the Starlette app.
- Surfaced the token variable in `.env.example`, `Makefile`, and Compose app environment.
- Added tests for disabled auth, required auth, invalid auth, valid auth, and unaffected health checks.

## Files Changed

- `.env.example`
- `Makefile`
- `docker-compose.yml`
- `src/vocky/app.py`
- `src/vocky/auth.py`
- `src/vocky/config.py`
- `tests/test_public_access.py`
- `works/backlog.md`
- `works/current/20260424_1451_add_bearer_token_protection_for_mcp_traffic/plan.md`
- `works/current/20260424_1451_add_bearer_token_protection_for_mcp_traffic/result.md`

## Verification Performed

- `uv run pytest tests/test_public_access.py -q`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None. Durable docs updates are planned for `P1.S4`.

## Follow-Ups

- Add public smoke header support in `P1.S3`.

## Commit References

- Pending.
