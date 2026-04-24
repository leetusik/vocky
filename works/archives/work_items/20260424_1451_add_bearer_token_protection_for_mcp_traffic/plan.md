# Plan

- Work item: works/current/20260424_1451_add_bearer_token_protection_for_mcp_traffic
- Created at: 20260424_1451
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S2
- Slice: add bearer-token protection for MCP traffic

## Context

The public route work allows configured external Host headers, but the service still exposes MCP capture and review tools without authentication. Public internet access should require a simple client-compatible token gate.

## Goal

Require `Authorization: Bearer <token>` on `/mcp` requests when `VOCKY_MCP_AUTH_TOKEN` is configured, while keeping `/healthz` unauthenticated and preserving local no-token development by default.

## Scope

- In scope:
  - Add an optional MCP auth token setting.
  - Add Starlette edge middleware for `/mcp` and `/mcp/...`.
  - Return HTTP 401 with `WWW-Authenticate: Bearer` for missing or wrong credentials.
  - Add tests for enabled and disabled auth behavior.
  - Surface the setting in `.env.example`, Makefile exports, and Compose app env.
- Out of scope:
  - User accounts, OAuth, Cloudflare Access integration, or per-tool authorization.
  - Smoke-client auth header support, which is handled in `P1.S3`.

## Approach

Implement a small ASGI middleware that checks only MCP paths and uses constant-time token comparison. Install it from `create_app()` with the configured token; a blank token disables enforcement.

## Affected Files

- `src/vocky/auth.py`
- `src/vocky/app.py`
- `src/vocky/config.py`
- `tests/test_public_access.py`
- `.env.example`
- `Makefile`
- `docker-compose.yml`
- `works/backlog.md`
- Work item plan/result files

## Reference Docs To Review

- `docs/api.md`
- `docs/architecture.md`

## Risks and Open Questions

- Auth must be app-level because FastMCP tool-level auth would be more invasive than this MVP needs.
- Do not protect `/healthz`; Cloudflare Tunnel and smoke checks need a simple liveness path.

## Verification Plan

- Run `uv run pytest tests/test_public_access.py -q`.
- Re-run MCP integration tests later in phase review.

## Planned Commits

- `feat(mcp): add bearer-token protection`
