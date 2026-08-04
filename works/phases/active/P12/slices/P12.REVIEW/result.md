# Result — P12.REVIEW: Phase review of "Production launch & hardening"

**Verdict: `pass`.** All seven middle slices are `done`, every validation below is green, the phase
objective and `intent.md` are satisfied item for item, and the eight durable-doc versions consolidating
the phase's *Doc impact* list are landed.

`explain: not written — run /explain for this phase`

---

## Validation — all slices together

Run from the repo root on 2026-08-04, against the sandbox's already-running `vocky-postgres-1`
(`postgres:17`, `127.0.0.1:55432`). Live checks were **read-only public HTTPS only** — no ssh, no box
contact.

| # | Command | Result |
|---|---|---|
| 1 | `python3 scripts/workflow.py validate` | **PASS** — "Workflow validation passed." (re-run after the doc rebuild: still passing) |
| 2 | `DATABASE_URL=…55432/vocky TEST_DATABASE_URL=…55432/vocky_test uv run pytest -q` | **215 passed** in 9.95s, 0 failures / 0 errors. Covers S1's admin fail-closed cases, S3's limiter cases, and the P10 chain CI now gates. Matches the count S3, S6 and S7 each measured independently. |
| 3a | `pnpm lint` (from `web/`) | **PASS**, clean |
| 3b | `pnpm typecheck` | **PASS**, clean |
| 3c | `pnpm test` | **78 passed (78)**, 10 test files |
| 3d | `pnpm format:check` | **PASS** — "All matched files use Prettier code style!" (S2's sweep holds; S6's gate premise intact) |
| 3e | `make check-skill-parity` | **PASS** — "web/public/SKILL.md matches the canonical skill byte-for-byte." |
| 4a | `bash -n deploy/backup.sh deploy/status.sh` | **PASS**, both clean |
| 4b | `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose --env-file /dev/null -f compose.prod.yml config` | **exit 0**, rendered clean (`--env-file /dev/null` used deliberately to defeat the dev-`.env` auto-load trap this phase recorded twice) |
| 4c | logging caps, parsed from `config --format json` | **5/5 services** carry `driver=json-file, max-size=10m, max-file=3` (`api`, `postgres`, `redis`, `web`, `worker`) |
| 5a | `curl … https://vocky.hi2vi.com{/healthz,/,/install.sh,/SKILL.md}` | **200, 200, 200, 200** |
| 5b | served `/SKILL.md` vs `skills/vocky-feedback/SKILL.md` | **`cmp` CLEAN** — byte parity holds live |
| 6 | `gh run list -R leetusik/vocky --limit 5` | one run, **`success`** — `30873072664`, push `6c16ac5`, `CI`, 53s. S6's first runner execution, still the latest. |

**Code spot-checks of each slice's central claim** (the results assert them; I verified them in the tree):
`src/vocky/auth.py:100-103` returns `503 {"detail": "Admin API is not configured"}` on `if not
self.token`; `compose.prod.yml` carries `${VAR:?…}` at all five interpolation sites across the three
secrets; `Makefile:15` no longer exports `VOCKY_API_AUTH_TOKEN`; no vestigial design-token name survives
in `web/src` outside `globals.css`'s history comment; `src/vocky/rate_limit.py` exists and
`check_rate_limit` is the first statement in both `signup` and `login`; `deploy/{backup,status}.sh`,
`restore.md` and `vocky.conf.md` are all present; `ci.yml` has four jobs, `postgres:17`, `pnpm
format:check`, and `astral-sh/setup-uv@v7` (the orchestrator's correction, not the executor's stale
`@v9`).

## Judgment against the objective and `intent.md`

| Intent item | Outcome |
|---|---|
| Run the operator-gated production bring-up | **Met.** Live at `https://vocky.hi2vi.com` since 2026-08-04, first deploy `6c16ac5`. All four operator gates cleared; the whole deploy chain, P10's 11-revision migration, and P11's install path all ran for the first time and were green. |
| Order D5 **before or with** the launch | **Met.** S3 (order 3) landed the limiter before S4 (order 4). |
| Rate-limit `/auth/*` (D5) | **Met**, via the recommended mechanism — an in-process per-`(IP, route)` fixed-window limiter, not the console-only Cloudflare rule — and the `X-Real-IP` correctness trap the notebook flagged is specifically covered by a test. |
| Add the CI test workflow | **Met and proven**, extending `ci.yml` rather than starting a second workflow, exactly as the file's own header demanded. Both of P11's documented exclusions are closed, and the first runner run was green. |
| Write `docs/current/qa.md` | **Met.** S7 authored the whole v0002 body; this review landed it verbatim. Scope was respected — the doc documents the `/qa-check` gap, it does not build the driver. |
| Decide `/admin/api/*` + `VOCKY_ADMIN_AUTH_TOKEN` | **Met.** Operator decision KEEP / FAIL-CLOSED, landed in code, and it closed a genuine pre-existing hole (a blank token left nine routes — including `PATCH`/`DELETE` — unauthenticated to every co-tenant container). S1 also went beyond its brief in the right direction, hardening `POSTGRES_PASSWORD` and `SESSION_SECRET` the same way and closing the phase's Finding 2. |
| Postgres backups + basic log/metrics | **Met as artifacts**, which is what the slice's plan scoped. `backup.sh` / `status.sh` / `restore.md` / the five-service log cap are authored, validated and committed; the on-box application is correctly left as an operator runbook. Called out honestly in the docs — see the deliberate gap below. |
| Stale-artifact sweep + prettier debt + token rename | **Met** in S2, mechanically, with the prettier sweep landing *before* the gate that depends on it — the only order that works. |
| Out of scope stays out | **Held.** D3, D6, D2, D4 all still `deferred`; no feature work landed. |
| D5 bookkeeping caveat | **Resolved.** `works/deferred/dropped/D5/` reads `status: dropped` with a `dropped_reason` that carries the "Resolved by P12.S3 … not abandoned" meaning, as the DECOMP caveat required. |
| D7 for the QA driver | **Opened** (`works/deferred/open/D7`, source `P12.S7`). |

