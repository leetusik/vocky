# Plan — P12.REVIEW: Phase review of "Production launch & hardening"

Mode: `/do-whole-phase auto` (orchestrator planned inline).
Executor: `slice-executor-high` (review is always top tier).

## What you are reviewing

Phase P12 took vocky live. Seven middle slices, all `done`: S1 (admin fail-closed), S2 (hygiene sweep:
Makefile token, prettier ×14, design-token renames), S3 (in-process `/auth/*` rate limiter, closed D5),
S4 (`co-work` — the production bring-up; vocky is **live** at `https://vocky.hi2vi.com`), S5
(backup/restore/status artifacts + log caps), S6 (`ci.yml` pytest job + prettier gate; first runner
execution green), S7 (qa.md v0002 body authored into its `result.md`).

Read, in order: `phase.md` end to end (the notebook is long — every section is evidence),
`intent.md`, each slice's `plan.md` + `result.md`, and the docs the phase touches.

**Cross-repo context, already resolved — do not flag it:** the edge vhost deliberately moved to the
edge repo (`~/projects/personal/edge`), whose phase P6 adopted `vocky.conf`, added the `edge-deploy`
workflow, deployed it (first run green), and **passed its own phase review** (edge commit `2708c65`).
vocky's `deploy/vocky.conf` is now the pointer `deploy/vocky.conf.md`. That is the intended end state.

## Validation — all slices together

Run and report actual output:

1. `python3 scripts/workflow.py validate`.
2. Full Python suite from repo root against a reachable Postgres (the sandbox has `vocky-postgres-1`;
   S7 measured 215 passed): `DATABASE_URL=… TEST_DATABASE_URL=… uv run pytest -q`. This covers S1
   (admin fail-closed tests), S3 (limiter tests), and the P10 chain CI now gates.
3. Web suite from `web/`: `pnpm lint && pnpm typecheck && pnpm test && pnpm format:check` (covers S2 +
   S6's gate premise). `make check-skill-parity`.
4. S5 artifacts: `bash -n deploy/backup.sh deploy/status.sh`;
   `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml config`
   rendered and checked: 5/5 services carry the `10m`/`3` logging cap; config exits 0.
5. S4 (live, read-only, public URLs only — **no ssh, no box contact**):
   `curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com{/healthz,/,/install.sh,/SKILL.md}`
   → all 200; served `/SKILL.md` still `cmp`-clean against `skills/vocky-feedback/SKILL.md`.
6. S6: `gh run list -R leetusik/vocky --limit 3` if `gh` is available (first run `30873072664` was
   green); otherwise note it as verified by the orchestrator on 2026-08-04.

## Judgment

Review the phase against its objective (`phase.json`) and `intent.md`: launch executed operator-gated;
D5 closed with an origin limiter despite the forbidden edge zone; CI gate real and proven; qa.md
authored; `/admin/api/*` decided (keep, fail-closed); backups/log/metrics present as artifacts with the
on-box application correctly left operator-gated; out-of-scope items (D3, feature work) untouched.
Check the D5 bookkeeping caveat resolved (D5 `dropped` with a "resolved, not abandoned" reason) and D7
opened for the QA driver.

Complete ALL validation and judgment before deciding the verdict, so every finding lands in one cycle.

## On a PASS only — consolidate the durable docs

`phase.md` § *Doc impact* (all entries, S1 through S7) is your authoritative checklist. Consolidate
into **one new version per touched doc** via
`python3 scripts/workflow.py doc-new-version --doc <id> --summary "…" --source P12.REVIEW` — the only
workflow command you may run besides `validate`/`docs`. Never hand-edit `docs/current/*` (generated) or
old `docs/versions/*` files; author each new version file the command creates. Expected surface (verify
against the actual Doc impact list, which wins over this summary):

- **operations.md** — the big one: "vocky is NOT deployed" → live (first deploy `6c16ac5`, 2026-08-04);
  the bring-up checklist executed (all probes flipped, Cloudflare-not-a-barrier proven, clean-env
  install 0.2.0, cache policy answered: deliberately uncached); the edge vhost step now "dispatch the
  edge repo's `edge-deploy` workflow" (scp path retired, `deploy/vocky.conf` → pointer); `/auth/*`
  origin limiter (S3) replacing the "no origin rate limit" gap; `ci.yml` section updated (pytest +
  format gates, exclusions closed, first run green); backups/restore/status (S5) + log caps with the
  recreate caveat; first-deploy `:previous` note.
- **qa.md** — paste the v0002 body **verbatim** from `P12.S7/result.md` § "Proposed qa.md v0002 body";
  do not re-derive or summarize it.
- **architecture.md** (`:150`) and **api.md** (`:637`) — stale `deploy/vocky.conf` references → the
  edge repo/pointer reality; architecture also gets S3's limiter and S1's fail-closed middleware if its
  text describes the old behavior (check).
- **security.md** — S1 (fail-closed admin auth, 503-when-unconfigured, `${VAR:?}` hardening) and S3
  (limiter: 20/900s per IP+route, `X-Real-IP` precedence) if its text is now stale (check).
- **product.md / experience.md / frontend.md** — the "not deployed" echoes only; smallest honest edit.

Fewer versions is fine when a Doc impact line turns out already-covered; every consolidated-or-skipped
entry must be dispositioned in `result.md`.

## On changes_requested / blocked

Stop **before** any consolidation. Return the verdict with numbered findings and proposed fix slices
(`P12.F<n>` names + one-line scopes). You still finish all validation first.

## Deliverables

- `result.md`: validation transcript, judgment, per-Doc-impact disposition, and — required —
  `explain: not written — run /explain for this phase`.
- `phase.md`: a short review section appended.
- Return `review_verdict: pass | changes_requested | blocked` plus the summary. Never commit, never
  transition slice/phase status (the orchestrator records the verdict via `review-phase`).
