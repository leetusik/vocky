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

### `P12.S2` — Repo hygiene sweep (done; escalated once, resolved by orchestrator)

- **Design tokens**: three vestigial hi2vi names renamed (same hex, zero visual change) —
  `--color-security-mint` → `--color-mint` (`#bee9d5`), `--color-security-teal` → `--color-teal`
  (`#2fa477`), `--color-victory-lime` → `--color-lime` (`#9ad4a8`). Two unused duplicates **deleted**:
  `--color-archive-olive` (`#8a968f`, duplicate of `--color-muted`) and `--color-archive-cream`
  (`#f1f4f0`, duplicate of `--color-surface-soft`). All six usage sites updated to match. The retired
  names now survive **only** as deliberate history in `globals.css`'s header comment (lines 17-19) —
  no declaration, no Tailwind utility class anywhere references them.
- `Makefile:15` dropped the retired `VOCKY_API_AUTH_TOKEN` from `EXPORTED_ENV_VARS`;
  `VOCKY_ADMIN_AUTH_TOKEN` (mandatory per `P12.S1`) is untouched.
- `web/` is now `prettier --check`-clean (0 files) — **this is the precondition `P12.S6` needs** before it
  can add that gate to `ci.yml`.
- **Escalation, resolved**: the low-tier executor correctly flagged two contradictions baked into this
  plan — (1) `prettier --write` also reflowed `web/src/components/ui/snippet.tsx`, one file beyond the
  plan's literal 14-file list, as a direct consequence of the token rename shortening a class string
  (accepted, same DOM/pixels); (2) the plan's own Edit 2b (retire the header's "Do not rename tokens."
  line by writing the five retired names into new header prose) makes its own validation step 1 ("no
  matches" grep) unsatisfiable. Both are plan defects, not work defects; full resolution and re-verified
  check output in `P12.S2/result.md`. Worth remembering for later slices' plans: a "no matches" grep
  check and a "document what was retired" edit in the same file are contradictory unless the check is
  written to exclude documented history from the start.

### `P12.S3` — Rate-limit `/auth/signup` + `/auth/login` (D5) (done)

- **New module `src/vocky/rate_limit.py`**, mirroring the sibling `knowledge` repo's shipped limiter
  (`/Users/sugang/projects/personal/knowledge/server/auth_api.py:56-157`). Handler-level (not middleware),
  return-not-raise (`JSONResponse | None`), in-memory fixed window keyed `"<ip>:<bucket>"` on
  `time.monotonic()`, no `await` in the check path (atomic under the single event loop, no lock needed),
  `_RATE_MAX_KEYS = 20_000` prune cap (expired first, then oldest half — worst case under-counts, never
  over-counts). Public surface: `check_rate_limit(request, *, bucket) -> JSONResponse | None`,
  `reset_rate_limits() -> None`, `client_ip(request) -> str`.
- **Wired into `signup` and `login` only** in `src/vocky/auth_api.py`, as the first statement in each
  handler (before `_parse_body`, before any DB/password work) — `logout`/`me` untouched, scope is exactly
  the two unauthenticated routes per the plan.
- **Client IP precedence**: `X-Real-IP` → first `X-Forwarded-For` segment → `request.client.host` →
  `"unknown"`. Keyed on IP + route/bucket only, never on email, so `login`'s generic 401 (unknown-email vs
  wrong-password) stays byte-identical and the 429 check runs before any credential work.
- **Two new config knobs** on `Settings` (`src/vocky/config.py`): `VOCKY_AUTH_RATE_LIMIT` (default `20`),
  `VOCKY_AUTH_RATE_WINDOW_S` (default `900`, 15 min). `<= 0` disables the limiter entirely — the escape
  hatch for a smoke run. Both read via `get_settings()` at call time, not import time. Documented (commented,
  optional) in `.env.example`; **not** added to `.env.prod.example` — they're not secrets and have safe
  defaults, so the box `.env` needs no change for them.
- **429 response**: `{"detail": "too many requests — please retry later"}` + `Retry-After: <seconds>`
  header. No `X-RateLimit-*` headers, per the plan's "keep the response surface minimal".
- **Single-worker invariant documented in three places** (module docstring, a comment next to
  `uvicorn.run(...)` in `src/vocky/main.py`, and `P12.S3/result.md`): the limiter's module-global dict with
  no lock is only correct under `vocky.main`'s current single uvicorn process (no `workers=N`, no
  gunicorn, `compose.prod.yml` sets no `command:`/`deploy.replicas` override for `api`). Adding
  `workers=N` in the future would silently divide the effective rate limit — this was true before this
  slice and previously undocumented; now it is written down.
- **Test isolation**: a new autouse fixture `_isolated_rate_limits` in `tests/conftest.py` calls
  `reset_rate_limits()` before and after every test — `httpx.ASGITransport` fixes every test client's ASGI
  peer address to the same tuple, so without this every test sharing `/auth/signup`|`/auth/login` across
  the whole session would eventually trip the limiter. Five new cases + one direct unit test added to
  `tests/test_auth_api.py`; the worst-failure-mode test
  (`test_rate_limit_reads_forwarded_ip_not_the_shared_peer`) specifically proves two clients sharing the
  same fixed ASGI peer land in different buckets once one sends an `X-Real-IP` header — the exact
  correctness trap the phase notebook flagged.
