# Plan

- Work item: works/current/20260424_1645_add_admin_rest_routing_surface
- Created at: 20260424_1645
- Phase ID: P3
- Phase: Admin REST API for human review
- Slice ID: P3.S1
- Slice: add admin REST routing surface

## Context

The app currently hosts `/healthz` and MCP under `/mcp` via a root mount. Admin REST routes must be separate from MCP tool handlers and mounted before the MCP root mount.

## Goal

Add the Admin REST route namespace and optional bearer protection.

## Scope

- In scope: `/admin/api/healthz`, admin route registration, admin path auth helpers/middleware, admin token config, and routing/auth tests.
- Out of scope: Feedback query and management endpoints.

## Approach

Create `src/vocky/admin_api.py` with initial routes, mount those routes before the MCP root mount, and add `VOCKY_ADMIN_AUTH_TOKEN`-based bearer protection for `/admin/api/*`.

## Affected Files

- `src/vocky/admin_api.py`
- `src/vocky/app.py`
- `src/vocky/auth.py`
- `src/vocky/config.py`
- `tests/test_public_access.py`

## Reference Docs To Review

- `docs/architecture.md`

## Risks and Open Questions

- The MCP root mount could catch Admin paths if route ordering is wrong.
- Admin REST should remain separate from MCP tool handlers.

## Verification Plan

- Run public-access/routing tests.

## Planned Commits

- Not committing unless requested.
