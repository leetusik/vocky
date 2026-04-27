# Plan

- Work item: works/current/20260425_0050_web_capture_rest_api_auth
- Created at: 20260425_0050
- Phase ID: P1
- Phase: Public Web Capture REST API
- Slice ID: P1.S2
- Slice: add web capture REST route and API auth

## Goal

Add the queue-backed public server-to-server REST capture endpoint and optional bearer auth for `/api/*`.

## Scope

- Add `POST /api/feedback` using the shared capture validation/receipt module and existing Redis queue.
- Add `VOCKY_API_AUTH_TOKEN` to runtime settings and path-scoped auth middleware for `/api/*`.
- Mount API routes before the MCP catch-all.
- Add REST capture tests and `/api/*` auth tests.
- Do not add REST review, query, summary, job-status, or management endpoints.

## Context

- `P1.S1` extracted transport-neutral capture models and normalization.
- REST success should return `202` with the same accepted receipt object as MCP structured content.
- REST validation failures should return `400 {"detail": "..."}` and queue failures should return `503 {"detail": "capture queue unavailable"}`.

## Milestones

1. Implement the REST capture route and response/error mapping.
2. Add API bearer middleware and settings integration.
3. Add tests for REST capture behavior, queue failure, validation failures, auth, and route ordering.
4. Run targeted REST/auth/MCP tests.

## Validation

- `uv run pytest tests/test_capture_api.py tests/test_public_access.py tests/test_mcp_integration.py -q`

## Risks / open questions

- Pydantic body-shape errors need concise REST `detail` strings without changing MCP behavior.
- The API route must be registered before the MCP catch-all mount.

## Docs to update

- Durable docs and operator config examples are scheduled for `P1.S3`.
