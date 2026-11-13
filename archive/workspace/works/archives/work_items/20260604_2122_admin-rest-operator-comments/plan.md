# Plan

- Work item: works/current/20260604_2122_admin-rest-operator-comments
- Created at: 20260604_2122
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.S2
- Slice: admin REST operator-comment endpoints

## Goal

Expose operator add/list of comments through the existing Admin REST review track, and surface a feedback
event's comments in the existing Admin detail payload, built on the P1.S1 store.

## Scope

- In scope: `serialize_comment` (shared, in `tools/query_feedback_common.py`); `AdminFeedbackCommentInput`;
  `POST /admin/api/feedback/{feedback_id}/comments`; `GET /admin/api/feedback/{feedback_id}/comments`;
  `comments` array in `GET /admin/api/feedback/{feedback_id}` detail; route registration; admin tests;
  `docs/api.md` + `docs/architecture.md`.
- Out of scope: Admin Web UI changes; public `/api/*` read (S3); MCP; attachments (P2).

## Context

Reuses the Admin REST idiom in `src/vocky/admin_api.py`: `parse_feedback_id`, `get_feedback_service()`
singleton, `{"detail": ...}` JSON errors (400/404/500), Pydantic input models, `serialize_record`, and the
existing `AdminBearerAuthMiddleware` (no per-route auth). The new routes use a distinct 2-segment path so
there is no ordering conflict with `/admin/api/feedback/{feedback_id}`. `serialize_comment` lives in the
shared `tools/query_feedback_common.py` so S2 (admin) and S3 (public) emit an identical comment shape.

## Milestones

1. Add `serialize_comment(comment) -> {id, author, body, created_at}` to `tools/query_feedback_common.py`.
2. In `admin_api.py`: `AdminFeedbackCommentInput{author?, body}`; `post_admin_feedback_comment`
   (400 bad UUID / bad JSON / blank body; 404 missing parent; 201 `{comment}`); `list_admin_feedback_comments`
   (404 missing parent; 200 `{comments}` oldest-first); include `comments` in the detail handler; register routes.
3. Tests in `tests/test_admin_api.py`: add→201, list oldest-first, missing parent→404 (POST+GET),
   blank body→400, detail includes comments.
4. Docs: `docs/api.md` (Admin operator-comment contract) + `docs/architecture.md` (admin comment surface).
5. Run admin tests.

## Validation

- `uv run pytest tests/test_admin_api.py -q` passes including the new comment cases.
- POST with blank `body` → 400; POST/GET on a missing parent feedback → 404; detail payload carries `comments`.

## Risks / open questions

- Parent-existence check is an explicit `get_feedback_event` (two DB calls for POST) to honor the 404
  contract rather than relying on an FK violation surfacing as a 500.

## Docs to update

- `docs/api.md` — operator-comment add/list contract under Admin Feedback REST API.
- `docs/architecture.md` — note the Admin operator-comment surface over the new store.
