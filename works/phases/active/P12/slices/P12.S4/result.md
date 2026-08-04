# Result — P12.S4: Production bring-up at `vocky.hi2vi.com`

Executed 2026-08-04. Kind `co-work` — run inline by the orchestrator with the operator in the loop, per
plan. **Verdict: done. vocky is live in production at `https://vocky.hi2vi.com`, serving 200 end to end.**

The slice ran in three sessions: the gate instructions + operator execution (G1–G3), the Gate 4 box
reset (recorded in full in `phase.md` § *P12.S4 Gate 4 executed — and the box was NOT virgin*), and this
final deploy + smoke pass, resumed on the operator's "edge p6.s3 done. you continue the job."

## Gates (operator) — all four cleared

| Gate | Outcome |
|---|---|
| G1 DNS | Proxied `vocky` record on the `hi2vi.com` zone. Pre-vhost state was 526 (origin cert unverifiable before the edge vhost existed), which was the correct intermediate. |
| G2 box `.env` | Executed by the agent at the operator's request ("you do the step 4"), after the box-reset detour: three fresh `openssl rand -base64 32` secrets, mode 600. Fail-loud `${VAR:?}` proven with `--env-file` (the naive `env -u` test false-passes — Compose auto-reads the project `.env`; trap recorded in `phase.md`). |
| G3 GitHub secrets | `ORACLE_SSH_PRIVATE_KEY` + `ORACLE_SSH_KNOWN_HOSTS` set on `leetusik/vocky`. |
| G4 push | Box checkout fast-forwarded to `6c16ac5` == `origin/main`. |

## Part B — the deploy

**B1/B2** were completed during the Gate 4 box reset (clone at `/home/opc/vocky` — the load-bearing
path — old dev stack dumped, wiped, and its override file quarantined; see `phase.md`).

**B6 (edge vhost) was superseded and never run as written.** Edge repo **P6** made `edge/conf.d/vocky.conf`
canonical (edge `87d5b2e`), fixed the stale rate-limit header comment during adoption, added the
dispatch-only `edge-deploy` workflow (validate → stage → deploy, strictly additive, whole-tree gated),
and its **first run was green**: the six-conf tree staged to the box at 2026-08-04 03:04 and gracefully
reloaded. The vhost reached production exactly once, through the versioned path we intend to keep using —
the manual B6.1–B6.6 scp procedure is retired. Verified before the deploy: `vocky.conf` on the box
(15775 bytes), port-80 Host probe → 301, `https://vocky.hi2vi.com/` → 502 ("vhost live, origin down").

**B3–B5 — `deploy/deploy.sh`, first run, green end to end:**

- Pre-flight: `changple_shared_network` present; `compose config -q` clean; only the old differently-named
  `vocky-app`/`vocky-worker` dev images present, so the script took its documented no-`:previous`
  first-deploy branch.
- Both images built on the box (`vocky-api:latest`, `vocky-web:latest`; web build ~16.5s Next.js compile).
- **Migration — P10's accounts-v2 chain ran for the first time anywhere and applied cleanly**: all 11
  revisions, `20260423_2337` (create feedback_events) through `20260728_1200` (org-level credentials),
  in a one-off container before any new code served. No errors, no warnings beyond normal alembic INFO.
- Health gate: `vocky-api` healthy on poll 1, `vocky-web` healthy on poll 8 (~40s — inside its
  `start_period`), `vocky-worker` stable-running on 2 consecutive polls. postgres/redis healthy.
  `[deploy] DONE`.

## Part C — smoke

| Probe | Result |
|---|---|
| C1 `GET /healthz` | **200** |
| C1 `GET /` | **200** |
| C2 signup round-trip | **Pass.** `POST /api/auth/signup` → 200 `{ok:true}`, httpOnly `vocky_session` cookie set, authenticated `GET /dashboard` → 200 (anonymous → 307 to `/login`). Live account created: `p12-smoke-20260804@example.com` (throwaway; operator may delete). First attempt returned **403 by design** — bare curl sends no `Sec-Fetch-Site`/`Origin`, and the BFF's CSRF second layer (`session.ts:191`) rejects exactly that; adding `Origin: https://vocky.hi2vi.com` (as any browser does) passes. Not a defect. |
| C3 armed probes | `/install.sh` → **200**, `/SKILL.md` → **200**, served `SKILL.md` **byte-identical** (`cmp` clean) to `skills/vocky-feedback/SKILL.md`. |
| C4 clean-env install | **Pass.** `buildpack-deps:bookworm-scm` container, `curl -fsSL …/install.sh \| bash` → uv bootstrapped, **vocky 0.2.0** built from `git+https://github.com/leetusik/vocky@6c16ac5` (exactly `origin/main`), 4 executables installed, `vocky --version` → `0.2.0`, `vocky capture --help` renders. |
| C5 Cloudflare-not-a-barrier | **Proven, three ways in one pass**: Cloudflare served a shell script to curl (correct `application/x-sh`, no challenge), passed a non-browser JSON POST to the auth surface, and did not interfere with uv's fetches. Same empirical result knowledge got. |
| C6 CI first run | **Green.** Run `30873072664` (push of `6c16ac5`) — the first-ever runner execution of `ci.yml` including S6's Postgres-backed `pytest` job and the `pnpm format:check` step — completed `success` in 53s with zero iteration needed. |
| Co-tenants | `hi2vi.com`, `knowledge.hi2vi.com`, `changple.ai`, `miracle.changple.ai` all **200** after the reload. (The plan's B6.6 list named `changple5.com`, which is not a served hostname — the changple vhosts serve `changple.ai` / `miracle.changple.ai`.) |

## Open questions — answered

1. **Cache policy for `/install.sh` and `/SKILL.md`:** measured live — `cache-control: public, max-age=0`,
   `cf-cache-status: DYNAMIC`. Nothing caches; every install gets fresh bytes. That is the safe default
   (no stale-installer window after a push) and needs no change at current traffic. Revisit only if these
   paths ever see real volume.
2. **A Cloudflare `/auth/*` rate rule on top of S3's in-app limiter:** not added. The in-app limiter
   (20/900s per IP+route) is the primary and is versioned; a console rule would be unversioned belt-and-
   braces. Recommend leaving it to operator discretion; nothing in this phase depends on it.
3. **Can P12.S5 install its backup artifacts itself?** **Yes** — box access from this environment is
   proven at length (Gate 4, the deploy, the smoke).
4. **`compose.prod.yml`'s stale migrate-idiom comment:** fixed in-slice (now describes `deploy.sh`'s
   one-off `compose run --rm --no-deps api` migration).
5. **`deploy/vocky.conf` stale header comment:** mooted — the file left this repo (edge P6 owns it) and
   the comment was fixed during the edge adoption.

## Defects found

**None requiring a fix slice.** The deploy chain, P10's migration, and P11's install path all worked
first try. The only surprises were operational, all resolved in-slice and recorded in `phase.md`: the
non-virgin box (Gate 4), the `env -u` false-pass trap, the plan's wrong co-tenant hostname list, and the
expected-by-design 403 on origin-less POSTs.

## Loose ends for the operator

- Throwaway prod account `p12-smoke-20260804@example.com` exists (owner of an empty auto-provisioned
  tenant). Delete at leisure or leave; nothing references it.
- Box keepsakes from Gate 4 (`/home/opc/vocky-preP12-*.{sql,bak}`) can be deleted once the old dev data
  is confirmed unneeded.
- `deploy-production.yml` (`workflow_dispatch`) has still never run; the manual first deploy stands in
  for it. Its first dispatch is a natural follow-up but not required by this phase.
