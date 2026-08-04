# Result — P13.REVIEW: phase review of "Feedback email alerts over SMTP"

**Verdict: `pass`.** No findings, no fix slices. Five doc versions consolidated. One deferred-job
recommendation for the orchestrator to create.

## 1. Validation — all slices together

| Command | Outcome |
| --- | --- |
| `python3 scripts/workflow.py validate` | **pass** — "Workflow validation passed." (run twice: before the doc work and after `rebuild-docs`) |
| `uv run pytest -q` | **pass — 225 passed in 9.52s**, exactly the count S3 recorded. Test DB reachable (`nc -z 127.0.0.1 55432` OK, `vocky-postgres-1` up) |
| `uv run pytest --collect-only -q` | 225 tests collected across 30 `test_*.py` files (used to correct `qa.md`'s stale 215/29) |
| prod compose, all required vars exported | **exit 0** |
| prod compose, `VOCKY_SMTP_PASSWORD` unset | **exit 1** with the exact `:?` message — `error while interpolating services.worker.environment.VOCKY_SMTP_PASSWORD: required variable VOCKY_SMTP_PASSWORD is missing a value: VOCKY_SMTP_PASSWORD is required — set it in the box .env` |
| dev compose, no SMTP vars | **exit 0** — the local stack still starts unconfigured |

**The negative test is genuine, not a false pass.** `operations.md` warns that `env -u VAR` proves
nothing because Compose auto-reads the project `.env`. Checked: the repo-root `.env` contains
**zero** `VOCKY_SMTP*` lines (`grep -c VOCKY_SMTP .env` → `0`), so nothing could have supplied the
value behind the guard. Recorded that caveat in the new `operations.md` version so the next person
re-running this check knows what makes it meaningful.

No lint/type step exists to run — reconfirmed for the fourth time this phase (no `ruff` in
`pyproject.toml`/`Makefile`, binary not installed, no `mypy`). This is now written into `qa.md`
rather than left as a per-slice rediscovery.

## 2. Judgment against objective + intent

Read `phase.md` end to end, `intent.md`, all five slices' `plan.md`/`result.md`, and the landed code.

**One plain-text email per persisted event, to the owning org's owner** — verified in
`src/vocky/accounts/repository.py`. The `select(UserModel.email)` joins
`TenantMemberModel.user_id == UserModel.id` then `ProjectModel.tenant_id == TenantMemberModel.tenant_id`,
filtered `ProjectModel.id == project_id` **and** `TenantMemberModel.role == "owner"`, ordered
`(created_at, id)` with `.limit(1)` + `.scalars().first()`. The project-anchored join makes a
cross-tenant recipient structurally impossible; the `role` filter is present; the oldest-wins
tie-break is deterministic where two owner rows exist (the schema permits them) instead of raising
as `.one()` would. `AccountsService` wraps it on a fresh session, `SQLAlchemyError` → `AccountsReadError`.
Matches `intent.md`'s "the proper multi-tenant reading of 'the logged in email'" exactly.

**Unconfigured ⇒ cleanly disabled** — `Settings.smtp_configured` = non-blank host **and** non-blank
effective From (`smtp_from` falling back to `smtp_user`). `notify_feedback_persisted` returns before
any lookup or send when it is false, with **no log at that branch at all** — so no per-job ERROR
spam and no raise. Defaults are all-blank/587, so a stack that knows nothing about SMTP behaves
exactly as before this phase.

**The containment invariant — read in the code, not just the tests.** `src/vocky/worker.py:70-94`:
the persistence `try:` covers only the two `create_feedback_event*` calls, its
`except FeedbackPersistenceError` branch calls `_handle_persistence_failure(job)` and **`return`s**,
and the notify block sits textually after that block at the same indentation level as the `try`.
So the alert code physically cannot execute on a persistence failure, and its own bare
`except Exception` does nothing but `logger.exception("Feedback alert failed for job %s", ...)` and
fall through — it never touches `requeue_job`/`dead_letter_job`, which appear only inside
`_handle_persistence_failure`. This is Decision 2's "structurally outside, not merely a different
except clause", satisfied literally. `test_worker_contains_notifier_failure` backs it behaviorally
(raising notifier → `process_next_job()` still `True`, queue and dead-letter list both length 0).
`run_worker()` wires `notifier=get_feedback_alert_notifier()`, so the path is live in production.

**Scope wall respected.** The phase's non-`works/` diff is **12 files, +538/-15**: four
env/compose files, four `src/` files, three test files (plus `notifications.py` as one of the four
src files). No `web/`, no `/settings` route, no preferences, no digest, no scheduler, no HTML part,
no recipient configuration. `pyproject.toml` and `uv.lock` are **byte-unchanged by the entire phase**
— stdlib `smtplib` only, so neither the CLI's `httpx`+`typer` core nor the `server` extra moved
(Decision 1 honored, including the "keep the blocking send in one swappable function" consequence:
`_send_message` is a module-level function, not inlined).

**Secrets hygiene.** No credential anywhere in the repo — grep for the live host/user across all
code, config, compose and docs matches only `works/` prose (the non-secret endpoint facts from the
operator's acceptance note); the password appears nowhere at all. The five `VOCKY_SMTP_*` vars are
in the `worker` service's `environment:` block **only**, in both compose files — `api`/`web`
untouched, so the per-service isolation invariant holds. `compose.prod.yml`'s header and
`.env.prod.example`'s header were read side by side and agree: four `:?` secrets,
`VOCKY_SMTP_HOST`/`USER` also `:?` but not secret, `PORT`/`FROM` optional `:-`. `deploy/deploy.sh`
correctly gained nothing — compose interpolation stays the single enforcement point.

**S5's operator gate was handled correctly**: the executor authored the runbook, refused to SSH or
invent credentials, returned `needs_operator`, and the operator's live confirmation (real capture →
alert email received, `mail.privateemail.com:587`, user `hi@hi2vi.com`) is recorded in `phase.md` as
the acceptance evidence. The phase objective is met end to end, in production.

Minor observations, none rising to a finding: `OwnerEmailResolver.get_owner_email_for_project` types
its argument as `object` (harmless — no type checker is configured); the serial worker plus a 10s
SMTP timeout means an unreachable SMTP server can delay the next job by that much (documented in
`architecture.md` as the number to revisit if volume grows).

## 3. Doc versions created (pass-only consolidation)

Each was created with `doc-new-version --source P13.REVIEW`, edited at the returned `edit_path`
only, then `rebuild-docs` (`docs/current/*.md` regenerated; no hand-edits, no old version patched).

| Doc | Version | What it captures |
| --- | --- | --- |
| `backend` | `v0006` | New "P13 Additions" section: the owner-email primitive (join shape, the anchor as the multi-tenant guarantee, oldest-wins, `None` ≠ exception), the five `VOCKY_SMTP_*` settings + `smtp_from_value`/`smtp_configured`, and all of `notifications.py` including its deliberate no-swallow exception policy and the no-new-dependency fact |
| `architecture` | `v0011` | New "Feedback Alert Hook and Its Containment" section with the actual call-site code and **why placement, not clause ordering, is what prevents duplicate feedback rows**; the accepted no-DLQ tradeoff; the `to_thread`/10s latency note. Also: status paragraph (first outbound email path), the `VOCKY_SMTP_*` entry in the Configuration Surface list, and the "exactly three interpolated secrets" line corrected to four |
| `operations` | `v0007` | Box-secrets table gains `VOCKY_SMTP_PASSWORD` (three → four, "all four fail loudly"); new "SMTP feedback alerts" section — the five vars with prod `:?` vs dev `:-` and why, worker-only placement, why `deploy.sh` must not gain a second enforcement point, the changple5 Django→vocky mapping table with `docker exec … env` as the discovery method that actually worked, the live non-secret endpoint, the two-part live verification, and triage by failure shape. Also extends the `env -u` warning box to the SMTP guards |
| `security` | `v0010` | "All three box secrets" corrected to four; new "Outbound Email" section — recipient is **derived, never supplied**, what content leaves the box and to whom, worker-only credential placement, and the failure mode stated as a durability (not security) tradeoff |
| `qa` | `v0003` | Suite recount 29 files/215 tests → **30/225** (verified by `--collect-only`), the new `test_notifications` cluster and where containment is tested, the stale "`ruff check` is clean but not gated" line replaced with the truth that **no lint/type step exists at all**, and a new "Verifying feedback email alerts" section (nothing automated ever sends mail; both halves required; the 2026-08-04 baseline) |

`security` and `qa` go beyond the Doc impact list, deliberately. Both were judgment calls, and both
are corrections of statements this phase made false: `security.md` asserted "all three box secrets",
and `qa.md` asserted a test count and a ruff status that three slices had already contradicted in
their notes. Leaving either would have shipped a doc set that disagrees with the repo.

## 4. Deferred-job recommendation (recommended, NOT created — I may not run `defer-job`)

`phase.md`'s open question — does Decision 2's lost-alert tradeoff warrant a retry/outbox? —
**yes, as a deferred job; no, as work to do now.** The tradeoff is sound at current volume and the
containment that creates it is the right call, but "a failed alert is visible only in the worker's
log" has no operator-facing signal at all, and nobody watches worker logs continuously.

- **title**: `Retry or outbox for failed feedback alert emails`
- **reason**: A feedback alert that fails to send is logged (`Feedback alert failed for job …`) and
  lost — no retry, no queue, no operator-visible signal. Deliberate in P13 (Decision 2: containment
  had to be total, and a notify DLQ would have been a queue with no consumer or drain tooling), and
  acceptable while the feedback itself is durably stored and readable in the app. It stops being
  acceptable once someone actually relies on the email as their notification channel.
- **trigger**: A real alert is observed missing/failed on the box, **or** feedback volume grows past
  the single-owner scale, **or** any work adds a second notification channel or a preferences
  surface (the natural moment to introduce a real outbox rather than bolt retry onto the hook).
- **source**: `P13.REVIEW`

## 5. Deviations from plan.md

- The plan's expected doc set was `backend` / `architecture` / `operations` (+ `qa` at my
  discretion). I created all four **plus `security`**, for the reason in §3 — the plan explicitly
  left final wording and warrant to my judgment.
- `qa` was **not** skipped. The plan framed it as "only if the live-verification path is worth
  recording"; it also turned out to carry two now-false facts this phase moved, so the version does
  both jobs.
- Nothing else. No source code was touched (review slice rule), no status transitioned, nothing
  committed, `defer-job` recommended rather than run.

`explain`: not written — run `/explain` for this phase.
