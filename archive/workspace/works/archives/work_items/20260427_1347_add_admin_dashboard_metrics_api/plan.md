# Plan

- Work item: works/current/20260427_1347_add_admin_dashboard_metrics_api
- Created at: 20260427_1347
- Phase ID: P3
- Phase: Dashboard metrics
- Slice ID: P3.S1
- Slice: add Admin dashboard metrics API

## Goal

Add a protected Admin REST metrics endpoint that returns feedback volume, like, dislike, unrated, and zero-filled UTC daily trend counts for an explicit ingest-time window.

## Scope

- Add transport-neutral dashboard metrics types and service/repository methods.
- Add `GET /admin/api/feedback/metrics` before feedback ID routes.
- Require `start_ingested_at` and `end_ingested_at` query parameters, normalize timezone-aware timestamps to UTC, and reject invalid windows.
- Return `window`, `totals`, and UTC `daily_counts` with `total`, `liked`, `disliked`, and `unrated` counts.
- Cover success, validation, storage failure, route ordering, and auth boundary behavior in tests.
- Update `docs/api.md` and `docs/architecture.md`.

## Context

- Existing query helpers already parse timezone-aware timestamps, normalize to UTC, and validate inclusive-start/exclusive-end windows.
- Existing Admin REST list/detail/patch/delete routes use the feedback service and map query validation failures to JSON `400` responses.
- Existing summary repository logic has the UTC day-series shape, but it only returns total counts; P3 needs per-feedback-value buckets.
- Admin bearer middleware already protects `/admin/api/*`, so a route under that prefix should inherit the existing boundary.

## Milestones

1. Add metrics dataclasses and export them.
2. Implement repository aggregate queries and service read method.
3. Add Admin REST query normalization, serialization, and route registration.
4. Add focused API/persistence/auth tests.
5. Update API and architecture reference docs.

## Validation

- `uv run pytest tests/test_admin_api.py tests/test_public_access.py tests/test_persistence.py`

## Risks / open questions

- PostgreSQL day bucketing should stay UTC and zero-fill every requested day, including partial-day windows.
- The endpoint intentionally supports only the time window in this slice; additional filters can be added later if product scope changes.

## Docs to update

- `docs/api.md`
- `docs/architecture.md`
