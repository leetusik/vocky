# Plan

- Work item: works/current/20260604_2314_async-link-attachments
- Created at: 20260604_2314
- Phase ID: P2
- Phase: Feedback Image Attachments
- Slice ID: P2.S4
- Slice: async-link attachments through capture path

## Goal

Carry `attachment_ids` through the asynchronous capture path so the worker links uploaded
attachments to the feedback row after persist, without putting binaries on the queue and without
breaking attachment-free capture.

## Scope

- In scope: REST capture input `attachment_ids` + `normalize_attachment_ids`, queue
  serialize/deserialize (back-compat), worker `_process_job` branch, capture/queue/worker tests,
  `docs/api.md` + `docs/architecture.md`.
- Out of scope: the `CreateFeedbackEvent.attachment_ids` field and
  `create_feedback_event_with_attachments` (landed in S2); reads/downloads (S5).

## Context

- `_normalize_capture_payload` is shared by MCP and REST. To keep MCP attachment-free, declare
  `attachment_ids` only on `RestCaptureFeedbackInput` and read it via `getattr(raw, ...)`.
- `_serialize_payload` is an explicit allowlist; `_deserialize_payload` uses `.get(key, default)`, so
  adding `attachment_ids` with an empty default keeps in-flight jobs decodable.
- The worker discards the persisted record; branch on `job.payload.attachment_ids`.

## Milestones

1. `RestCaptureFeedbackInput.attachment_ids` + `normalize_attachment_ids` (UUID parse, dedupe, count
   cap) wired into `_normalize_capture_payload`.
2. Queue `_serialize_payload` / `_deserialize_payload` additions.
3. Worker `_process_job` branch.
4. Tests: capture validation (parse/dedupe/non-UUID/too-many/MCP-free), queue round-trip + legacy
   default + string-encoding, worker branch + DB-backed link.
5. Docs.

## Validation

- `uv run pytest tests/test_capture_queue.py tests/test_capture_validation.py tests/test_worker.py -q`
  green; full `uv run pytest` green.

## Risks / open questions

- Silent `attachment_ids` drop between enqueue and worker — guarded by an explicit round-trip test
  and a legacy-default test.
- MCP must not gain attachments — guarded by `test_mcp_capture_is_attachment_free`.

## Docs to update

- `docs/api.md` (`attachment_ids` in capture input + upload-first note),
  `docs/architecture.md` (Async Capture and Attachment Linking).
