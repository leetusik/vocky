# Phase P13: Feedback email alerts over SMTP

_Intent: see [intent.md](intent.md)._

## Objective

When the worker persists a captured feedback event, send one plain-text email alert via SMTP to the account email of the owning org's owner (feedback -> project -> tenant -> owner member). SMTP transport is configured entirely from env (VOCKY_SMTP_*), reusing the SMTP account changple5 already uses in production; unconfigured SMTP means alerts are cleanly disabled, and a send failure is never allowed to duplicate or requeue an already-persisted feedback event. Recipient/preferences configurability is deliberately out of scope — this phase lands the default-on, owner-addressed alert only.

## Context

Greenfield feature: there is **zero** email/SMTP/notification code anywhere in `src/`, `web/`, config, or compose (re-verified at DECOMP). Everything in this phase is new surface plus three edit points: `src/vocky/config.py`, `src/vocky/accounts/repository.py` (+ `service.py`), and `src/vocky/worker.py`, then the env/compose plumbing.

The dependency chain runs **recipient → notifier → hook → plumbing → bring-up**, so each slice builds on landed code and never stubs a future slice.

## Decomposition

Five middle slices, single pass (no product visual design in this phase, so no `co-work` round and no `DECOMP2`). All five are **`risk: medium`** — see "Risk calls" below for why none of them is `low`.

**P13.S1 — owner-email recipient resolution (accounts repository + service)** · order 1
The one genuinely missing data primitive. Adds a single 3-join read to `AccountsRepository` walking `feedback_events.project_id → projects.tenant_id → tenant_members(role='owner') → users.email`, plus the thin `AccountsService` passthrough, plus a small DB-backed test. Cut first and alone because it is the **multi-tenant correctness hot spot** of the phase: a wrong join or a missing `role='owner'` filter mails one org's feedback to another org's owner. Deliberately lands with no caller — S2 consumes it.

**P13.S2 — SMTP settings + feedback alert notifier module** · order 2, depends on S1
`VOCKY_SMTP_*` settings on `Settings` + the "unconfigured ⇒ cleanly disabled" property, and the new notifier module that renders the plain-text message and sends it over stdlib `smtplib` inside `asyncio.to_thread`. Owns recipient resolution internally (via the S1 service method) so that S3's worker hook stays a one-liner. Ships with a small test covering: disabled-when-unconfigured (no send attempted), rendering, and one send path against a fake transport. No worker wiring here — the module is inert until S3.

**P13.S3 — worker post-persist alert hook + DI wiring + failure containment** · order 3, depends on S2
Captures the currently-discarded `FeedbackEventRecord` returned by `create_feedback_event(_with_attachments)`, adds the `notifier=` DI argument to `CaptureWorker`, wires it in `run_worker()`, and calls the notifier **after** the persistence `try/except` has succeeded, inside its own `try/except Exception` that logs and swallows. Small worker-test additions: notifier called on success, notifier exception does **not** requeue/dead-letter, `project_id is None` (and `record is None`) skips silently. This is the slice that carries the phase's one real trap — see "Failure containment" below.