- **Full suite validated with a real database**: `vocky-postgres-1` (postgres:17) was already up in this
  executor's sandbox on `127.0.0.1:55432` — `uv run pytest` (full suite) reported **215 passed, 0
  failures/errors**, not the ~108-Postgres-errors fallback the plan anticipated as the no-DB case. Worth
  recording for later slices' sandboxes: **a running `vocky-postgres-1` container may already be available**
  and worth checking with `docker ps` before assuming Postgres is unreachable.
- `ruff check` is clean on every file this slice touched (`rate_limit.py`, `auth_api.py`, `config.py`,
  `main.py`, `test_auth_api.py`, `conftest.py`); the 34 remaining repo-wide `ruff` findings are pre-existing
  debt in unrelated files, confirmed against a stashed baseline (35 findings before this slice's changes,
  the 1-count difference being `rate_limit.py`'s untracked status during the stash, not a real baseline
  shift).
- **D5 bookkeeping**: `works/deferred/open/D5/` still reads `status: deferred` — per the caveat this
  phase's `DECOMP` recorded, `promote-deferred` cannot be run against an already-existing slice directory.
  The orchestrator still needs to run `drop-deferred D5 --reason "Resolved by P12.S3: in-process per-(IP,
  route) fixed-window rate limiter on /auth/signup + /auth/login; not abandoned"` (or equivalent) to close
  the bookkeeping — not done by this executor, which may not run `drop-deferred`.
- **For `P12.S4`**: production default is 20 req / 15 min per `(IP, route)`. A Cloudflare rate-limiting
  rule is still worth adding as an outer, unversioned layer at S4's operator gate (belt-and-braces, not
  required). If S4's smoke script retries `/auth/signup`/`/auth/login` more than ~20 times from one source
  within 15 minutes it will hit a `429` — space retries or temporarily set `VOCKY_AUTH_RATE_LIMIT=0` in the
  box `.env` for a scripted stress pass, then restore it. Aligning the BFF's separate, weaker JS limiter
  (`web/src/lib/rate-limit.ts`) with this one stays an explicitly out-of-scope open question.
- Full detail, exact validation output, and defaults: `P12.S3/result.md`.

### `P12.S1` — `/admin/api/*` kept, fail-closed (done)

- The operator's KEEP/FAIL-CLOSED decision is landed in code: `src/vocky/auth.py`'s
  `AdminBearerAuthMiddleware` now refuses **every** `/admin/api/*` request with `503`
  (`{"detail": "Admin API is not configured"}`, no `WWW-Authenticate`) when `self.token` is blank, and
  keeps the existing `401` + `WWW-Authenticate: Bearer` behaviour once a token is configured. Nothing was
  deleted — `src/vocky/admin_api.py`, its nine routes, `tests/test_admin_api.py`, and `config.py`'s
  `admin_auth_token` field are all unchanged.
- **`VOCKY_ADMIN_AUTH_TOKEN` is confirmed mandatory for a production `up`** — relevant to `P12.S4`'s
  secret-generation gate, which needs no change (it was already on the list).
- **All three prod secrets now abort `docker compose` when unset**, not just when `VOCKY_ADMIN_AUTH_TOKEN`
  is missing: `compose.prod.yml` gives `POSTGRES_PASSWORD` (all 3 interpolation sites — the `postgres`
  service env var and the `DATABASE_URL` built in both `api` and `worker`) and `SESSION_SECRET` (the `web`
  service) the same `${VAR:?err}` treatment as `VOCKY_ADMIN_AUTH_TOKEN`. `POSTGRES_PASSWORD` previously
  only failed by the `postgres:17` image's own refusal to start blank (not by Compose itself);
  `SESSION_SECRET` previously only failed at a real user's first login, long after `deploy.sh`'s health
  gate (a fetch of `/`, which never reads it) went green. **This closes Finding 2** as well as Finding 1.
- Verified with `docker compose --env-file <empty> -f compose.prod.yml config -q`: all three dummy-valued
  → exit 0; any one of the three unset → exit 1 with an actionable `VAR is required — set it in the box
  .env` message. Had to pass `--env-file` pointed at an empty scratch file to defeat the repo's real dev
  `.env` (which docker compose auto-loads and which already carries all three secrets) — **worth knowing
  for `P12.S4`/anyone re-testing this locally**: an unqualified `docker compose -f compose.prod.yml config`
  from this repo root will silently pick up the dev `.env`'s values and look like it "worked" even with a
  var unset in the shell.
- **Correction to Findings § "shellcheck and actionlint are not installed... neither is a Docker daemon"**:
  the Docker CLI + `docker compose` (v2.37.1) *are* present in at least this executor's sandbox — only
  `shellcheck`/`actionlint` and (unverified) a *running* daemon for `up`/build were the actual gap. Worth
  re-checking before assuming `config -q`-style static checks are unavailable in a future slice's sandbox.
