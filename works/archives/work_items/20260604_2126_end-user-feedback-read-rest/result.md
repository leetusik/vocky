# Result

- Work item: works/current/20260604_2126_end-user-feedback-read-rest
- Created at: 20260604_2126
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.S3
- Slice: end-user feedback read REST
- Review status: pending (P1.REVIEW intentionally deferred at user request)
- Reviewer:
- Next action: User will run `phase review` (P1.REVIEW) later; phase stays `in_progress` until it passes.

## Outcome

Added the scoped public end-user read `GET /api/feedback`:

- `require_scope_value` + `normalize_user_feedback_query` in `api.py`: require non-blank `user_id` AND
  `source_product` (the scoping boundary — never queried unscoped; 400 otherwise), and AND-combine the
  optional basic filters (`feedback_value`, `channel`, `target_type`, `trigger_type`, `conversation_id`,
  `session_id`, `source_integration`, `tag`, `start_ingested_at`/`end_ingested_at`) plus `limit`/`cursor`
  with that mandatory scope. Reuses the existing `query_feedback_common` normalizers + cursor helpers.
- `serialize_user_feedback_record(record, comments)`: the full feedback record shape (matching the
  Admin/MCP contract) plus a `comments` array (`serialize_comment`, oldest-first). Per the user's "proper
  read" steer; `api.py` owns its serializer per the per-transport house convention.
- `FeedbackService.list_feedback_with_comments(query)`: reads the page and its operator comments in one
  session, fetching comments via the batched `list_comments_for_feedback_ids` (no N+1).
- `list_user_feedback` handler: 400 on `FeedbackQueryValidationError`, 500 on `FeedbackReadError`, returns
  `{records, next_cursor?}`. Registered `GET /api/feedback` alongside the existing POST; auto-guarded by
  the existing `APIBearerAuthMiddleware`.
- Shared `parse_int_param` moved from `admin_api.py` to `tools/query_feedback_common.py`; `admin_api.py`
  now imports it (local copy removed — DRY, behavior unchanged).

## Deviations from plan

- None of substance. The `parse_int_param` move was planned; admin tests confirm no behavior change.

## Validation run

- `uv run pytest -q` → 122 passed (full suite). New `tests/test_user_feedback_api.py` (5 tests) covers:
  caller-scope-only (excludes other users and other products) with nested operator comments; missing/blank
  `user_id`→400; missing/blank `source_product`→400; a basic filter (`feedback_value=2`) narrows; cursor
  pagination across two pages; auth required (401 missing/wrong bearer, 200 with the right bearer).
- Migration head single + linear (`alembic heads` = `20260604_2116`); round-trip verified in P1.S1.

## Files changed

- `src/vocky/api.py` — scope helper, query normalizer, public serializer, `list_user_feedback`, GET route,
  imports.
- `src/vocky/feedback/service.py` — `list_feedback_with_comments`.
- `src/vocky/tools/query_feedback_common.py` — shared `parse_int_param`.
- `src/vocky/admin_api.py` — import shared `parse_int_param`; removed the local copy.
- `tests/test_user_feedback_api.py` — new end-user read tests.

## Docs updated

- `docs/product.md` — carved the scoped self-read out of the "no public query endpoints" non-goal; updated
  Product Surface Roles and Product Direction; added `comment` / `operator comment` terminology.
- `docs/api.md` — new "End-User Feedback Read REST API" contract; Status + MVP Surfaces updated.
- `docs/architecture.md` — runtime shape, Three-Track API Shape, and read-path note now include the scoped read.
- `docs/changple5-apply.md` (private) — read endpoint in defaults, a "My Feedback Read (End-User)" wiring
  section, and an operator-comment note under Human/Admin Review.

## Roadmap updates

- P1.S1/S2/S3 all done. P1.REVIEW deferred per user; phase remains `in_progress` and work items remain
  under `works/current/` (no archival until review passes).

## Retrospective

- The scoped read needed no new repository filters — `user_id`/`source_product` were already first-class
  indexed filters — so the slice was mostly a required-scope normalizer + a public serializer + the
  batched comment join. Keeping every optional filter AND-combined with the mandatory scope makes
  cross-user leakage structurally impossible, which the scoping test verifies directly.
