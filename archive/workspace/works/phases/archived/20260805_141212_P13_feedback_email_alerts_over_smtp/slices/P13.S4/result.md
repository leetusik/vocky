# Result — P13.S4: SMTP env/compose/deploy plumbing (prod + dev)

## What was done

Pure env/compose/doc plumbing, no application code, per `plan.md`.

1. **`compose.prod.yml`** — worker service `environment:` block gained the five SMTP
   vars, following Decision 3's recommended forms:
   - `VOCKY_SMTP_HOST: ${VOCKY_SMTP_HOST:?VOCKY_SMTP_HOST is required — set it in the box .env}`
   - `VOCKY_SMTP_PORT: ${VOCKY_SMTP_PORT:-587}`
   - `VOCKY_SMTP_USER: ${VOCKY_SMTP_USER:?VOCKY_SMTP_USER is required — set it in the box .env}`
   - `VOCKY_SMTP_PASSWORD: ${VOCKY_SMTP_PASSWORD:?VOCKY_SMTP_PASSWORD is required — set it in the box .env}`
   - `VOCKY_SMTP_FROM: ${VOCKY_SMTP_FROM:-}`

   Added only to the `worker` service (not `api`/`web`), with a short comment above
   the block explaining the worker-is-sole-sender invariant and why HOST/USER/PASSWORD
   use `:?` while PORT/FROM use `:-`. The file header prose was updated: "three
   secrets... all three use the `:?` form" became "four... VOCKY_SMTP_PASSWORD... All
   four use the `:?` form", with VOCKY_SMTP_HOST/VOCKY_SMTP_USER called out as also
   `:?` (required but not secret) and VOCKY_SMTP_PORT/VOCKY_SMTP_FROM as optional
   `:-` config. The existing "no `env_file:`" isolation prose was left intact.

2. **`.env.prod.example`** — header changed from "three secrets... ALL THREE ARE
   REQUIRED" to "four secrets... plus VOCKY_SMTP_HOST/VOCKY_SMTP_USER which are
   required but not secret... plus optional config" — worded to match
   `compose.prod.yml`'s header so the two don't drift. Added a commented SMTP section
   after `VOCKY_ADMIN_AUTH_TOKEN=` with `VOCKY_SMTP_HOST=`/`VOCKY_SMTP_USER=`/
   `VOCKY_SMTP_PASSWORD=` (REQUIRED) and `VOCKY_SMTP_PORT=`/`VOCKY_SMTP_FROM=`
   (optional, with default-587 / defaults-to-user prose), plus the prose: these are
   copied from the SMTP account changple5 already uses in production, read out of
   changple5's env on the box at bring-up (P13.S5's runbook covers the exact
   mapping), worker service only, alerts go to each org owner's account email.

3. **`docker-compose.yml`** (dev) — worker service `environment:` block gained the
   mirrored optional form: `VOCKY_SMTP_HOST/USER/PASSWORD/FROM: ${...:-}`,
   `VOCKY_SMTP_PORT: ${...:-587}`, with one short comment noting the local stack
   starts fine unconfigured and runs with alerts disabled.

4. **`.env.example`** (dev) — added the commented block from the plan verbatim,
   directly after the `VOCKY_ADMIN_AUTH_TOKEN` precedent line.

### Not changed (per plan)

- `deploy/deploy.sh` — no secret list added; compose's `${VAR:?}` remains the single
  enforcement point.
- No `api`/`web` service changes, no application code, no CI changes.

## Validation

All three plan-specified commands run from repo root:

1. `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x VOCKY_SMTP_HOST=x
   VOCKY_SMTP_USER=x VOCKY_SMTP_PASSWORD=x docker compose -f compose.prod.yml config
   --quiet` — **PASS** (exit 0), all seven required vars present, `VOCKY_SMTP_PORT`/
   `VOCKY_SMTP_FROM` fall back to their defaults.

2. Same command with `VOCKY_SMTP_PASSWORD` unset — **PASS (negative test confirms the
   guard)**: exit code 1, error:
   `error while interpolating services.worker.environment.VOCKY_SMTP_PASSWORD:
   required variable VOCKY_SMTP_PASSWORD is missing a value: VOCKY_SMTP_PASSWORD is
   required — set it in the box .env`

3. `docker compose -f docker-compose.yml config --quiet` (no SMTP vars set, via `env
   -u` to strip any leaked from the shell) — **PASS** (exit 0), dev stack stays
   optional.

4. `uv run pytest -q` — **skipped**, no code changed (per plan).

## Deviations from plan

None. All four files changed exactly as specified; interpolation forms match
Decision 3's recommendation; header prose in `compose.prod.yml` and
`.env.prod.example` kept coherent with each other (both now say "four secrets... all
four use `:?`... VOCKY_SMTP_HOST/USER also `:?` but not secret... PORT/FROM optional
`:-`").

## Doc impact

Recorded to `phase.md`: `operations.md` will need the SMTP block documented — the
fourth box secret (`VOCKY_SMTP_PASSWORD`), the required-vs-optional interpolation
forms for all five `VOCKY_SMTP_*` vars, and the worker-only placement invariant.

## Notes for S5

Exact box-`.env` var names the operator must fill on the vocky.hi2vi.com box (read
out of changple5's own env, per the phase's SMTP-account-reuse plan):

- `VOCKY_SMTP_HOST=` (required)
- `VOCKY_SMTP_USER=` (required)
- `VOCKY_SMTP_PASSWORD=` (required — the secret)
- `VOCKY_SMTP_PORT=` (optional, default 587 if omitted)
- `VOCKY_SMTP_FROM=` (optional, defaults to `VOCKY_SMTP_USER` if omitted)

After filling `.env` on the box, a normal `deploy/deploy.sh` run (or `docker compose
-f compose.prod.yml up -d worker` to only recreate the worker) picks these up — no
other deploy-script change was needed or made.
