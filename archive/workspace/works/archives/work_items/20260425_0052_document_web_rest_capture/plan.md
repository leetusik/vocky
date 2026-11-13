# Plan

- Work item: works/current/20260425_0052_document_web_rest_capture
- Created at: 20260425_0052
- Phase ID: P1
- Phase: Public Web Capture REST API
- Slice ID: P1.S3
- Slice: document web REST capture surface

## Goal

Update durable docs and operator configuration examples to reflect both MCP capture and server-to-server REST capture.

## Scope

- Update product, architecture, and API docs for the implemented `/api/feedback` ingestion surface.
- Update README and action-feedback integration guidance to explain when to use MCP versus REST and include a REST example.
- Add `VOCKY_API_AUTH_TOKEN` to `.env.example`, `docker-compose.yml`, and `Makefile` exported env vars.
- Keep REST docs scoped to capture ingestion only.

## Context

- `P1.S2` added `POST /api/feedback` with optional `/api/*` bearer auth.
- Existing docs still describe MCP-only ingestion in several places.
- Admin REST remains separate under `/admin/api/*` and continues to be the review/management surface.

## Milestones

1. Update config examples for `VOCKY_API_AUTH_TOKEN`.
2. Update reference docs for product scope, architecture, and REST contract.
3. Update README and integration guide with MCP-vs-REST guidance and examples.
4. Run targeted docs/config verification and REST/auth tests.

## Validation

- `uv run pytest tests/test_capture_api.py tests/test_public_access.py -q`
- `docker compose config`

## Risks / open questions

- Docs must not imply public REST review/query/management endpoints exist.
- Auth guidance should distinguish `/api/*`, `/admin/api/*`, and `/mcp`.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`
- `docs/action-feedback-integration.md`
