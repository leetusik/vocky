# Phase P12: Production launch & hardening: bring-up, rate limits, CI tests, QA doc

_Intent: see [intent.md](intent.md)._

## Objective

Take vocky live, then close the operational gaps its own phases left open: run the operator-gated production bring-up at `vocky.hi2vi.com` using the artifacts P6 authored but deliberately never executed (compose topology, edge vhost, deploy/rollback scripts, CI chain — none has ever touched real infrastructure), then rate-limit the public `/auth/*` surface (deferred D5 — a Cloudflare rule or an in-process per-IP limiter, since the shared edge forbids `limit_req_zone`), add the CI test workflow the repo has never had (`.github/workflows/` holds only `deploy-production.yml`), write `docs/current/qa.md` (still the bootstrap v0001 placeholder after nine phases), decide the fate of the now-unreachable `/admin/api/*` surface and its `VOCKY_ADMIN_AUTH_TOKEN` box secret, and add Postgres backups plus basic log/metrics. Deploying only after P10 and P11 is deliberate: the accounts-v2 migration then lands on an empty schema instead of as a live cutover on prod data. Feature work and the deferred attachment GC (D3, which needs a scheduler that does not exist) stay out of scope.

## Context

**This phase decomposes in ONE pass.** There is no product visual design in P12, so there is no `P12.DECOMP2` and no build inventory. `P12.S4` is `--kind co-work`, but it is an **infra/operator gate, not a `design-cowork` round**: no `handoff.md`, no `DesignSync`, no Claude Design, no cards. The `co-work` kind is used only because the slice needs the orchestrator on the main thread with the operator in the loop (Cloudflare DNS, on-box secret generation, GitHub repo secrets, the `git push`) — P6.S10 already anticipated "likely orchestrator-driven". The one design-adjacent item in this phase (the vestigial design-token rename, `P12.S2`) is a **pure mechanical rename with identical hex values and zero visual change**, deliberately kept out of any visual slice.

**The bring-up spec is `works/phases/active/P6/phase.md`**, not this file: the `P6.S10` row of its decomposition table plus every "Hand-off to S10" note in its *Findings & Notes*. The durable consolidated version is `docs/current/operations.md` § "Production Deploy Kit (P6)". This file records only what P12's own reading added.

## Decomposition

Seven middle slices, `P12.S1`–`P12.S7` (`DECOMP` is order 0, `REVIEW` is last). The phase is split **around** the bring-up rather than treating it as one trailing step, exactly as `intent.md` requires: two pre-launch slices that change what the box is asked to run, one pre-launch slice that must be in place before `/auth/*` becomes publicly reachable, the launch itself, then three slices that are statements about a system that is already running.

