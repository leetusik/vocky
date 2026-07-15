# P1.S2 — Retire MCP/agent-capture from the system

> Native plan for slice **P1.S2** (`implementation`, risk **high** → `slice-executor-high`).
> This is the core, load-bearing change. Exercise judgment within the boundaries below; the goal
> is a **coherent removal that leaves the app importable and the test suite green with no `mcp`
> reference anywhere under `src/`**. You never commit and never transition slice/phase status;
> write `result.md`, append cross-slice notes + confirm the Doc-impact list in `phase.md`, and
> return your verdict. Do **not** run `doc-new-version` (durable docs are versioned at P1.REVIEW).

## Context

P1 retires the MCP / AI-agent-decided feedback capture feature entirely, refocusing vocky on
**human-triggered REST feedback** (see `intent.md` and `phase.md` → Findings for the full removal
map). MCP is mounted into the same Starlette app as REST and shares the capture/queue/worker/
persistence layers, so this is whole-file deletes **plus** surgical edits to shared files. The
**REST surface must stay fully intact**: `api.py` (`POST`/`GET /api/feedback`, attachment
download), `admin_api.py`, `attachments_api.py`, `admin_ui.py`, and all of `capture_queue.py`,
`worker.py`, `feedback/`, `persistence/`, `storage/`, `channel.py`, `trigger.py`.

Operator decision (confirmed): `vocky-smoke` is **rewritten to a REST smoke**, not deleted.

## 1. Delete whole files
- `src/vocky/mcp_server.py`
- `src/vocky/tools/capture_feedback.py`, `list_feedback.py`, `list_liked_conversations.py`,
  `summarize_feedback.py`  *(keep `src/vocky/tools/__init__.py` and `query_feedback_common.py`)*
- `tests/test_mcp_integration.py`

## 2. Surgical source edits (remove MCP, keep the rest)

**`src/vocky/app.py`** — the load-bearing edit. Currently:
- line 17 imports `MCPBearerAuthMiddleware` alongside API/Admin middlewares → drop only
  `MCPBearerAuthMiddleware`.
- line 20 `from vocky.mcp_server import mcp` → delete.
- `lifespan()` (30-39) wraps the body in `async with mcp.session_manager.run():` → rewrite to keep
  only the disposal, e.g.:
  ```python
  @contextlib.asynccontextmanager
  async def lifespan(_: Starlette):
      try:
          yield
      finally:
          await dispose_redis_client()
          await dispose_engine()
  ```
- `Mount("/", app=mcp.streamable_http_app())` (line 54) → delete (this was the `/mcp` catch-all;
  REST/admin/health routes remain).
- `Middleware(MCPBearerAuthMiddleware, token=settings.mcp_auth_token_value)` (line 59) → delete.

**`src/vocky/config.py`** — remove the three MCP fields `mcp_allowed_hosts`,
`mcp_allowed_origins`, `mcp_auth_token` (37-39) and their three properties
`mcp_allowed_host_values`, `mcp_allowed_origin_values`, `mcp_auth_token_value` (52-68). Keep
`admin_auth_token*`, `api_auth_token*`, and all `attachments_*`.

**`src/vocky/auth.py`** — remove `is_mcp_path` and `MCPBearerAuthMiddleware`; keep
`is_admin_api_path`, `is_api_path`, `is_authorized_bearer`, `AdminBearerAuthMiddleware`,
`APIBearerAuthMiddleware`.

**`src/vocky/capture.py`** — remove the MCP-only symbols: `McpCaptureFeedbackInput` (58-59),
`normalize_mcp_payload` (295-298), and the `CaptureFeedbackInput = McpCaptureFeedbackInput` alias
(313-314). Keep `BaseCaptureFeedbackInput`, `RestCaptureFeedbackInput`, `normalize_rest_payload`,
`_normalize_capture_payload`, `serialize_capture_receipt`, and all validators. `normalize_payload`
(307-310) is a generic back-compat shim — keep it if anything still imports it after the test
cleanup, otherwise remove it (grep first).

**`src/vocky/tools/query_feedback_common.py`** — **keep the file** (REST depends on it). Remove
only its MCP coupling: the `from mcp.types import CallToolResult, TextContent` import (~line 11)
and the `error_result()` function (~245-251), which are used only by the deleted MCP tools. Verify
nothing else in the file (or in `api.py`/`admin_api.py`) still calls `error_result`.

