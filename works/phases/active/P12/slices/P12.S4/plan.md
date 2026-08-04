# Plan — P12.S4: Production bring-up at `vocky.hi2vi.com`

Mode: `/do-whole-phase auto`. **Not dispatched to an executor** — `kind: co-work`, run by the
orchestrator inline on the main thread with the operator in the loop.

**This is infra/operator co-work, not a `design-cowork` round.** No `handoff.md`, no `DesignSync`, no
Claude Design, no cards. The `co-work` kind is used only because the slice needs a human for four gates
and touches real infrastructure.

## What this is

The first-ever execution of the entire deploy chain. `compose.prod.yml`, `web/Dockerfile`,
`deploy/vocky.conf`, `deploy/deploy.sh`, `deploy/rollback.sh` and the three-file GitHub Actions chain were
all validated **statically only** — no `docker build`, no `compose up`, no `nginx -t` on `vocky.conf`, no
script has ever executed. So this is simultaneously the first behavioural test of **P6.S4–S8**, of
**P10's accounts-v2 migration**, and of **P11's install path**.

**Plan it to iterate, not to succeed first time.** `phase.md` records the routing rule:

- **In-slice iteration** for *deploy-chain* defects — a wrong path, a missing env, a healthcheck timing
  out, a compose or nginx syntax error, an image that will not build, a migrate invocation the box's
  Compose refuses.
- **A follow-on `P12.F<n>` fix slice** for *application* defects — a P10 migration or model bug the first
  real `alembic upgrade head` exposes, a P11 install-path bug, a web/BFF bug that only appears against a
  real origin. Those are other phases' code; they get their own plan and validation and must **not** be
  repaired inline on the main thread.

## Corrections to `phase.md` this plan carries

1. **`ssh oracle-cloud` IS configured.** `phase.md` § *Findings* records box reachability as UNVERIFIED
   because the permission classifier refused `~/.ssh/config` at DECOMP time. It is readable now:
   `Host oracle-cloud` → `HostName 140.245.64.173`, `User opc`,
   `IdentityFile /Users/sugang/projects/personal/keys/ssh-key-2025-05-08.key`, `ForwardAgent yes`.
   An actual connection has still **not** been attempted — that is step A1 below.
2. **The unpushed-commit count is 66, not 57.** Measured at plan time
   (`origin/main` `3e1e85a` → `main` `49f9c95`). Re-measure before pushing; it drifts every slice.

---

## Gate G — operator only (the slice starts `pending` here)

### G1 · Cloudflare DNS
A **proxied** (orange-cloud) `vocky` record on the `hi2vi.com` zone, pointing at the box
(`140.245.64.173`). Mirror the record type used by the sibling `knowledge` / `hi2vi` records — the repo
never pins A vs CNAME, only the *proxied* flag. TLS needs nothing: the wildcard
`/home/opc/edge/certs/hi2vi.crt` already covers `*.hi2vi.com` and Cloudflare is Full (Strict).

**Verify:** `dig +short vocky.hi2vi.com` returns Cloudflare anycast IPs, and
`curl -sSI https://vocky.hi2vi.com/` completes a TLS handshake. A 502/404 here is fine — it proves
DNS + TLS, not the app.

### G2 · On-box `.env` secrets
On the box, `cp .env.prod.example .env` in `/home/opc/vocky` and fill **exactly three** values, each from
`openssl rand -base64 32`:

| Variable | Consumed by |
|---|---|
| `POSTGRES_PASSWORD` | the `postgres` service, and baked into api + worker `DATABASE_URL` |
| `SESSION_SECRET` | **web only** — rotating it logs every user out |
| `VOCKY_ADMIN_AUTH_TOKEN` | **api only** — guards `/admin/api/*`; still required after `P12.S1` |

Do **not** add `DATABASE_URL`, `REDIS_URL`, `VOCKY_API_BASE_URL` (committed literal container-name URLs)
or `NEXT_PUBLIC_APP_URL` (a compose *build arg*).

