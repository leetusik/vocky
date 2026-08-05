# Plan — P13.DECOMP (decompose "Feedback email alerts over SMTP")

## Job

Decompose phase P13 into middle slices (bare folders via `new-slice` only — never pre-fill any
slice's `plan.md`), seed `phase.md` (Decomposition, Findings & Notes, Constraints), and set each
slice's `--risk` deliberately (it selects the executor tier; `low` only for fully mechanical work).
No product visual design in this phase — single-pass decomposition, no `co-work` design rounds, no
`DECOMP2`.

## Context (read first)

- `works/phases/active/P13/phase.md` — objective.
- `works/phases/active/P13/intent.md` — confirmed intent **plus a warm scoping section** ("Notes")
  done at phase creation: hook point, recipient-query gap, config precedent, prod-secret handling,
  the duplicate-feedback trap. Build on it; re-verify only what you touch.

Key facts already established (verify cheaply, don't re-derive):

- Greenfield: zero email/SMTP code anywhere in `src/`, `web/`, config, compose.
- Hook seam: `src/vocky/worker.py` `_process_job` — `create_feedback_event(...)` /
  `create_feedback_event_with_attachments(...)` return the persisted record, currently discarded.
  `run_worker()` wiring fits a `notifier=` DI argument on `CaptureWorker`.
- Recipient chain `feedback_events.project_id → projects.tenant_id → tenant_members(role='owner')
  → users.email` exists in schema but no repository method walks it; `AccountsRepository` needs one
  new 3-join query. `project_id` is nullable — the hook needs an explicit skip branch.
- Config: pydantic-settings `VOCKY_*` aliases; `admin_auth_token` empty-string-disables pattern is
  the model for "SMTP unconfigured ⇒ alerts cleanly off".
- Prod secrets: SMTP password is the fourth box secret — `.env.prod.example`, `${VAR:?}` in the
  **worker** service env block only, compose header prose; check the dev `docker-compose.yml`
  worker mirror too.

## Decisions this DECOMP must make (record rationale in phase.md)

1. **SMTP client**: stdlib `smtplib` in `asyncio.to_thread` vs `aiosmtplib` in the `server` extra
   (never core deps — pip-installable CLI stays lean). Lean stdlib unless you find a concrete
   reason otherwise.
2. **Failure containment**: send failure must NEVER requeue/duplicate the already-persisted
   feedback event. Swallow-and-log vs separate notify DLQ — decide and record. (Simplest safe
   answer is fine; this is a single-owner product today.)
3. **Slice cut**: likely shape is ~3–4 middle slices, e.g. (a) settings + notifier module +
   owner-email repository query, (b) worker hook + DI wiring + tests, (c) compose/env/deploy
   plumbing + docs impact, and (d) an operator-gated bring-up step to copy changple5's SMTP
   credentials onto the box (its exact env var names could not be read at phase creation — a
   permission block; capturing them belongs to that operator-facing step, likely a `pending`-gated
   slice or an explicit operator note in the slice you cut for it). You own the final cut — this is
   guidance, not a mandate.

## Constraints

- One plain-text email per persisted event, to the owning org's owner. No preferences/digests/UI —
  explicitly out of scope.
- Alerts default-on when SMTP configured; unconfigured ⇒ cleanly disabled, never a crash.
- Keep test files small per the workspace contract.
- Append "Doc impact" one-liners to `phase.md` for durable-truth changes (backend doc, deploy doc,
  qa doc as applicable) — the REVIEW slice consolidates.

## Deliverables

- Middle slices created with `new-slice` (bare folders), sensible `--order`, deliberate `--risk`.
- `phase.md` seeded: slice breakdown + rationale, findings, constraints, open decisions resolved.
- `result.md` in this slice folder summarizing the decomposition.
