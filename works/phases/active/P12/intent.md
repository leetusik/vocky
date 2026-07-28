# Intent — P12

- Captured at: 2026-07-28T16:05:22+09:00
- Origin: operator

## Original Input (verbatim)

_One `/create-phase` run created P10, P11 and P12 from this single request; the full original is preserved in each.
**P12 is the vocky-specific third phase** the operator selected from the offered candidates — it is **not** mirrored
from `../knowledge`; every item is sourced from vocky's own record._

> and revise phases. reference how ../knolwedge did. We'll follow them.

Follow-up (same session, answering the clarifying questions):

> 1. I meant learn how it implemented and we'll follow that in general. like org/project, key, like stuff. how to
> user to install etc..

> don't need to change anything. about it. while you asking this question. i /update-workspace already.

Follow-up (same session, after the three phases were created — **this is what moved the deploy into P12**):

> mind that deploy will be done at p12 so p6 doesn't have to mind it. and commit the changes

## Confirmed Intent (refined + clarified)

**Take vocky live here, not in P6** — then close the operational gaps that vocky's own phases explicitly left open.

**The production bring-up moves from `P6` into this phase.** P6 authored every deploy artifact (S5 `compose.prod.yml`,
S6 `deploy/vocky.conf`, S7 `deploy/deploy.sh` + `rollback.sh`, S8 the GitHub Actions chain) but **deliberately never
executed any of them** — there was no Docker daemon or Postgres in the sandbox, so every P6 slice recorded
"behavioral proof is the bring-up / CI". The bring-up was P6's last slice; the operator moved it here.

**Why this ordering is better, not just different**: P10 adds `UNIQUE(tenant_id, name)` plus a three-phase
`project_credentials.tenant_id` backfill. Run *after* a deploy, that is a live cutover on production data with the
migration-before-code footgun (new code reads a column the migration adds — deploy code first and every `vk_`
request 500s) and a defensive de-dupe of rows that may already exist. Run *before* the first deploy, it is just a
migration against an empty schema. Same for P11's install/onboarding copy: it should describe the shipped model, not
a model that is about to change under it. So the sequence is **P10 → P11 → P12 (launch)**.

Everything below stays as scoped — each item is a debt vocky recorded against itself, and unlike P10 and P11 this
phase follows nothing from `../knowledge`:

- **Run the production bring-up** at `vocky.hi2vi.com` — agent-drives / operator-gates, the model P6's DECOMP
  session already confirmed. The full hand-off is recorded in `works/phases/active/P6/phase.md` (the S10 row of its
  decomposition table, plus the "Hand-off to S10" notes each deploy slice appended) — **read that, it is the spec**:
  - Operator-only gates (`pending`): a **proxied Cloudflare `vocky` DNS record** on the `hi2vi.com` zone; on-box
    secret generation into `.env` (`POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`, e.g.
    `openssl rand -base64 32` each); three GitHub repo secrets on `leetusik/vocky` (`ORACLE_SSH_PRIVATE_KEY`,
    `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE` — the hi2vi/knowledge key material is reusable).
  - Agent steps: clone the box to **`/home/opc/vocky`** — this path is **load-bearing**, because `deploy.sh` pins no
    `-p`, so the Compose project name derives from the clone directory and any other path silently orphans
    `vocky_postgres-data` / `vocky_redis-data` / `vocky_attachments-data`; then
    `COMPOSE_BAKE=false docker compose -f compose.prod.yml up -d --build`, the five-service health gate, migrate,
    `scp deploy/vocky.conf → /home/opc/edge/conf.d/`, `ssh oracle-cloud 'cd /home/opc/edge && ./validate.sh &&
    ./deploy.sh'`, then an external smoke of `https://vocky.hi2vi.com`.
  - **Nothing in the deploy chain has ever run.** This is the first behavioral test of P6.S4–S8 *and* of P10's
    migration *and* of P11's install path — expect the bring-up to surface defects in all three, and plan the slice
    to iterate rather than to succeed first time.
- **Rate-limit the public `/auth/*` surface** — deferred job **D5**, sourced from `P6.S6`. `/auth/login` and
  `/auth/signup` are an unauthenticated password grant plus open signup, routed to `vocky-api` through the shared
  edge, and vocky has **no server-side per-IP limiter**. The shared edge **forbids** a `limit_req_zone` (global-name
  footgun across tenants of that nginx), so the fix is either a Cloudflare rate-limiting rule or an in-process
  limiter in `src/vocky/auth_api.py`. P6's own Open Questions section accepted this "for launch behind Cloudflare"
  and routed it here.
- **Add the CI test workflow the repo has never had.** `.github/workflows/` contains exactly one file,
  `deploy-production.yml` (P6.S8). The 27 pytest files (108 of which need Postgres) and the 56 vitest tests have
  only ever run locally — nothing gates a merge today.
