# P1.S2 result — Retire MCP/agent-capture from the system

**Status: done.** MCP / AI-agent-decided capture is fully removed. The app imports cleanly
with `mcp` uninstalled, no `mcp` reference remains under `src/`, and the **full DB-backed suite is
green** (Postgres + Redis were reachable in this sandbox, so the suite was run here — not deferred).

## What was done

### Whole-file deletes
- `src/vocky/mcp_server.py`
- `src/vocky/tools/{capture_feedback,list_feedback,list_liked_conversations,summarize_feedback}.py`
- `tests/test_mcp_integration.py`
- Kept `src/vocky/tools/__init__.py` (docstring updated from "MCP tool modules." to
  "Shared feedback query helpers used by the REST surfaces.") and
  `src/vocky/tools/query_feedback_common.py`.

### Surgical source edits (MCP out, REST intact)
- **`app.py`** (load-bearing): dropped the `mcp` import, `MCPBearerAuthMiddleware`, the root
  `Mount("/", app=mcp.streamable_http_app())` catch-all, and unused `Mount` import; unwrapped
  `lifespan()` to redis/engine disposal only. Final routes: `/healthz`, admin API, admin UI, public
  API, attachments — no `""` (root) mount. Middleware: API + Admin bearer only.
- **`config.py`**: removed the 3 `mcp_*` fields and their 3 `mcp_*_value` properties.
- **`auth.py`**: removed `is_mcp_path` and `MCPBearerAuthMiddleware`; kept the admin/api helpers and
  middlewares.
- **`capture.py`**: removed `McpCaptureFeedbackInput`, `normalize_mcp_payload`, and the
  `CaptureFeedbackInput = McpCaptureFeedbackInput` alias. Also removed the generic
  `normalize_payload` back-compat shim — grep confirmed it was unused (its only would-be callers
  were the now-deleted tests/tools; the tool modules had their own separate `normalize_payload`).
  Kept `Base/RestCaptureFeedbackInput`, `normalize_rest_payload`, `_normalize_capture_payload`,
  `serialize_capture_receipt`, and all validators.
- **`tools/query_feedback_common.py`**: removed `from mcp.types import CallToolResult, TextContent`
  and `error_result()`. Confirmed no retained file (`api.py`, `admin_api.py`, `attachments_api.py`)
  calls `error_result`.

### Dependency / env / packaging
- `pyproject.toml`: removed `mcp[cli]>=1.27.0,<2.0.0`; refreshed the stale `description`
  ("Feedback MCP for agents." → "Human-triggered feedback capture REST API."). Kept `vocky-smoke`.
- `uv lock && uv sync`: `uv.lock` dropped `mcp` **and 17 MCP-only transitive deps** (annotated-doc,
  attrs, cffi, cryptography, httpx-sse, jsonschema(+specifications), markdown-it-py, mdurl,
  pycparser, referencing, rich, rpds-py, shellingham, sse-starlette, typer, plus pywin32). The env
  now has `mcp` uninstalled.
- Removed the `VOCKY_MCP_*` block from `.env.example`, `docker-compose.yml`, and the `Makefile`
  `EXPORTED_ENV_VARS` (all three: `VOCKY_MCP_ALLOWED_HOSTS`, `VOCKY_MCP_ALLOWED_ORIGINS`,
  `VOCKY_MCP_AUTH_TOKEN`).

### Runtime admin asset — `src/vocky/admin_assets/docs.json`
Scrubbed all MCP content, kept valid JSON: removed the MCP nav row, the entire `mcp-tools` section,
the `VOCKY_MCP_AUTH_TOKEN` auth-token row, the public-custom-domain MCP client row + `MCP allowed
Host`/`Origin` definitions + the `VOCKY_MCP_*` env-code lines, and reworded the remaining bare-"MCP"
prose (rest-capture summary, admin-rest paragraph + read-filters item, local-self-hosting & external
"MCP smoke flow" → "REST smoke flow", "three tracks" → "two tracks", the expose-with-tokens callout).
New `topic_ids`: `[operator-overview, rest-capture, admin-rest, auth-tokens, local-self-hosting,
public-custom-domain]`. See **Deviations** — this went beyond the plan's literal 4-item list because
the verification greps require `src/` fully MCP-free and `docs.json` is entirely S2's scope.
`tests/test_admin_ui.py` was updated in lockstep (topic list, trimmed `required_text`, deleted the
now-moot `test_admin_ui_routes_are_registered_before_mcp_mount`).

### Smoke rewrite — `src/vocky/smoke.py` (`vocky-smoke`)
Replaced the MCP flow (`run_mcp_smoke`, `make_mcp_client_headers`, `mcp.client.*` imports, the
MCP-only timestamp helpers) with a REST capture→persist→read loop:
1. `make_smoke_health_request(f"{base_url}/healthz")` (unchanged) → assert `status == "ok"`.
2. `make_smoke_request_headers()` — `User-Agent` + optional `Authorization: Bearer
   <VOCKY_API_AUTH_TOKEN>` (omitted when the token is empty).