## 3. Dependency, env, packaging
- `pyproject.toml`: remove the `"mcp[cli]>=1.27.0,<2.0.0"` dependency (line 17). Also update the
  now-inaccurate `description` on line 8 (`"Feedback MCP for agents."`) to a REST/human-feedback
  phrasing, e.g. `"Human-triggered feedback capture REST API."`. Keep the `vocky-smoke` script
  entry (line 37). After editing, run `uv lock && uv sync` so `uv.lock` drops `mcp` and its
  MCP-only transitive deps (uv.lock will change — it's committed with this slice).
- Remove the `VOCKY_MCP_*` block from `.env.example`, `docker-compose.yml`, and the `Makefile`
  `EXPORTED_ENV_VARS` (three names: `VOCKY_MCP_ALLOWED_HOSTS`, `VOCKY_MCP_ALLOWED_ORIGINS`,
  `VOCKY_MCP_AUTH_TOKEN`). Grep each file for `VOCKY_MCP` / `mcp` to confirm none remain.

## 4. Runtime admin asset — `src/vocky/admin_assets/docs.json`
Remove the MCP nav row (`["MCP", "/mcp", ...]`), the whole `"id": "mcp-tools"` section, the
`VOCKY_MCP_AUTH_TOKEN` env row, and the MCP public-access row. Keep the JSON valid. (This asset is
served at runtime and asserted by `test_admin_ui.py`, so it changes in lockstep with that test.)

## 5. Rewrite `src/vocky/smoke.py` (`vocky-smoke`) to a REST smoke
Replace the MCP flow (`run_mcp_smoke`, `make_mcp_client_headers`, `mcp.client.*` imports, the
timestamp helpers used only by it) with a minimal REST capture→persist→read loop over the public
API. **Keep** `make_http_user_agent` and `make_smoke_health_request` (also imported by
`tests/test_public_access.py`). New flow in `main()`:
1. Health check via `make_smoke_health_request(f"{base_url}/healthz")` (unchanged), assert `ok`.
2. Build headers with `User-Agent` + optional `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` (the
   REST surface is guarded by `APIBearerAuthMiddleware`; omit the header when the token is empty).
3. `POST {base_url}/api/feedback` (httpx) with a unique `message`, `source={"product":
   "vocky-smoke", "integration": "make-smoke"}`, a unique `user_id` and `session_id`, plus
   `target_type/target_id/target_role/target_text` and `tags: ["smoke"]`. Expect **HTTP 202** and
   a body with `status == "accepted"` and a `request_id` (shape = `CaptureFeedbackResponse`).
4. Poll `GET {base_url}/api/feedback?user_id=<smoke user>&source_product=vocky-smoke&session_id=<...>`
   (the read is **scoped**, so `user_id` + `source_product` are required) up to ~20× with 0.5s
   sleeps until `records` contains the row whose `message` matches; assert its `target_*` and
   `user_id` round-tripped (the worker must be running to persist — `make smoke` brings the stack
   up). There is no REST summarize endpoint, so **drop the `summarize_feedback` step**.
5. Print concise health/capture/list confirmations.

## 6. Test cleanup → suite green (no `mcp` references)
- `tests/test_public_access.py` — remove MCP transport-security / `/mcp` routing /
  `MCPBearerAuthMiddleware` / `make_transport_security_settings` / MCP-smoke-header assertions;
  keep the general routing/health assertions (re-home any that were only structurally tied to the
  MCP mount).
- `tests/test_admin_ui.py` — remove the `mcp-tools` nav, `/mcp`, and `VOCKY_MCP_*` assertions and
  delete the route-ordering test `test_admin_ui_routes_are_registered_before_mcp_mount` (moot once
  the root mount is gone).
- `tests/test_capture_validation.py` — drop the `normalize_mcp_payload` / `McpCaptureFeedbackInput`
  assertions; keep the `normalize_rest_payload` / base-validation coverage.
- `tests/test_query_validation.py` — it imports input models from the deleted tool modules
  (`tools.list_feedback`, `tools.summarize_feedback`, `tools.list_liked_conversations`). Keep only
  the coverage that exercises the retained `tools.query_feedback_common` helpers (trim the file to
  those imports); if nothing meaningful remains, delete the file. Do not leave imports of deleted
  modules.
- Leave the MCP-free REST tests untouched (`test_capture_api.py`, `test_user_feedback_api.py`,
  `test_admin_api.py`, `test_attachments_api.py`, `test_feedback_attachments.py`,
  `test_feedback_comments.py`, `test_capture_queue.py`, `test_worker.py`, `test_persistence.py`,
  `test_storage.py`).

## Out of scope (later slices)
README and the ad-hoc `docs/*.md` MCP prose → **P1.S3**. Durable docs `docs/current/{api,
architecture,product,experience}.md` → versioned at **P1.REVIEW** from the Doc-impact list.

## Verification
Run in this order; report results in `result.md`:
- `grep -rE "import mcp|from mcp|mcp\.|streamable_http|FastMCP" src/ tests/` → **empty**.
- `grep -riE "VOCKY_MCP|/mcp\b|mcp-tools" src/ .env.example docker-compose.yml Makefile` → only
  incidental non-MCP matches, if any.
- `uv sync` then `uv run python -c "import vocky.app"` → imports cleanly with `mcp` uninstalled.
- `uv run python -c "import json,pathlib; json.loads(pathlib.Path('src/vocky/admin_assets/docs.json').read_text())"`
  → docs.json still valid JSON.
- `uv run pytest --collect-only -q` → collects with **no import errors** (proves every test file is
  clean of deleted symbols).
- DB-free unit tests: `uv run pytest tests/test_capture_validation.py tests/test_query_validation.py`
  → green.
- Full suite: if a test database + Redis are reachable (or Docker is available for `make bootstrap`),
  run `make test` (or `uv run pytest`) and report green. **If the DB-backed suite cannot run in
  this environment, say so explicitly in `result.md`** and flag it for P1.REVIEW / the operator to
  run against the compose stack — do not claim green without running it.
- Optional: `uv build` succeeds (packaging still valid without the mcp dep).

## phase.md notes (append when done)
Under Findings & Notes: what deleted cleanly vs needed surgery, the final `lifespan`/routing shape,
the REST smoke's endpoints/scope, and whether the full DB-backed suite was run here or deferred.
Confirm the **Doc impact** list (`api`, `architecture`, `product`, `experience`) still holds for
P1.REVIEW.