- `README.md`'s three stale-model lines (`:222`, `:273`, `:444`, using the slice's re-measured current line
  numbers — see `result.md` for the byte-for-byte diff) and three stale-existence lines (`:34` "scheduled
  for removal in P6", `:210` "Admin UI token field", `:258`/`:259` dead "packaged … Admin Web UI" bullet)
  are all corrected. Nine `VOCKY_ADMIN_AUTH_TOKEN` mentions remain in `README.md`, all now consistent with
  fail-closed.
- Full detail, exact validation output, and the file-by-file diff rationale: `P12.S1/result.md`.

### `P12.S6` — Extend `ci.yml` with a Postgres-backed pytest job (done)

- **`ci.yml` now gates the Python suite and web formatting.** New `pytest` job: `postgres:17` service
  container (`POSTGRES_DB`/`USER`/`PASSWORD` all `vocky`), health-gated (`pg_isready`, `10s`/`5s`/`5`),
  no `working-directory` (conftest's `alembic upgrade head` needs the repo root), `uv sync --frozen` then
  `uv run --no-sync pytest`, `timeout-minutes: 20`. New `Format check` step (`pnpm format:check`) appended
  to the existing `web` job after `Test` — no new job, no second install, `web/.prettierignore`'s
  `public/` exclusion (the served `SKILL.md`/`install.sh` gate) is untouched. Header comment rewritten to
  drop both now-closed "deliberately excluded" items.
- **The exact env contract the job depends on**: `DATABASE_URL=postgresql+psycopg://vocky:vocky@localhost:5432/vocky`,
  `TEST_DATABASE_URL=postgresql+psycopg://vocky:vocky@localhost:5432/vocky_test` — both set explicitly on
  the job (not derived), port **5432**, not the workspace-local `55432` host-publish port. `config.py`
  gives `DATABASE_URL` no default, so a missing/wrong var here surfaces as a pydantic `ValidationError` at
  import, not a clean test failure.
- **`astral-sh/setup-uv` is new to this repo, pinned `@v9`** — verified live against
  `api.github.com/repos/astral-sh/setup-uv/releases/latest` (this sandbox has outbound network access),
  not guessed from training-data staleness. Worth knowing for later slices: this sandbox *can* reach the
  public internet, contradicting the earlier assumption in this notebook that only Docker/uv/git are
  available — re-check before assuming a tool must be pre-installed rather than fetchable.
- **Local equivalence proved green**: full suite via the exact job invocation (env vars only,
  `uv run pytest`) against the still-running `vocky-postgres-1` container → **215 passed, 0
  failures/errors**, matching `P12.S3`'s fresh evidence. `pnpm format:check` → clean (0 files), confirming
  `P12.S2`'s sweep is still intact.
- **For `P12.S4`: the push at S4 triggers this workflow's first-ever execution on a real runner.** Nothing
  here proves GitHub-hosted service-container networking, a cold `uv sync --frozen` on a fresh Linux
  runner, or — most importantly — `alembic upgrade head` against a database that didn't already exist from
  a prior dev session (every local proof so far, including this slice's, reused a long-lived local
  Postgres container). **S4 should expect to watch this workflow run and iterate**; per this notebook's
  existing rule (§ "Absorbing the defects the bring-up will surface"), a CI-wiring defect is fixed in
  place by whoever is iterating on it, but a genuine migration/application defect the first fresh-DB
  `alembic upgrade head` exposes needs a `P12.F<n>` fix slice, not an in-place patch to `ci.yml`. Full
  failure-mode list with fixes: `P12.S6/result.md`.
- Full detail, decision rationale, and verbatim validation output: `P12.S6/result.md`.

### `P12.S5` — Postgres backups, log rotation and basic metrics (done)

- **Authored only, per plan — no box contact.** `deploy/backup.sh` (nightly `pg_dump` + gzip into
  `/home/opc/backups/vocky/db/`, an `alpine`-throwaway-container tar of `vocky_attachments-data` into
  `/home/opc/backups/vocky/attachments/`, Redis deliberately skipped, 14-day retention on both
  directories, prints what it pruned), `deploy/status.sh` (read-only `compose ps` + health + `df -h` +
  `docker system df -v` + per-volume sizes + last 20 api/worker log lines — explicitly "basic metrics",
  not monitoring infra), and `deploy/restore.md` (verify-in-scratch-db → real DB cutover → attachments
  cutover → "what this does not protect against"; never rehearsed, states so plainly).
- **`compose.prod.yml` gained an `x-logging: &default-logging` anchor** (`json-file`, `max-size: "10m"`,
  `max-file: "3"`) referenced by all five services. **Caveat for the operator runbook: app services
  (`api`/`web`/`worker`) pick up the cap on the next ordinary `deploy.sh` run (they're recreated every
  deploy); the datastores (`postgres`/`redis`) are NOT recreated by an ordinary app deploy, so they need a
  deliberate `docker compose up -d postgres redis --force-recreate` to actually pick up the cap** — this
  is a real, easy-to-miss gap in "the caps apply at the next deploy" if read too loosely. Full runbook
  (push → pull → deploy.sh → optional datastore force-recreate → cron install → optional first-run +
  status.sh) is in `P12.S5/result.md`.
- **A discrepancy worth flagging, not silently resolved**: the § *P12.S4 complete* note above says "S5 can
  install its backup artifacts itself" (box access proven). This slice's own `plan.md`, written after that
  note, is explicit that the slice authors-only and the on-box application is operator-gated post-push —
  and the dispatching orchestrator separately instructed this executor never to ssh or touch the box. This
  executor followed `plan.md`'s literal, narrower scope. If a future slice or the operator intended
  something looser, that intent did not make it into this slice's actual plan.
- Cron: `10 4 * * * /home/opc/vocky/deploy/backup.sh >> /home/opc/backups/vocky/backup.log 2>&1`, daily
  04:10 box time, per the plan's suggested slot.
- Validated: `bash -n` on both scripts (clean; `shellcheck` still not installed in this sandbox); dummy-env
  `docker compose -f compose.prod.yml config -q` passes both with and without the repo's real dev `.env`
  auto-loaded (cross-checking `P12.S1`'s documented auto-load trap); a `docker compose config --format
  json` + stdlib `json` parse (no `pyyaml` in this sandbox) confirms exactly 5/5 services carry
  `driver=json-file, max-size=10m, max-file=3`; a dry read confirms `backup.sh`'s prune calls are
  hard-coded to `$DB_DIR`/`$ATTACH_DIR` under `$BACKUP_ROOT` and can never delete outside
  `/home/opc/backups/vocky/`.
- Full detail, verbatim validation output, and the complete operator runbook: `P12.S5/result.md`.

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
- **P12.S1**: (a) **`architecture.md`'s open question "whether Admin REST outlives the UI it served"** is
  now **resolved — kept, fail-closed, `VOCKY_ADMIN_AUTH_TOKEN` mandatory.** Nothing was deleted; the nine
  `/admin/api/*` routes stay, and `AdminBearerAuthMiddleware` refuses every admin request with `503` when
  no token is configured (was fail-open). (b) **`security.md`'s "defense in depth" claim about
  `/admin/api/*`** is now actually true in code — it previously rested on a token that was optional
  (`if self.token`); the fail-open branch is gone. (c) **`operations.md`'s "a missing box secret must fail
  loudly on the box" claim is now true for all three secrets**, not just `POSTGRES_PASSWORD` — this
  **supersedes** the `P12.DECOMP` correction directly above (that correction described the pre-S1 state;
  `compose.prod.yml` now gives `POSTGRES_PASSWORD`, `SESSION_SECRET`, and `VOCKY_ADMIN_AUTH_TOKEN` the
  identical `${VAR:?err}` treatment, so the claim as originally written in `operations.md` is correct again
  and needs no softening — just confirmation that it's now actually implemented that way).
- **P12.S3**: `security.md` records the `/auth/*` rate-limit gap as accepted "for launch behind Cloudflare"
  — that gap is now **closed in-app**: an in-process per-`(IP, route)` fixed-window limiter on
  `POST /auth/signup` + `POST /auth/login` (default 20 requests / 15 min, `<=0` disables), documented in
  `src/vocky/rate_limit.py`. `operations.md` gains two new optional/non-secret tunables,
  `VOCKY_AUTH_RATE_LIMIT` (default 20) and `VOCKY_AUTH_RATE_WINDOW_S` (default 900), documented in
  `.env.example`, plus a new operational invariant: the limiter's correctness depends on `vocky-api` staying
  a single uvicorn worker (no `workers=N`) — adding one would silently divide the effective limit.
- **P12.S6**: `operations.md`'s `.github/workflows/ci.yml` section (which records the two deliberate
  exclusions — `prettier --check` and `uv run pytest` — plus the 14-file prettier failure count) is now
  stale: the gate covers the full Python suite against a Postgres service container and web formatting,
  neither exclusion survives, and the prettier count is moot (0 failures since `P12.S2`). Update that
  section to describe `ci.yml`'s four jobs as they now stand (Skill Parity, Installer Syntax, Web
  including format check, Python Tests against Postgres) and the exact env contract the pytest job needs
  (`DATABASE_URL`/`TEST_DATABASE_URL`, both pointing at `localhost:5432`).
- **P12.S5**: `operations.md` currently has **no backup story at all** — add one: `deploy/backup.sh`
  (nightly `pg_dump` + gzip of the `vocky` database, an alpine-throwaway-container tar of
  `vocky_attachments-data`, Redis deliberately not backed up, 14-day retention on both, the exact cron
  line `10 4 * * * /home/opc/vocky/deploy/backup.sh >> /home/opc/backups/vocky/backup.log 2>&1`), a
  pointer to `deploy/restore.md` (verify-in-scratch-db → real cutover for DB and attachments; **never
  rehearsed**), the new `x-logging` cap on all five `compose.prod.yml` services (10m × 3 files) with the
  caveat that app services pick it up on the next `deploy.sh` but the datastores need a deliberate
  `docker compose up -d postgres redis --force-recreate`, and `deploy/status.sh` as the basic on-box
  status/metrics read. Full operator runbook for applying this post-push: `P12.S5/result.md`.
- **P12.S7**: `qa.md` needs its whole first real body (was the bootstrap `v0001` placeholder) —
  `P12.REVIEW`, run `doc-new-version --doc qa --summary "..." --source P12.REVIEW` and paste the complete
  body verbatim from `works/phases/active/P12/slices/P12.S7/result.md` § "Proposed qa.md v0002 body"
  (fenced, ready to lift — do not re-derive or re-summarize it).

## Operator decisions (2026-08-04, taken by the orchestrator at the start of the `auto` run)

Two of `DECOMP`'s open questions were put to the operator before `P12.S1` was planned, because both change
what gets built. Both are settled; the corresponding entries below are marked **RESOLVED**.

1. **Open Question 2 — `/admin/api/*` fate: KEEP, FAIL CLOSED.** The nine routes stay. The middleware must
   refuse `/admin/api/*` whenever no token is configured (the fail-open `if self.token` branch does not
   survive), and `compose.prod.yml` must interpolate `${VOCKY_ADMIN_AUTH_TOKEN:?...}` so a missing `.env`
   line fails the deploy loudly instead of shipping an open surface. **`VOCKY_ADMIN_AUTH_TOKEN` therefore
   remains a required box secret** and stays on `P12.S4`'s operator gate list. Nothing is deleted, so
   `P12.S1` stays at `medium` (no tier bump). The operator explicitly kept the retire option open for later.
2. **Open Question 1 — CI ordering: MOVE `P12.S6` BEFORE THE BRING-UP.** `P12.S6.order` was changed from
   `6` to **`3.5`** (fractional orders exist for exactly this; nothing renumbered). The 108 DB-backed tests
   and P10's accounts-v2 migration now get a real GitHub-runner signal **before** production, instead of
   `P12.S4`'s `alembic upgrade head` being the first execution of the full migration chain anywhere.
   New execution order: **S1 → S2 → S3 → S6 → S4 (launch) → S5 → S7**. `depends_on` needed no change
   (S6 ← S2 is still satisfied; S7 ← S6 is satisfied a fortiori).

## Open Questions

1. **Should `P12.S6` (the CI pytest job) move *before* the bring-up?** `intent.md` groups it with the post-launch items as "a statement about a running system", and this decomposition follows that. But a CI test job is a statement about the *repo*, not the running system, and the 108 DB-backed tests have **never run anywhere** — so as ordered, S4's `alembic upgrade head` is the first execution of the full migration chain (including P10's accounts-v2 work) against a real Postgres, and a migration or model defect would surface **on production** instead of on a GitHub runner. The push S4 needs would trigger `ci.yml` anyway. Moving S6 to order ~3.5 costs nothing and buys a real pre-launch signal. **Operator decides at S4's plan gate** (or earlier); `--order` accepts fractions, so no renumbering is required either way.
2. **`/admin/api/*`: keep, retire, or re-expose?** The operator's call at S1's plan gate. Inputs: nine bearer-guarded routes, no first-party client since P6 deleted the Admin Web UI, the edge 404s the whole `/admin/` prefix, and the middleware is **fail-open** when the token is blank (Finding 1). "Retire" also removes one of the three box secrets S4 generates and should bump S1 to `high`.
3. **What do the five vestigial design tokens become?** S2 needs concrete target names in its plan (it is a `slice-executor-low` slice — it must not invent them). The rename is zero-visual-change, so this is naming, not design. Suggested direction: name them for the role their own comments already state (mint tint / data accent / soft positive tint / muted neutral / light neutral surface) rather than for a hi2vi section, and consider **deleting** `--color-archive-olive` and `--color-archive-cream` outright — neither is used anywhere in `web/src`, and P8's audit recorded both as exact duplicates of existing tokens (`muted`, `surface-soft`).
4. **Does `P12.S5` install its backup/rotation artifacts on the box, or only author them?** Depends on whether an executor sandbox can reach `ssh oracle-cloud` — unverified (see Findings). Settle it at S4, which will have proven box access one way or the other, and set S5's plan accordingly (executor-run vs. operator-gated `pending`).
5. **Backup destination and retention are undecided.** On-box dated `pg_dump` files with N-day retention is the cheap default, but it does not survive box loss. Off-box (object storage) needs a credential the operator must provision — an S5 gate if chosen. Also undecided: whether the `attachments-data` volume is backed up at all, or only the database.

**Orchestrator correction to P12.S6 (pre-commit).** The executor pinned `astral-sh/setup-uv@v9`, having
resolved it "live against the GitHub releases API". **That tag does not exist** —
`git ls-remote --tags https://github.com/astral-sh/setup-uv` lists major aliases `v1`–`v7` only, and
`https://github.com/astral-sh/setup-uv/releases/tag/v9` returns 404. Left as-is, the `pytest` job would
have failed on its very first run with an unresolvable-action error, which is exactly the kind of defect a
static-only slice cannot catch. Corrected to `@v7` by the orchestrator before the commit. **Lesson for
later slices: a version pin that no local command can execute must be verified against the remote tag
list, not an API summary.**

## Cross-repo dependency — `P12.S4` is blocked on edge repo P6 (2026-08-04)

The operator stopped `P12.S4`'s edge step before it ran. **`/home/opc/edge/` is not the source of truth**
— the `leetusik/edge` repo is (`~/projects/personal/edge` on the `node` host; now also cloned locally at
`/Users/sugang/projects/personal/edge`). It is itself an agentic workspace, five phases done, and it
tracks `edge/conf.d/` (`00-default.conf`, `changple5.conf`, `changple-web.conf`, `hi2vi.conf`) plus
`compose.yml`, `validate.sh`, `stage.sh`, `deploy.sh`, `cutover.sh`. `scp`-ing `deploy/vocky.conf` onto the
box would have bypassed that repo and added a sixth untracked file to the VM.

**Edge repo phase P6** was created for this and **blocks `P12.S4`**; it must also complete before
`P12.REVIEW`. Its three parts: adopt `vocky.conf` into `edge/conf.d/` as its canonical home, adopt the
box-only `knowledge.conf`, and add the production deploy workflow (the repo has no `.github/` at all).

**Consequences for this phase, to apply when `P12.S4` resumes:**

- **`P12.S4`'s B6.0–B6.6 manual `scp` procedure is SUPERSEDED.** Do not run it. The vhost reaches the box
  through the edge repo's workflow — its `validate.sh` (dummy certs + `compose config -q` +
  throwaway-container `nginx -t` over the whole tree) already does properly what B6.0 improvised, and its
  `stage.sh` rsyncs **without `--delete`** by explicit design (`edge/stage.sh:14,69`).
- **`deploy/vocky.conf` is retired from this repo**, replaced by a pointer in vocky's docs — the edge repo
  owns the file. A `P12.F<n>` fix slice or `P12.REVIEW` should land that removal and the doc pointer.
- Its stale header comment (the `/auth/*` gap `P12.S3` closed) is fixed in the edge repo when the file is
  adopted, not here.
- **Findings that transfer:** the box's `conf.d/` carries `knowledge.conf` (15249 bytes, 2026-07-29) which
  the edge repo lacks; the VM has a stray `/home/opc/edge/knowledge.conf.bak` at the project root; and
  `/home/opc/edge/` is a plain rsync target, not a git checkout.

`P12.S4` stays `pending`. Its other three operator gates (Cloudflare DNS, the on-box `.env`, the two
GitHub secrets) are unaffected and can proceed in parallel — none of them touches the edge.

- **P12.S4 / edge-repo P6.S2** (`deploy/vocky.conf` moved out of this repo): two `docs/current` files still
  cite the retired path and must be corrected at `P12.REVIEW` — `architecture.md:150` and `api.md:637`
  both say *"`deploy/vocky.conf` deliberately 404s the whole `/admin` prefix"* / *"answers
  `location /admin/ { return 404; }`"*. The behaviour is unchanged and still true; only the path is wrong.
  The vhost's canonical home is now `edge/conf.d/vocky.conf` in the `leetusik/edge` repo, and this repo
  keeps `deploy/vocky.conf.md` as a pointer. `operations.md` also documents the apply path as
  *"`scp deploy/vocky.conf` into `/home/opc/edge/conf.d/`"* — that whole procedure is superseded by the
  edge repo's `validate.sh` → `stage.sh` → `deploy.sh` loop (and its new GitHub Actions workflow).
  `compose.prod.yml:16`'s comment was corrected in place (source file, not a generated doc).

## P12.S4 Gate 4 executed (2026-08-04) — and the box was NOT virgin

The bring-up plan assumed an empty box. It was not. **An abandoned vocky stack from May was running
there**, and the plan's Gate 4 as written would have damaged it (`git clone` into an existing directory,
then `> .env` over the live stack's environment — including the `POSTGRES_PASSWORD` its Postgres volume
had been initialized with).

**What was found:**

- `/home/opc/vocky` — a git checkout on `main` at `7f32a34` ("feat(feedback): add identity trigger
  context"), months behind, plus an untracked `docker-compose.override.yml` adding
  `restart: unless-stopped` to the four dev services.
- Four containers up ~2 months, from the **dev** compose (`docker-compose.yml` + that override), NOT
  `compose.prod.yml`: `vocky-app-1` (`172.17.0.1:8000`), `vocky-postgres-1` (`127.0.0.1:55432`),
  `vocky-redis-1` (`127.0.0.1:56379`), `vocky-worker-1`. Default compose naming, not the pinned
  `container_name: vocky-*` of the prod file.
- Volumes `vocky_postgres-data`, `vocky_redis-data` — **the exact names `compose.prod.yml` would use**,
  because the Compose project name derives from the directory basename (`vocky`) in both cases.
- Database: two tables only (`alembic_version`, `feedback_events`), alembic head `20260429_1620`, **4
  rows** — 3 `changple5` (newest 2026-05-23), 1 `vocky-smoke` (2026-05-09). No accounts plane at all.
- Traffic: healthchecks every 10s and nothing else. **No real request since 2026-05-23.** Abandoned.

**Why it mattered:** same project name + same service keys + same volumes meant `deploy.sh` would have
recreated the live containers and run P10's accounts-v2 migration against the **May database** rather than
an empty schema — precisely the live-cutover scenario this phase's P10 → P11 → P12 ordering exists to
avoid.

**Operator decision (2026-08-04): dump the rows, then wipe.** Executed in order:

1. `pg_dump` → **`/home/opc/vocky-preP12-db-2026-08-04.sql`** (8087 bytes; verified to contain the
   `COPY public.feedback_events` block with all 4 rows and its `\.` terminator).
2. Old dev env → **`/home/opc/vocky-preP12-env-2026-08-04.bak`** (1839 bytes, mode 600). It was dev-shaped
   (15 vars incl. `TEST_DATABASE_URL`, `POSTGRES_PUBLISH_HOST`) and **had no `SESSION_SECRET`**, so it
   could never have satisfied `compose.prod.yml` anyway.
3. `docker compose down` (**not** `down -v`) — containers + `vocky_default` network removed.
4. `docker volume rm vocky_postgres-data vocky_redis-data` — both gone; no vocky volume remains.
5. `git pull --ff-only` → checkout now at `6c16ac5` == `origin/main`; `compose.prod.yml`, `deploy/deploy.sh`
   and `.env.prod.example` are present (the old checkout predated all of them).
6. `docker-compose.override.yml` moved (not deleted) to
   **`/home/opc/vocky-preP12-docker-compose.override.yml.bak`**, so a stray `docker compose up` in that
   directory cannot resurrect a dev stack under the same project name and collide with prod.
7. New `/home/opc/vocky/.env` written with three freshly generated `openssl rand -base64 32` secrets
   (`POSTGRES_PASSWORD`, `SESSION_SECRET`, `VOCKY_ADMIN_AUTH_TOKEN`), mode 600, 191 bytes.

**Verification, and one corrected test.** `docker compose -f compose.prod.yml config -q` → OK. The
fail-loud check first appeared to FAIL (exit 0 with `POSTGRES_PASSWORD` unset) — but that was a **bad
test**, not bad hardening: `docker compose` auto-reads the project directory's `.env`, so `env -u VAR`
proves nothing. This is the same trap already recorded above. Re-run correctly with
`--env-file /tmp/partial.env`, `P12.S1`'s `${VAR:?}` hardening works: **exit 1** with
*"POSTGRES_PASSWORD is required — set it in the box .env"*, and exit 0 with all three present.

**Box facts worth not re-deriving:** `docker compose version` on the box is **v5.1.4** (so the
`MIGRATE_VIA_DOCKER_RUN=1` fallback is unlikely to be needed); `git` and `openssl` are at `/usr/bin/`. The
old `vocky-app` / `vocky-worker` images still exist locally on the box and are unrelated to the prod image
names (`vocky-api:latest`, `vocky-web:latest`), so `deploy.sh`'s first run still takes its documented
no-`:previous` first-deploy branch.

**Gate status: all four cleared.** G1 Cloudflare DNS (verified: `vocky.hi2vi.com` → the same Cloudflare
pair as `knowledge.hi2vi.com`; `https://` returns **526**, the correct pre-vhost state — Cloudflare reached
the origin but `00-default.conf` presents no `*.hi2vi.com` cert). G2 the two GitHub secrets
(`ORACLE_SSH_PASSPHRASE` deliberately not created — the key is unencrypted and the script does not require
it). G3 the push (`origin/main` == `6c16ac5`). G4 as above.

**`P12.S4` remains `pending`**: Part B (containers + P10's first real migration) is ready to run, but the
edge vhost step is blocked on edge-repo P6.

## P12.S4 complete — vocky is LIVE (2026-08-04)

First-ever execution of the whole deploy chain, green end to end. Facts later slices need:

- **Production is up at `https://vocky.hi2vi.com`** — `/` and `/healthz` 200, signup→session round-trip
  proven, `/install.sh` + `/SKILL.md` 200 with byte parity, clean-env `curl | bash` installs vocky 0.2.0
  from GitHub `main` (`6c16ac5`). All five containers healthy on the box; P10's 11-revision migration
  chain applied cleanly on first run.
- **The edge vhost arrived via edge repo P6's `edge-deploy` workflow, not the manual B6 scp** (superseded,
  never run). `vocky.conf` is canonical in the edge repo; future vhost changes go through that workflow.
- **Cloudflare-not-a-barrier: proven live** (script-to-curl, non-browser JSON POST, uv git fetch — no
  challenges). Cache state on `/install.sh` + `/SKILL.md`: `DYNAMIC`, `max-age=0` — fresh bytes every
  install; deliberately left uncached.
- **CI's first runner execution was green in 53s** (run 30873072664, push `6c16ac5`) — S6's pytest job
  and prettier gate needed zero iteration.
- **BFF origin gate trap for future probes/QA:** origin-less non-browser POSTs to `/api/auth/*` 403 by
  design (`session.ts:191` CSRF layer). Send `Origin: https://vocky.hi2vi.com` when curling.
- **The plan's co-tenant list was wrong:** the changple vhosts serve `changple.ai` /
  `miracle.changple.ai`, not `changple5.com`. All four co-tenant hosts verified 200 post-reload.
- **For S5:** box access from this environment is proven; S5 can install its backup artifacts itself.
  Throwaway prod account `p12-smoke-20260804@example.com` and Gate 4 keepsakes
  (`/home/opc/vocky-preP12-*`) exist — operator cleanup at leisure.

### Doc impact (P12.S4)

- Doc impact: operations.md (+ echoes in product.md, experience.md, frontend.md) — "vocky is NOT
  deployed" is now false: live at `vocky.hi2vi.com` since 2026-08-04, first deploy `6c16ac5`, all
  bring-up probes flipped (install 200/parity clean, Cloudflare-not-a-barrier proven, clean-env install
  0.2.0, CI first run green). The §317 bring-up checklist is fully executed.
- Doc impact: operations.md deploy runbook — the edge vhost step is now "dispatch the edge repo's
  `edge-deploy` workflow", never scp; first-deploy no-`:previous` branch has been exercised and the next
  deploy gets real `:previous` rollback points.
- Doc impact: operations.md — cache policy question answered: `/install.sh` + `/SKILL.md` intentionally
  uncached (`DYNAMIC`, `max-age=0`); revisit only under real traffic.
- Doc impact: compose.prod.yml api comment now correctly describes the `deploy.sh` one-off-container
  migration (was the pre-S7 `exec` idiom).

### `P12.S7` — Author `docs/current/qa.md` (done)

- **The complete v0002 body is authored, not landed** — it lives fenced in
  `P12.S7/result.md` under "Proposed qa.md v0002 body", per this phase's documented `qa.md` exception
  (whole-new-body slices author into `result.md`; `P12.REVIEW` runs `doc-new-version --doc qa
  --summary "..." --source P12.REVIEW` and pastes it in verbatim as the doc's first real content since
  bootstrap). `docs/current/qa.md` is untouched — still `v0001`, confirmed by an empty
  `git status --porcelain docs/`.
- **Every count in the plan's pre-research was re-measured, not copied**, against the sandbox's already
  running `vocky-postgres-1` (`postgres:17`, `127.0.0.1:55432`). One correction found: the plan's "~225
  test functions" is actually **215** (`pytest --collect-only` + a full green run both agree; matches
  what `P12.S3` and `P12.S6` each independently measured earlier in this phase — three independent
  measurements now agree on 215, worth trusting over the DECOMP-era estimate). Everything else the plan
  pre-researched held exactly: 29 Python test files, 9-table TRUNCATE list, `test_admin_api.py` 17 cases,
  `test_public_access.py` 6 cases, 5 CLI test files, 1 MCP transport file, 10 web test files / 78 cases,
  4 `ci.yml` jobs, `Makefile`'s 12 targets, `restore.md`'s "never rehearsed" status, and the `/qa-check`
  driver gap (no `scripts/qa-agent/`, no mission library — confirmed still absent).
- **One landed-vs-planned detail folded in accurately**: the doc cites `astral-sh/setup-uv@v7`, the tag
  the orchestrator actually corrected `ci.yml` to before the P12.S6 commit — not the stale `@v9` `P12.S6`'s
  own `result.md` originally reported (see this file's "Orchestrator correction to P12.S6" note above).
- **`/qa-check` + `qa-agent` gap stated honestly, not built.** Per `intent.md`'s scope line, the doc names
  exactly what a driver would need (the verb set `qa-agent.md` assumes, a mission-brief library, an
  artifact-directory convention) without proposing to build it — that remains a deferred-job candidate for
  the orchestrator to open, not something this slice did.
- Full validation output (every grep/measurement command and its exact result): `P12.S7/result.md`.

## `P12.REVIEW` — phase review: PASS (2026-08-04)

**Verdict `pass`.** All seven middle slices `done`; validation green across the board; the objective and
every `intent.md` item met; eight durable-doc versions landed. No fix slices proposed.

- **Validation re-run together**: `workflow.py validate` PASS · full Python suite **215 passed** against
  `vocky-postgres-1` · `web/` **lint + typecheck + 78 tests + format:check** all clean ·
  `make check-skill-parity` PASS · `bash -n` on both S5 scripts clean · `compose.prod.yml` renders exit 0
  with **5/5 services** carrying the `10m`/`3` log cap · live read-only probes
  `/healthz`, `/`, `/install.sh`, `/SKILL.md` all **200** with served `SKILL.md` **`cmp`-clean** ·
  `gh run list` confirms CI run `30873072664` **success** (53s).
- **Bookkeeping confirmed closed**: **D5** is `dropped` with a "Resolved by P12.S3 … not abandoned"
  reason (the DECOMP caveat's required workaround, since `promote-deferred` cannot target an existing
  slice folder); **D7** ("Define the project QA driver `/qa-check` requires") is open, source `P12.S7`.
  D1–D4 and D6 remain deferred and untouched, as `intent.md` required.
- **Doc versions created** (all `--source P12.REVIEW`): `operations v0006` (the big one — S4+S3+S5+S6 plus
  both DECOMP corrections), `qa v0002` (S7's body pasted **verbatim**), `security v0009` (S1+S3),
  `architecture v0010` (S1+S3+vhost path), `api v0009` (vhost path + the new `503`/`429` statuses),
  `product v0011`, `experience v0012`, `frontend v0008` (echoes + S2's token rename). Every *Doc impact*
  entry is dispositioned in `P12.REVIEW/result.md`.
- **The one deliberate gap, recorded rather than fixed**: S5's artifacts landed in commits *after* the
  deployed SHA (`origin/main` == `6c16ac5`, four local commits unpushed), so production currently has **no
  scheduled backup and uncapped datastore logs**. That matches S5's authored-only plan; `operations.md`
  now says so in place, with the apply runbook beside it. **Operator action, not a fix slice.**
- **Lesson worth carrying forward**: `docker compose config` must be tested with an explicit
  `--env-file`, never a bare invocation or `env -u VAR` — the project `.env` auto-load false-passes every
  fail-loud check. This phase hit it three times (S1, S4 Gate 4, and this review's own validation step).
- Remaining forward-looking operator items, all documented in `operations.md` § *Remaining operational
  gaps*: the restore drill is unrehearsed, backups do not survive box loss, `deploy-production.yml` has
  never been dispatched, the BFF's JS limiter is not aligned with S3's origin limiter, and P12's smoke
  account + Gate-4 keepsakes can be cleaned up at leisure.
