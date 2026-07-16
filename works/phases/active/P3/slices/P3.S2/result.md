# P3.S2 result — `/api/*` project-scoped feedback review + manage

## Outcome: done

Added the external-admin-panel path (D-P3-2): a project's `vk_` credential can now
read and manage **its own project's** feedback over `/api/project/feedback`, porting
the operator verbs from `admin_api.py`. The only new logic is per-project scoping;
no schema change.

## What landed

- **New module `src/vocky/project_feedback_api.py`** — routes under
  `/api/project/feedback`, guarded automatically by the existing
  `ProjectCredentialAuthMiddleware` (path is `/api/…`). Project is implicit in the
  credential (no path/query param). Endpoints:
  - `GET /api/project/feedback` — list (filters + keyset paging).
  - `GET /api/project/feedback/{id}` — get-one (+ `comments` + `attachments`,
    attachment `url` = `/api/project/feedback/{id}/attachments/{aid}`).
  - `PATCH /api/project/feedback/{id}` — review fields only (feedback_value,
    comment, channel, tags, source_metadata, attributes).
  - `DELETE /api/project/feedback/{id}` — delete + best-effort file cleanup → 204.
  - `GET|POST /api/project/feedback/{id}/comments` — operator comments list/add.
  - `GET /api/project/feedback/{id}/attachments/{aid}` — download (`X-Content-Type-Options: nosniff`).
  - Route order: `/comments` and `/attachments/{id}` registered **before** the bare
    `/{feedback_id}` routes, mirroring `admin_api.py`.
- **Scoping:** every handler starts `credential = get_request_credential(request)`.
  - List **forces** `query.filters.project_id = credential.project_id` (overrides any
    caller-supplied value); the shared `_apply_query_filters` hook from S1 does the WHERE.
  - Per-feedback ops go through a shared `_load_project_feedback(feedback_id,
    project_id)` helper = `get_feedback_event` then return the record only if
    `record.project_id == project_id`, else `None`. `None` → **404 (never 403)**, so
    cross-project existence never leaks (matches D-P2-5). Reused in get / patch /
    delete / comment post+list / attachment-download. For patch/delete/attachment the
    ownership check runs before any mutation or `get_admin_attachment` linkage read.
- **Reuse (no duplication):** lifted `serialize_record` into
  `src/vocky/tools/query_feedback_common.py` (S3's cross-project read reuses it) and
  re-pointed `admin_api.py` to import it (removed its local copy + the now-unused
  `FeedbackEventRecord` import). The remaining transport helpers/input-models
  (`normalize_list_query`, `AdminFeedbackPatchInput`, `AdminFeedbackCommentInput`,
  `normalize_tags`, `normalize_admin_channel_write`, `parse_feedback_id`,
  `parse_attachment_id`) are imported from `admin_api.py`; low-level
  normalizers/cursor helpers come from `query_feedback_common.py`. `serialize_record`
  output is unchanged (no `project_id` field — the caller knows its project).
- **Wiring:** `app.py` imports `project_feedback_routes` and splices
  `*project_feedback_routes` into `create_app()`'s route list (paths don't overlap
  `*api_routes`, so order is irrelevant).

## Tests — `tests/test_project_feedback_api.py` (terse, high-value)

Uses `configured_project_credential` + `httpx.ASGITransport` Bearer, mints a **second**
project+credential under the same tenant (`_mint_project_credential` via
`get_accounts_service()`) to prove isolation, seeds feedback with `project_id` via raw
SQL under `get_engine().begin()`.

- `test_list_scopes_to_credential_project_and_paginates` — project-A key lists only A's
  rows (B excluded), newest-first; `limit=1` + cursor paging walks both A rows; response
  records omit `project_id`.
- `test_cross_project_feedback_returns_404_never_403` — get / patch / delete /
  comment-post / comment-list / attachment-download on a **project-B** feedback id via
  project-A's key all return **404**; asserts the B row is untouched (delete didn't fire).
- `test_patch_comment_and_delete_own_feedback` — patch a review field (feedback_value
  2→1, comment trimmed); comment add (author/body trimmed) then list; get-one nests the
  comment; delete → 204 then get → 404.
- `test_missing_or_invalid_credential_returns_401` — missing and bogus Bearer → 401;
  valid → 200 (one middleware check).

## Validation

- `uv run pytest tests/test_project_feedback_api.py tests/test_admin_api.py` — **21 passed**
  (4 new + 17 admin; admin stayed green after the `serialize_record` move).
- `uv run pytest` (full suite) — **160 passed** (confirms the shared-serializer lift
  didn't break `api.py` / other importers).
- `python3 scripts/workflow.py validate` — **passed**.
- `ruff` is not installed in this environment; cleaned obvious unused names by hand.

## Deviations from plan

None. The plan noted `project_id` scoping "in `_apply_query_filters`" as S2 work, but
S1 had already added that hook (per the P3.S1 outcomes note), so S2 only sets
`query.filters.project_id` from the credential — no repository change was needed.
