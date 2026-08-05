# P6.REVIEW — result

**Verdict: `pass`.** P6 met its *reframed* objective — every production artifact authored and statically
validated, nothing deployed. All nine middle slices (S1–S9) are `done`, each `result.md` explains its
deviations, and re-running their validation reproduced their recorded outcomes. Eight durable docs were
consolidated into new versions. Three cosmetic staleness findings are recorded below for the orchestrator
to fast-path; none of them blocks the phase.

**explain:** not written — run `/explain` for this phase.

## What I judged P6 against

Not its `phase.json` objective string, which is stale twice over. `phase.md` §Context records both reframes:
the landing/webpage moved to P8→P9 (D-P8-1 superseded D-P4-3), and on 2026-07-28 the operator moved the live
bring-up out of P6 into P12 (`"mind that deploy will be done at p12 so p6 doesn't have to mind it"`). The
standard applied was therefore: **every production artifact authored and statically validated, nothing
deployed.** The `P6.S10` row and the "Hand-off to S10" notes stay in `phase.md` on purpose — they are the
spec P12 executes — and their presence was treated as correct, not as unfinished work.

Two things the plan flagged as non-defects, confirmed as such and **not** reported as findings: (1) nothing
in P6 ever ran against real infrastructure (no Docker daemon, no Postgres in-sandbox); (2) `P6.S9` did not
publish to PyPI, because the publish moved to P11.

## Objective check — did P6 ship?

