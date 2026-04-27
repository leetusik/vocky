# Plan

- Work item: works/current/20260427_1125_build_operator_navigation_shell_and_token_client
- Created at: 20260427_1125
- Phase ID: P1
- Phase: Self-hosted Web UI foundation
- Slice ID: P1.S3
- Slice: build operator navigation shell and token client

## Goal

Build the first vanilla Admin Web UI operator shell with compact navigation, token handling, and a health-check path to existing Admin REST.

## Scope

- Update packaged Admin UI HTML/CSS/JS only; no frontend build system or new dependencies.
- Add Dashboard, Feedback, and Docs navigation views with foundational placeholder state, not full metrics/docs/workflows.
- Store the entered Admin bearer token in `sessionStorage` key `vocky.adminToken`.
- Call `/admin/api/healthz` as a same-origin Admin REST health check.
- Attach bearer auth only to `/admin/api/*` client calls.

## Context

- `P1.S2` added explicit packaged routes and static assets.
- Existing `VOCKY_ADMIN_AUTH_TOKEN` and Admin REST middleware remain the only server-side Admin auth model.
- P2/P3/P4 will add real Docs, Dashboard metrics, and Feedback management workflows.

## Milestones

1. Replace the placeholder asset contents with the operator console shell.
2. Add or update tests for shell content, session storage key, Admin REST path, and route/auth boundaries.
3. Run targeted pytest for public access and Admin UI.

## Validation

- `uv run pytest tests/test_public_access.py tests/test_admin_ui.py -q`

## Risks / open questions

- The client must not send the Admin bearer token to `/mcp`, `/api/*`, or static asset paths.
- Keep the UI honest about future work without adding visible instructional copy or oversized marketing layout.

## Docs to update

- None expected for this slice.
