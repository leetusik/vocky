# Plan — P13.REVIEW: phase review of "Feedback email alerts over SMTP"

## Context

All five middle slices are done. S1–S4 landed code (owner-email lookup → settings + notifier →
worker hook → compose/env plumbing); S5 was the operator-gated bring-up, closed with live
acceptance evidence: the operator deployed with changple5's SMTP credentials
(`mail.privateemail.com:587`, user `hi@hi2vi.com`) and confirmed a real alert email arrived for a
real captured feedback event. Read `works/phases/active/P13/phase.md` end to end (decomposition,
decisions 1–3, codebase facts, every per-slice notes section, the Doc impact list) and
`works/phases/active/P13/intent.md`, plus each slice's `plan.md`/`result.md`.

## 1. Validate all slices together

- `python3 scripts/workflow.py validate` — state integrity.
- `uv run pytest -q` — the whole suite (expected 225 passing; needs the test DB at
  `127.0.0.1:55432` — the dev compose Postgres. Report honestly if unreachable).
- Compose guards (S4's validation, re-run):
  - `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x VOCKY_SMTP_HOST=x
    VOCKY_SMTP_USER=x VOCKY_SMTP_PASSWORD=x docker compose -f compose.prod.yml config --quiet`
    → exit 0.
  - Same minus `VOCKY_SMTP_PASSWORD` → non-zero with the `:?` error.
  - `docker compose -f docker-compose.yml config --quiet` with no SMTP vars → exit 0.

## 2. Review against objective / intent / docs

Judge the phase against `phase.md`'s Objective and `intent.md`'s confirmed intent. Specifically
verify in the code (read, don't re-implement):

- One plain-text email per persisted event, addressed to the owning org's owner via the S1 3-join
  (role='owner' filter present; oldest-wins tie-break; multi-tenant leak impossible for a wrong
  project).
- Unconfigured SMTP ⇒ cleanly disabled: no raise, no per-job ERROR spam, worker unaffected.
- The containment invariant: the notify call sits structurally outside the persistence
  `try:`/except path; no alert failure can reach `requeue_job`/`dead_letter_job` (this is the
  phase's one real trap — check the actual code shape in `src/vocky/worker.py`, not just the
  tests).
- Scope wall respected: no preferences/digests/UI/HTML mail crept in; no new dependencies (core
  OR server extra); CLI deps untouched.
- Secrets hygiene: no real credential anywhere in the repo; SMTP vars on the worker service only;
  compose header prose and `.env.prod.example` prose consistent with each other.

## 3. Verdict and (pass-only) doc consolidation

**On `pass` only**, consolidate `phase.md`'s Doc impact list into new doc versions with
`python3 scripts/workflow.py doc-new-version --doc <name> --summary "..." --source P13.REVIEW`
(then confirm `docs/current/*.md` regenerated). Write docs only — never source. Expected set,
per the Doc impact list (use your judgment on final wording and whether each is truly warranted):

- `backend` — S1's owner-email primitive; S2's `VOCKY_SMTP_*` settings + `smtp_configured` gate +
  `src/vocky/notifications.py` module.
- `architecture` — S3's post-persist alert hook, DI wiring, and the swallow-and-log containment
  rule.
- `operations` — S4's SMTP block (fourth box secret, required-vs-optional forms, worker-only
  placement) + S5's bring-up runbook facts (Django→vocky var mapping, discovery commands, the
  live SMTP endpoint facts recorded in the S5 acceptance note).
- `qa` only if you judge the live-verification path worth recording there; otherwise skip it and
  say so.

A `changes_requested` or `blocked` verdict **stops before consolidation**: complete validation and
judgment first so the whole picture arrives in one cycle, then return the verdict with numbered
findings and proposed fix slices (names + one-line scopes) — do not run `doc-new-version`.

## 4. Deferred-job candidate (recommend only — you may NOT run `defer-job`)

Phase.md's open question: whether the lost-alert-on-failure tradeoff (Decision 2) warrants a
retry/outbox deferred job. Give a recommendation (title/reason/trigger) in your return; the
orchestrator will create it if warranted.

## Wrap-up

Write `result.md` (free-form): validation evidence, judgment per intent bullet, doc versions
created (pass only), the defer-job recommendation. Do NOT transition any slice/phase status and do
NOT commit — the orchestrator records the verdict via `review-phase`.

Return: `review_verdict` (pass | changes_requested | blocked), numbered findings (empty on pass),
proposed fix slices (if any), doc versions created, the defer-job recommendation, and the fixed
pointer `explain: not written — run /explain for this phase`.
