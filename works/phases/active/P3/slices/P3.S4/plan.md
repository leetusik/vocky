# P3.S4 — Usage monitoring (derived + last-used) — native plan → slice-executor-mid

Read `works/phases/active/P3/phase.md` (D-P3-5; **S1 outcomes** — `last_used_at` now stamped, the
`project_id` filter; **S3 outcomes** — `FeedbackQueryFilters.project_ids`; **S2 outcomes** —
`serialize_record` shared) and `AGENTS.md` first. This is the **final middle slice** and is
**pure reuse**: `summarize_feedback`/`get_feedback_metrics` already apply `_apply_query_filters`
(repository.py:459,470,514), so scoping metrics by `project_ids`/`project_id` works with **no
repository change, no new query, no migration, no new tables** (D-P3-5 — operational visibility, not
billing). Write no commits, no status transitions, no `doc-new-version`.

## New surface — `src/vocky/usage_api.py` (three endpoints, all reuse)

Each builds `FeedbackMetricsQuery(filters=FeedbackQueryFilters(start_ingested_at, end_ingested_at,
project_ids=<scope>))` and calls `get_feedback_service().get_feedback_metrics(query)`, serialized with
the existing `serialize_metrics` (`admin_api.py:255-276`). **Window:** reuse `parse_timestamp` +
`validate_time_window`; **default to the last 30 days** when both are omitted (`utc_now()` is available
in app code) so the dashboard can call with no params. If only one bound is given, default the other
sensibly (or require both — your call; keep it friendly).

| Method | Path | Auth | Scope | Response |
|---|---|---|---|---|
| GET | `/app/usage` | session (`require_user`) | tenant's projects: `list_projects_for_tenant(ctx.tenant.id)` → ids as `project_ids`; **empty set → zeroed metrics** (short-circuit) | `{window, totals, daily_counts, projects:[{id,name,created_at}]}` |
| GET | `/app/projects/{project_id}/usage` | session | one project via `_load_scoped_project` (404 cross-tenant) | `{window, totals, daily_counts, credentials:[serialize_credential]}` |
| GET | `/api/project/usage` | project key via `get_request_credential` | the credential's project | `{window, totals, daily_counts, credentials:[serialize_credential]}` |

- `/app/usage` = tenant aggregate volume + light project list (P4 overview). `/app/projects/{id}/usage`
  = per-project drill-down that surfaces the project's credentials with `last_used_at` (the S1 stamp).
  `/api/project/usage` = external-panel counterpart (the project's own key sees its usage).
- **Reuse (no duplication):** `serialize_metrics`/`serialize_metric_counts`/`serialize_daily_metric_count`
  (`admin_api.py` — lift them into `tools/query_feedback_common.py` alongside `serialize_record` and
  re-point `admin_api.py`, or import; do not copy); `serialize_credential` + `_load_scoped_project`
  (`app_api.py`); `list_projects_for_tenant`/`list_project_credentials`/`get_project` (accounts
  service); `get_request_credential` (`auth.py`); `parse_timestamp`/`validate_time_window`
  (`query_feedback_common.py`).
- **Wiring** (`app.py`): `from vocky.usage_api import routes as usage_routes`; splice `*usage_routes`
  into `create_app()`. `/app/*` usage routes are guarded per-handler by `require_user`;
  `/api/project/usage` is auto-guarded by `ProjectCredentialAuthMiddleware` (path `/api/…`). One
  `routes` list in `usage_api.py` is fine (middleware guards by path predicate). Mind route order vs
  `/api/project/feedback/...` and `/app/projects/{id}/...` — no overlap, but register cleanly.

## Tests — `tests/test_usage_api.py` (terse)

Reuse `configured_project_credential` + session-token signup (`test_app_api.py` pattern). Seed feedback
across 2 projects with `project_id` + varied `feedback_value` (1/2/null) inside a known window (raw SQL
under `get_engine().begin()`):

- `GET /app/usage` → totals aggregate **both** projects (correct liked/disliked/unrated split); a
  **second tenant's** feedback is **not** counted; the `projects` list matches.
- `GET /app/projects/{id}/usage` → that project's totals only; cross-tenant project id → 404; the
  credentials list surfaces `last_used_at`.
- `GET /api/project/usage` → the credential's project totals only.
- default window (no bounds) → sane 30-day window; explicit window respected.
- missing auth → 401 on each surface.

## Verify before returning

- `uv run pytest tests/test_usage_api.py tests/test_admin_api.py` (admin metrics must stay green) on real
  Postgres; if the DB can't run, `blocked`. Optionally full `uv run pytest`.

## result.md + phase.md notes; verdict

Write a free-form `result.md`. Append to `phase.md`: the three usage endpoints, that they're **derived**
from `get_feedback_metrics` (no new tables/queries, D-P3-5) and surface the S1 `last_used_at` stamps,
where the metrics serializers now live (if lifted), and one **Doc impact** line (`api.md`: `/app/usage`,
`/app/projects/{id}/usage`, `/api/project/usage`; `product.md`: usage monitoring is operational-only, no
billing/metering; `architecture.md`: usage derived from feedback metrics). No `doc-new-version`. Return
`done` on green verification, `blocked` if the DB can't run, or `escalate` with findings if it exceeds a
mid-tier mechanical scope. No commits, no status transitions.
