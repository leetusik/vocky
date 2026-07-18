# P6.S1 — Admin Web UI removal · plan

> Slice `P6.S1` (implementation, risk **medium**). First middle slice of P6; shrinks the route surface
> before the nginx map (S6). Read `phase.md` (Findings + Constraints) for accumulated context.

## Context

P6 physically removes the **packaged Admin Web UI** — a documented P6 cleanup (operations.md "Deferred
to P6"). The vocky app has **two decoupled admin surfaces** sharing only the `/admin` URL-prefix string:

- **Admin Web UI** (REMOVE): `src/vocky/admin_ui.py` exposes five flat Starlette `Route`s (`/admin`,
  `/admin/`, `/admin/assets/{app.css,app.js,docs.json}`) serving packaged text from the
  `vocky.admin_assets` subpackage. No `Mount`, no `StaticFiles` — just routes spread into the host app.
- **Admin REST API** (PRESERVE): `src/vocky/admin_api.py` (`/admin/api/*`), guarded by
  `AdminBearerAuthMiddleware` + `VOCKY_ADMIN_AUTH_TOKEN` (`auth.py` `is_admin_api_path` matches
  `/admin/api` only). It does **not** import `admin_ui`; `admin_ui` does not import it. Deleting the Web
  UI leaves the REST surface and its token **fully intact.**

Operator-confirmed scope: delete `admin_ui.py`, `admin_assets/*`, the `/admin` mount — **the
`/admin/api/*` REST surface and `VOCKY_ADMIN_AUTH_TOKEN` stay** (corrects the DECOMP one-liner that said
"`/admin` + `/admin/api` mounts"; only the Web UI goes).

## Delete entirely

- `src/vocky/admin_ui.py`
- `src/vocky/admin_assets/` (whole dir: `__init__.py`, `index.html`, `app.css`, `app.js`, `docs.json`)
- `scripts/check_admin_ui_package.py`
- `tests/test_admin_ui.py` (all three tests are UI-specific; it imports `admin_ui`)

## Edit

- **`src/vocky/app.py`** — remove the `admin_ui` import (`from vocky.admin_ui import routes as admin_ui_routes`, ~line 15) and the `*admin_ui_routes,` spread (~line 66). **Preserve** the `admin_api` import (~line 14), the `*admin_routes,` spread (~line 65), and the `AdminBearerAuthMiddleware` middleware (~line 77).
- **`Makefile`** — remove the `package-check` target (the block whose last step runs `scripts/check_admin_ui_package.py`), drop `package-check` from `.PHONY`, and change `verify: package-check smoke test` → `verify: smoke test`. **Keep** `VOCKY_ADMIN_AUTH_TOKEN` in `EXPORTED_ENV_VARS` (it still guards `/admin/api`).
- **`tests/test_public_access.py`** — remove the UI-asset assertion (`is_admin_api_path("/admin/assets/app.js") is False`, ~line 36) and the four UI route-registration assertions for `/admin`, `/admin/assets/app.css|app.js|docs.json` (~lines 157–160). **Keep** the `/admin/api/*` assertions (~lines 155–156) and everything covering `/api/*` + `/mcp` auth.

## Preserve (do NOT touch)

`src/vocky/admin_api.py`; `src/vocky/auth.py` (`AdminBearerAuthMiddleware`, `is_admin_api_path`);
`config.py` `admin_auth_token`/`admin_auth_token_value`; the three admin lines in `app.py` above;
`VOCKY_ADMIN_AUTH_TOKEN` in `docker-compose.yml`, `.env.example`, `Makefile EXPORTED_ENV_VARS`;
`tests/test_admin_api.py`.

## Docs

Do **not** rewrite prose docs here (durable docs are versioned at REVIEW). Append a one-line **Doc
impact** note to `phase.md`: the Admin Web UI removal makes stale the `/admin` Web-UI mentions in
`README.md` (token-into-UI instructions), `docs/current/architecture.md` (route-groups: "/admin
packaged Admin Web UI"), `docs/current/api.md`, and `docs/current/operations.md` (its own "Deferred to
P6" removal line) — the REVIEW slice consolidates these. Leave `pyproject.toml` unchanged (the wheel
`packages = ["src/vocky"]` drops `admin_assets` automatically once the dir is gone).

## Verification

- App builds with the UI gone: `uv run python -c "from vocky.app import create_app; app = create_app(); print('ok')"`.
- Route surface: assert no `/admin` or `/admin/assets/*` routes remain, and `/admin/api/*` routes + the
  admin bearer middleware are still registered (the trimmed `tests/test_public_access.py` covers this).
- `uv run pytest tests/test_public_access.py tests/test_admin_api.py -q` green (REST auth + registration).
- `grep -rn "admin_ui\|admin_assets" src/ tests/ scripts/ Makefile` returns nothing.
- `python3 scripts/workflow.py validate` passes (state integrity).

## Executor notes

Keep it surgical — Web UI only. If you find any importer of `admin_ui`/`admin_assets` beyond `app.py`
and the deleted test, or any coupling that would break `/admin/api/*`, **escalate** with findings rather
than widening scope. Write `result.md` (free-form) and append the Doc-impact note to `phase.md`. Do not
commit; do not transition status.