**Verify:** `cd /home/opc/vocky && docker compose -f compose.prod.yml config -q` exits 0; unsetting any
one of the three makes it exit 1 with the `:?` message `P12.S1` added.

### G3 · GitHub repo secrets on `leetusik/vocky`
`ORACLE_SSH_PRIVATE_KEY`, `ORACLE_SSH_KNOWN_HOSTS`, `ORACLE_SSH_PASSPHRASE` — the hi2vi/knowledge key
material for this same box is reusable. Only the first two are hard-required by
`deploy/github-actions-production-deploy.sh`; the passphrase is optional.

**Verify:** all three listed under Settings → Secrets → Actions. Real proof is a `workflow_dispatch` of
`deploy-production.yml`, which can wait until after the manual first deploy.

### G4 · The `git push`
66 commits are unpushed. `CLAUDE.md` forbids pushing unasked, so this is the operator's call — but it is a
**hard prerequisite**, not a nicety: the on-box gate ancestor-verifies `TARGET_SHA` against fetched
`origin/main`, `install.sh` resolves the GitHub `main` `git+https://` target, and `ci.yml` (including the
job `P12.S6` just added) has never executed on a runner. **The push must precede the installer probe
(§C4)** — installing before it silently delivers a pre-P10 CLI with no org keys and no `vocky capture`.

**Verify:** `git rev-list --count origin/main..main` → `0`.

---

## Part A — reachability and pre-flight (agent, after G is cleared)

- **A1.** `ssh oracle-cloud 'echo ok; docker --version; docker compose version'` — first real proof of box
  access and of the Compose major version.
- **A2.** `ssh oracle-cloud 'docker network inspect changple_shared_network >/dev/null && echo net-ok'` —
  the external network every service attaches to.
- **A3.** `ssh oracle-cloud 'ls -d /home/opc/vocky /home/opc/edge/conf.d 2>&1; docker images | grep -c vocky- || true'`
  — does the clone already exist, and does a `vocky-api:latest` already exist (which would change the
  first-run no-`:previous` behaviour)?

## Part B — the deploy (agent)

- **B1. Clone to `/home/opc/vocky` — the path is load-bearing.** `deploy/deploy.sh`'s `dc()` pins no `-p`,
  so the Compose project name derives from the clone directory's basename: `/home/opc/vocky` → project
  `vocky` → volumes `vocky_postgres-data` / `vocky_redis-data` / `vocky_attachments-data`. **Any other
  path silently orphans the datastores on the next deploy.** The path is already hard-coded in both
  GitHub-Actions deploy scripts.
  ```sh
  ssh oracle-cloud 'git clone https://github.com/leetusik/vocky.git /home/opc/vocky'
  ```
