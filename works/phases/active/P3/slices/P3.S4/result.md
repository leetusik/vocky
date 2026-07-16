# P3.S4 result — Usage monitoring (derived + last-used)

## What landed

New module **`src/vocky/usage_api.py`** with three read-only usage surfaces, all
**pure reuse** of `get_feedback_metrics` scoped through the shared
`_apply_query_filters` chokepoint — **no repository change, no new query, no
migration, no new tables** (D-P3-5, operational visibility not billing):

| Method | Path | Auth | Scope | Response |
|---|---|---|---|---|
| GET | `/app/usage` | session (`require_user`) | tenant's projects via `list_projects_for_tenant` → `project_ids`; empty tenant short-circuits to zeroed metrics | `{window, totals, daily_counts, projects:[{id,name,created_at}]}` |
| GET | `/app/projects/{project_id}/usage` | session | one project via `_load_scoped_project` (404 cross-tenant) → `project_id` | `{window, totals, daily_counts, credentials:[serialize_credential]}` |
| GET | `/api/project/usage` | project `vk_` key via `get_request_credential` | the credential's project → `project_id` | `{window, totals, daily_counts, credentials:[serialize_credential]}` |

- **Window:** `_resolve_usage_window` reuses `parse_timestamp` + `validate_time_window`.
  Both bounds optional; defaults to the **last 30 days** ending `utc_now()` when
  both omitted, and fills in the missing bound when only one is given
  (`end`=now, or `start`=`end`-30d).
- **Reuse (no duplication):** `serialize_metrics` imported from `admin_api`
  (the established cross-module pattern — `app_feedback_api` / `project_feedback_api`
  already import helpers from `admin_api`; I did **not** lift the serializers into
  `query_feedback_common.py` to keep churn/risk minimal and admin metrics
  untouched by construction); `serialize_credential` + `_load_scoped_project`
  from `app_api`; `list_projects_for_tenant` / `list_project_credentials` from the
  accounts service; `get_request_credential` from `auth`. Zeroed short-circuit
  reuses `serialize_metrics(_zeroed_metrics(), query)` so the empty-tenant shape
  matches (honors the S3 "never pass an empty id set to a query" convention).
- **Wiring:** `from vocky.usage_api import routes as usage_routes` in `app.py`,
  spliced into `create_app()` after `*app_feedback_routes`. `/app/*` usage routes
  are guarded per-handler by `require_user` (AuthError → app-wide 401);
  `/api/project/usage` is auto-guarded by `ProjectCredentialAuthMiddleware`
  (path `/api/…`). No route-order collision: the `/usage` suffix distinguishes
  `/app/projects/{id}/usage` from `app_api`'s `/app/projects/{id}` and
  `/api/project/usage` from `/api/project/feedback/...`.
- **Surfaces the S1 `last_used_at` stamp:** the per-project surfaces return the
  project's credentials via `serialize_credential`, which carries `last_used_at`
  (stamped best-effort by the ingest middleware, wired in P3.S1).

## Tests — `tests/test_usage_api.py`

Reuses the `/app/*` signup + `POST /app/projects` pattern and the
`configured_project_credential` fixture; seeds feedback via raw SQL with
`project_id` + varied `feedback_value` (1/2/null). Five terse tests:

- `test_app_usage_aggregates_tenant_and_isolates_other` — totals aggregate both
  of the tenant's projects (total=5, liked=3, disliked=1, unrated=1) with the
  correct value split; a second tenant's 5 rows are **not** counted; the
  `projects` list matches; a brand-new tenant with no projects → zeroed totals +
  empty `projects` (short-circuit).
- `test_project_usage_drilldown_credentials_and_cross_tenant_404` — one project's
  totals only (project B excluded); the credentials list surfaces a non-null
  `last_used_at` after `touch_credential_last_used`; a cross-tenant project id → 404.
- `test_api_project_usage_scopes_to_credential_project` — the credential's own
  project totals only (a second same-tenant project's row excluded); credentials listed.
- `test_default_window_covers_last_30_days` — no bounds counts only a row from
  yesterday (a 60-day-old row excluded); an explicit wide window counts both.
- `test_usage_requires_auth` — 401 on each of the three surfaces without a token.

## Validation

| Command | Result |
|---|---|
| `uv run pytest tests/test_usage_api.py tests/test_admin_api.py` | **22 passed** (admin metrics stay green) |
| `uv run pytest` (full suite) | **168 passed** (was 163) |
| `python3 scripts/workflow.py validate` | **passed** |

Ran on the real test Postgres (`configured_database` / `configured_project_credential`
fixtures) — DB available, not blocked.

## Deviations from plan

- The plan offered a choice between lifting the metrics serializers into
  `tools/query_feedback_common.py` (re-pointing `admin_api`) **or** importing them.
  I chose to **import `serialize_metrics` from `admin_api`** — lower churn/risk,
  matches the existing cross-module import pattern, and leaves admin metrics
  untouched by construction. No other deviations.
