# Plan

- Work item: works/current/20260424_1448_make_mcp_endpoint_public_host_aware_and_slash_stable
- Created at: 20260424_1448
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S1
- Slice: make MCP endpoint public-host aware and slash-stable

## Context

FastMCP currently auto-enables localhost-only DNS rebinding protection because the server is initialized with default `host="127.0.0.1"`. The app then mounts a child MCP app at `/mcp`, so `/mcp` redirects to `/mcp/` and can emit an `http://` Location behind a TLS proxy.

## Goal

Make the canonical MCP endpoint work directly at `/mcp` for local and public hostnames, without a Host-header workaround and without relying on a slash redirect.

## Scope

- In scope:
  - Add runtime settings for MCP allowed Host and Origin values.
  - Pass explicit FastMCP transport-security settings including localhost defaults plus configured public hosts.
  - Change the Starlette integration so the FastMCP app owns `/mcp` directly rather than being mounted at `/mcp`.
  - Add tests for host acceptance/rejection and the no-redirect canonical path.
- Out of scope:
  - Bearer-token enforcement, which is handled in `P1.S2`.
  - Cloudflare account or tunnel state changes.

## Approach

Expose comma-separated config values, derive transport security with safe localhost defaults plus configured host/origin entries, set FastMCP `streamable_http_path="/mcp"`, and mount the FastMCP Starlette app at root after `/healthz`. Verify `/mcp` returns from the MCP app directly and public Host values can pass the SDK middleware.

## Affected Files

- `src/vocky/config.py`
- `src/vocky/mcp_server.py`
- `src/vocky/app.py`
- `tests/test_public_access.py`
- `.env.example`
- `works/backlog.md`
- Work item plan/result files

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Starlette may still redirect `/mcp/` to `/mcp`; the canonical public URL will be `/mcp`.
- The SDK validates Host exactly except for `:*` wildcard port suffixes, so configured hosts should include the plain hostname and local wildcard entries.

## Verification Plan

- Run focused tests for public access routing and host validation.
- Confirm existing in-memory MCP integration tests still pass.

## Planned Commits

- `fix(mcp): allow public host and stabilize mcp route`