**P13.S4 — SMTP env/compose/deploy plumbing (prod + dev)** · order 4, depends on S3
`.env.prod.example` gains the SMTP block (the box's fourth secret) and its "ALL THREE ARE REQUIRED" prose becomes four; `compose.prod.yml` gains the SMTP vars in the **worker** service env block only (the worker is the sole sender — the api never sends) plus the matching header-prose update; the dev `docker-compose.yml` worker block gets the mirrored optional form; `.env.example` gains the dev-side commented block. Appends the phase's "Doc impact" lines. No application code.

**P13.S5 — production bring-up: changple5 SMTP credentials + live alert verification** · order 5, depends on S4
The operator-gated tail. Prepares the exact box runbook (how to read changple5's SMTP host/port/user/password out of its own env on the box, which `VOCKY_SMTP_*` names they map onto in vocky's gitignored `.env`, the redeploy command, and the verification: capture one feedback event and confirm the alert email lands), then **returns `needs_operator`** with that runbook — the credentials live only on the box, and reading another project's env was already permission-blocked once at phase creation. The executor never SSHes and never invents credentials; the orchestrator sets the slice `pending` on that return, and the operator's confirmation of a real received email is the slice's acceptance evidence.

### Risk calls (why nothing is `low`)

`risk` picks the executor tier and is the phase's main cost lever, so `low` is reserved for fully mechanical plans. None of these qualify:

- **S1** — a hand-written 3-join query with a magic-string role filter and a deterministic tie-break; multi-tenant leak risk.
- **S2** — new module shape, TLS/STARTTLS/port handling, and the disabled-path semantics.
- **S3** — the never-requeue containment rule sits one indentation level away from a duplicate-feedback bug.
- **S4** — looks mechanical but is not: `compose.prod.yml` and `.env.prod.example` both state the "exactly three secrets, all `${VAR:?}`" invariant in prose, and the SMTP secret is deliberately **optional**, so the interpolation form has to be chosen and the surrounding prose kept coherent in several places.
- **S5** — operator-gated by construction; the executor must recognize the permission boundary and hand off cleanly rather than improvise.

The orchestrator may still bump any of these up a tier; it may not bump them down.

## Findings & Notes

### Decision 1 — SMTP client: stdlib `smtplib` in `asyncio.to_thread` (no new dependency)

`smtplib` + `email.message.EmailMessage` from the standard library, called through `asyncio.to_thread` so the worker's single-threaded asyncio loop is never blocked. **Rejected:** adding `aiosmtplib` to the `server` extra.

Rationale: the volume is one short plain-text message per captured feedback event on a single-owner product — the blocking-send window is milliseconds and it happens on the worker, which is the only sender and has no HTTP latency budget to protect. Stdlib covers SSL, STARTTLS and AUTH, so `aiosmtplib` would buy nothing measurable while adding a dependency to the `server` extra (and dependency churn to `uv.lock`) for the entire deployment. Core deps stay untouched either way — the pip-installable CLI (`httpx` + `typer`) must stay lean, and the notifier is server-side only.

Consequence for S2: the module must keep the blocking send isolated in one small function so it is trivially swappable if volume ever justifies `aiosmtplib`.

### Decision 2 — failure containment: swallow-and-log, no notify DLQ

The notifier call happens **after** the persistence `try/except` has already succeeded (the feedback row is committed), and is wrapped in its own `try/except Exception` that `logger.exception(...)`s and returns. It must never re-raise into `_process_job`'s persistence path and must never touch `requeue_job` / `dead_letter_job`. **Rejected:** a separate notify DLQ in Redis.

Rationale: the trap here is structural, not statistical — `_handle_persistence_failure` retries the *whole* capture job, so any exception escaping the alert path re-enqueues an already-persisted event and creates **duplicate feedback rows**. Containment must therefore be total. A notify DLQ would add a queue with no consumer, no drain tooling and no operator UI on a single-owner product; the honest tradeoff is that a failed alert is **lost and visible only in the worker's logs**, which is acceptable while the feedback itself is durably stored and readable in the app. If alert reliability ever matters, the follow-up is a deferred job (retry/outbox), not machinery added speculatively now — the REVIEW slice is the right place to raise that as a `defer-job` candidate.

Concrete shape for S3: the notifier call site must sit **outside** the persistence `try:` block, not merely in a different `except` clause.

### Decision 3 — where the SMTP secret lives, and its interpolation form (guidance for S4)

The worker is the **only** sender, so the SMTP vars belong in the `worker` service's `environment:` block in `compose.prod.yml` and nowhere else — `api` and `web` must not receive them (the compose header's per-service isolation rule is explicit that no `env_file:` exists precisely so secrets do not bleed across containers).

Recommended forms, with the reasoning S4 should preserve in prose:
- **prod (`compose.prod.yml`)**: `${VOCKY_SMTP_PASSWORD:?...}` matches the box-secret pattern of the existing three and fails the deploy loudly rather than silently shipping a stack whose alerts are quietly off — production *intends* alerts on. `.env.prod.example` then documents **four** required secrets, not three.
- **dev (`docker-compose.yml`)**: the `:-` empty-default form, so a local stack with no SMTP configured still starts and simply runs with alerts disabled (that is exactly the "unconfigured ⇒ cleanly disabled" contract from S2).

S4 owns the final call, but any deviation must be recorded — the "exactly three `${VAR:?}` secrets" statement appears in both `compose.prod.yml`'s header and `.env.prod.example`'s header and they must not drift apart.

### Codebase facts (verified at DECOMP — do not re-derive)

