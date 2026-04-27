# Plan

- Work item: works/current/20260427_1235_build_docs_content_framework
- Created at: 20260427_1235
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.S1
- Slice: build Docs content framework

## Goal

Add the maintainable Docs content framework for the Admin Web UI so operator documentation can be served as a packaged static asset and rendered in the existing Docs view.

## Scope

- Add a structured Admin UI docs JSON asset served from `/admin/assets/docs.json`.
- Replace the Docs placeholder with topic navigation, article rendering hooks, loading/empty/error states, and responsive layout styling.
- Render docs content in `app.js` with DOM APIs and without changing token storage or Admin API health behavior.
- Extend Admin UI tests for the docs asset route, static-auth boundaries, route ordering, and DOM hooks.

## Context

- P2 is an active backlog phase. P2.DECOMP is complete and must be preserved.
- The Admin UI is a no-build packaged asset surface under `src/vocky/admin_assets`.
- `/admin` and `/admin/assets/*` are unauthenticated; Admin REST bearer auth remains scoped to `/admin/api` and `/admin/api/*`.

## Milestones

1. Add the docs asset route and starter structured docs data.
2. Update the Docs view HTML/CSS/JS renderer and states.
3. Add focused tests for route/static behavior and core hooks.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`

## Risks / open questions

- Keep the first docs payload small in this slice; P2.S2 and P2.S3 will populate the full operator reference content.
- Avoid adding any browser auth behavior outside existing `/admin/api/*` requests.

## Docs to update

- None planned for this slice; durable docs updates are planned for P2.S3 if completed UI docs change project truth.
