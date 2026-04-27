# Plan

- Work item: works/current/20260427_1123_add_admin_web_ui_route_and_static_assets
- Created at: 20260427_1123
- Phase ID: P1
- Phase: Self-hosted Web UI foundation
- Slice ID: P1.S2
- Slice: add Admin Web UI route and static assets

## Goal

Add packaged Starlette browser routes for the Admin Web UI foundation without changing MCP, public REST capture, or Admin REST behavior.

## Scope

- Add `GET /admin` and `GET /admin/` routes that serve the Admin UI HTML shell.
- Add packaged static serving for `GET /admin/assets/app.css` and `GET /admin/assets/app.js`.
- Register Admin Web UI routes before the catch-all MCP mount so `/admin` paths are not swallowed by MCP.
- Keep `/admin/api/*`, `/api/*`, and `/mcp` behavior unchanged.
- Add focused tests in `tests/test_admin_ui.py`.

## Context

- The UI is vanilla packaged resources under the Python package; no Node, React, Vite, or new Python dependencies.
- Admin REST remains the data boundary under `/admin/api/*`.
- The shell can load without server-side Admin auth; protected data remains controlled by existing Admin REST auth.

## Milestones

1. Inspect Starlette app route composition and existing public/auth tests.
2. Add the packaged HTML/CSS/JS resources and routes.
3. Add route/static/auth regression tests and run targeted pytest.

## Validation

- `uv run pytest tests/test_public_access.py tests/test_admin_ui.py -q`

## Risks / open questions

- Route order must preserve `/admin/api/*` and `/mcp`.
- Package data must be loadable from installed package resources, not only from the source tree.

## Docs to update

- None expected for this slice; P1.S1 already recorded route direction in durable docs.