- **Hook seam** (`src/vocky/worker.py:67-85`): `_process_job` calls `create_feedback_event(...)` / `create_feedback_event_with_attachments(...)` and **discards** the returned `FeedbackEventRecord`. `run_worker()` (`worker.py:114`) constructs `CaptureWorker(queue=..., feedback_service=...)` — a `notifier=` keyword fits with no signature churn for existing callers if it is defaulted.
- **Existing worker test doubles return `None`** (`tests/test_worker.py`: `FlakyFeedbackService`, `RecordingFeedbackService`, `BrokenFeedbackService` all declare `-> None`). So S3's hook **must tolerate a `None` record** — treat it as "nothing to notify about" alongside the `project_id is None` skip. Done that way, every existing worker test keeps passing untouched; done naively (attribute access on the record) they all break.
- **`FeedbackEventRecord.project_id` is `UUID | None`** (`src/vocky/feedback/types.py:46`), so the skip branch is required by the type, not just by defensiveness.
- **`role="owner"`** is a bare string literal written in exactly two places, both in `src/vocky/accounts/service.py` (lines 125, 165). S1 should read from the same value; introducing a shared constant is optional but must not change either write site's behavior.
- **Services are session-maker-backed**: `get_feedback_service()` / `get_accounts_service()` both wrap `get_session_maker()` (`feedback/service.py:389`, `accounts/service.py:492`). The notifier gets an accounts service the same way — there is no session-injection seam, so a fresh session per lookup is the house style.
- **`TenantMemberModel`** (`persistence/models.py:204`) has `UniqueConstraint("tenant_id", "user_id")` and indexes on both FKs, but **nothing forbids two `role='owner'` rows** in one tenant. S1 must pick a deterministic winner (oldest `created_at`, then `id` — the same oldest-wins tie-break `get_project_by_name` already uses) rather than relying on `.one()`, which would raise.
- **Config precedent** (`src/vocky/config.py`): pydantic-settings, `VOCKY_*` aliases, `extra="ignore"`, and `get_settings()` is `@lru_cache(maxsize=1)` — tests that vary settings must call `get_settings.cache_clear()` (conftest already does this for `DATABASE_URL`). `admin_auth_token` + its `admin_auth_token_value` stripped-property is the exact model for `smtp_*` + an `smtp_enabled`-style property.
- **Tests need a live Postgres**: `make test` (`check-test-db` + `uv run pytest`) requires both `DATABASE_URL` and `TEST_DATABASE_URL` set to *different* databases and a reachable server (conftest default `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky`, dev compose publishes `${POSTGRES_PORT:-5432}`). S1 (DB-backed) needs it; S2/S3 tests are pure-Python but still import the shared conftest. Slice plans should say so, and a slice that cannot reach a DB should report that rather than pretend the suite passed.
- **Deploy scripts carry no secret list**: `deploy/deploy.sh` only asserts `.env` **exists** (and greps `POSTGRES_PASSWORD` for a fallback `DATABASE_URL`), so adding an SMTP secret needs **no** `deploy.sh` change — the enforcement is compose's `${VAR:?}` interpolation. Do not add a second enforcement point.
- **No web/UI surface** for alerts exists or is in scope (no `/settings` route; `AppNavItem.soon` is the affordance when one comes).

## Constraints

- **Scope wall**: exactly one plain-text email per persisted feedback event, addressed to the owning org's owner. No preferences, no digests, no batching, no scheduler, no UI toggle, no HTML mail, no recipient configuration — all explicitly deferred by `intent.md`.
- **Default-on when configured; cleanly off when not.** Missing/blank SMTP config disables alerts silently at startup and per-send; it must never raise, never crash the worker, and never log at ERROR on every job.
- **Never duplicate feedback.** No alert-path failure may reach the capture job's requeue or dead-letter path (see Decision 2).
- **No new core dependencies.** The pip-installable CLI keeps its `httpx` + `typer` core; server-only additions go in the `server` extra, and this phase adds none at all (Decision 1).
- **Secrets stay off git.** Real SMTP credentials only ever live in the box's gitignored `.env`; the repo carries placeholders and prose. Per-service env isolation in `compose.prod.yml` is preserved — SMTP vars on the `worker` service only.
- **Keep test files small** (workspace contract): a handful of high-value cases per slice, extending `tests/test_worker.py` / `tests/test_accounts_persistence.py` in place where natural rather than growing new scaffolding.
- **No `doc-new-version` in a middle slice.** Durable-truth changes get a one-line "Doc impact" note below; `P13.REVIEW` consolidates them.

## Doc impact

_One-liners appended by each slice; `P13.REVIEW` consolidates them into doc versions._

