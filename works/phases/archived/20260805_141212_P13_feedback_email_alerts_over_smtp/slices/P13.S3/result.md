# Result — P13.S3: worker post-persist alert hook + DI wiring + failure containment

## What changed

`src/vocky/worker.py` only, exactly per plan:

1. `CaptureWorker.__init__` gained a defaulted DI arg `notifier: FeedbackAlertNotifier | None = None`,
   stored as `self._notifier`. Import added: `from vocky.notifications import FeedbackAlertNotifier,
   get_feedback_alert_notifier`.
2. `_process_job` now captures the return value of both persistence calls into `record` (was
   discarded before). After the existing `try/except FeedbackPersistenceError` block and its
   "Persisted accepted capture job" info log, a new contained block:
   ```python
   if self._notifier is not None:
       try:
           await self._notifier.notify_feedback_persisted(record)
       except Exception:
           logger.exception("Feedback alert failed for job %s", job.request_id)
   ```
   This sits structurally outside the persistence `try:` — it can only run after that block has
   already returned successfully (the `except FeedbackPersistenceError` branch `return`s before
   reaching it) — and it never calls `requeue_job`/`dead_letter_job`. Bare `except Exception` +
   `logger.exception` + fall through, matching Decision 2 exactly.
3. `run_worker()` now passes `notifier=get_feedback_alert_notifier()` into the `CaptureWorker(...)`
   constructor call, alongside the existing `queue=` / `feedback_service=` args.

`tests/test_worker.py`: added two tiny doubles (`RecordingNotifier` — records the records it's
called with; `BrokenNotifier` — always raises `RuntimeError`) and two new async tests:

- `test_worker_notifies_after_persist` — `RecordingNotifier` is called exactly once, with `None`
  (the existing `RecordingFeedbackService.create_feedback_event` doubles return `None`, so this
  exercises the plan's expected "record may be `None`, must flow through safely" path).
- `test_worker_contains_notifier_failure` — `BrokenNotifier` raises on every call;
  `process_next_job` still returns `True`, and both the queue and dead-letter list stay empty after
  processing, proving the alert failure never reaches `requeue_job`/`dead_letter_job`.

All six pre-existing worker tests were left byte-for-byte untouched — no double's signature or
behavior needed to change, confirming (per the plan's own signal) that the hook shape is right.

## Validation

- `uv run pytest tests/test_worker.py -q` → **8 passed** (6 pre-existing + 2 new), no changes to
  existing test code.
- `uv run pytest -q` (full suite, live Postgres reachable at `127.0.0.1:55432`, confirmed with
  `nc -z` before running) → **225 passed** (S2 baseline was 223; +2 matches exactly the two new
  worker tests, nothing else moved).

## Deviations from plan.md

None. Followed the plan's exact code shape, DI signature, containment structure, and test scope
(no doubles/scaffolding beyond the two named in the plan, no edits to `notifications.py`,
`config.py`, or the accounts layer).

## Doc impact

Recorded as a one-line note in `phase.md`'s "Doc impact" list (see phase notes below) —
`architecture.md` gains a description of the worker's post-persist alert hook and its swallow-and-
log containment rule. No `doc-new-version` run here (middle-slice rule; `P13.REVIEW` consolidates).
