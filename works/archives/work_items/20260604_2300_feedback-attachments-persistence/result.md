# Result

- Work item: works/current/20260604_2300_feedback-attachments-persistence
- Created at: 20260604_2300
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S2
- Slice: feedback_attachments persistence
- Review status: pending
- Reviewer:
- Next action: Implement P2.S3 (synchronous attachment upload endpoint).

## Outcome

Added the `feedback_attachments` store and its domain/repo/service layer, mirroring
`feedback_comments` but with a nullable `feedback_id` for upload-before-link:

- `FeedbackAttachmentModel` (`src/vocky/persistence/models.py`): nullable `feedback_id` FK→
  `feedback_events.id` `ON DELETE CASCADE`; `storage_key`/`content_type`/`claimed_source_product`
  Text NN; `byte_size` Integer NN; `filename`/`claimed_user_id` nullable; tz-aware `created_at`;
  indexes `ix_feedback_attachments_feedback_id`, `ix_feedback_attachments_feedback_id_created_at`,
  `ix_feedback_attachments_created_at` (D3 sweep). Exported from `persistence/__init__.py`.
- Migration `alembic/versions/20260604_2305_add_feedback_attachments.py` (`down_revision =
  "20260604_2116"`) — single linear head `20260604_2305`.
- Types `CreateFeedbackAttachment` / `FeedbackAttachmentRecord` (`src/vocky/feedback/types.py`),
  exported via `feedback/__init__.py`.
- Repository (`src/vocky/feedback/repository.py`): `create_feedback_attachment`,
  `get_feedback_attachment`, `link_attachments_to_feedback` (guarded `UPDATE ... RETURNING` with the
  `claimed_user_id IS NULL` branch for anonymous feedback; dedupes ids; logs skipped; returns linked
  count; `synchronize_session=False`), batched `list_attachments_for_feedback_ids`,
  `list_feedback_attachments`, `list_storage_keys_for_feedback`, `_to_attachment_record`.
- Service (`src/vocky/feedback/service.py`): `create_unlinked_attachment`,
  `create_feedback_event_with_attachments` (event insert + guarded link in one session/commit),
  `get_feedback_attachment`, `list_feedback_attachments`.
- `tests/conftest.py` TRUNCATE extended with `feedback_attachments` (both pre/post).

## Deviations from plan

- Added `attachment_ids: tuple[UUID, ...] = ()` to `CreateFeedbackEvent` in this slice (the backlog
  scheduled that field under P2.S4). Rationale: `create_feedback_event_with_attachments` (an S2
  deliverable) reads `payload.attachment_ids`, and the S2 rollback/link tests construct a
  `CreateFeedbackEvent` carrying ids. The carrier field belongs with the method that consumes it;
  S4 still owns the capture-input field, the normalizer, the queue serialize/deserialize, and the
  worker branch. The field defaults to `()`, so this is forward-compatible and changes no behavior
  for attachment-free events.
- `tests/test_persistence.py::test_migration_applies_and_expected_indexes_exist` hard-codes the head
  revision; updated `20260604_2116` → `20260604_2305`. The asserted `feedback_events` index list is
  unchanged.

## Validation run

- `uv run pytest tests/test_feedback_attachments.py -q` → 12 passed (create unlinked; get unknown→
  None; link matching scope; idempotent re-link→0; scope mismatch skipped; cross-feedback theft
  blocked; anonymous IS-NULL link; create-with-attachments links; create-with-attachments rolls back
  on forced link failure leaving event unwritten + attachment unlinked; batched list oldest-first +
  empty→{}; storage-key listing; FK cascade on delete).
- `uv run alembic heads` → single head `20260604_2305`.
- `uv run pytest -q` → 143 passed (131 prior + 12 new; no regressions).

## Files changed

- `src/vocky/persistence/models.py` (FeedbackAttachmentModel)
- `src/vocky/persistence/__init__.py` (export)
- `src/vocky/feedback/types.py` (CreateFeedbackAttachment, FeedbackAttachmentRecord, +attachment_ids
  on CreateFeedbackEvent)
- `src/vocky/feedback/__init__.py` (exports)
- `src/vocky/feedback/repository.py` (attachment methods + mapper, `update`/`logging` imports)
- `src/vocky/feedback/service.py` (attachment service methods)
- `alembic/versions/20260604_2305_add_feedback_attachments.py` (new)
- `tests/conftest.py` (TRUNCATE), `tests/test_persistence.py` (head revision)
- `tests/test_feedback_attachments.py` (new, 12 tests)

## Docs updated

- `docs/architecture.md` — added the **Feedback Attachment Store** section (nullable-FK + cascade
  rationale, `claimed_*` identity-binding, guarded idempotent link, batched read).

## Roadmap updates

- `P2.S2` done. Next slice `P2.S3` (synchronous attachment upload endpoint). Phase P2 stays
  `in_progress`.

## Retrospective

- The nullable-`feedback_id`-but-cascade shape is the crux: it lets uploads exist before capture
  persists while still cleaning up linked rows on delete. The guarded `RETURNING` update gives both
  idempotency (`feedback_id IS NULL`) and observability (which ids were skipped) in one round trip,
  and the anonymous `IS NULL` branch is the easy-to-miss correctness detail that the dedicated test
  pins down.
