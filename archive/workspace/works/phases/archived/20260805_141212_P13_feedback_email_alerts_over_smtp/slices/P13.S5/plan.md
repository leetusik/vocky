# Plan — P13.S5: production bring-up — changple5 SMTP credentials + live alert verification

## Context

Read `works/phases/active/P13/phase.md` first — especially the P13.S4 notes (the exact box-`.env`
var list) and the intent: production reuses the SMTP account changple5 already uses. The
credentials live ONLY on the box (reading another project's env was permission-blocked once at
phase creation), so this slice is **operator-gated by construction**.

**Your job is to author the runbook, not to run it.** You never SSH, never invent credentials,
never deploy. You prepare the exact box runbook, write it into this slice's `result.md`, and
return **`needs_operator`** with the runbook so the orchestrator can hand it to the operator. The
operator's confirmation of a real received alert email is this slice's acceptance evidence.

## The runbook must cover (be concrete, command-level)

1. **Ship the code**: the box deploys from `origin/main` (`deploy/deploy.sh [ref]`, run on the box
   from `/home/opc/vocky`, per the script header). Note that P13.S1–S4 must be pushed to
   `origin/main` first (the operator pushes — we never push), and that `deploy.sh` will now FAIL
   its compose interpolation until the SMTP vars are in the box `.env` (`:?` guards from S4) — so
   env-first, deploy-second is the required order.
2. **Read changple5's SMTP settings on the box**: changple5 is a Django app, so its env speaks
   Django email names. Give 2–3 discovery commands with fallbacks, e.g. grepping likely env files
   (`grep -iE 'email|smtp' /home/opc/changple5/.env` — adjust path guesses to what you can infer)
   and, most robust, reading the running container's environment
   (`docker ps` to find the changple5 app container, then
   `docker exec <container> env | grep -iE 'email|smtp'`).
3. **Map Django names → vocky names** (the operator maps whatever they find):
   `EMAIL_HOST → VOCKY_SMTP_HOST`, `EMAIL_PORT → VOCKY_SMTP_PORT` (587 STARTTLS / 465 SSL —
   vocky picks SSL iff port is 465), `EMAIL_HOST_USER → VOCKY_SMTP_USER`,
   `EMAIL_HOST_PASSWORD → VOCKY_SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL → VOCKY_SMTP_FROM` (optional —
   blank falls back to the user). Include the "append to `/home/opc/vocky/.env`" step with the
   exact five lines to fill.
4. **Deploy**: `cd /home/opc/vocky && deploy/deploy.sh` (defaults to `origin/main`). Note the
   worker is recreated on every deploy, so it picks up the new env; no separate step needed.
5. **Verify live**: capture one real feedback event (any of the existing paths — the vocky CLI
   with a project credential, or a POST to `/api/feedback` — reuse whatever the operator already
   uses; `docs/current/qa.md` may have the QA capture path if you want to reference it), then:
   - `docker logs vocky-worker --since 5m` shows the persisted-job line and NO
     "Feedback alert failed" line;
   - the org owner's inbox (the operator's own account email) received the plain-text alert.
6. **Failure triage**, one line each: `:?` abort at deploy → var missing in `.env`; alert-failed
   log line → credentials/TLS mismatch (retry port 465 vs 587); email absent but no error →
   check spam, check `VOCKY_SMTP_FROM` validity as a sender the SMTP account may use.

## What you may do in the repo

Nothing outside the slice folder and `phase.md`. This slice changes no code, no compose, no docs
(`operations.md`'s durable version is the REVIEW slice's consolidation job — S4 already left the
Doc impact line; add one more only if the runbook adds durable truth worth recording, phrased as a
one-liner under Doc impact, e.g. the Django→vocky var mapping).

## Wrap-up

- Write the full runbook into `result.md` (it IS the deliverable).
- Append a short "P13.S5 notes" section to `phase.md` (runbook location + what confirmation is
  awaited from the operator).
- Return **`needs_operator`** (NOT `done`) with: a one-paragraph summary, the runbook location,
  and the explicit list of what the operator must do and confirm back (the received email is the
  acceptance evidence). Only the operator can complete this slice.
