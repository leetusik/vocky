# Plan — P13.S4: SMTP env/compose/deploy plumbing (prod + dev)

## Context

Read `works/phases/active/P13/phase.md` first — Decision 3 (where the SMTP vars live and their
interpolation forms) and the S2 notes (the settings: `VOCKY_SMTP_HOST`, `VOCKY_SMTP_PORT`
(default 587), `VOCKY_SMTP_USER`, `VOCKY_SMTP_PASSWORD`, `VOCKY_SMTP_FROM` (falls back to
`smtp_user`); alerts enabled iff host + effective-from are non-blank). No application code in this
slice — files are `compose.prod.yml`, `.env.prod.example`, `docker-compose.yml`, `.env.example`.

The **worker** is the sole sender: SMTP vars go on the worker service's `environment:` block ONLY —
never on `api` or `web` (per-service secret isolation is an explicit compose invariant).

## Changes

### 1. `compose.prod.yml` — worker service env block

Add the five vars, with these forms (my call, following Decision 3's reasoning):

- `VOCKY_SMTP_HOST: ${VOCKY_SMTP_HOST:?...}` — required: production *intends* alerts on, and a
  blank host silently disables them, which is exactly the quiet degradation the `:?` convention
  exists to prevent.
- `VOCKY_SMTP_PORT: ${VOCKY_SMTP_PORT:-587}` — config with a sane default, not required.
- `VOCKY_SMTP_USER: ${VOCKY_SMTP_USER:?...}` — required (the changple5 account authenticates).
- `VOCKY_SMTP_PASSWORD: ${VOCKY_SMTP_PASSWORD:?...}` — required; THE fourth box secret.
- `VOCKY_SMTP_FROM: ${VOCKY_SMTP_FROM:-}` — optional; blank falls back to `smtp_user` in config.py.

Each with a short error message in the `:?` form matching the existing style ("... is required —
set it in the box .env"). Add a brief comment above the block (worker is the sole sender; the api
never sends; alerts cleanly disable when unconfigured — but prod requires them on).

**Header prose**: the compose header says "POSTGRES_PASSWORD, SESSION_SECRET, and
VOCKY_ADMIN_AUTH_TOKEN are `${VAR:?err}` interpolations... All three use the `:?` form". Update it
coherently: the box `.env` now carries the SMTP block too — one new secret (`VOCKY_SMTP_PASSWORD`)
plus its non-secret companions (`VOCKY_SMTP_HOST`/`USER` required, `PORT`/`FROM` optional). Keep
the "no `env_file:`" isolation prose intact. Do not let the counts drift from
`.env.prod.example`'s.

### 2. `.env.prod.example`

- Header: "three secrets" language becomes four-secrets-and-a-config-block, staying consistent
  with the compose header (the two must not drift — say the same thing in both).
- Add a commented SMTP section after `VOCKY_ADMIN_AUTH_TOKEN`:
  - `VOCKY_SMTP_HOST=` (REQUIRED), `VOCKY_SMTP_USER=` (REQUIRED), `VOCKY_SMTP_PASSWORD=`
    (REQUIRED — the secret), `VOCKY_SMTP_PORT=` (optional, default 587), `VOCKY_SMTP_FROM=`
    (optional, defaults to VOCKY_SMTP_USER).
  - Prose: these are copied from the SMTP account changple5 already uses in production (the
    operator reads them out of changple5's env on the box at bring-up — P13.S5's runbook covers
    the exact mapping); worker service only; feedback alerts go to each org owner's account email.

### 3. `docker-compose.yml` (dev) — worker service env block

Mirror the five vars in the `:-` empty-default form so a local stack with no SMTP configured
starts fine and runs with alerts disabled:
`VOCKY_SMTP_HOST: ${VOCKY_SMTP_HOST:-}`, `VOCKY_SMTP_PORT: ${VOCKY_SMTP_PORT:-587}`,
`VOCKY_SMTP_USER: ${VOCKY_SMTP_USER:-}`, `VOCKY_SMTP_PASSWORD: ${VOCKY_SMTP_PASSWORD:-}`,
`VOCKY_SMTP_FROM: ${VOCKY_SMTP_FROM:-}`. One short comment line.

### 4. `.env.example` (dev)

Add a commented block in the existing style (see the `VOCKY_ADMIN_AUTH_TOKEN` precedent):

```
# Optional SMTP transport for feedback email alerts (sent by the worker to each org
# owner's account email). Leave unset to run with alerts disabled.
# VOCKY_SMTP_HOST=
# VOCKY_SMTP_PORT=587
# VOCKY_SMTP_USER=
# VOCKY_SMTP_PASSWORD=
# VOCKY_SMTP_FROM=
```

### NOT changed

- `deploy/deploy.sh` — carries no secret list by design; compose's `${VAR:?}` is the single
  enforcement point. Do not add a second one.
- No api/web service changes, no application code, no CI changes.

## Validation

- `docker compose -f compose.prod.yml config --quiet` with the seven required vars exported as
  dummies (`POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`, `VOCKY_SMTP_HOST`,
  `VOCKY_SMTP_USER`, `VOCKY_SMTP_PASSWORD`, plus nothing else) — must pass.
- Same command with `VOCKY_SMTP_PASSWORD` unset — must FAIL with the `:?` error (proves the guard).
- `docker compose -f docker-compose.yml config --quiet` with NO SMTP vars set — must pass (dev
  stays optional).
- `uv run pytest -q` is not needed (no code changed) — skip it; say so in result.md.

## Wrap-up

Write `result.md`; append to `phase.md`: a cross-slice note for S5 listing the exact box-`.env`
var names the operator must fill, and one "Doc impact" line (`operations.md`: the SMTP block —
fourth box secret, required-vs-optional forms, worker-only placement).