- **B2.** Place the G2 `.env` at `/home/opc/vocky/.env`.
- **B3. Run `deploy/deploy.sh`, not a raw `compose up`.** P6.S7's hand-off says to; the script owns the
  whole ordered lifecycle. `COMPOSE_BAKE=false` is required (this host's Compose panics on the bake path)
  and the script exports it itself.
  ```sh
  ssh oracle-cloud 'cd /home/opc/vocky && deploy/deploy.sh'
  ```
  Its order is load-bearing: tag rollback points → `up -d postgres redis` + health → `build` →
  **migrate** → `up -d` → gate. It never runs `down` or `down -v` on any path. On this first run both
  images lack a `:previous`, so a failure leaves the stack **up for inspection** and exits non-zero —
  that is the documented first-deploy branch, not a bug.
- **B4. Health gate:** `postgres`, `redis`, `api`, `web` must go `healthy`; **`worker` is gated on state**
  (`running` and not `Restarting`, two consecutive polls) because it has no healthcheck by design. Budget:
  `HEALTH_TRIES=24 × HEALTH_INTERVAL=5s`; note `api` has a `start_period: 60s`, so only ~60s of that
  budget is real health — a slow cold first boot is the likely false timeout.
- **B5. Migration** runs inside `deploy.sh` as
  `docker compose -f compose.prod.yml run --rm -T --no-deps --name vocky-migrate-$$ api uv run --no-sync alembic upgrade head`.
  It takes the **service key `api`**, never the container name. Documented fallback if the box's Compose
  refuses it: `MIGRATE_VIA_DOCKER_RUN=1`. **This is P10's accounts-v2 migration running for the first time
  anywhere — read its output rather than skimming it.**
- **B6. Edge vhost.** Never `docker cp` into `edge-nginx`, never recreate the edge container.
  ```sh
  scp deploy/vocky.conf oracle-cloud:/home/opc/edge/conf.d/vocky.conf
  ssh oracle-cloud 'cd /home/opc/edge && ./validate.sh && ./deploy.sh'
  ```
  The `conf.d/` tree is tested and reloaded **as a unit**: a bad `vocky.conf` fails `nginx -t` for every
  co-tenant. Untouchable siblings: `00-default.conf`, `changple5.conf`, `changple-web.conf`, `hi2vi.conf`,
  `knowledge.conf`. A failed `nginx -t` reloads nothing and the edge keeps serving last-known-good.

## Part C — smoke (agent), the point of the whole slice

- **C1.** `curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/healthz` → `200` (api) and
  `https://vocky.hi2vi.com/` → `200` (web).
- **C2. An authenticated round-trip — do not skip this.** A blank `SESSION_SECRET` **passes** the health
  gate, because the web healthcheck fetches `/`, the static landing page, which never reads it; it fails
  only at a real user's first login. So sign up (or log in) over the real origin and confirm a session.
  Mind `P12.S3`'s limiter while doing it: >20 `/auth/*` requests from one IP in 15 min returns 429. Space
  the attempts rather than disabling the limiter.
- **C3. The two armed probes P11 left**, both `404` today:
  ```sh
  curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh   # must become 200
  curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/SKILL.md     # must become 200
  ```
  Then byte-parity on the served copy:
  `curl -fsSL …/SKILL.md -o /tmp/served-SKILL.md && cmp /tmp/served-SKILL.md skills/vocky-feedback/SKILL.md`
  → exit 0.
- **C4. Install from the real target into a clean environment — install-and-check, not assert.** Only
  meaningful **after** the G4 push. Run `curl -fsSL https://vocky.hi2vi.com/install.sh | bash`, then
  assert `vocky --version` ≥ `0.2.0` and that `vocky capture --help` renders.
- **C5. Run the Cloudflare-not-a-barrier probe live.** It is unrunnable while the site is down; do not
  design around an unverified blocker.
- **C6.** Confirm `ci.yml`'s first-ever runner execution (triggered by the G4 push) — the `pytest` job
  with its Postgres service container and the `pnpm format:check` step have never run on GitHub. Watch it
  and iterate; `P12.S6`'s `result.md` lists the likely first-run failure modes.

## Open questions to settle during the slice

- **Cache policy for `/install.sh` and `/SKILL.md`** — deliberately left as a bring-up question. Both are
  served straight off `web/public/` through the edge's `/` catch-all.
- **Whether a Cloudflare rate-limiting rule on `/auth/*` is still worth adding** as an outer layer now
  that `P12.S3`'s in-app limiter has landed. Console-only and unversioned, so it can never be the primary.
- **Whether `P12.S5` can install its backup artifacts itself**, which A1 now answers: box access from this
  session is proven or it is not.
- `compose.prod.yml`'s api comment still cites the pre-S7 `exec vocky-api …` migrate idiom and is wrong as
  written — a candidate one-line fix while in the file.

## Deliverables

- `result.md`: what actually happened at each step, every defect found and how it was routed (in-slice vs
  a proposed `P12.F<n>`), the smoke output, and the answers to the open questions above.
- Notes appended to `phase.md` § *Findings & Notes*, and **Doc impact** lines for `P12.REVIEW`: at minimum
  the two statements that become false the moment this succeeds — *"vocky is NOT deployed"*
  (`operations.md:18-26`, echoed in `product.md`, `experience.md`, `frontend.md`) and *"the hosted install
  line 404s until P12 deploys"*.
