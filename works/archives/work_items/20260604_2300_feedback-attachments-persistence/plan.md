# Plan

- Work item: works/current/20260604_2300_feedback-attachments-persistence
- Created at: 20260604_2300
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S2
- Slice: feedback_attachments persistence

## Goal

Add the `feedback_attachments` store (table + migration) and its domain/repository/service layer so
later slices can create unlinked attachments (S3), link them through the worker (S4), and read them
(S5). Mirror the `feedback_comments` pattern, but make `feedback_id` nullable for upload-before-link
and add `claimed_user_id`/`claimed_source_product` identity-binding columns.

## Scope

- In scope: `FeedbackAttachmentModel`, Alembic migration off `20260604_2116`, persistence export,
  conftest TRUNCATE, `CreateFeedbackAttachment`/`FeedbackAttachmentRecord` types, repository methods
  (create/get/guarded link/batched list/list/storage-keys), service wrappers +
  `create_feedback_event_with_attachments`, tests, `docs/architecture.md`.
- Out of scope: HTTP upload (S3), capture/queue/worker wiring (S4), reads/downloads (S5).

## Context

- Mirrors `feedback_comments` (`FeedbackCommentModel`, the comments migration, repo
  `_to_comment_record` + `list_comments_for_feedback_ids`, service try/except pattern).
- `expire_on_commit=False` (`db.py`) keeps the record usable after commit in
  `create_feedback_event_with_attachments`.
- The guarded link needs a `claimed_user_id IS NULL` branch because feedback `user_id` is nullable
  and SQL `col = NULL` never matches.

## Milestones

1. Model + nullable-FK cascade + three indexes; export it.
2. Migration `20260604_2305_add_feedback_attachments.py` (single linear head).
3. Domain types + exports.
4. Repository methods + `_to_attachment_record` (guarded `UPDATE ... RETURNING`).
5. Service wrappers + `create_feedback_event_with_attachments` (one txn).
6. conftest TRUNCATE; `tests/test_feedback_attachments.py`.
7. `docs/architecture.md` Feedback Attachment Store section.

## Validation

- `uv run pytest tests/test_feedback_attachments.py -q` green; `uv run alembic heads` single head;
  full `uv run pytest` green.

## Risks / open questions

- Cross-user link integrity: the guarded `feedback_id IS NULL AND claimed_* = ...` UPDATE is the
  security boundary; the anonymous `IS NULL` branch and cross-feedback-theft cases need explicit
  tests.
- Atomicity: event insert + link must share one session/commit; a forced link failure must roll back
  the event.

## Docs to update

- `docs/architecture.md` — Feedback Attachment Store (nullable FK + cascade rationale, `claimed_*`,
  guarded idempotent link, batched read).