- **Write `docs/current/qa.md`.** It is still the bootstrap `v0001` placeholder, untouched across all nine completed
  phases, despite the repo carrying two real test suites and a `qa-agent` subagent with a `/qa-check` skill that
  requires a project-defined QA driver that does not exist.
- **Decide the fate of `/admin/api/*`.** P6.S1 deleted the packaged Admin Web UI; P6.S6 404s the `/admin/` path at
  the edge. Nine admin-bearer routes therefore survive, unreachable from outside, while `VOCKY_ADMIN_AUTH_TOKEN`
  remains a **required** production box secret guarding a surface nobody can reach.
  `docs/current/architecture.md` already carries this as an open question ("whether Admin REST outlives the UI it
  served"). Resolve it: keep, retire, or re-expose deliberately.
- **Postgres backups plus basic log/metrics.** The production topology (P6.S5) has a `vocky-postgres` service with a
  named volume and no backup story at all; nothing exports logs or metrics off the box.

**Out of scope**: feature work of any kind, and the deferred attachment GC (**D3**) — that one needs a periodic
scheduler which does not exist in the repo, making it a build, not a hardening pass. It stays deferred.

## Clarifications Resolved

- Q: "Revise phases" — do you mean adopt knowledge's phase-*authoring* conventions, mirror its *roadmap*, both, or
  rescope the in-flight P6? — A (verbatim): "1. I meant learn how it implemented and we'll follow that in general.
  like org/project, key, like stuff. how to user to install etc.." → **the implementation substance**, not the
  workflow conventions. That answer scoped P10 and P11; P12 is the operator's separately-selected third phase.
- Q: Which new phases should I create now? — A: Accounts v2, Frictionless onboarding, **Post-launch hardening**.
  **Public/shareable feedback (knowledge's P19 analogue) was offered and deliberately not selected** — it is not
  planned.
- Q: Where should the adopted phase-authoring conventions be recorded? — A (verbatim): "don't need to change
  anything. about it. while you asking this question. i /update-workspace already." → **no change to `CLAUDE.md` /
  `AGENTS.md` or any workflow machinery.**

## Notes

- **Sibling phases from the same request**: P10 (accounts v2) and P11 (frictionless onboarding). Execution order
  **P10 → P11 → P12**.
- **The D5 ordering caveat is now resolved by the move.** D5's trigger reads *"at/soon after go-live"*; with the
  bring-up living in this same phase, the limiter lands beside the launch rather than two phases behind it. Order
  the slices so D5 is in place **before or with** the bring-up, not after — go-live is the moment `/auth/signup`
  and `/auth/login` become publicly reachable, and P6's own Open Questions only accepted the gap "for launch behind
  Cloudflare".
- **Sequence the slices so the launch is not first.** Rate limiting is a pre-launch item; backups, log/metrics and
  the CI test workflow are statements *about a running system* and belong after the bring-up. The `/admin/api/*`
  decision and `qa.md` are independent of it. DECOMP should split this phase around the bring-up, not treat it as a
  single trailing step.
- **Small stale artifacts to sweep while in here** (cheap, mechanical, low risk):
  - the root `Makefile` still exports the retired `VOCKY_API_AUTH_TOKEN` in `EXPORTED_ENV_VARS`
  - `README.md:161` still references that same retired global capture token
  - `README.md` / `docs/cli.md` carry a "PyPI publishing is P6; until then…" caveat that P11 will make stale — check
    which of them P11 already dropped before touching it
- **Other open items worth a decision at DECOMP, all already recorded in the archived phases** — include or
  explicitly route them, don't silently drop them:
  - **D4** — project-scope the end-user attachment download endpoint (`GET /api/feedback/{id}/attachments/{aid}` is
    still `user_id` + `source_product`-scoped, not project-scoped like the D-P3-6-tightened self-read). A small
    isolation asymmetry; its trigger is "the next time the `/api/*` attachment surface is touched".
  - **D2** — public-safe field projection for end-user feedback reads. Re-examined and re-deferred by both P3 and
    P4 with the note "revisit only if a non-owner / end-user feedback view is ever added". Still no such view.
  - the **`pnpm format:check` debt** — 13 pre-existing P4-era failures, explicitly flagged by P9 as a defer-job
    candidate; a CI test workflow will surface them, so decide before the gate goes red
  - the **design token-rename pass** — retiring vestigial hi2vi names (`victory-lime`, `archive-*`, `security-*`),
    costed in the P8 gate's `build-prompt.md §2.4` as its own mechanical slice. Explicitly **not** to be folded into
    a visual slice.
- P6's accumulated "Doc impact" list is long and lands at `P6.REVIEW`, not here — `operations.md` (production
  topology, deploy/rollback runbook, CI path, GH secrets, edge apply path, CLI distribution), `security.md` (the CSP
  string, edge TLS/HSTS/CF-real-IP, the `/admin` internal-only decision, the `/auth/*` rate-limit gap). Read the
  consolidated versions before planning, not the running list.
