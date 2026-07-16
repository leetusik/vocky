# P3.S2 — `/api/*` project-scoped feedback review + manage (native plan → slice-executor-mid)

Read `works/phases/active/P3/phase.md` (esp. the **P3.S1 outcomes** section — scope contract, read
hook) and `AGENTS.md` first. This is the external-admin-panel path (D-P3-2): a project's `vk_` key
reads + manages **its own project's** feedback over `/api/*`. Heavy reuse of the service verbs already
exercised by `admin_api.py`; the only new logic is per-project scoping. **No schema change.** Write no
commits and make no status transitions.

## New surface — `src/vocky/project_feedback_api.py` (routes under `/api/project/feedback`)

Project is **implicit in the credential** (no project path/query param). Distinct prefix from the
end-user self-read (`GET /api/feedback` stays as-is), so no route collision.

| Method | Path | Service / helper reused |
|---|---|---|
| GET | `/api/project/feedback` | `list_feedback` + `serialize_record` (filters + keyset paging) |
| GET | `/api/project/feedback/{feedback_id}` | `get_feedback_event` + `list_feedback_comments` + `list_feedback_attachments` |
| PATCH | `/api/project/feedback/{feedback_id}` | `update_feedback_event` (review fields only) |
| DELETE | `/api/project/feedback/{feedback_id}` | `delete_feedback_event` (+ best-effort file cleanup) |
| GET | `/api/project/feedback/{feedback_id}/comments` | `list_feedback_comments` |
| POST | `/api/project/feedback/{feedback_id}/comments` | `create_feedback_comment` |
| GET | `/api/project/feedback/{feedback_id}/attachments/{attachment_id}` | `get_admin_attachment` + storage stream |

- Use route prefix **`/api/project/feedback`** (operator-approved).
- **Route order** (Starlette first-match): register `/comments` and `/attachments/{id}` **before** the
  bare `/{feedback_id}` routes, exactly as `admin_api.py:537-559` orders them.

## Handler pattern (the only new logic)

Every handler starts `credential = get_request_credential(request)` (from `vocky.auth`; guaranteed
present on `/api/*`) and scopes to `credential.project_id`:

- **List:** `normalize_list_query(request)` (admin_api's all-optional normalizer), then **force**
  `query.filters.project_id = credential.project_id` (overrides anything in the query; the shared
  `_apply_query_filters` hook from S1 does the WHERE). Serialize with `serialize_record` + `encode_cursor`
  (paging identical to `list_admin_feedback`, `admin_api.py:279-298`).
- **Per-feedback ops:** add a shared helper
  `_load_project_feedback(feedback_id, project_id) -> FeedbackEventRecord | None` = `get_feedback_event`
  then return the record only if `record.project_id == project_id`, else `None`. `None` → **404
  (never 403)** (matches D-P2-5 cross-tenant isolation, so cross-project existence never leaks). Reuse it
  in get / patch / delete / comments / attachment-download.
  - *get-one*: load→404; attach `comments` + `attachments` (attachment `url` =
    `/api/project/feedback/{id}/attachments/{aid}`). Mirror `get_admin_feedback` (`admin_api.py:317-348`).
  - *patch*: reuse `AdminFeedbackPatchInput` + its `model_fields_set` update-building (feedback_value,
    comment, channel, tags, source_metadata, attributes — **no** project_id, it isn't in the model);
    load-and-verify (404) → `update_feedback_event`. Mirror `patch_admin_feedback` (416-458).
  - *delete*: load-and-verify (404) → `delete_feedback_event` → best-effort storage cleanup → 204. Mirror
    `delete_admin_feedback` (504-534).
  - *comment post/list*: reuse `AdminFeedbackCommentInput`; load-and-verify parent (404) → create/list.
    Mirror `post_admin_feedback_comment` (351-387) / `list_admin_feedback_comments` (390-413).
  - *attachment download*: load-and-verify parent feedback (404) → `get_admin_attachment(feedback_id,
    attachment_id)` (linkage-only within the already project-verified feedback → safe) → stream with
    `X-Content-Type-Options: nosniff`. Mirror `download_admin_feedback_attachment` (461-501).

## Reuse strategy (no duplication)

`serialize_record`, `normalize_list_query`, `AdminFeedbackPatchInput`, `AdminFeedbackCommentInput`,
`normalize_tags`, `normalize_admin_channel_write`, `parse_feedback_id`/`parse_attachment_id` currently
live in `admin_api.py` and are pure transport shapes. **Lift `serialize_record` into
`src/vocky/tools/query_feedback_common.py`** (S3's cross-project read reuses it) and re-point
`admin_api.py`'s use; import the remaining helpers/input-models from `admin_api.py` (lifting them too is
fine — your discretion — but **do not copy** the ~30-line serializer). The low-level normalizers/cursor
helpers are already shared in `query_feedback_common.py`. Keep `serialize_record` output as-is (no
`project_id` field needed — the caller knows their project).

## Wiring — `src/vocky/app.py`

`from vocky.project_feedback_api import routes as project_feedback_routes`; splice `*project_feedback_routes`
into `create_app()`'s route list among the `/api/*` routes (order vs `*api_routes` irrelevant — paths
don't overlap). Guarded automatically by the existing `ProjectCredentialAuthMiddleware` (path `/api/…`).

## Tests — `tests/test_project_feedback_api.py` (terse, high-value)

Reuse `configured_project_credential` + `httpx.ASGITransport` Bearer. Mint a **second**
project+credential (small helper via `get_accounts_service()`, mirroring the fixture internals in
`tests/conftest.py`) to prove isolation. Seed feedback with `project_id` set (raw SQL under
`get_engine().begin()`, as existing API tests do):

- list via project-A key → only A's feedback (B excluded); paging cursor works.
- get / patch / delete / comment-post / comment-list / attachment-download on a **project-B** feedback id
  via project-A's key → **404**.
- patch updates a review field; comment add then list; delete → 204 then 404.
- missing/invalid credential → 401 (middleware; one check).

## Verify before returning

- `uv run pytest tests/test_project_feedback_api.py tests/test_admin_api.py` (admin must stay green) —
  real Postgres per `conftest.py`. If the test DB can't run, return `blocked`, don't skip.
- Optionally a quick full `uv run pytest`.

## result.md + phase.md notes; verdict

Write a free-form `result.md`. Append to `phase.md`: the new module + `/api/project/feedback` prefix,
the `_load_project_feedback` + 404-on-cross-project convention (S3/S4 mirror it), where `serialize_record`
now lives (shared in `query_feedback_common.py`), and one **Doc impact** line (`api.md`: new
`/api/project/feedback` review+manage endpoints, project-credential authed; `product.md`/`experience.md`:
external panels can now read+manage their project's feedback by API). No `doc-new-version`.
Return `done` on green verification, `blocked` if the DB can't run, or `escalate` with findings if the
slice exceeds a mid-tier mechanical scope. No commits, no status transitions.
