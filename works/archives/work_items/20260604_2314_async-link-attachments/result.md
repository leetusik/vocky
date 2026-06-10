# Result

- Work item: works/current/20260604_2314_async-link-attachments
- Created at: 20260604_2314
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S4
- Slice: async-link attachments through capture path
- Review status: pending
- Reviewer:
- Next action: Implement P2.S5 (attachment exposure in reads + scoped downloads + delete-on-delete).

## Outcome

Carried `attachment_ids` through the async capture path:

- `src/vocky/capture.py`: `RestCaptureFeedbackInput.attachment_ids: list[str] | None`;
  `normalize_attachment_ids` (parse each to UUID → `CaptureFeedbackValidationError` on non-UUID,
  dedupe, cap at `attachments_max_count`); wired into the shared `_normalize_capture_payload` via
  `getattr(raw, "attachment_ids", None)` so MCP capture (no such field) stays attachment-free.
- `src/vocky/capture_queue.py`: `_serialize_payload` emits `attachment_ids` as a list of string
  UUIDs; `_deserialize_payload` rebuilds `tuple(UUID(x) for x in raw.get("attachment_ids", []))` —
  the `.get(..., [])` default keeps jobs serialized before this change decodable.
- `src/vocky/worker.py` `_process_job`: branches to `create_feedback_event_with_attachments` when
  `job.payload.attachment_ids` is non-empty, else the unchanged `create_feedback_event`; retry /
  dead-letter semantics untouched.

## Deviations from plan

- The `CreateFeedbackEvent.attachment_ids` field and `create_feedback_event_with_attachments`
  service method were implemented in S2 (the method consumes the field), so this slice did not need
  to add them — only the capture-input field, normalizer, queue plumbing, and worker branch, as the
  plan anticipated.

## Validation run

- `uv run pytest tests/test_capture_queue.py tests/test_capture_validation.py tests/test_worker.py
  -q` → 35 passed, including: queue round-trip preserves `attachment_ids`; `serialize_job` encodes
  them as string UUIDs (no bytes); legacy job without the key → `()`; capture parse + dedupe;
  non-UUID → 400-mapped error; too-many → error; MCP capture attachment-free; worker chooses the
  with-attachments path only when ids are present; worker links a real attachment on persist
  (DB-backed).
- `uv run pytest -q` → 160 passed (150 prior + 10 new; no regressions).

## Files changed

- `src/vocky/capture.py` (`attachment_ids` field, `normalize_attachment_ids`, wiring, `get_settings`
  import)
- `src/vocky/capture_queue.py` (serialize/deserialize `attachment_ids`)
- `src/vocky/worker.py` (`_process_job` branch)
- `tests/test_capture_queue.py`, `tests/test_capture_validation.py`, `tests/test_worker.py`

## Docs updated

- `docs/api.md` — `attachment_ids` in the Web Feedback Capture REST input + upload-first/link-later
  note.
- `docs/architecture.md` — new **Async Capture and Attachment Linking** section (upload-first; only
  UUID strings on the queue; back-compat; scope-verified worker link; never dead-letter a missing
  screenshot).

## Roadmap updates

- `P2.S4` done. Next slice `P2.S5` (reads + downloads + delete-on-delete). Phase P2 stays
  `in_progress`.

## Retrospective

- The load-bearing risk was the silent drop of `attachment_ids` between enqueue and worker; pinning
  it with an explicit serialize-to-strings test plus a legacy-default decode test makes the
  queue-contract change safe. Keeping the field off the MCP input (shared normalizer + `getattr`)
  honored "MCP stays attachment-free" without forking the normalizer.
