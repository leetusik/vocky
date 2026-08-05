# Plan — P13.S3: worker post-persist alert hook + DI wiring + failure containment

## Context

Read `works/phases/active/P13/phase.md` first — Decision 2 (swallow-and-log containment; the
notifier call must sit OUTSIDE the persistence `try:` block), the "Codebase facts", and the
P13.S1/P13.S2 notes. S2 landed `src/vocky/notifications.py` with
`FeedbackAlertNotifier.notify_feedback_persisted(record: FeedbackEventRecord | None)` (which itself
silently skips `None` records, `None` project_ids, unconfigured SMTP, and missing owners) and the
`get_feedback_alert_notifier()` factory. This slice wires it into the worker.

**The one real trap:** `_handle_persistence_failure` retries the WHOLE capture job — any exception
escaping the alert path into the persistence retry path re-enqueues an already-persisted event and
creates duplicate feedback rows. Containment must be total.

## Changes (`src/vocky/worker.py` only)

1. `CaptureWorker.__init__` gains a defaulted DI argument:
   `notifier: FeedbackAlertNotifier | None = None` — default `None` means "no alerts", so every
   existing constructor call (tests included) is untouched. Import the type for annotation.

2. `_process_job`:
   - Capture the return value of both persistence calls:
     `record = await self._feedback_service.create_feedback_event_with_attachments(...)` /
     `... = await self._feedback_service.create_feedback_event(...)`. NOTE: the existing worker
     test doubles declare `-> None`, so `record` may be `None` — that must flow through safely
     (the notifier already treats `None` as "nothing to notify").
   - AFTER the existing `try/except FeedbackPersistenceError` block (structurally outside the
     `try:`, after the `except` branch's `return`), add the contained notify step:

     ```python
     if self._notifier is not None:
         try:
             await self._notifier.notify_feedback_persisted(record)
         except Exception:
             logger.exception("Feedback alert failed for job %s", job.request_id)
     ```

     Bare `except Exception` + `logger.exception` + fall through — never re-raise, never touch
     `requeue_job`/`dead_letter_job`. Keep the existing "Persisted accepted capture job" log line
     (order relative to the notify call is your choice; persisting-then-logging-then-notifying
     reads cleanest).

3. `run_worker()`: wire `notifier=get_feedback_alert_notifier()` into the `CaptureWorker(...)`
   constructor call.

No changes to `notifications.py`, `config.py`, or the accounts layer.

## Tests (small — extend `tests/test_worker.py` in place)

House style: fakeredis queue + tiny doubles. Add a small `RecordingNotifier` (records the records
it was called with) and a `BrokenNotifier` (always raises `RuntimeError`). Three cases:

1. Success path: worker with `RecordingNotifier` → notifier called exactly once after persistence
   (called-with-`None` is fine given the existing doubles return `None`).
2. Containment: worker with `BrokenNotifier` → `process_next_job` returns `True`, queue length 0,
   dead-letter length 0 (the alert failure neither requeues nor dead-letters).
3. No-notifier default: existing constructor without `notifier=` still works — implicitly covered
   by every existing test passing unchanged; no new test needed for it. (So: 2 new tests + doubles.)

All existing worker tests must pass UNTOUCHED — if any needs editing, stop and reconsider the hook
shape (that signals the seam is wrong).

## Validation

- `uv run pytest tests/test_worker.py -q`
- `uv run pytest -q` (full suite; needs the test DB — `vocky-postgres-1` on 127.0.0.1:55432 was
  reachable in S1/S2). Report honestly if unreachable.

## Out of scope

- No compose/env plumbing (S4), no bring-up (S5).
- No retry/outbox for failed alerts.
- No notifications.py changes.

## Wrap-up

Write `result.md`; append to `phase.md`: a cross-slice note confirming the end-to-end wiring is
live (env-configured SMTP now sends on every persisted event) and one "Doc impact" line
(`architecture.md`: the worker's post-persist alert hook and its containment rule).
