# Plan

- Work item: works/current/20260604_2116_operator-comment-store-persistence
- Created at: 20260604_2116
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.S1
- Slice: operator comment store and persistence

## Goal

Introduce the operator-comment store as a new first-class subsystem keyed by feedback id, with the
persistence (model + migration), domain types, repository, and service methods needed by the later HTTP
slices (P1.S2 admin add/list, P1.S3 end-user read). No HTTP surface in this slice.

## Scope

- In scope: `FeedbackCommentModel` + Alembic migration; `CreateFeedbackComment`/`FeedbackCommentRecord`
  domain types + exports; repository `create_feedback_comment`, `list_feedback_comments`,
  batched `list_comments_for_feedback_ids`, `_to_comment_record`; service `create_feedback_comment`,
  `list_feedback_comments`; persistence tests; `docs/architecture.md`.
- Out of scope: any HTTP route or serializer (S2/S3); the combined `list_feedback_with_comments` service
  helper (added in S3); Admin Web UI; MCP; attachments (P2).

## Context

Operator comments are a NEW store, never an overload of the existing user `comment` column. Mirrors the
existing `feedback_events` patterns: `Base` from `vocky.persistence.base`, `utc_now` default, `PG_UUID`,
`DateTime(timezone=True)`, explicit `Index(...)`, hand-written Alembic migration chained off head
`20260429_1620`. Repository/service follow the per-call `async with self._session_maker()` +
`FeedbackPersistenceError`/`FeedbackReadError` wrapping. `feedback_comments.feedback_id` is the repo's
first FK (`ON DELETE CASCADE`), so deleting feedback removes its comments. The batched
`list_comments_for_feedback_ids` exists to avoid N+1 in P1.S3.

## Milestones

1. Add `FeedbackCommentModel` (`feedback_comments`) + `ForeignKey` import in `persistence/models.py`.
2. Add migration `alembic/versions/20260604_2116_add_feedback_comments.py` (down_revision `20260429_1620`).
3. Add `CreateFeedbackComment`/`FeedbackCommentRecord` to `feedback/types.py`; export via `feedback/__init__.py`.
4. Add repository methods + `_to_comment_record`; add service `create_feedback_comment`/`list_feedback_comments`.
5. Tests (create, list oldest-first, empty, FK cascade, batched grouping/empty); update `docs/architecture.md`.
6. Run targeted persistence tests + `alembic upgrade head` against the test DB.

## Validation

- `uv run pytest tests/test_feedback_comments.py -q` passes (create/list/empty/cascade/batched).
- Full migration applies cleanly via the test harness (`alembic upgrade head` in conftest) and round-trips
  (`downgrade -1` then `upgrade head`) against `vocky_test`.
- No HTTP files touched in this slice.

## Risks / open questions

- Operator identity: Vocky has no operator accounts, so `author` is an optional caller-supplied label.
- Same-microsecond `created_at` ties: ordering uses `(created_at, id)` for stable oldest-first output.

## Docs to update

- `docs/architecture.md` — document the `feedback_comments` store (shape, FK CASCADE, indexes).
