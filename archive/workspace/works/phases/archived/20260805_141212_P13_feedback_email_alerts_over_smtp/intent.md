# Intent — P13

- Captured at: 2026-08-04T16:38:57+09:00
- Origin: operator

## Original Input (verbatim)

> need a feedback alert.
> /create-phase . use smtp for the task. default to sending to the logged in email, later will be able
> it configurable.

## Confirmed Intent (refined + clarified)

When a feedback event is captured and persisted, vocky sends **one plain-text email alert per event**
over **SMTP** to the **account email of the owner of the org that owns the event's project** (the
proper multi-tenant reading of "the logged in email" — each tenant's owner gets alerts for their own
org's feedback; the operator gets changple's because they own that org). SMTP transport is configured
entirely from env, **reusing the SMTP account changple5 already uses in production**; with SMTP
unconfigured, alerts are cleanly disabled — never a crash. Deeper configurability (recipient choice,
per-user preferences, digests, UI toggles) is **explicitly later** and out of this phase's scope.

## Clarifications Resolved

- Q: Which SMTP provider/credentials will production use? — A: **"use what changple5 already using."**
  Changple5's Django backend sends mail today; its SMTP host/user/password are copied from its env on
  the box at bring-up. (A permission-classifier block prevented reading the exact var names during
  phase creation, so recording them is a DECOMP/bring-up step.)
- Q: When should an alert go out? — A: **Every event** — one email per captured feedback event, right
  after the worker persists it. (Batched digest rejected: needs a scheduler the repo doesn't have.)
- Q: Who receives it? — A: **The owning org's owner** — the account email of the owner member of the
  tenant that owns the feedback's project. (A single global operator address rejected: wrong the
  moment anyone else signs up.)

## Notes

Scoping exploration done at phase creation (read-only), so `DECOMP` starts warm:

- **Greenfield**: zero email/SMTP/notification code anywhere in `src/`, `web/`, config, compose.
- **Hook point**: `src/vocky/worker.py` `_process_job` (worker.py:66-79) — the persisted
  `FeedbackEventRecord` is returned and currently discarded; a post-commit hook there is the clean
  seam, and `run_worker()`'s constructor wiring fits a `notifier=` DI argument.
- **Recipient query gap**: the chain `feedback_events.project_id → projects.tenant_id →
  tenant_members(role='owner') → users.email` exists in schema (indexes present) but no repository
  method walks it — `AccountsRepository` needs one new 3-join query. `role="owner"` is a magic string
  written in exactly two places in `accounts/service.py`. `project_id` is nullable in the model
  (though enqueue guarantees it for new events) — the hook needs an explicit skip branch.
- **Config precedent**: pydantic-settings with `VOCKY_*` aliases; the `admin_auth_token` pattern
  (empty string = feature disabled) is the model for "SMTP unconfigured ⇒ alerts off".
- **Prod secrets**: the SMTP password becomes the **fourth box secret** — `.env.prod.example`, a
  `${VAR:?}` interpolation in the **worker** service's env block only (the worker is the sender), and
  the compose header prose updated. Check the dev `docker-compose.yml` worker mirror too.
- **SMTP dependency question** (DECOMP decides): stdlib `smtplib` wrapped in `asyncio.to_thread` (the
  worker loop is single-threaded asyncio) vs adding `aiosmtplib` to the `server` extra — never to
  core deps (the pip-installable CLI stays lean).
- **Safety constraint (the one real trap)**: a send failure must **never** requeue the capture job —
  the feedback row is already committed, so a naive re-raise into the persistence retry path creates
  duplicate feedback rows. Swallow-and-log vs a separate notify DLQ is DECOMP's call.
- **No web settings surface exists** (no `/settings` route; `AppNavItem.soon` is the ready affordance
  when one comes). Out of scope beyond this note.
- No product visual design (plain-text email first) — no design split, no `design-cowork`.