3. `POST {base_url}/api/feedback` (httpx) with unique `message`, `source={"product":"vocky-smoke",
   "integration":"make-smoke"}`, unique `user_id`/`session_id`, `target_*`, `tags:["smoke"]` →
   expect **202** with `status == "accepted"` and a `request_id`.
4. Poll `GET {base_url}/api/feedback?user_id=<smoke>&source_product=vocky-smoke&session_id=<...>`
   (scoped read) up to 20× @0.5s until the matching row appears; assert `user_id`/`target_*`
   round-tripped. **No summarize step** (no REST summarize endpoint).
5. Prints health/capture/list confirmations.
Kept `make_http_user_agent` and `make_smoke_health_request` as the plan required.

### Test cleanup
- `test_public_access.py`: dropped MCP transport-security, `/mcp` routing, `MCPBearerAuthMiddleware`,
  `make_transport_security_settings`, and MCP-smoke-header tests/imports; kept the general
  path-helper/health/bearer coverage (re-homed the path-helper assertions), and replaced the
  MCP-mount route-ordering check with a `create_app()` route-registration test that also asserts no
  `""` root catch-all mount remains.
- `test_admin_ui.py`: as above (docs.json lockstep + deleted route-ordering test).
- `test_capture_validation.py`: dropped `McpCaptureFeedbackInput`/`normalize_mcp_payload`; repointed
  `make_input` to `RestCaptureFeedbackInput` and all calls to `normalize_rest_payload`; removed the
  moot `test_mcp_capture_is_attachment_free`; neutralized a `source_metadata={"channel":"mcp"}` data
  literal to `"web"`.
- `test_query_validation.py`: it imported input models from the 3 deleted tool modules; rewrote it to
  exercise the retained `query_feedback_common` helpers directly (normalize_tag, validate_time_window,
  normalize_limit, normalize_feedback_value, normalize_target_type_filter,
  normalize_trigger_type_filter, decode/encode_cursor, normalize_optional_text) — same validation
  coverage, no deleted-module imports.

## Verification (all commands run in this sandbox)

| Command | Result |
| --- | --- |
| `grep -rnE "import mcp\|from mcp\|mcp\.\|streamable_http\|FastMCP" src/ tests/` | **EMPTY** (pass) |
| `grep -rinE "VOCKY_MCP\|/mcp\b\|mcp-tools" src/ .env.example docker-compose.yml Makefile` | **EMPTY** (pass) |
| `grep -rin "mcp" src/` | **NONE** under `src/` (pass) |
| `uv lock` | dropped `mcp` + 17 MCP-only transitive deps |
| `uv sync` + `uv run python -c "import vocky.app"` | imports cleanly; `mcp` uninstalled confirmed; routes have no `""` mount |
| `uv run python -c "json.loads(docs.json)"` | valid JSON, version 1 |
| `uv run pytest --collect-only -q` | 132 tests collected, **no import errors** |
| `uv run pytest tests/test_capture_validation.py tests/test_query_validation.py` | 33 passed |
| `uv run pytest tests/test_public_access.py tests/test_admin_ui.py` | 9 passed |
| **`make test` (full DB-backed suite)** | **132 passed** (Postgres 55432 + Redis 56379 reachable) |
| `uv build` | wheel + sdist built successfully (packaging valid without `mcp`); `dist/` is gitignored |

## Deviations from plan.md

1. **docs.json scope (expansion, not contradiction).** The plan's section 4 enumerated 4 specific
   removals, but leaving the rest would keep `VOCKY_MCP_ALLOWED_HOSTS/ORIGINS` and a `FastMCP`
   reference in `docs.json`, which the plan's own verification greps flag and which the section-6
   test cleanup (removing `VOCKY_MCP_*` assertions) presupposes are gone. Since `docs.json` is
   entirely S2's scope (S3 covers only README + `docs/*.md`), I scrubbed **all** MCP content from it
   and updated `test_admin_ui.py` in lockstep. Net effect matches the plan's stated exit criterion
   ("no `mcp` reference anywhere under `src/`").
2. **Removed `capture.normalize_payload`** (the plan said keep-if-imported / else-remove; grep
   confirmed unused → removed).
3. **Full DB-backed suite was RUN here, not deferred** — Postgres/Redis/Docker were available, so
   `make test` was executed and is green. No deferral to P1.REVIEW/operator is needed for the suite.

## Doc impact
No change to the running Doc-impact list — the four durable-doc areas (`api`, `architecture`,
`product`, `experience`) still hold for consolidation at **P1.REVIEW**. `docs.json` is a runtime
admin asset, not a durable `docs/current/*` doc, so it was edited directly in this slice.