| Slice | Kind | Risk | Order | Delivers |
|---|---|---|---|---|
| **P12.S1** Decide the fate of `/admin/api/*` and `VOCKY_ADMIN_AUTH_TOKEN` | impl | med | 1 | Resolve the two open questions `architecture.md` carries (keep / retire / re-expose Admin REST; whether the token stays a mandatory box secret) **and land the consequence in code**. First, because it decides the box `.env` secret list `P12.S4` generates, and because the middleware is **fail-open today** (see Findings). |
| **P12.S2** Repo hygiene sweep | **low** | 2 | 2 | Three mechanical, greppable edits with zero behavior change: drop the retired `VOCKY_API_AUTH_TOKEN` from `Makefile:15` `EXPORTED_ENV_VARS`; clear the 14 `prettier --check` failures under `web/`; rename the five vestigial hi2vi design tokens (`--color-victory-lime`, `--color-archive-olive`, `--color-archive-cream`, `--color-security-mint`, `--color-security-teal`) and their 6 usage sites, **same hex values**. Pre-launch so the push at S4 carries a clean tree, and before S6 can gate on `prettier --check`. |
| **P12.S3** Rate-limit the public `/auth/*` surface (D5) | impl | med | 3 | Deferred job **D5**. An in-process per-IP limiter on `/auth/signup` + `/auth/login` (recommended mechanism — see Findings), optionally belt-and-braces with a Cloudflare rule applied by the operator at S4. Must be in place **before or with** go-live: go-live is the moment the unauthenticated password grant and open signup become publicly reachable. |
| **P12.S4** Production bring-up at `vocky.hi2vi.com` | **co-work** | **high** | 4 | The live first deploy. Orchestrator-driven on the main thread, operator-gated (`pending`) at: the proxied Cloudflare `vocky` DNS record on the `hi2vi.com` zone; on-box `.env` secret generation; the three `ORACLE_SSH_*` GitHub repo secrets on `leetusik/vocky`; and the **`git push` of the 57 unpushed commits**. Agent steps per the P6.S10 spec. **Never bundled with anything else.** |
| **P12.S5** Postgres backups, log rotation and basic metrics | impl | med | 5 | `pg_dump` backup script + retention + a documented restore drill; the attachments volume's backup story; a `logging:` driver cap on all five prod services (unbounded `json-file` logs are the box's real disk risk); a minimal on-box status/metrics read. Post-launch by definition — it is a statement about a running system, and it also exercises `deploy.sh` a second time on a live stack. |
| **P12.S6** Extend `ci.yml` with a Postgres-backed pytest job | impl | med | 6 | **Add a job to the existing `.github/workflows/ci.yml`, do not start a new workflow** (see the `ci.yml` reconciliation in Findings). A `postgres:17` service container, the two-database `DATABASE_URL` + `TEST_DATABASE_URL` contract the suite requires, `uv run pytest`; plus the `prettier --check` gate that S2's sweep makes safe to turn on. |
| **P12.S7** Author `docs/current/qa.md` | impl | med | 7 | Replace the bootstrap `v0001` placeholder with a real QA doc: the test topology, how each suite runs locally, the CI gates as they stand after S6, the manual checks automation cannot cover, and the honest status of `/qa-check` + `qa-agent`. Last, so it documents the CI gate S6 actually landed. **Body is authored into `P12.S7/result.md`, not into `docs/` — see the doc convention below.** |

### Ordering rationale

- **Pre-launch, independent of the launch (may go early):** S1 (`/admin` fate) and S2 (hygiene sweep). S1 is first because its outcome decides whether `VOCKY_ADMIN_AUTH_TOKEN` is still one of the three secrets the operator generates on the box at S4 — a dependency in the wrong direction would mean regenerating the box `.env` after launch. S2 is pure hygiene and only needs to precede the push (S4) and the CI gate (S6).
- **Pre-launch, required by the launch:** S3. `intent.md` is explicit — order the slices so D5 is in place **before or with** the bring-up, not after. P6's Open Questions only accepted the unthrottled gap "for launch behind Cloudflare", and the move of the bring-up into this phase removed the reason to keep accepting it.
- **The launch:** S4, alone.
- **Post-launch (statements about a running system):** S5, S6, S7. S6 is placed here per `intent.md`'s grouping; the tension in that placement is real and is recorded as **Open Question 1** for the operator to settle at S4's plan gate.
- `depends_on` is advisory (existence-checked only) and is set where a real ordering dependency exists: S4 ← S1, S3; S5 ← S4; S6 ← S2; S7 ← S6. S2 and S3 depend on nothing.

### Risk ratings (risk selects the executor tier — the phase's main cost lever)

- **S2 = `low`** (→ `slice-executor-low`, a literal plan-follower): the only fully mechanical slice. Three edits whose completion is provable by grep plus the standard `pnpm lint && pnpm typecheck && pnpm test && pnpm build` gate; no judgment, no design decision inside the slice. Its plan must enumerate every file and the exact new token names.
- **S1 = `medium`**: bounded — either a documented "keep" plus a fail-closed fix, or a deletion of `src/vocky/admin_api.py`, its middleware wiring, `tests/test_admin_api.py`, the config field and the compose/`.env.prod.example` entries. **If the operator chooses "retire" at the plan gate, the orchestrator should bump this one tier to `high`** — it becomes a ~500-line module removal touching app wiring.
- **S3 = `medium`**: a new middleware in the public auth path with one real correctness trap (the client IP behind Cloudflare + the shared edge) and a real failure mode (locking out a legitimate user); well-scoped but needs judgment.
- **S4 = `high`** (`co-work`, orchestrator-run inline): the first-ever execution of the entire deploy chain against real infrastructure, with four operator gates and a plan that must iterate rather than succeed first time.
- **S5 = `medium`**: authoring backup/rotation artifacts plus an on-box runbook is bounded; the destructive parts (restore drill, cron install) are operator-gated rather than executed by the executor.
- **S6 = `medium`**: service containers plus the suite's two-database contract, and the first-ever run of the 108 DB-backed tests may surface real failures the plan cannot pre-script.
- **S7 = `medium`**: authoring a whole durable doc from evidence is judgment work, but touches no code.

