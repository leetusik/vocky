# Plan

- Work item: works/current/20260604_2027_decompose-client-feedback-rest
- Created at: 20260604_2027
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Break phase P1 into concrete, dependency-ordered middle slices that deliver (a) operator-authored comments on feedback and (b) a scoped end-user REST read of a user's own feedback plus those comments — then record those slices in `works/backlog.md` between `P1.DECOMP` and `P1.REVIEW`. No production code in this slice; only analysis and backlog edits.

## Scope

- In scope: analyze the existing capture/read/persist patterns, design the middle slices, write them into `works/backlog.md`, set P1 `in_progress`, mark `P1.DECOMP` done.
- Out of scope: implementing any middle slice; touching `src/`, `alembic/`, `tests/`, or `docs/`; image attachments (phase P2).

## Context

Grounded in the current codebase (read during this slice):

- Single store `feedback_events` (`src/vocky/persistence/models.py`); `user_id` and `source_product` are already first-class indexed columns and already supported read filters (`FeedbackQueryFilters`, `_apply_query_filters` in `src/vocky/feedback/repository.py`).
- Read path: `FeedbackRepository.list_feedback` does newest-first `(ingested_at desc, id desc)` cursor pagination; Admin REST `GET /admin/api/feedback` (`src/vocky/admin_api.py`) reuses it via `normalize_list_query` + `serialize_record` + `encode_cursor`. Cursor/limit helpers live in `vocky.tools.query_feedback_common`.
- Service layer (`src/vocky/feedback/service.py`) wraps the repo per-call in `get_session_maker()` sessions with `FeedbackPersistenceError` / `FeedbackReadError`. Domain types are dataclasses in `src/vocky/feedback/types.py`, exported via `src/vocky/feedback/__init__.py`.
- Public REST today is capture-only: `src/vocky/api.py` exposes only `POST /api/feedback`. Auth is path-prefix bearer middleware in `src/vocky/auth.py` wired in `src/vocky/app.py` (`APIBearerAuthMiddleware` for `/api/*`, `AdminBearerAuthMiddleware` for `/admin/api/*`).
- The existing `comment` column is the end user's own comment captured at feedback time and is operator-editable via `PATCH`; operator comments must be a NEW separate store, not an overload of `comment`.
- Tests use pytest + `httpx.ASGITransport` + `fakeredis` with a real migrated Postgres test DB (`tests/conftest.py`, `tests/test_admin_api.py`, `tests/test_public_access.py`).

## Milestones

1. Confirm the slice breakdown and dependency order (S1 persistence → S2 operator HTTP → S3 end-user HTTP), each naming exact files, behavior, and edge cases.
2. Insert `P1.S1`, `P1.S2`, `P1.S3` into `works/backlog.md` between `P1.DECOMP` and `P1.REVIEW`; set P1 `Status: in_progress`; set P1 work items to this folder; mark `P1.DECOMP` `[x]` / done with a summary note.
3. Fill `result.md` and stop (do not start `P1.S1`).

### Planned middle slices (recorded into the backlog by this slice)

- **P1.S1 — Operator comment store + persistence.** New `FeedbackCommentModel` (`feedback_comments`: `id` UUID PK, `feedback_id` UUID FK→`feedback_events.id` ON DELETE CASCADE, `author` Text nullable, `body` Text not null, `created_at` tz-aware default `utc_now`/`CURRENT_TIMESTAMP`; index on `feedback_id`, `(feedback_id, created_at)`) in `src/vocky/persistence/models.py` + Alembic migration mirroring `alembic/versions/20260429_1620_*`. New domain types `CreateFeedbackComment` / `FeedbackCommentRecord` in `feedback/types.py` (export via `feedback/__init__.py`). Repository: `create_feedback_comment`, `list_feedback_comments(feedback_id)` (oldest-first), and batched `list_comments_for_feedback_ids(ids)` (to avoid N+1 in S3) + `_to_comment_record`. Service: `create_feedback_comment`, `list_feedback_comments` with existing error wrapping. Tests for create/list ordering, FK cascade on feedback delete, empty list. Docs: `architecture.md` (new store). No HTTP.
- **P1.S2 — Admin REST operator-comment endpoints.** In `src/vocky/admin_api.py`: `AdminFeedbackCommentInput` (`author?`, `body`), `serialize_comment`, `POST /admin/api/feedback/{feedback_id}/comments` (required non-blank `body`, trimmed optional `author`; 404 if parent missing; 201 `{comment}`), `GET /admin/api/feedback/{feedback_id}/comments` (404 if parent missing; 200 `{comments}` oldest-first), and include `comments` in the existing `GET /admin/api/feedback/{feedback_id}` detail payload. Register routes; auth via existing `AdminBearerAuthMiddleware`. Tests in `tests/test_admin_api.py` (add→201, list order, missing parent→404, blank body→400, detail includes comments). Docs: `api.md` (Admin operator-comment contract), `architecture.md`.
- **P1.S3 — End-user feedback read REST.** In `src/vocky/api.py`: `GET /api/feedback` handler requiring non-blank `user_id` AND `source_product` query params (400 if either missing/blank — the security boundary, never query unscoped), optional `limit`/`cursor` (reuse `normalize_limit`/`decode_cursor`/`encode_cursor`), building `ListFeedbackQuery(filters=FeedbackQueryFilters(user_id=…, source_product=…))`, returning `{records, next_cursor?}` with each record including its operator `comments` (batched via S1's `list_comments_for_feedback_ids`); public serializer; 500 on `FeedbackReadError`. Confirm `APIBearerAuthMiddleware` guards GET. New service helper to fetch a page with comments. Tests in new `tests/test_user_feedback_api.py` (only caller's `user_id`+`source_product`; excludes other users/products; includes comments; missing `user_id`→400; missing `source_product`→400; pagination; auth required). Docs: `product.md` (carve scoped self-read out of the "no public query endpoints" boundary), `api.md` (new End-User Read section), `architecture.md`, and `docs/changple5-apply.md` (private handoff: operator page + "my feedback" wiring).

## Validation

- `works/backlog.md` parses; P1 now lists `P1.DECOMP` (done), `P1.S1`, `P1.S2`, `P1.S3` (todo), `P1.REVIEW` (todo) in order; P1 `Status: in_progress`; work item linked.
- Each middle slice names exact files, expected behavior, and edge cases (concreteness bar from CLAUDE.md).
- No `src/`, `alembic/`, `tests/`, or `docs/` files changed by this slice.

## Risks / open questions

- Operator identity: Vocky has no operator accounts, so `author` is a caller-supplied label (the integrating product's operator id/name), optional for MVP. Flagged for S2; not a blocker.
- Slice granularity: S1 is persistence-only (no user-visible surface) but is independently unit-tested and consumed by S2/S3; kept separate for cleaner review boundaries.
- S3 expands the public REST surface (currently capture-only) — a deliberate product-scope change S3 must reflect in `product.md`.

## Docs to update

- None in this slice. Doc updates happen inside the middle slices: `architecture.md` (S1, S2, S3), `api.md` (S2, S3), `product.md` (S3), `docs/changple5-apply.md` (S3, private).
