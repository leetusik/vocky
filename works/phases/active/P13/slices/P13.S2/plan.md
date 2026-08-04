# Plan — P13.S2: SMTP settings + feedback alert notifier module

## Context

Read `works/phases/active/P13/phase.md` first — especially Decision 1 (stdlib `smtplib` in
`asyncio.to_thread`, no new dependency), Decision 2 (containment lives in S3, but the notifier must
be safe to call), the "Codebase facts", and the P13.S1 notes (the accounts primitive to call is
`AccountsService.get_owner_email_for_project(project_id) -> str | None`).

This slice lands the notifier as an inert module — no worker wiring (that's S3). Two deliverables:
the `VOCKY_SMTP_*` settings block and the notifier module.

## 1. Settings (`src/vocky/config.py`)

Add to `Settings`, following the existing alias style (see `admin_auth_token` at config.py:39 and
its `admin_auth_token_value` stripped-property at config.py:64-68 — the exact model):

- `smtp_host: str = Field(default="", alias="VOCKY_SMTP_HOST")`
- `smtp_port: int = Field(default=587, alias="VOCKY_SMTP_PORT")`
- `smtp_user: str = Field(default="", alias="VOCKY_SMTP_USER")`
- `smtp_password: str = Field(default="", alias="VOCKY_SMTP_PASSWORD")`
- `smtp_from: str = Field(default="", alias="VOCKY_SMTP_FROM")` — the From header/envelope sender;
  when blank, fall back to `smtp_user`.
- A property `smtp_configured: bool` (or similarly named) — True iff `smtp_host.strip()` is
  non-empty AND the effective from-address (`smtp_from` falling back to `smtp_user`, stripped) is
  non-empty. This is the single "unconfigured ⇒ cleanly disabled" gate. A helper property for the
  effective from-address is welcome.

No `${...}` validation, no required fields — everything defaults to disabled.

## 2. Notifier module

**Shape (my call, follow it):** a single module `src/vocky/notifications.py` — one small class plus
a factory is nowhere near enough to justify a package (house comparison: `capture_queue.py`,
`rate_limit.py` are single modules; `accounts/`/`feedback/` are packages because they hold
repo+service+types). Keep the blocking send isolated in one function per Decision 1's consequence.

Contents:

- `class FeedbackAlertNotifier` with constructor taking `settings` and an accounts service (DI for
  tests), and one public method:

  ```
  async def notify_feedback_persisted(self, record: FeedbackEventRecord | None) -> None
  ```

  Behavior, in order:
  1. `record is None` or `record.project_id is None` → return silently (debug-level log at most).
  2. Not `smtp_configured` → return silently. Log ONCE at startup/info that alerts are disabled is
     optional; per-send it must stay silent (constraint: never log ERROR on every job).
  3. Resolve recipient via `accounts_service.get_owner_email_for_project(record.project_id)`;
     `None` → log at warning once per event ("no owner email for project ...") and return.
  4. Render one plain-text `email.message.EmailMessage`:
     - Subject: short and stable, e.g. `Vocky feedback: <source_product>` (include
       `feedback_value` if present).
     - Body: plain text lines — message, feedback_value, comment, channel, source_product,
       event/ingested timestamp, event id, project id. No HTML, no templates, no links required.
  5. Send via the isolated blocking function wrapped in `asyncio.to_thread`.

- The blocking send function (module-level, e.g. `_send_message(settings, message)`): stdlib
  `smtplib` — `SMTP_SSL` when `smtp_port == 465`, else `SMTP` + `starttls()` (wrap starttls in the
  standard try; if the server doesn't offer it, let the exception propagate — the caller decides).
  AUTH with `smtp_user`/`smtp_password` only when `smtp_user` is non-blank. Sensible timeout
  (e.g. 10s).

- **Exception policy of the module:** the notifier may let exceptions from the send path propagate
  out of `notify_feedback_persisted` — S3's worker hook owns the swallow-and-log containment.
  (Steps 1–3 above return, they don't raise.) Do not double-swallow here; keep the module honest
  and testable.

- Factory `get_feedback_alert_notifier()` following the house factory style (see
  `get_feedback_service()` / `get_accounts_service()`): builds from `get_settings()` and
  `get_accounts_service()`. Module-level singleton with a `dispose_`/reset seam is NOT needed —
  keep it simple; an `@lru_cache` or plain constructor-per-call, whichever the neighbors do least
  ceremoniously.

## 3. Tests (small — new `tests/test_notifications.py`)

Pure-Python (no DB needed, but the shared conftest imports fine). Inject fakes; monkeypatch the
module-level send function rather than real smtplib. Four cases max:

1. Unconfigured settings → no recipient lookup, no send attempted.
2. `record.project_id is None` (and `record is None`) → no lookup, no send.
3. Configured + owner resolves → send called once; assert To/From/Subject and that the body
   contains the message text and feedback_value.
4. Owner lookup returns `None` → no send, no raise.

Build `Settings` instances directly (kwargs by alias) rather than via env where convenient;
remember `get_settings()` is `@lru_cache` — avoid depending on it in tests (inject settings).

## Validation

- `uv run pytest tests/test_notifications.py -q`
- `uv run pytest -q` (full suite — should stay green; needs the test DB reachable, conftest
  default `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky`). Report honestly if the DB is
  unreachable.

## Out of scope

- No worker changes, no DI into `CaptureWorker` (S3).
- No compose/env-file changes (S4).
- No retry/outbox machinery.

## Wrap-up

Write `result.md`; append to `phase.md`: the exact class/factory/method names S3 should wire, the
settings names S4 must plumb (including the from-address fallback rule), and one "Doc impact" line
(`backend.md`: SMTP settings + notifier module).