- (P13.DECOMP) None yet — decomposition changed no durable truth. Expected areas for the phase: `backend.md` (SMTP settings + notifier module + the accounts owner-email primitive), `architecture.md` (the worker's post-persist alert hook and its containment rule), `operations.md` (the fourth box secret and the SMTP bring-up runbook), and possibly `qa.md` (how a live alert is verified).
- (P13.S1) `backend.md` gains `AccountsRepository.get_owner_email_for_project(project_id) -> str | None` and the matching `AccountsService` passthrough — a single 3-join read (`projects.tenant_id -> tenant_members(role='owner') -> users.email`), oldest-wins tie-break, `None` on missing project/no owner.
- (P13.S2) `backend.md` gains: `Settings.smtp_host/port/user/password/from` (`VOCKY_SMTP_*`, all optional, all default-disabled) plus `smtp_from_value` (effective From, falling back to `smtp_user`) and `smtp_configured` (the single "unconfigured ⇒ cleanly disabled" gate); and the new `src/vocky/notifications.py` module — `FeedbackAlertNotifier.notify_feedback_persisted(record)` (renders one plain-text `EmailMessage` and sends it via stdlib `smtplib` in `asyncio.to_thread`) plus `get_feedback_alert_notifier()` factory — inert until S3 wires it into the worker.

## P13.S1 notes (owner-email recipient resolution)

- Landed `AccountsRepository.get_owner_email_for_project(project_id: UUID) -> str | None` (right after `get_project_by_name` in `repository.py`) and the thin `AccountsService.get_owner_email_for_project` passthrough (right before `get_or_create_project` in `service.py`). No caller yet — inert until S2.
- **S2 should call**: `AccountsService.get_owner_email_for_project(project_id)` via the existing `get_accounts_service()` factory. Returns `None` for "nothing to notify" (missing project or tenant with no owner) — not an exception. `AccountsReadError` is the only exception it can raise (genuine DB failure); S3's containment rule (never let an alert-path exception escape into the persistence job's requeue/dead-letter path) applies to this call too.
- `role="owner"` stayed a bare string literal, matching the two existing write sites (`service.py` — now around lines 135/175 after the insertion) — no shared constant added, per plan's "do not refactor the write sites."
- Selecting `UserModel.email` directly (not the whole `UserModel`) let the repository method return `str | None` straight from `.scalars().first()` with no new `_to_*_record` mapper.
- Ruff is **not configured in this repo at all** (no `ruff` in `dependencies`/dev group, no `[tool.ruff]`, no lint Makefile target, `ruff` binary not installed) — later slices' plans should treat "run ruff if configured" as a no-op here rather than expect a house lint command to exist.
- Test-DB reachability confirmed working via the already-running dev compose stack (`vocky-postgres-1` on `127.0.0.1:55432`); `uv run pytest tests/test_accounts_persistence.py -q` and the full `uv run pytest -q` (218 tests) both passed clean before and after this slice.

## P13.S2 notes (SMTP settings + notifier module)

- Landed `src/vocky/notifications.py` as a single module (not a package) per the plan's shape
  call — `class FeedbackAlertNotifier(settings, accounts_service)` with
  `async def notify_feedback_persisted(self, record: FeedbackEventRecord | None) -> None`, a
  module-level `_render_message(settings, record, to_email) -> EmailMessage`, a module-level
  blocking `_send_message(settings, message) -> None` (the isolation point for Decision 1), and
  `get_feedback_alert_notifier()` as a plain constructor-per-call factory (no `@lru_cache`,
  matching `get_feedback_service()`/`get_accounts_service()`).
- **S3 should call**: `await notifier.notify_feedback_persisted(record)` where `notifier` comes
  from `get_feedback_alert_notifier()` (or DI in tests) and `record` is the
  `FeedbackEventRecord | None` currently discarded at `worker.py:67-85`. The method itself
  tolerates `record is None`, `record.project_id is None`, and unconfigured SMTP by returning
  silently — but the accounts-service lookup (`AccountsReadError`) and the SMTP send
  (`smtplib`/socket exceptions) both propagate out of it by design (Decision 2/the plan's
  "exception policy" section: this module must stay honest and testable, not double-swallow). S3's
  own `try/except Exception` around the call site, sitting **outside** the persistence `try:`
  block, is the only containment — it is load-bearing, not optional.
- **S4 should plumb**: `VOCKY_SMTP_HOST` (default `""`), `VOCKY_SMTP_PORT` (default `587`),
  `VOCKY_SMTP_USER` (default `""`), `VOCKY_SMTP_PASSWORD` (default `""`), `VOCKY_SMTP_FROM`
  (default `""`). **From-address fallback rule**: when `VOCKY_SMTP_FROM` is blank, the notifier
  uses `VOCKY_SMTP_USER` as the effective From header/envelope sender
  (`Settings.smtp_from_value`) — worth a line in the env-file prose so an operator who sets only
  the user still gets alerts. `smtp_configured` requires a non-blank host **and** a non-blank
  effective From; port/user/password may stay at defaults with alerts simply off.
- Test-DB reachability confirmed again via the running `vocky-postgres-1` container
  (`127.0.0.1:55432`); `uv run pytest tests/test_notifications.py -q` (5 passed, pure-Python, no
  DB needed) and the full `uv run pytest -q` (223 passed, up from S1's 218 baseline by exactly the
  5 new tests) both passed clean.
- No ruff/mypy step run — confirmed (again) neither is configured anywhere in this repo.

## Open Questions

- None blocking. Two things are deliberately left to their slice: the notifier module's exact file/package shape (single module vs `src/vocky/notifications/` package — S2's call, following the `accounts`/`feedback` house style), and the final interpolation form for the SMTP secret in compose (S4's call, with Decision 3's recommendation as the default).
- For `P13.REVIEW` to consider: whether the lost-alert-on-failure tradeoff (Decision 2) warrants a `defer-job` for a retry/outbox path.
