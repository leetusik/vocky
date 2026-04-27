# Plan

- Work item: works/current/20260427_1351_build_dashboard_data_and_time_window_controls
- Created at: 20260427_1351
- Phase ID: P3
- Phase: Dashboard metrics
- Slice ID: P3.S2
- Slice: build dashboard data and time-window controls

## Goal

Add dashboard client-side data flow and time-window controls for metrics, health, and recent feedback records.

## Scope

- Add dashboard state for loading, unauthorized, error, empty, refreshed, and active preset/window values.
- Add 7-day, 30-day, and 90-day preset controls, with 30 days as the default.
- Refresh the dashboard by fetching `/admin/api/healthz`, `/admin/api/feedback/metrics`, and `/admin/api/feedback?limit=5`.
- Keep all Admin API calls behind the existing `adminFetch` bearer-token behavior.
- Add HTML hooks and focused static asset tests for the data-flow hooks.
- Avoid final dashboard metric/trend/recent-activity rendering polish; that is `P3.S3`.

## Context

- `P3.S1` added `GET /admin/api/feedback/metrics`.
- The Admin Web UI already has session token handling, health checks, navigation, docs loading, and a placeholder dashboard.
- The current refresh button only checks health; after this slice it should refresh all dashboard data.
- Static tests assert key HTML/JS/CSS hooks rather than browser execution.

## Milestones

1. Add dashboard state, preset constants, and UTC window calculation helpers.
2. Add Admin API fetch helpers for health, metrics, and recent records using `adminFetch`.
3. Wire refresh and token actions to the dashboard data loader.
4. Add HTML hooks for dashboard status and preset controls.
5. Update focused Admin UI/static tests.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py`

## Risks / open questions

- The app should treat `401` distinctly so operators see authorization state instead of a generic failure.
- Empty metrics and empty recent-record responses should be represented separately from load errors.
- Time-window calculation should use UTC ISO strings and avoid local timezone drift in API requests.

## Docs to update

- None planned for this data-flow slice.
