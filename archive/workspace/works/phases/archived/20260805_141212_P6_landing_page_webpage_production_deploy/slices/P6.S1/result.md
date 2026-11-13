# P6.S1 — Admin Web UI removal · result

Surgically removed the packaged Admin **Web UI** and its supporting harness, leaving the separate
`/admin/api/*` REST surface and its `VOCKY_ADMIN_AUTH_TOKEN` bearer fully intact. Executed the plan
exactly; no scope widening.

## Deleted entirely

- `src/vocky/admin_ui.py` — the five flat Starlette Web-UI `Route`s.
- `src/vocky/admin_assets/` (whole dir: `__init__.py`, `index.html`, `app.css`, `app.js`, `docs.json`,
  plus its `__pycache__`).
- `scripts/check_admin_ui_package.py` — the wheel-packaging check for the UI assets.
- `tests/test_admin_ui.py` — all three tests were UI-specific and imported `admin_ui`.

## Edited

- `src/vocky/app.py` — removed `from vocky.admin_ui import routes as admin_ui_routes` and the
  `*admin_ui_routes,` spread. **Preserved** the `admin_api` import, the `*admin_routes,` spread, and the
  `AdminBearerAuthMiddleware` middleware (verified both middlewares still register).
- `Makefile` — removed the `package-check` target and its wheel-build block, dropped `package-check`
  from `.PHONY`, and changed `verify: package-check smoke test` → `verify: smoke test`. Kept
  `VOCKY_ADMIN_AUTH_TOKEN` in `EXPORTED_ENV_VARS` (still guards `/admin/api`).
- `tests/test_public_access.py` — removed the UI-asset helper assertion
  (`is_admin_api_path("/admin/assets/app.js") is False`) and the four UI route-registration assertions
  (`/admin`, `/admin/assets/app.css|app.js|docs.json`). Kept the `/admin/api/*` assertions, the
  `is_admin_api_path("/admin") is False` matcher assertion, and all `/api/*` + `/mcp` auth coverage.

## Preserved (untouched)

`src/vocky/admin_api.py`, `src/vocky/auth.py` (`AdminBearerAuthMiddleware`, `is_admin_api_path`),
`config.py` admin-token settings, `VOCKY_ADMIN_AUTH_TOKEN` in `docker-compose.yml`/`.env.example`/`Makefile`,
`tests/test_admin_api.py`, and `pyproject.toml` (the wheel `packages = ["src/vocky"]` drops the now-gone
`admin_assets` automatically).

## Coupling check

`grep -rn "admin_ui\|admin_assets" src/ tests/ scripts/ Makefile` confirmed the only importers were
`app.py` (edited) and the deleted `test_admin_ui.py` / `check_admin_ui_package.py`. `test_admin_api.py`
has no dependency on the UI. No unexpected importer; nothing that touches `/admin/api/*`.

## Verification

| Check | Command | Result |
|---|---|---|
| App builds without the UI | `uv run python -c "from vocky.app import create_app; app = create_app(); print('ok')"` | **PASS** — prints `ok` |
| Route surface | in-process assertion over `app.routes` | **PASS** — `admin_ui_routes_remaining=[]`; `/admin/api/*` (9 routes) present; middleware `['ProjectCredentialAuthMiddleware', 'AdminBearerAuthMiddleware']` |
| UI-removal tests | `uv run pytest tests/test_public_access.py tests/test_admin_api.py -q` | Route-surface + auth tests **PASS**; DB-backed tests errored on environment (see below) |
| No stale refs | `grep -rn "admin_ui\|admin_assets" src/ tests/ scripts/ Makefile` | **PASS** — no matches (exit 1) |
| State integrity | `python3 scripts/workflow.py validate` | **PASS** — "Workflow validation passed." |

### pytest detail

`tests/test_public_access.py`: 4 passed, 1 error.
- PASS `test_parse_csv_setting_trims_blanks_and_deduplicates`
- PASS `test_path_auth_helpers_match_only_their_path_families_and_bearer_headers` (edited — trimmed helper)
- PASS `test_admin_bearer_auth_middleware_requires_configured_token`
- PASS `test_core_rest_and_admin_routes_are_registered_without_a_catch_all_mount` (edited — trimmed routes)
- ERROR `test_project_credential_auth_middleware_enforces_mandatory_ingest_auth` — **environment only**

`tests/test_admin_api.py`: all 17 tests ERROR at fixture setup — **environment only**.

All errors are `psycopg.OperationalError: connection ... port 55432 ... Connection refused`: no test
Postgres is running and Docker is unavailable in this sandbox (`docker info` fails), so the DB-backed
fixtures cannot connect. These errors are unrelated to this change (which touches no DB code) and would
occur for any DB-backed test regardless. Every test that actually exercises the Web-UI removal — route
registration, admin-bearer middleware, path-auth helpers — passes. The phase REVIEW slice re-runs full
behavioral validation where a database is available.

## Deviations

- The plan's pytest step could not run fully green in this sandbox because Docker/Postgres is
  unavailable; the DB-backed tests error on `connection refused` (environmental, not a regression). The
  UI-removal-relevant subset is green. No code deviation from the plan.

## Doc impact

Appended to `phase.md` "Doc impact": the Web-UI removal makes stale the `/admin` Web-UI mentions in
`README.md` (token-into-UI instructions), `docs/current/architecture.md` (route-groups "/admin packaged
Admin Web UI" + the P4-open-question resolution note), `docs/current/api.md`, and
`docs/current/operations.md` (its "Deferred to P6" removal line) — for the REVIEW slice to consolidate.
