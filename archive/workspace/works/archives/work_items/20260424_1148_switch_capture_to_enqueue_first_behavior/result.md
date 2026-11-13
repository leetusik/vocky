# Result

- Work item: works/current/20260424_1148_switch_capture_to_enqueue_first_behavior
- Created at: 20260424_1148
- Phase ID: P1
- Phase: Async capture pipeline and self-hosted operator runbook
- Slice ID: P1.S3
- Slice: switch capture to enqueue-first behavior
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.S4` to update smoke, README, and self-hosted operator guidance for the new eventual-consistency workflow.

## Summary

Switched `capture_feedback` from synchronous database persistence to queue acceptance and updated the capture-focused tests to validate the new receipt contract and queue-failure behavior.

## Changes Made

- Replaced the direct feedback-service write in `src/vocky/tools/capture_feedback.py` with Redis queue acceptance through the shared capture queue.
- Changed the MCP success payload to `request_id`, `accepted_at`, and `status`.
- Mapped queue failures to the MCP tool error `capture queue unavailable`.
- Updated capture-side MCP integration tests to use fake Redis and assert the queued job contains the normalized payload the worker will later persist.

## Files Changed

- `src/vocky/tools/capture_feedback.py`
- `tests/test_mcp_integration.py`
- `works/backlog.md`
- `works/current/20260424_1148_switch_capture_to_enqueue_first_behavior/plan.md`
- `works/current/20260424_1148_switch_capture_to_enqueue_first_behavior/result.md`

## Verification Performed

- Ran `uv run pytest tests/test_capture_validation.py tests/test_capture_queue.py tests/test_worker.py tests/test_mcp_integration.py -k 'capture_feedback or test_blank_message_is_rejected or test_blank_source_product_is_rejected or test_naive_event_at_is_rejected or test_blank_tag_is_rejected or test_duplicate_tags_are_rejected_after_normalization or test_json_metadata_is_accepted_and_event_at_is_normalized or test_enqueue_and_pop_round_trip_preserves_payload or test_dead_letter_job_records_failure_context or test_worker_requeues_then_persists_after_transient_failure or test_worker_dead_letters_after_max_attempts or test_worker_returns_false_when_queue_is_empty'`.

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Update smoke and operator docs so verification waits for background persistence instead of assuming immediate read-after-write visibility.

## Commit References

- None.