**The one deliberate gap, and why it is not a finding.** S5's artifacts landed in commits *after* the
deployed SHA (`origin/main` == `6c16ac5`; four local commits are unpushed), so production today has no
scheduled backup and uncapped datastore logs. That is the plan's intent, not a defect — S5 was scoped to
author, with the destructive/on-box parts operator-gated — and the *docs now say so in place* rather than
implying backups are running. It is an operator action, not a fix slice: no code change would help.

**Cross-repo context confirmed and not flagged**, per the plan: the edge vhost's move to `leetusik/edge`
is the intended end state, and `deploy/vocky.conf.md` is the pointer left behind.

**No `P12.F<n>` fix slices are proposed.** Nothing in the phase's work is defective; the remaining items
(restore drill unrehearsed, backups not off-box, `deploy-production.yml` never dispatched, the BFF/origin
limiter mismatch) are all documented forward-looking operator or future-phase items, not P12 defects.

## Doc impact — disposition of every entry

Eight versions created, all `--source P12.REVIEW`, all authored in the file `doc-new-version` returned,
then `rebuild-docs`. No `docs/current/*` file and no existing version was hand-edited.

| Doc | Version | Consolidates |
|---|---|---|
| **operations** | `v0006` | S4 (all four Doc-impact lines), S3, S5, S6, and both `P12.DECOMP` corrections |
| **qa** | `v0002` | S7 — body pasted **verbatim** from `P12.S7/result.md` § "Proposed qa.md v0002 body" (frontmatter + body splice, no re-derivation) |
| **security** | `v0009` | S1 (a, b) + S3 |
| **architecture** | `v0010` | S1 (a) + S3 + the S4 vhost-path correction |
| **api** | `v0009` | the S4 vhost-path correction at `:637`, plus S1's `503` and S3's `429` as documented statuses |
| **product** | `v0011` | the S4 "not deployed" echo |
| **experience** | `v0012` | the S4 "404s until P12" echo |
| **frontend** | `v0008` | the S4 "not deployed" echoes (×2) + S2's token rename |

Per-entry notes:

- **`P12.DECOMP` (a)** — the *"a missing box secret must fail loudly"* claim. Resolved as the Doc impact
  list itself directed: **superseded by S1**, so `operations.md` now states the claim as *true, and only
  since P12.S1*, with the `${VAR:?}` mechanism and the `env -u` false-pass trap spelled out. Not softened.
- **`P12.DECOMP` (b)** — the prettier count. **14** is retained as the measured number, now in the past
  tense (swept to zero by S2 before the gate went on).
- **S1 (a)(b)(c)** — consolidated into `architecture.md`'s Open Questions (the question is now *Resolved
  in P12*, not merely re-worded), `security.md` (a new subsection explaining that the defense-in-depth
  claim was previously false in code), and `operations.md` § Box secrets. Also reached `api.md`, which
  documents the surface's status codes.
- **S3** — `security.md` § rewritten from "gap" to "gap closed", with the four properties worth knowing
  before touching it; `operations.md` gained the two tunables **and** the single-worker invariant;
  `architecture.md` gained both to its Configuration Surface and the handler-level design note.
- **S4** — all four lines consolidated into `operations.md` (live status, edge-repo dispatch path
  replacing scp, cache policy answered, first-deploy `:previous` note), with the echoes in `product.md` /
  `experience.md` / `frontend.md` flipped to the smallest honest edit. The `compose.prod.yml` comment fix
  was a source file, so nothing to version. I also folded in the box-was-not-virgin lesson and the BFF
  origin-gate trap, both of which are durable operational truth.
- **S5** — `operations.md` gained a whole new *Backups, log caps and on-box status* section, including the
  datastore `--force-recreate` gotcha stated in its own callout, plus the honest authored-not-applied
  banner.
- **S6** — `operations.md`'s `ci.yml` section rewritten to four jobs with the exact env contract; the
  "never executed on a runner" sentence replaced with the green first run.
- **S7** — landed verbatim; no re-derivation, no summarizing.

**Small in-scope corrections made while consolidating** (each is durable truth the phase's own work made
verifiable, not scope creep): `operations.md`'s local-gate line said "56/56 tests" (P4-era) — corrected to
the measured **78/78 across 10 files**, with `format:check` added to the pre-push advice; `frontend.md`'s
`border-security-mint` call-site reference and its "token renames were deferred" line, both made false by
S2; `architecture.md`'s `VOCKY_ADMIN_AUTH_TOKEN` line still called the token "optional".

## Deviations from `plan.md`

- **Step 4b** — ran `docker compose config` with `--env-file /dev/null` rather than bare, deliberately.
  The plan's literal command would have silently picked up the repo's dev `.env`; this phase recorded that
  exact false-pass twice (S1, and again on the box at S4 Gate 4). Same assertion, sound method.
- **Step 6** — `gh` was available, so the CI run was verified directly rather than taken on the
  orchestrator's word. Same conclusion.
- The plan's expected doc surface listed six-to-eight docs "verify against the actual Doc impact list,
  which wins"; the list produced **eight**, matching its prediction including the conditional `security.md`
  and `architecture.md` checks (both were indeed stale).
- No other deviation. No code was edited on this review slice, no state transition was run, nothing was
  committed.