| Slice | Deliverable | Verified how | Status |
|---|---|---|---|
| S1 | Admin Web UI physically removed | `admin_ui.py`, `admin_assets/`, `check_admin_ui_package.py` all absent; `grep -rn "admin_ui\|admin_assets" src/ tests/ scripts/ Makefile` → no match; live app enumerates **exactly 9 `/admin/api/*` routes** and both middlewares | ✅ |
| S2 | Site metadata + production origin | `pnpm build` emits all six routes (`icon.svg`, `apple-icon`, `opengraph-image`, `robots.txt`, `sitemap.xml`, `manifest.webmanifest`) as `○ Static` | ✅ |
| S3 | CSP + security headers | `web/next.config.ts` carries `isProd`-gated CSP + `Permissions-Policy` incl. `browsing-topics=()`; no HSTS in the app (correct — edge's) | ✅ |
| S4 | `web/Dockerfile` | statically reviewed: no build-stage `NODE_ENV`, `ARG NEXT_PUBLIC_APP_URL` + non-empty assert, standalone copy, `USER node`, `EXPOSE 3000`, image `HEALTHCHECK` | ✅ |
| S5 | `compose.prod.yml` + `.env.prod.example` | `docker compose config -q` exit 0 (prod **and** dev); five services, `expose:`-only, `external: true`, container-name upstreams, shared `attachments-data`, three `${...}` secrets, no `env_file:` | ✅ |
| S6 | `deploy/vocky.conf` | house-rule grep empty (exit 1); all nine locations present; **routing map re-reconciled against the live route table** (see below) | ✅ |
| S7 | `deploy.sh` + `rollback.sh` | `bash -n` both pass, both `-rwxr-xr-x`; rendered compose confirms `worker → image: vocky-api:latest` with **no `build:`** | ✅ |
| S8 | CI deploy chain | `bash -n` all three scripts pass; YAML parses — jobs `[preflight, deploy]`, `environment.url=https://vocky.hi2vi.com`, `concurrency.group=vocky-deploy`, `on: workflow_dispatch` only | ✅ |
| S9 | PyPI packaging | `uv build` **reproduced** sdist 79 KB + wheel 95 KB; `uvx --from <wheel> vocky --version` → `0.1.0` installing **15 packages** | ✅ |

**Nothing deployed** — confirmed: no box clone, no box `.env`, no DNS record, no `ORACLE_SSH_*` secrets, no
container ever started. Correct for the reframed scope.

## Validation re-run across the whole phase

The orchestrator trusted each `done` verdict without re-running per-slice validation, so everything below was
re-executed here.

| Command | Result |
|---|---|
| `python3 scripts/workflow.py validate` | **PASS** — "Workflow validation passed." (re-run after doc consolidation) |
| `uv run pytest -q` | **79 passed, 108 errors** — byte-identical to what S1/S9 recorded; every error is `psycopg.OperationalError` (no Postgres on 55432, no Docker daemon) |
| `cd web && pnpm test` | **PASS** — 5 files, 56/56 |
| `cd web && pnpm lint` | **PASS** — eslint clean, no findings |
| `cd web && pnpm build` | **PASS** — compiled + typechecked, 13/13 static pages, all six metadata routes emitted `○ Static` |
| `uv run python -c "from vocky.app import create_app; …"` | **PASS** — 9 `/admin/api/*` routes, middleware `['ProjectCredentialAuthMiddleware', 'AdminBearerAuthMiddleware']`, `/mcp` mount present |
| `grep -rn "admin_ui\|admin_assets" src/ tests/ scripts/ Makefile` | **PASS** (empty, exit 1) |
| `POSTGRES_PASSWORD=x SESSION_SECRET=x VOCKY_ADMIN_AUTH_TOKEN=x docker compose -f compose.prod.yml config -q` | **exit 0** |
| `POSTGRES_PASSWORD=x docker compose -f docker-compose.yml config -q` | **exit 0** |
| `grep -n "VOCKY_API_AUTH_TOKEN" docker-compose.yml compose.prod.yml` | **PASS** (empty) |
| `grep -n "default_server\|listen \[::\]\|limit_req_zone" deploy/vocky.conf` | **PASS** (empty, exit 1) |
| `bash -n` × 4 (`deploy.sh`, `rollback.sh`, `github-actions-production-deploy.sh`, `oracle-production-deploy-remote.sh`) | **all PASS**; all four `-rwxr-xr-x` |
| `uv run --with pyyaml python3 -c "yaml.safe_load(...)"` on the workflow | **PASS** |
| `uv build --out-dir <tmp>` | **PASS** — sdist **79,195 B**, wheel **95,390 B** (reproduces S9 exactly; the hatch sdist include-list is holding) |
| `uvx --no-cache --from <wheel> vocky --version` | **PASS** — `0.1.0`, **15 packages** installed (lean-CLI split proven independently of S9's run) |

**Could not be run in-sandbox** (reported rather than skipped silently): `docker build` of either image, an
actual `docker compose up`/health-gate, `nginx -t` on `deploy/vocky.conf`, any execution of `deploy.sh` /
`rollback.sh` / the CI chain, and the 108 DB-backed tests. No Docker daemon, no Postgres, no nginx, no box.
`shellcheck` and `actionlint` are also not installed. **All of this is P12's behavioral proof**, exactly as
every slice recorded.

## Cross-checks I ran beyond the per-slice commands

- **Edge routing map vs the live route table.** Enumerated all 30 backend route paths and the web app's built
  route list, then walked them through `deploy/vocky.conf`'s longest-prefix map. Everything lands correctly:
  `/api/project/*` and `/api/feedback*` → api (they do *not* match `/api/app/`); `/api/auth/*` and
  `/api/app/feedback/[id]/attachments/[id]` → web (the two real BFF routes, and they correctly beat `/api/`);
  `/auth/*`, `/app/*`, `= /healthz`, `/mcp` → api; `/admin/api/*` → caught by `location /admin/` → 404; the
  web app's own pages (`/dashboard`, `/projects/*`, `/feedback*`, `/login`, `/signup`) fall to `/` → web.
  **No uncovered prefix, no misroute.**
- **The `/admin` story end to end.** S1 deleted the UI; the app now exposes only the nine bearer-guarded
  `/admin/api/*` routes; S6 404s the whole `/admin/` prefix at the edge; `VOCKY_ADMIN_AUTH_TOKEN` remains a
  required box secret in `.env.prod.example`. Coherent. The tension (a mandatory secret guarding an
  externally-unreachable surface) is real and is **deliberate defense in depth** — co-tenant containers on
  `changple_shared_network` can reach `vocky-api:8000` directly, so the app-level bearer is the actual
  boundary and the edge 404 is an outer layer. Routed to P12, documented, not failed on.
- **CI ↔ deploy contract.** The on-box gate hands off `deploy/deploy.sh "$TARGET_SHA"` and the workflow
  `bash -n`s S7's script; `deploy.sh` is unmodified by S8 (`git status` clean). `/home/opc/vocky` is
  consistent across all three scripts and the workflow comment — which matters, because `dc()` pins no `-p`,
  so the clone dir basename *is* the Compose project name and the volume prefix.
- **CI smoke ↔ edge map.** The workflow smokes `/healthz` and `/`; both are real, correctly-routed edge paths
  (exact-match to api, catch-all to web).
- **D5 (the `/auth/*` rate-limit gap)** is recorded accurately in `works/deferred/open/D5/`, sourced to
  `P6.S6`, still `deferred`. Not reopened.

## Findings (non-blocking — reported, not fixed here)

The review writes no source code, so these are handed back. All three are **doc-only wording corrections with
no behavior, contract, or workflow impact** — CLAUDE.md's fast-path exception covers them; they do **not**
warrant `P6.F<n>` fix slices.

1. **`README.md` describes the deleted Admin Web UI as still shipping.** Line 32 ("A packaged self-hosted
   operator Admin Web UI still ships under `/admin` … scheduled for removal in P6"), line 184 ("still loads
   for self-hosted operators … paste that token into the Admin UI token field"), and line 233 ("The packaged
   (superseded, P6-removal) Admin Web UI under `/admin`"). S1 removed it; these three are now flatly false.
   S1's `result.md` routed them to REVIEW, but README is source, not a versioned doc, so the review cannot
   fix them.
2. **`README.md` line 48 says "PyPI publishing is P6; until then, install from a checkout."** The publish
   moved to P11. The install-from-checkout instruction is still correct; only the phase attribution is wrong.
3. **`Makefile` line 15 still exports the retired `VOCKY_API_AUTH_TOKEN`** in `EXPORTED_ENV_VARS`. Harmless
   (it exports an unset var and nothing reads it) but stale since P1 retired the token.

Two lower-severity observations, recorded for whoever touches these files next:

4. **`compose.prod.yml` comment drift** (api service, near the `DATABASE_URL` line): it still cites the
   pre-S7 migrate idiom `docker compose exec vocky-api uv run --no-sync alembic upgrade head`. S7 replaced
   that with `docker compose run --rm -T --no-deps --name vocky-migrate-$$ api …` — and `exec`/`run` take a
   **service key**, not the container name, so the comment's command would fail as written. Comment only;
   `deploy.sh` is correct.
5. **`deploy/oracle-production-deploy-remote.sh` declares `PROJECT_NAME` and `COMPOSE_ENV_FILE` but never
   references them** (S8 documented this deliberately — `collect_status` mirrors `deploy.sh`'s unpinned
   `dc()`). Would be SC2034 under shellcheck, which is not installed. Intentional; noted only so a later
   shellcheck run isn't mistaken for a regression.

## Doc consolidation

Eight versions created from the `phase.md` "Doc impact" running list (S1–S9), each edited at its returned
`edit_path`, then `rebuild-docs`. Two forward-looking facts are stated honestly in every doc that touches
them: **vocky is not deployed** (bring-up is P12) and **the CLI is not on PyPI** (distribution is P11).
Nothing was written that presumes either has happened.

| Doc | Version | Covers |
|---|---|---|
| `operations` | **v0004** | The big one. A prominent "vocky is NOT deployed" status block; the box + shared-edge model and vhost apply path; the serving contract and five-service table; the three box secrets and the no-`env_file:` rule; the two images and their traps; the edge routing map, header-inheritance footgun, and house rules; the full deploy/rollback runbook (ordering, the `run`-takes-a-service-key migrate idiom, `COMPOSE_BAKE=false`, never-`down`, the `MIGRATE_VIA_DOCKER_RUN` fallback); the CI path and its three required secrets; `NEXT_PUBLIC_APP_URL` as a build-time origin knob; the metadata routes; the lean-CLI vs `[server]` distribution model incl. the uv `default-extras` and 680 MB sdist gotchas; and the two carried-forward gaps (D5, the admin-token tension). **The "Deferred to P6" list is gone.** |
| `security` | **v0007** | The app/edge split — the prod-gated all-`'self'` CSP with its `'unsafe-inline'`/no-nonce rationale, edge HSTS `max-age=300` (and *why* it is short on a shared wildcard), the additive `upgrade-insecure-requests` CSP that intersects rather than overrides, Cloudflare real-IP restore, `/admin` internal-only at the edge, and the `/auth/*` origin rate-limit gap (D5) stated as a deliberate accepted gap. The Admin section is rewritten from "removal is P6" to "removed in P6". |
| `frontend` | **v0005** | The six metadata routes + Satori font caveat, `NEXT_PUBLIC_APP_URL` as build-time-only, the prod-gated CSP and no-`middleware.ts` choice, the standalone production image and its no-`NODE_ENV`-in-build trap; the old Admin UI is now *deleted*, not merely superseded; four new constraints and the removal of "Deploy is P6". |
| `architecture` | **v0008** | New **Production Deployment Topology (P6)** section (co-tenant five-container shape, no host ports, two upstreams, in-app `/mcp`, worker-reuses-api-image as an architectural constraint, migrations external to images, three permanent volumes, image-tag rollback unit); the Admin-UI removal threaded through Status / repo shape / runtime shape / two-track shape / MVP boundaries; the old Open Question resolved and replaced with the two that actually remain. |
| `api` | **v0007** | "P6 changed no endpoint contract" stated explicitly; `/admin` + `/admin/assets/*` documented as deleted; the Admin REST notes updated to "no first-party client" and the production edge 404. |
| `backend` | **v0004** | Fixes a now-false route-registration line (`create_app()` no longer spreads `*admin_ui_routes`) and adds an **Admin Web UI Removal (P6)** section listing exactly what went and what deliberately stayed. *This doc was not on the running list* — see Deviations. |
| `product` | **v0008** | The Admin Web UI retired for real; a new **Distribution and Availability (P6)** section making "not deployed / not published" unambiguous; the stale "PyPI publish is P6" and "removed in P6" future-tense clauses corrected. |
| `experience` | **v0009** | A top-of-guide note that there is no hosted vocky and every base URL is your own deployment; a new "Installing it" section (lean CLI vs `[server]`, publish is P11); Admin REST framed as API-only and edge-404'd. |

`docs/current/*` rebuilt and `validate` passes (it checks current against `docs/index.json`).

## Deviations from `plan.md`

1. **Versioned `backend.md`, which the running list did not name.** The plan said to verify against the
   running list rather than trust its own sentence — doing so surfaced that `backend.md` §App Wiring still
   documented `create_app()` as registering `*admin_ui_routes`, which S1 removed. That is durable truth made
   false by this phase, so it was consolidated too. Eight docs, not seven.
2. **Did not version `decisions.md`.** Considered and deliberately skipped: nothing in it is false. Its
   "removed with the UI itself in P6" clause is now simply satisfied, and D-P8-1 already declares that
   D-P4-3's "until P6" clauses read as P8/P9. Adding P6 ADRs would be new authorship, not consolidation.
3. **Two `doc-new-version` calls failed on `ENAMETOOLONG`** (the generated filename is the slugified summary;
   macOS caps a filename at 255 bytes, and the `Edit` tool's temp-file suffix eats ~28 more). Re-ran with
   shorter summaries. One partial creation (`product` v0008) had written its file and index entry before the
   edit failed; the file was deleted and the index entry removed programmatically before re-creating it
   cleanly. `validate` passes and `docs/index.json` has exactly one v0008 product entry.
4. Otherwise none. No source code was edited (review rule), no status transitioned, nothing committed.
