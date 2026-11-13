# Result

- Work item: works/current/20260604_2116_operator-comment-store-persistence
- Created at: 20260604_2116
- Phase ID: P1
- Phase: Client Feedback REST — Operator Comments and End-User Read
- Slice ID: P1.S1
- Slice: operator comment store and persistence
- Review status: pending
- Reviewer:
- Next action: Implement P1.S2 (Admin REST operator-comment endpoints).

## Outcome

Shipped the operator-comment store as a new first-class subsystem, no HTTP surface:

- `FeedbackCommentModel` (`feedback_comments`: `id` UUID PK, `feedback_id` UUID FK→`feedback_events.id`
  `ON DELETE CASCADE`, `author` Text null, `body` Text not null, `created_at` tz-aware default
  `utc_now`/`CURRENT_TIMESTAMP`) with indexes on `feedback_id` and `(feedback_id, created_at)`.
- Alembic migration `20260604_2116_add_feedback_comments` (down_revision `20260429_1620`, the prior head),
  round-trips cleanly (`downgrade -1` then `upgrade head` verified against `vocky_test`).
- Domain types `CreateFeedbackComment` / `FeedbackCommentRecord` in `feedback/types.py`, exported from
  `feedback/__init__.py`.
- Repository `create_feedback_comment`, `list_feedback_comments` (oldest-first by `(created_at, id)`),
  batched `list_comments_for_feedback_ids` (groups by feedback id, `{}` on empty input — avoids N+1 in S3),
  and `_to_comment_record`.
- Service `create_feedback_comment` (`FeedbackPersistenceError` wrapping) and `list_feedback_comments`
  (`FeedbackReadError` wrapping), following the existing per-call session pattern.

## Deviations from plan

- Also updated `tests/conftest.py` and `tests/test_persistence.py` (not pre-listed but required by the FK):
  - The `configured_database` fixture truncated only `feedback_events`. Postgres refuses to `TRUNCATE` a
    table referenced by a foreign key (even when the child is empty), so the new FK would have broken every
    test using the fixture. Changed both truncations to `TRUNCATE TABLE feedback_events, feedback_comments`.
  - `test_migration_applies_and_expected_indexes_exist` asserted the head revision `20260429_1620`; updated
    to `20260604_2116` since this slice moves the head.

## Validation run

- `uv run pytest tests/test_feedback_comments.py tests/test_persistence.py -q` → 13 passed.
- Migration round-trip on `vocky_test`: `alembic current` = head, `downgrade -1`, `upgrade head` all clean;
  verified `feedback_comments` columns `[author, body, created_at, feedback_id, id]`, indexes
  `[ix_feedback_comments_feedback_id, ix_feedback_comments_feedback_id_created_at, pk_feedback_comments]`,
  and FK `fk_feedback_comments_feedback_id_feedback_events`.
- New tests cover: field persistence (with/without author), oldest-first ordering (seeded out of order),
  empty list → `()`, FK cascade on feedback delete (2 → 0 rows), batched grouping + `{}` for `[]`.

## Files changed

- `src/vocky/persistence/models.py` — `ForeignKey` import + `FeedbackCommentModel`.
- `alembic/versions/20260604_2116_add_feedback_comments.py` — new migration.
- `src/vocky/feedback/types.py` — `CreateFeedbackComment`, `FeedbackCommentRecord`.
- `src/vocky/feedback/__init__.py` — export the new types.
- `src/vocky/feedback/repository.py` — comment create/list/batched methods + `_to_comment_record`.
- `src/vocky/feedback/service.py` — `create_feedback_comment`, `list_feedback_comments`.
- `tests/test_feedback_comments.py` — new persistence tests.
- `tests/conftest.py` — truncate `feedback_comments` alongside `feedback_events`.
- `tests/test_persistence.py` — updated expected head revision.

## Docs updated

- `docs/architecture.md` — new "Operator Comment Store" section (table shape, FK CASCADE, indexes,
  oldest-first reads, batched fetch rationale).

## Roadmap updates

- P1.S1 done. P1.S2 (admin comment endpoints) and P1.S3 (end-user read) can both build on this store.

## Retrospective

- The only non-obvious work was the conftest truncation: the first FK in the repo changes Postgres
  TRUNCATE semantics for `feedback_events`. Catching it before running the suite avoided a broad,
  confusing regression across unrelated test files.
