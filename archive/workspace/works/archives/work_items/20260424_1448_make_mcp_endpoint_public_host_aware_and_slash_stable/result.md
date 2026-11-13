# Result

- Work item: works/current/20260424_1448_make_mcp_endpoint_public_host_aware_and_slash_stable
- Created at: 20260424_1448
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S1
- Slice: make MCP endpoint public-host aware and slash-stable
- Review status: complete
- Reviewer: self
- Next action: Start `P1.S2` to add bearer-token protection for MCP traffic.

## Summary

Made the MCP route public-host aware while keeping FastMCP DNS rebinding protection enabled. The canonical endpoint is now `/mcp` directly instead of a mounted `/mcp/` child path.

## Changes Made

- Added comma-separated MCP Host and Origin allowlist settings.
- Passed explicit `TransportSecuritySettings` into FastMCP with localhost defaults plus configured public values.
- Changed the FastMCP streamable HTTP path to `/mcp` and mounted the MCP app at the Starlette root after `/healthz`.
- Added public-access tests for CSV parsing, Host/Origin allowlist behavior, direct `/mcp` routing, and invalid Host rejection.
- Surfaced the new allowlist variables in `.env.example`, `Makefile`, and Compose app environment.

## Files Changed

- `.env.example`
- `Makefile`
- `docker-compose.yml`
- `src/vocky/app.py`
- `src/vocky/config.py`
- `src/vocky/mcp_server.py`
- `tests/test_public_access.py`
- `works/backlog.md`
- `works/current/20260424_1448_make_mcp_endpoint_public_host_aware_and_slash_stable/plan.md`
- `works/current/20260424_1448_make_mcp_endpoint_public_host_aware_and_slash_stable/result.md`

## Verification Performed

- `uv run pytest tests/test_public_access.py -q`

## Review Findings

- The app-level TestClient must run the ASGI lifespan because FastMCP requires its session manager to be active.

## Blocking Findings

- None.

## Reference Docs Updated

- None. Durable docs updates are planned for `P1.S4`.

## Follow-Ups

- Add bearer-token protection in `P1.S2`.

## Commit References

- Pending.
