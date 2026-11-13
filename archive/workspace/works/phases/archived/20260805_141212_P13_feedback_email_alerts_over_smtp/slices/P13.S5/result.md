# Result — P13.S5: production bring-up — changple5 SMTP credentials + live alert verification

**Status: `needs_operator`.** This slice authors the box runbook only. The executor never SSHed,
never deployed, and never invented or read a credential — the SMTP secrets live only on the box's
gitignored `.env` and on changple5's own env, both outside this repo's reach.

Everything below is the deliverable. Follow it in order on the box (`ssh oracle-cloud` =
`opc@140.245.64.173`, per `docs/current/operations.md`). All commands assume the box shell,
`cd /home/opc/vocky` unless stated otherwise.

---

## 0. Preconditions

- P13.S1–S4 must be on `origin/main` **before** you start (the operator pushes — this workspace
  never pushes). Verify locally first:
  ```
  git log --oneline -5 origin/main   # should show the P13.S1..S4 commits
  ```
- `deploy/deploy.sh` will now **fail** its `docker compose` interpolation until
  `VOCKY_SMTP_HOST` / `VOCKY_SMTP_USER` / `VOCKY_SMTP_PASSWORD` are in the box `.env` — the
  `${VAR:?...}` guards `P13.S4` added to `compose.prod.yml`'s `worker` service abort `docker
  compose` itself (not just the app) when any of the three is unset or blank. **Env-first,
  deploy-second is required** — do not run `deploy/deploy.sh` before step 3 below.

## 1. Ship the code (box)

```
cd /home/opc/vocky
git fetch --prune
git log origin/main --oneline -5     # confirm P13.S1..S4 are present
```

Do **not** `deploy/deploy.sh` yet — that is step 4, after the env is filled (step 3).

## 2. Read changple5's SMTP settings on the box

changple5 is a Django app, so its env speaks Django's email settings names
(`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`).
Try these in order — stop at the first that yields real values:

**a. Grep a likely env file next to the changple5 checkout** (path is a guess — the vhost is
named `changple5.conf` in the shared edge, so the sibling-project convention on this box is
`/home/opc/<project>`; adjust if the actual clone lives elsewhere):
```
grep -iE 'email|smtp' /home/opc/changple5/.env
```
If that path doesn't exist, list what's actually on the box to find it:
```
ls -la /home/opc/ | grep -i changple
```

**b. Grep a Django `settings.py` / `.env.production` variant** if (a) shows nothing (some Django
apps keep email config in a separate settings module rather than `.env`):
```
grep -riE 'email_host|email_port|default_from_email|smtp' /home/opc/changple5/*/settings*.py 2>/dev/null
grep -iE 'email|smtp' /home/opc/changple5/.env.production 2>/dev/null
```

**c. Most robust — read the running container's actual environment** (works regardless of where
the source file lives, since this is what Django actually loaded):
```
docker ps --format 'table {{.Names}}\t{{.Image}}' | grep -i changple
docker exec <changple5-container-name> env | grep -iE 'email|smtp'
```
(`<changple5-container-name>` — read it off the `docker ps` output above; do not guess it.)

Record the five values you find (host, port, user, password, from-address — `from` may be
blank/absent, that's fine) before moving to step 3.

## 3. Map Django names → vocky names, fill the box `.env`

| Django name (changple5)   | vocky name (`/home/opc/vocky/.env`) | Notes |
|---|---|---|
| `EMAIL_HOST`               | `VOCKY_SMTP_HOST`     | required |
| `EMAIL_PORT`                | `VOCKY_SMTP_PORT`     | optional, default `587`. vocky picks SSL iff the port is exactly `465`, else STARTTLS on `587`/anything else — set it to whatever changple5 uses (typically `587` or `465`) |
| `EMAIL_HOST_USER`           | `VOCKY_SMTP_USER`     | required |
| `EMAIL_HOST_PASSWORD`       | `VOCKY_SMTP_PASSWORD` | required, the secret |
| `DEFAULT_FROM_EMAIL`        | `VOCKY_SMTP_FROM`     | optional — if blank, vocky's `Settings.smtp_from_value` falls back to `VOCKY_SMTP_USER`, so it is safe to leave unset |

Append exactly these five lines to `/home/opc/vocky/.env` (the file already has
`POSTGRES_PASSWORD` / `SESSION_SECRET` / `VOCKY_ADMIN_AUTH_TOKEN` from P12 — do not touch those;
`.env.prod.example` in this repo already documents this block as a template, so `.env` should
already have empty placeholders for these five keys if the box pulled `origin/main` past S4 —
check first with `grep -c VOCKY_SMTP /home/opc/vocky/.env` before appending, to avoid duplicate
keys):

```
VOCKY_SMTP_HOST=<value from step 2>
VOCKY_SMTP_PORT=<value from step 2, or leave blank/omit for the 587 default>
VOCKY_SMTP_USER=<value from step 2>
VOCKY_SMTP_PASSWORD=<value from step 2>
VOCKY_SMTP_FROM=<value from step 2, or leave blank/omit to fall back to VOCKY_SMTP_USER>
```

If the file already has the five placeholder keys (blank `KEY=`), edit those lines in place
instead of appending duplicates — a duplicate key in a `.env` file is read inconsistently by
different tools and should be avoided.

Sanity-check the compose interpolation resolves before deploying:
```
docker compose -f compose.prod.yml config --quiet && echo "compose config OK"
```
(This must print `compose config OK` with no `:?` error. If it errors, see Failure Triage #1.)

## 4. Deploy

```
cd /home/opc/vocky
deploy/deploy.sh
```
(No ref argument — defaults to `origin/main`, which already carries P13.S1–S4 per step 1.)

The worker container is unconditionally recreated by `deploy.sh` (`docker compose up -d` in step
6 of the script, after the image build + migration), so it picks up the newly-filled SMTP env
automatically — no separate restart step is needed. Watch for the script's final line:
`DONE — ref <ref> live ...`. If it instead calls `rollback_or_die`, see Failure Triage.

## 5. Verify live

Capture one real feedback event. Reuse whichever path is already at hand on the box or from a
dev machine that can reach `https://vocky.hi2vi.com`:

- **Easiest — `make external-smoke`** from a local checkout of this repo (does a full
  signup → project → ingest-key → `POST /api/feedback` → poll round trip against the real
  external URL):
  ```
  VOCKY_EXTERNAL_BASE_URL=https://vocky.hi2vi.com make external-smoke
  ```
  This creates a throwaway account/project, so the resulting alert email goes to that throwaway
  account's owner — **use the account/project you actually want alerted instead** if you want the
  live email to land in your own inbox (see the next bullet).
- **Or** — a manual `POST /api/feedback` with an existing project's `vk_` ingest key (whatever
  the operator already has for a real project whose owner is the operator's own account), per
  `docs/current/qa.md`'s smoke description: hit `POST https://vocky.hi2vi.com/api/feedback` with
  the ingest key, wait a few seconds for the worker to persist it.
- **Or** — the `vocky` CLI capture path (`vocky capture ...`) against a real project, if that is
  what's normally used to test this box.

Whichever path you use, then confirm both of the following on the box:

1. **Worker log shows persistence with no alert failure:**
   ```
   docker logs vocky-worker --since 5m
   ```
   Expect a line showing the job was persisted (feedback event created), and **no**
   `"Feedback alert failed"` (or equivalent `logger.exception` traceback) line. A clean run has
   nothing more than the normal persistence log line for that job.

2. **The org owner's inbox received the plain-text alert.** Check the account email of the
   project's owning org's owner (the operator's own account email if you used the operator's own
   project/account in step 5's capture). It should be one plain-text email with the feedback
   content, sent `From:` either the configured `VOCKY_SMTP_FROM` or `VOCKY_SMTP_USER` (whichever
   applies per step 3's fallback rule).

**Acceptance evidence for this slice: a real received alert email, confirmed back by the
operator.** Nothing else closes this slice.

## 6. Failure triage

- **`deploy/deploy.sh` (or the `docker compose config --quiet` sanity check in step 3) aborts with
  a `:?` error** (e.g. `VOCKY_SMTP_HOST is required — set it in the box .env`) → one of
  `VOCKY_SMTP_HOST` / `VOCKY_SMTP_USER` / `VOCKY_SMTP_PASSWORD` is missing or blank in
  `/home/opc/vocky/.env` — re-check step 3's five lines were actually saved (watch for a stray
  duplicate key further down the file shadowing the one you edited).
- **Deploy succeeds, worker running, but `docker logs vocky-worker` shows a
  `"Feedback alert failed"` / `logger.exception` line after a capture** → credentials or TLS
  mismatch between what's in `.env` and what changple5's SMTP account actually expects. Most
  common fix: retry with the other port (`465` for implicit SSL vs `587` for STARTTLS) —
  `VOCKY_SMTP_PORT=465` if you set `587` or vice versa — then re-run `deploy/deploy.sh` (or
  `docker compose -f compose.prod.yml up -d worker` to recreate just the worker without a full
  rebuild) and retry step 5.
- **No error in the worker log, but the email never arrives** → check spam/junk on the receiving
  inbox first; if still nothing, check that `VOCKY_SMTP_FROM` (or the `VOCKY_SMTP_USER` fallback)
  is a sender address the SMTP account is actually authorized to send *as* — some SMTP providers
  silently drop or bounce-to-nowhere a send whose `From:` doesn't match an authorized identity on
  the account, even though the SMTP transaction itself reports success.

---

## What the operator must do and confirm back

1. Push P13.S1–S4 to `origin/main` (if not already done).
2. SSH to the box and follow steps 2–5 above: read changple5's SMTP settings, fill the five
   `VOCKY_SMTP_*` lines in `/home/opc/vocky/.env`, run `deploy/deploy.sh`, capture one feedback
   event, and confirm:
   - `docker logs vocky-worker --since 5m` shows persistence with no alert-failed line, **and**
   - a real plain-text alert email landed in the org owner's inbox.
3. Report back which of the two verification checks passed (ideally paste the relevant
   `docker logs` snippet, redacting nothing sensitive since worker logs carry no credentials) and
   confirm the received email — that confirmation is this slice's acceptance evidence, at which
   point the orchestrator can move this slice out of `pending`/`needs_operator` and finish it.
4. If Failure Triage doesn't resolve an issue, report the exact error/log line back so the
   runbook (or the notifier module itself) can be revisited.

## Notes on scope discipline

- No code, compose, or doc file was touched by this slice — only this `result.md` and the
  "P13.S5 notes" section appended to `phase.md`.
- The Django→vocky var mapping table above is new durable-ish detail; a one-line "Doc impact" note
  was added to `phase.md` for `P13.REVIEW` to fold into `operations.md`'s consolidated SMTP
  bring-up section (matching what `P13.S4` already flagged there).
- `deploy/deploy.sh` needed no change to support this (confirmed again, consistent with S4's
  finding): the `:?` guard in `compose.prod.yml` is the sole enforcement point for the SMTP
  secrets, same as the existing three box secrets.
