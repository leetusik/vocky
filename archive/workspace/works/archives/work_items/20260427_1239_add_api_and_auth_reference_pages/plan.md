# Plan

- Work item: works/current/20260427_1239_add_api_and_auth_reference_pages
- Created at: 20260427_1239
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.S2
- Slice: add API and auth reference pages

## Goal

Populate the in-app Docs payload with operator reference pages for the implemented API surfaces and bearer-token behavior.

## Scope

- Replace the starter docs content with structured topics for MCP tools, REST capture, Admin REST, and auth tokens.
- Source the content from current `docs/api.md`, `docs/architecture.md`, and README truth without changing any API contracts.
- Add tests that validate JSON structure and representative required strings so future content edits cannot silently drop core pages.

## Context

- P2.S1 added `/admin/assets/docs.json` and a DOM-based renderer that supports paragraphs, tables, lists, definition lists, code blocks, steps, headings, and callouts.
- The required operator essentials include `/mcp`, `capture_feedback`, `list_feedback`, `summarize_feedback`, `list_liked_conversations`, `POST /api/feedback`, `/admin/api/*`, status expectations, and bearer-token variables.
- This slice should not edit durable docs unless it discovers a contract mismatch; no contract changes are planned.

## Milestones

1. Expand `docs.json` with API and auth reference topics.
2. Add focused Admin UI tests for required content and JSON validity.
3. Run the P2 focused test set.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`

## Risks / open questions

- Keep content concise enough for in-app use while preserving contract-critical details.
- Avoid introducing SaaS tenant/account/billing terminology.

## Docs to update

- None planned; this slice mirrors existing durable docs into the Admin UI docs asset.
