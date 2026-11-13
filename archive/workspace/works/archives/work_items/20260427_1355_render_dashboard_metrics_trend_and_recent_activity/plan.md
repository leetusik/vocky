# Plan

- Work item: works/current/20260427_1355_render_dashboard_metrics_trend_and_recent_activity
- Created at: 20260427_1355
- Phase ID: P3
- Phase: Dashboard metrics
- Slice ID: P3.S3
- Slice: render dashboard metrics, trend, and recent activity

## Goal

Replace the dashboard placeholders with operator-facing metric cards, a daily trend view, and recent activity backed by the `P3.S1`/`P3.S2` data flow.

## Scope

- Render volume, likes, dislikes, and unrated counts from the metrics endpoint.
- Render a compact UTC daily trend from `daily_counts`.
- Render recent feedback activity from `GET /admin/api/feedback?limit=5`.
- Keep empty, unauthorized, loading, refreshed, and error UI states coherent.
- Keep the UI dense, responsive, vanilla HTML/CSS/JS, and consistent with the existing Admin shell.
- Update product and architecture docs to reflect implemented dashboard metrics in the Admin Web UI.
- Update focused static asset tests.

## Context

- `P3.S1` added the Admin metrics endpoint and docs for the API/read model.
- `P3.S2` added dashboard client state, refresh behavior, and time-window presets.
- The existing dashboard still has placeholder runtime/auth cards and a generic activity list.
- P4 is reserved for full feedback review and management; recent activity here should stay read-only.

## Milestones

1. Replace placeholder dashboard cards with metric cards and concrete data hooks.
2. Add trend and recent activity containers.
3. Render metrics, trend bars, and recent records from dashboard state.
4. Style responsive metric/trend/recent activity layouts.
5. Update product/architecture docs and focused UI tests.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py`

## Risks / open questions

- Long messages and labels must wrap without resizing fixed dashboard controls unexpectedly.
- Recent activity should not imply edit/manage capabilities before P4.
- Empty and unauthorized states should not leave stale metrics on screen.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