### Routing decisions — every item `intent.md` said must be included or explicitly routed

| Item | Decision |
|---|---|
| **D5** — `/auth/*` rate limiting | **Own slice, `P12.S3`**, pre-launch. Mechanism recommendation in Findings (in-process limiter primary; Cloudflare rule optional at S4). **Bookkeeping caveat below.** |
| **`/admin/api/*` fate + `VOCKY_ADMIN_AUTH_TOKEN`** | **Own slice, `P12.S1`**, first. The decision itself is the operator's, made at S1's plan gate; the executor lands the consequence. |
| **`docs/current/qa.md`** | **Own slice, `P12.S7`**, last. **Scope: document QA only — do NOT build the `/qa-check` driver.** A browser/UI driver (mission library, artifact conventions, a browser runtime, `observe`/`click`/`network_tail`/… verbs) is a feature build, not a hardening pass, and is out of proportion here. The doc states plainly that `/qa-check` + `qa-agent` are unusable until such a driver exists. **Recommendation for the orchestrator: open a deferred job for "define the project QA driver `/qa-check` requires"** — this executor may not run `defer-job`. |
| **CI test workflow** | **Own slice, `P12.S6`** — *extends* `.github/workflows/ci.yml`, which already exists (P11.S4). See the reconciliation in Findings. |
| **Postgres backups + basic log/metrics** | **Own slice, `P12.S5`**, post-launch. |
| **Stale-artifact sweep** | **Folded into `P12.S2`.** Confirmed live: `Makefile:15` still exports `VOCKY_API_AUTH_TOKEN`. **Two of the three intent items are already fixed** — no `README.md` line references the retired token as current (`README.md:187` and `:351` describe it correctly as *retired*), and **no "PyPI publishing is P6 / until then" caveat survives in `README.md` or `docs/cli.md`** (P11 already dropped it; a `PyPI` grep on `README.md` is empty). So S2's stale-artifact work is the `Makefile` line only. |
| **`pnpm format:check` debt** | **Decided: fix it, in `P12.S2`, before the gate exists.** Re-measured today: **14 files**, not 12–13 (`web/README.md`, 4 `src/app` + `src/components` files, 5 `src/lib` files, 4 `tests/*.test.ts`). The fix is `prettier --write` — formatting only. `web/.prettierignore` excludes `public/`, so `install.sh` and the served `SKILL.md` byte-parity gate cannot be disturbed. Then `P12.S6` adds `prettier --check` to `ci.yml`, closing the second of the two exclusions `ci.yml` documents in its own header. |
| **Design token-rename pass** | **Included, folded into the mechanical `P12.S2`** — *not* into a visual slice (there is none). Justification: it is a same-hex rename across `globals.css` + 6 usage sites, verifiable by grep, and cohesive with the other two mechanical edits; keeping it as a separate slice would add a whole executor dispatch for ~10 lines. The **new names are a naming decision for S2's plan gate** — see Open Question 3. |
| **D4** — project-scope the end-user attachment download | **Stays deferred.** Its trigger is "the next time the `/api/*` attachment surface is touched"; **no P12 slice touches it** (S1 touches `/admin/api/*`, S3 touches `/auth/*`, nothing else touches request handlers). It is an API-contract/isolation change — feature work, which `intent.md` puts out of scope. It remains an open question in `architecture.md`. |
| **D2** — public-safe field projection for end-user reads | **Stays deferred.** Its stated revisit condition ("only if a non-owner / end-user feedback view is ever added") is still unmet — P12 adds no view of any kind. Re-deferred by P3 and P4 on the same grounds. |
| **D6** — org management | **Stays deferred**, out of scope per `intent.md`. It is a distinct product surface with its own authorization design (P10.DECOMP's reasoning is unchanged). |
| **D3** — attachment GC | **Stays deferred**, out of scope per `intent.md`: it needs a periodic scheduler that does not exist in the repo, so it is a build, not a hardening pass. |
| **D1** — trajectory-aware feedback export | Not named by `intent.md`; **stays deferred** — product direction, not hardening. Noted here only so the sweep of the deferred store is complete (`D1`–`D6` are all accounted for). |

**D5 bookkeeping caveat (for `P12.REVIEW`).** `P12.S3` was created with `new-slice`, not `promote-deferred`, because a decomposition executor may run only `new-slice`. `scripts/workflow.py promote-deferred` calls `create_slice`, which hard-fails on an existing slice directory (`slice already exists`), so **`promote-deferred D5 --slice P12.S3` can no longer be run** — the normal `deferred → promoted` transition is unavailable for D5. `works/deferred/open/D5/` therefore still reads `status: deferred`. Once S3 lands, the orchestrator should close it deliberately — `drop-deferred D5 --reason "Resolved by P12.S3: <mechanism>; not abandoned"` is the only available command, and its reason text has to carry the "resolved, not abandoned" meaning because there is no `resolved` status.

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

### The box, the edge, and the clone path (do not re-derive)

- **Box:** `ssh oracle-cloud` = `opc@140.245.64.173`. vocky is a **co-tenant**. There is no `edge` ssh alias — `edge` is a Compose project at `/home/opc/edge` (container `edge-nginx`, `nginx:1.27-alpine`) on the external `changple_shared_network`.
- **Vhost apply path:** `scp deploy/vocky.conf` → `/home/opc/edge/conf.d/`, then `cd /home/opc/edge && ./validate.sh && ./deploy.sh` (an `nginx -t` gate plus a graceful reload). **Never recreate the edge container.** Co-tenant vhosts that must not be disturbed: `00-default.conf`, `changple5.conf`, `changple-web.conf`, `hi2vi.conf`, `knowledge.conf`.
- **TLS is already provisioned** — the wildcard `/home/opc/edge/certs/hi2vi.crt` covers `*.hi2vi.com`. Cloudflare is Full (Strict). Nothing to issue.
- **CONSISTENCY NOTE — clone the box to `/home/opc/vocky`, the path is load-bearing.** `deploy/deploy.sh`'s `dc()` pins **no `-p`**, so the Compose project name derives from the clone directory's basename. `/home/opc/vocky` → project `vocky` → named volumes `vocky_postgres-data`, `vocky_redis-data`, `vocky_attachments-data`. **A clone at any other path silently orphans the datastore volumes on the next deploy.** Container names are pinned and image tags explicit, so only the directory name matters for identity. `/home/opc/vocky` is already hard-coded in `deploy/github-actions-production-deploy.sh` and `deploy/oracle-production-deploy-remote.sh`.
- **Nothing in the deploy chain has ever run.** `compose.prod.yml`, `.env.prod.example`, `web/Dockerfile`, `deploy/vocky.conf`, `deploy/deploy.sh`, `deploy/rollback.sh`, and the three-file GitHub Actions chain were all validated **statically only** (compose parser, `bash -n`, YAML parse, `pnpm build`, house-rule greps). No `docker build`, no `docker compose up`, no `nginx -t` on `vocky.conf`, no execution of any deploy script. The bring-up is simultaneously the first behavioral test of **P6.S4–S8**, of **P10's accounts-v2 migration**, and of **P11's install path**. Plan S4 to iterate.
- **Box reachability from an executor sandbox is UNVERIFIED.** This decomposition could not probe it — reading `~/.ssh/config` was refused by the permission classifier, so no `ssh oracle-cloud` attempt was made. **Assume every box-touching step is orchestrator/operator-run until proven otherwise**; that assumption is one of the reasons S4 is `co-work` and why S5 is scoped to *author* its on-box artifacts plus a runbook rather than to install them itself.

### Pre-launch defects found while reading (all pre-date P12; each belongs to a specific slice)

1. **`AdminBearerAuthMiddleware` is fail-open.** `src/vocky/auth.py:84-109` guards `/admin/api/*` **only `if self.token`** — its own docstring says "when a token is configured". `src/vocky/config.py:39` defaults `VOCKY_ADMIN_AUTH_TOKEN` to `""`. `compose.prod.yml:104` interpolates it as a plain `${VOCKY_ADMIN_AUTH_TOKEN}` (not `${...:?err}`), and Compose substitutes an **empty string with a warning** for an unset variable — it does not fail. So a missing or typo'd `.env` line yields **nine unauthenticated `/admin/api/*` routes** — including `PATCH` and `DELETE` on any feedback record — reachable by every co-tenant container on `changple_shared_network`. The edge `return 404` on `/admin/` keeps it off the internet, but the whole "defense in depth" argument in `security.md` / `operations.md` rests on a token that is optional in code. **This is `P12.S1`'s central finding**: whichever way the fate decision goes, the fail-open branch must not survive the launch (retire the surface, or make the middleware fail **closed** and the interpolation `${VOCKY_ADMIN_AUTH_TOKEN:?...}`).
2. **`operations.md`'s claim that a missing box secret "must fail loudly" is only true for one of the three.** `POSTGRES_PASSWORD` does fail loudly, but by the `postgres:17` image's grace, not by compose. `SESSION_SECRET` blank → `web/src/lib/env.ts` `readEnvGroup` throws **at request time**, not at boot — and the web container's healthcheck is a fetch of `/`, the static landing page, which never reads the session env. **A blank `SESSION_SECRET` therefore passes `deploy.sh`'s health gate and fails only when a real user tries to log in.** S4's smoke must include an authenticated round-trip (signup or login), not just the two `/healthz` + `/` probes the CI workflow runs. `VOCKY_ADMIN_AUTH_TOKEN` blank → finding 1.
3. **57 commits are unpushed** (`origin/main` is 57 behind `main`). This is not incidental to the bring-up, it is a prerequisite: the on-box gate `git merge-base --is-ancestor`-verifies `TARGET_SHA` against **fetched `origin/main`**, `web/public/install.sh` resolves the **GitHub `main`** `git+https://` target, and `.github/workflows/ci.yml` has never executed on a runner because the commits are unpushed. Installing from the installer today would silently deliver a **pre-P10 CLI** (no org keys, no `vocky capture`). **The push is an operator gate inside S4** — `CLAUDE.md` forbids pushing unasked — and it must happen *before* the installer probe, not after.

### `.github/workflows/ci.yml` reconciliation (intent said "CI has never existed" — that wording predates P11)

`intent.md` says `.github/workflows/` holds exactly one file. **It now holds two.** P11.S4 added `ci.yml`, the repo's first `push`-to-`main` + `pull_request` gate, with three jobs: **Skill Parity** (`python3 scripts/skill_parity.py`), **Installer Syntax** (`bash -n web/public/install.sh`), and **Web** (`pnpm install --frozen-lockfile`, `lint`, `typecheck`, `test` on Node 22 / pnpm 10.28.2 via corepack). Its header comment names its two deliberate exclusions and says, verbatim, *"P12 is expected to add a job to this same file, not start a new one."* **S6 therefore extends `ci.yml`; it does not create a second workflow.** `deploy-production.yml` stays what it is — `workflow_dispatch`-only, main-guarded, ancestor-verified — and is not a CI gate.

**Concrete facts S6's plan needs:**
- The suite requires **two distinct databases**. `tests/conftest.py` reads `DATABASE_URL` (default `postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky`) **and** `TEST_DATABASE_URL`, and raises if they are equal or if `TEST_DATABASE_URL` has no database name; the test database is created/dropped by the session fixture and runs alembic against itself. `make test` enforces the same three preconditions via `check-test-db`.
- **Redis is not needed** — `fakeredis` is a dev dependency, so a Redis service container is probably unnecessary; confirm by running the suite, not by assuming.
- `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`. `[tool.uv] default-groups = ["dev"]`, and the dev group self-references `vocky[server]`, so a plain `uv sync` gives the full server dependency set — no `--extra server` flag is needed in CI.
- **`tests/` holds 29 files.** The last recorded run (P6.REVIEW, pre-P10/P11) was **79 passed / 108 errors**, every error a `psycopg.OperationalError` from the absent Postgres. **Those 108 have never run anywhere in this workspace**, so S6's first green run is genuinely new information — and it may not be green. Do not plan S6 as a mechanical YAML edit.

### D5 mechanism recommendation (for `P12.S3`'s plan gate)

Recommended: **an in-process per-IP limiter in `src/vocky/auth_api.py`** (or a small ASGI middleware beside `AdminBearerAuthMiddleware` in `src/vocky/app.py`), mirroring what the sibling `knowledge` already does. Reasons: it is versioned, reviewable and testable in the same repo; it survives a Cloudflare misconfiguration; and it is the only option that a CI test can prove. A Cloudflare rate-limiting rule is worth adding as an outer layer at S4's operator gate, but it is console-only, unversioned, and invisible to the test suite, so it cannot be the primary mechanism. **A `limit_req_zone` at the shared edge is forbidden** — zone and location names are global across the whole `conf.d/` tree, so a duplicate fails `nginx -t` for *every* co-tenant site.

**The correctness trap:** behind Cloudflare + the shared edge, the socket peer address is the **edge container**, not the user. Every request would share one bucket and the limiter would throttle the entire internet as a single client. `deploy/vocky.conf` restores the real client IP (`set_real_ip_from` over the full Cloudflare v4+v6 ranges, `real_ip_header CF-Connecting-IP`) and forwards it at the **server level** as `X-Real-IP` / `X-Forwarded-For`. The limiter must read the forwarded header and must treat it as untrusted when the request did not arrive through the edge (local/dev). Related: `vocky.conf` hoists all `proxy_set_header` directives to the server level precisely because **the first per-location `proxy_set_header` drops the entire inherited set** — do not add a per-location header to `/auth/` while implementing this.

The four routes are `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` (`src/vocky/auth_api.py:237-241`). Only the first two are the unauthenticated attack surface.

### The design tokens (for `P12.S2`)

Five vestigial hi2vi names in `web/src/app/globals.css:37-44`, all with a comment stating their real role:

| Current | Hex | Comment / real role | Usage sites |
|---|---|---|---|
| `--color-security-mint` | `#bee9d5` | mint tint (chip borders, key panel) | `show-once-key.tsx:56`, `ui/chip.tsx:19`, `ui/snippet.tsx:110`, `landing/skill-copy-button.tsx:77` |
| `--color-security-teal` | `#2fa477` | brighter data accent (endpoint label) | `ui/endpoint-card.tsx:36`, `ui/snippet.tsx:116` |
| `--color-victory-lime` | `#9ad4a8` | soft positive tint (rare) | `ui/snippet.tsx:116` |
| `--color-archive-olive` | `#8a968f` | muted neutral (= `muted`, intentional) | none in `web/src` beyond the declaration |
| `--color-archive-cream` | `#f1f4f0` | light neutral surface | none in `web/src` beyond the declaration |

Six usage sites total, all Tailwind utility classes (`border-security-mint`, `text-security-teal`, `text-victory-lime`, …). P8's audit had already recorded two of these as **palette collisions** — `archive-olive == muted` and `archive-cream == surface-soft == hairline-soft == surface-band` — so S2's plan should consider whether the two unused ones are **deleted** rather than renamed. The rename must keep every hex value byte-identical; if `pnpm build` output or any rendered color changes, the slice has overstepped.

### The doc convention this phase uses (binding on every slice)

- **No middle slice may run `doc-new-version` or hand-edit `docs/current/*.md`.** Durable docs are versioned **once, at `P12.REVIEW`**, consolidating the "Doc impact" list below.
- **`qa.md` is the exception that needs a rule.** It needs a whole new body, not a one-line delta. **`P12.S7` authors the complete intended `qa.md` body inside its own `result.md`** (clearly fenced and marked as the verbatim doc body), and appends a "Doc impact" line here pointing at it. `P12.REVIEW` then runs `doc-new-version --doc qa --summary "..." --source P12.REVIEW` and copies that body in verbatim. S7's plan inherits this convention.
- **Gotcha for every `doc-new-version` call: keep `--summary` short (≲180 chars).** The version filename is the slugified summary, macOS caps a filename at 255 bytes, and the `Edit` tool's temp suffix eats ~28 more — a long summary fails with `ENAMETOOLONG`, possibly only at first edit, leaving a stray file plus an index entry to clean up by hand.
- Two statements are currently written honestly across the doc set and **become false the moment S4 succeeds** — `P12.REVIEW` must fix both: *"vocky is NOT deployed"* (the block quote at `operations.md:18-26`, plus echoes in `product.md`, `experience.md`, `frontend.md`) and *"the hosted install line 404s until P12 deploys"*.

### Armed probes P11 left for the bring-up (S4 must run them, not assume them)

```sh
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh   # 404 today -> must be 200
curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/SKILL.md     # 404 today -> must be 200
```

After `/SKILL.md` flips, the **served bytes must `cmp` clean** against `skills/vocky-feedback/SKILL.md`. S4 must also run the **Cloudflare-not-a-barrier probe** live (unrunnable while the site is down — do not design around an unverified blocker), and must **install from the real `git+https://` target into a clean environment after the push** and assert `vocky --version` ≥ `0.2.0` and `vocky capture --help` renders — install-and-check, not assert. A cache policy for `/install.sh` and `/SKILL.md` was deliberately left as a bring-up question.

### Absorbing the defects the bring-up will surface

The bring-up is expected to fail at least once. The rule for this phase:

- **In-slice iteration** for anything that is a *deploy-chain* defect — a wrong path, a missing env, a healthcheck timing out, a compose or nginx syntax error, an image that will not build, a migrate invocation that the box's Compose version refuses (`MIGRATE_VIA_DOCKER_RUN=1` is the documented fallback). S4 owns the deploy artifacts it is executing and fixes them in place; that is what "plan it to iterate" means.
- **A follow-on `P12.F<n>` fix slice** for anything that turns out to be an *application* defect — a P10 migration or model bug the first real `alembic upgrade head` exposes, a P11 install-path bug, a web/BFF bug that only appears against a real origin. Those are other phases' code, they need their own plan and validation, and they must not be repaired inside a `co-work` slice on the main thread.
- **No `fix` slices are created now.** The orchestrator creates them if and when S4 or `P12.REVIEW` finds something.

### Smaller facts worth not re-deriving

- **`/mcp` has no container** — it is a Starlette `Mount` inside `vocky-api`; the edge routes `/mcp → vocky-api:8000`. `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com` is already set on the api service.
- **The worker has no healthcheck by design** and is gated on container **state** (`running` + not restarting), not health. It reuses `image: vocky-api:latest` with no `build:`, so one `docker compose build` freshens both — the stale-worker footgun is closed by construction.
- **`deploy.sh` never runs `down` or `down -v`** on any path, and its step order (tag → up datastores → build → **migrate** → up → gate) is load-bearing. The **first** deploy hits the no-`:previous` branch for both images, leaves the stack up for inspection, and exits non-zero on failure — that is expected, not a bug.
- `COMPOSE_BAKE=false` must stay exported (this host's Compose panics on the bake path).
- `docker compose run` takes the **service key `api`**, never the `container_name` `vocky-api`. `compose.prod.yml`'s api comment still cites the pre-S7 `exec vocky-api …` idiom and is wrong as written (`deploy.sh` is correct) — a candidate one-line fix for S2 or S4 if either is already in that file.
- `shellcheck` and `actionlint` are **not installed** in this sandbox; neither is a Docker daemon. Do not plan validation around them.
- The repo is public (`https://github.com/leetusik/vocky.git`) and `works/` is tracked, so the push at S4 publishes this notebook — already true of the previous 9 phases; it contains the box IP and paths, which are already public, and no secrets.

## Constraints

- **Shared-edge house rules** (violating any breaks *every* co-tenant site): never `default_server`; no `listen [::]` (IPv6); **no `limit_req_zone`** and globally-unique zone/location names; always restore Cloudflare real IPs (`set_real_ip_from` + `real_ip_header CF-Connecting-IP`); always use `resolver 127.0.0.11 valid=30s ipv6=off` with variable `proxy_pass` upstreams.
- **`/home/opc/vocky` is the only acceptable box clone path** (Compose project name → volume identity).
- **No middle slice versions docs.** `doc-new-version` and `rebuild-docs` are `P12.REVIEW`'s alone; `docs/current/*.md` is generated and never hand-edited.
- **Executors never commit and never transition slice/phase status.** Every `pending` gate in this phase is reached by the executor returning `needs_operator` (or, for S4, by the orchestrator pausing inline).
- **`P12.S4` is an infra co-work slice, not a design round** — no `handoff.md`, no `DesignSync`, no Claude Design, no `@dsCard` cards. Nothing in P12 is product visual design.
- **No feature work.** D3 (attachment GC) and D6 (org management) stay out of scope, as does anything that adds a user-facing capability.
- **Never push without being asked** (`CLAUDE.md`) — the S4 push is an operator gate, not an agent step.

## Doc impact

_Running list — `P12.REVIEW` consolidates these into durable-doc versions. One line per durable-truth change; do not version docs from a middle slice._

- **P12.DECOMP** (no source change): two corrections `P12.REVIEW` should fold in regardless of what the middle slices do — (a) `operations.md` § "Box secrets" claims *"None has a `:-` default: a missing value must fail loudly on the box"*, which is **false as written** (Compose substitutes an empty string with a warning for a plain `${VAR}`; only `POSTGRES_PASSWORD` fails loudly, and only because the `postgres:17` image refuses to initialize without it); (b) `operations.md` § "`.github/workflows/ci.yml`" records **14** prettier failures while `intent.md` says 12–13 — 14 is the measured number.

## Open Questions

1. **Should `P12.S6` (the CI pytest job) move *before* the bring-up?** `intent.md` groups it with the post-launch items as "a statement about a running system", and this decomposition follows that. But a CI test job is a statement about the *repo*, not the running system, and the 108 DB-backed tests have **never run anywhere** — so as ordered, S4's `alembic upgrade head` is the first execution of the full migration chain (including P10's accounts-v2 work) against a real Postgres, and a migration or model defect would surface **on production** instead of on a GitHub runner. The push S4 needs would trigger `ci.yml` anyway. Moving S6 to order ~3.5 costs nothing and buys a real pre-launch signal. **Operator decides at S4's plan gate** (or earlier); `--order` accepts fractions, so no renumbering is required either way.
2. **`/admin/api/*`: keep, retire, or re-expose?** The operator's call at S1's plan gate. Inputs: nine bearer-guarded routes, no first-party client since P6 deleted the Admin Web UI, the edge 404s the whole `/admin/` prefix, and the middleware is **fail-open** when the token is blank (Finding 1). "Retire" also removes one of the three box secrets S4 generates and should bump S1 to `high`.
3. **What do the five vestigial design tokens become?** S2 needs concrete target names in its plan (it is a `slice-executor-low` slice — it must not invent them). The rename is zero-visual-change, so this is naming, not design. Suggested direction: name them for the role their own comments already state (mint tint / data accent / soft positive tint / muted neutral / light neutral surface) rather than for a hi2vi section, and consider **deleting** `--color-archive-olive` and `--color-archive-cream` outright — neither is used anywhere in `web/src`, and P8's audit recorded both as exact duplicates of existing tokens (`muted`, `surface-soft`).
4. **Does `P12.S5` install its backup/rotation artifacts on the box, or only author them?** Depends on whether an executor sandbox can reach `ssh oracle-cloud` — unverified (see Findings). Settle it at S4, which will have proven box access one way or the other, and set S5's plan accordingly (executor-run vs. operator-gated `pending`).
5. **Backup destination and retention are undecided.** On-box dated `pg_dump` files with N-day retention is the cheap default, but it does not survive box loss. Off-box (object storage) needs a credential the operator must provision — an S5 gate if chosen. Also undecided: whether the `attachments-data` volume is backed up at all, or only the database.
