# Plan

- Work item: works/current/20260604_2126_end-user-feedback-read-rest
- Created at: 20260604_2126
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.S3
- Slice: end-user feedback read REST

## Goal

Add a scoped public read `GET /api/feedback` that returns a single end user's own feedback (strictly scoped
by required `user_id` + `source_product`) together with operator comments, with basic filters and cursor
pagination. This deliberately expands the previously capture-only public REST surface.

## Scope

- In scope: shared `parse_int_param` in `tools/query_feedback_common.py` (admin_api imports it, drops its
  local copy); `FeedbackService.list_feedback_with_comments`; `GET /api/feedback` handler + scoped query
  normalizer + public serializer in `src/vocky/api.py`; new `tests/test_user_feedback_api.py`;
  `docs/product.md`, `docs/api.md`, `docs/architecture.md`, private `docs/changple5-apply.md`.
- Out of scope: Admin Web UI; MCP; attachments (P2); any cross-user read.

## Context

`user_id` and `source_product` are already indexed columns and already supported by `FeedbackQueryFilters` /
`_apply_query_filters`, so the scoped read needs no new filters — only a required-scope normalizer. Every
filter is AND-combined with the mandatory scope, so the caller can never read another user's or product's
records. Reuses `normalize_limit` / `decode_cursor` / `encode_cursor` / `serialize_datetime` / the filter
normalizers from `tools/query_feedback_common.py`, the batched `list_comments_for_feedback_ids` from P1.S1
(no N+1), and `serialize_comment` from P1.S2. `APIBearerAuthMiddleware` guards all `/api/*` methods, so the
new GET is auto-protected by `VOCKY_API_AUTH_TOKEN`.

Per the user's steer, the read returns the **full** feedback record shape + a `comments` array (matching the
Admin/MCP record contract; new `api.py`-owned serializer per house convention) and supports **basic filters**:
`feedback_value`, `channel`, `target_type`, `trigger_type`, `conversation_id`, `session_id`,
`source_integration`, `tag`, and the `start_ingested_at` / `end_ingested_at` window.

## Milestones

1. Move `parse_int_param` to `tools/query_feedback_common.py`; update `admin_api.py` to import it.
2. Add `FeedbackService.list_feedback_with_comments(query)` (one session: list page + batched comments).
3. In `api.py`: `require_scope_value`; `normalize_user_feedback_query` (required `user_id`+`source_product`,
   optional basic filters + limit/cursor); `serialize_user_feedback_record(record, comments)` (full shape +
   `comments`); `list_user_feedback` handler (400 on validation, 500 on `FeedbackReadError`); register the GET.
4. New `tests/test_user_feedback_api.py`: scoping (only caller's records; excludes other users/products),
   comments included, missing/blank `user_id`→400, missing/blank `source_product`→400, a basic filter narrows,
   pagination, auth required (401).
5. Docs: `product.md`, `api.md`, `architecture.md`, private `changple5-apply.md`.
6. Run the new tests + the public-access/capture suites.

## Validation

- `uv run pytest tests/test_user_feedback_api.py tests/test_public_access.py tests/test_capture_api.py -q` passes.
- Scope enforcement verified: a record under a different `user_id` or `source_product` never appears; omitting
  either required param → 400; pagination returns a working `next_cursor`; a wrong/absent bearer → 401.

## Risks / open questions

- Full record shape echoes operator-review fields (`channel`, `tags`) and internal JSON blobs back to the
  trusted server-to-server caller. Accepted per the user's "proper read" steer; the caller already owns this
  data and the scope guarantees same-user-only results.

## Docs to update

- `docs/product.md` — carve a scoped self-read out of the "no public query endpoints" non-goal.
- `docs/api.md` — new "End-User Feedback Read" contract.
- `docs/architecture.md` — new public read surface over the shared store.
- `docs/changple5-apply.md` (private) — operator-comment note + "My Feedback" server-side wiring.
