# Result — P13.S2: SMTP settings + feedback alert notifier module

## What landed

### 1. Settings (`src/vocky/config.py`)

Added to `Settings`, following the `admin_auth_token` / `admin_auth_token_value` model exactly:

- `smtp_host: str = Field(default="", alias="VOCKY_SMTP_HOST")`
- `smtp_port: int = Field(default=587, alias="VOCKY_SMTP_PORT")`
- `smtp_user: str = Field(default="", alias="VOCKY_SMTP_USER")`
- `smtp_password: str = Field(default="", alias="VOCKY_SMTP_PASSWORD")`
- `smtp_from: str = Field(default="", alias="VOCKY_SMTP_FROM")`
- `smtp_from_value` property: `smtp_from.strip() or smtp_user.strip()` — the effective
  From/envelope-sender address.
- `smtp_configured` property: `bool(smtp_host.strip()) and bool(smtp_from_value)` — the single
  "unconfigured ⇒ cleanly disabled" gate.

No `${...}`/required validation; everything defaults to disabled, matching the plan.

### 2. Notifier module (`src/vocky/notifications.py`, new)

Single module (per the plan's shape call — same tier as `capture_queue.py`/`rate_limit.py`, not a
package):

- `class FeedbackAlertNotifier(settings, accounts_service)` with
  `async def notify_feedback_persisted(self, record: FeedbackEventRecord | None) -> None`
  implementing the five-step behavior from the plan exactly (record/project_id None → silent
  return with a debug log; unconfigured → silent return; owner-lookup `None` → `logger.warning`
  once, return; else render + send).
- `OwnerEmailResolver` — a `typing.Protocol` DI seam so tests can inject a fake accounts service
  without importing `AccountsService`.
- `_render_message(settings, record, to_email) -> EmailMessage` — plain-text
  `email.message.EmailMessage`. Subject: `"Vocky feedback: <source_product>"`, with
  `" (<feedback_value>)"` appended when `feedback_value is not None`. Body: one line each for
  message, feedback_value, comment, channel, source_product, event_at, ingested_at, event id,
  project id.
- `_send_message(settings, message)` — module-level blocking function (the isolation point
  Decision 1 requires): `smtplib.SMTP_SSL` when `smtp_port == 465`, else `smtplib.SMTP` +
  `starttls()`; `login()` only when `smtp_user` is non-blank; 10s timeout; used as a context
  manager (`with smtp_cls(...) as client:`).
- `get_feedback_alert_notifier()` — plain constructor-per-call factory (no `@lru_cache`, matching
  `get_feedback_service()`/`get_accounts_service()`'s style, both of which are also
  constructor-per-call), built from `get_settings()` + `get_accounts_service()`.

**Exception policy honored as specified:** steps 1–3 return, never raise; the accounts-service
lookup and the SMTP send are left to propagate out of `notify_feedback_persisted` — no
try/except anywhere in this module. S3 owns the swallow-and-log containment at the worker call
site.

No worker wiring, no DI into `CaptureWorker` — the module is inert, importable standalone, exactly
as scoped.

### 3. Tests (`tests/test_notifications.py`, new)

Pure-Python, no DB. Four conceptual cases (one is `@pytest.mark.parametrize`d over
`record=None` / `record.project_id=None`, so 5 test executions total, still one file, no
scaffolding):

1. `test_unconfigured_settings_skips_lookup_and_send` — unconfigured `Settings()` → no accounts
   call, no send.
2. `test_no_record_or_no_project_id_skips_lookup_and_send` (parametrized) — `record=None` and
   `record.project_id=None` → no accounts call, no send, even with SMTP configured.
3. `test_configured_and_owner_resolves_sends_once` — configured settings + owner resolves → send
   called once; asserts `To`/`From`/`Subject` and that the body contains the message text and the
   feedback value.
4. `test_owner_lookup_returns_none_skips_send` — owner lookup returns `None` → accounts called
   once, no send, no raise.

Settings are built directly via alias kwargs (`Settings(DATABASE_URL=..., VOCKY_SMTP_HOST=..., ...)`)
per the plan's guidance, never through the `@lru_cache`d `get_settings()`. The module-level
`notifications_module._send_message` is monkeypatched rather than touching real `smtplib`.
`FeedbackEventRecord` instances are built via a small local `_record(**overrides)` helper (all
fields are required kw-only, no dataclass defaults) rather than importing fixtures from elsewhere.

## Validation

- `uv run pytest tests/test_notifications.py -q` → **5 passed** (0.03s).
- `uv run pytest -q` → **223 passed** (9.59s) — up from the 218 baseline recorded in P13.S1's
  notes by exactly the 5 new tests; no regressions. Test DB was reachable via the already-running
  `vocky-postgres-1` container on `127.0.0.1:55432` (confirmed with `docker ps` before running).

No lint/type-check step was run: per P13.S1's notes, ruff is not configured anywhere in this repo
(no dependency, no `[tool.ruff]`, no Makefile target, binary not installed), and grepping
`pyproject.toml` confirms no `mypy` section either — there is no house static-check command to
run.

## Handoff for S3 (worker post-persist hook)

- Import: `from vocky.notifications import get_feedback_alert_notifier` (or construct
  `FeedbackAlertNotifier` directly with DI, matching how `CaptureWorker` already takes
  `feedback_service` as a constructor argument).
- Call: `await notifier.notify_feedback_persisted(record)` where `record` is the
  `FeedbackEventRecord | None` returned by `create_feedback_event(_with_attachments)` (currently
  discarded at `worker.py:67-85` — S3 must capture it).
- The call is safe to make unconditionally — it tolerates `record is None`, `record.project_id is
  None`, and unconfigured SMTP by returning silently. It is **not** safe against arbitrary
  exceptions: `AccountsReadError` from the owner-email lookup and any `smtplib`/socket exception
  from the send both propagate. S3's `try/except Exception` around this call site (outside the
  persistence `try:` block, per Decision 2) is load-bearing, not optional.
- Constructor signature: `FeedbackAlertNotifier(*, settings: Settings, accounts_service:
  OwnerEmailResolver)` — `accounts_service` only needs `get_owner_email_for_project`, so
  `AccountsService` satisfies the DI seam without modification.

## Handoff for S4 (env/compose plumbing)

Settings names to plumb, exactly as added to `config.py`:

- `VOCKY_SMTP_HOST` (default `""`)
- `VOCKY_SMTP_PORT` (default `587`)
- `VOCKY_SMTP_USER` (default `""`)
- `VOCKY_SMTP_PASSWORD` (default `""`)
- `VOCKY_SMTP_FROM` (default `""`) — **the from-address fallback rule**: when blank, the notifier
  uses `VOCKY_SMTP_USER` as the effective From/envelope-sender (`Settings.smtp_from_value`). S4
  should document this fallback in `.env.prod.example`/`.env.example` prose so an operator who
  sets only `VOCKY_SMTP_USER` still gets a working From header.
- `smtp_configured` requires a non-blank `VOCKY_SMTP_HOST` **and** a non-blank effective From
  address; port/user/password may all be left at defaults and alerts simply stay off.

## Deviations from plan.md

None. Every deliverable, method name, and behavior matches the plan as written. The only
plan-left-open choice was the module's exact shape, which the plan explicitly deferred to this
slice ("my call, follow it") — a single `src/vocky/notifications.py` module, as documented above.
