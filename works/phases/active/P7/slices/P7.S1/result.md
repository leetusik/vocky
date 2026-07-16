# Result — P7.S1: MCP transport foundation

## Outcome

Stood up a **tool-less, unauthenticated** FastMCP Streamable-HTTP endpoint at `/mcp`,
mounted in the Starlette host with its `session_manager` lifespan and transport-security
config. The endpoint completes the MCP `initialize` handshake and lists **zero** tools.
The `capture_feedback` tool and per-project credential auth remain out of scope (P7.S2).

## Mount decision — Option B (recommended), confirmed by verification

Used **Option B**: `Mount("/mcp", app=mcp.streamable_http_app())` with the server's inner
`streamable_http_path="/"`. External endpoint is `/mcp`; the host route path is `/mcp`
(non-empty), so the "no root catch-all mount" invariant (`assert "" not in route_paths`)
still holds. No fallback to Option A was needed.

- `mcp==1.28.1` resolved (pin `mcp[cli]>=1.27.0,<2.0.0`). Its `FastMCP.streamable_http_app()`
  registers the transport as a **`Route` at `streamable_http_path`** inside its own Starlette
  sub-app (whose own lifespan the host `Mount` does **not** trigger — confirming why the host
  must nest `session_manager.run()` itself).
- **Trailing slash:** a POST to bare `/mcp` 307-redirects to `/mcp/` (inner route is `/`).
  The MCP streamable client follows redirects by default (`create_mcp_http_client` sets
  `follow_redirects=True`), so both `/mcp` and `/mcp/` handshake successfully. Verified both
  paths empirically before finalizing. Real MCP clients configured with the `/mcp` URL will
  transparently follow the one-time redirect — note for S2/ops docs.

## Files changed

- `pyproject.toml` — added `"mcp[cli]>=1.27.0,<2.0.0"` to `[project].dependencies`.
- `uv.lock` — regenerated (`uv lock`); adds `mcp==1.28.1` + transitive deps.
- `src/vocky/config.py` — re-added **only** the allowlist settings: `mcp_allowed_hosts`
  (`VOCKY_MCP_ALLOWED_HOSTS`, default `""`), `mcp_allowed_origins` (`VOCKY_MCP_ALLOWED_ORIGINS`,
  default `""`), and properties `mcp_allowed_host_values` / `mcp_allowed_origin_values`.
  **Did not** re-add `mcp_auth_token` or `api_auth_token` (retired static-token model).
- `src/vocky/mcp_server.py` — **new**, transport only: `FastMCP(...)` with
  `json_response=True, stateless_http=True, streamable_http_path="/"`,
  `transport_security=make_transport_security_settings(settings)`, plus
  `DEFAULT_MCP_ALLOWED_HOSTS/_ORIGINS`, `append_unique`, `make_transport_security_settings`.
  **Omitted** (→ S2): the four `vocky.tools` side-effect imports, `make_error_result`,
  `install_protocol_aware_call_handler`.
- `src/vocky/app.py` — imported `Mount` and `from vocky.mcp_server import mcp`; nested the
  existing `try/yield/finally` inside `async with mcp.session_manager.run():`; appended
  `Mount("/mcp", app=mcp.streamable_http_app())` as the **last** route. No MCP auth middleware
  (S2); existing two middlewares untouched.
- `.env.example` — added commented `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`
  with a note that localhost is always allowed (set only for a public Host/Origin).
- `tests/test_public_access.py` — route-invariant test now asserts `"/mcp" in route_paths`
  **and keeps** `"" not in route_paths`; comment rewritten for the `/mcp` sub-path mount.
- `tests/test_mcp_transport.py` — **new**, one terse functional test driving the `/mcp`
  handshake in-process (see below).

## Verification

| Command | Result |
|---|---|
| `uv lock` / `uv sync` | mcp 1.28.1 installed |
| `uv run python -c "import vocky.app"` | OK (mount + lifespan wiring valid) |
| `uv run pytest tests/test_mcp_transport.py` | 1 passed |
| `uv run pytest tests/test_public_access.py` | passed (route-invariant updated) |
| `uv run pytest` (full suite) | **169 passed** |
| `python3 scripts/workflow.py validate` | Workflow validation passed |

**Functional test design & gotchas handled** (`tests/test_mcp_transport.py`):
- Builds `create_app()`; runs `async with mcp.session_manager.run():` explicitly because
  `httpx.ASGITransport` does not drive the app lifespan (so the mounted Streamable-HTTP app
  would otherwise 500 at request time).
- Uses the MCP SDK's `streamable_http_client` (non-deprecated form, takes a pre-built
  `http_client`) + `ClientSession` rather than hand-rolled JSON-RPC.
- Host `127.0.0.1:8000` (via the `http://127.0.0.1:8000/mcp` URL) satisfies the DNS-rebinding
  allowlist `127.0.0.1:*` (a **portless** Host would be rejected — the matcher requires a port).
- Asserts `init.serverInfo.name == "Vocky"` and `tools.tools == []`.

**Session-manager once-per-instance caveat (checked, safe):** `StreamableHTTPSessionManager.run()`
can only be called once per instance and the module-level `mcp` singleton is shared. No existing
test drives the full app lifespan — `test_admin_ui` uses `TestClient` **without** a `with` block
and `test_credentials_api` uses a bare `httpx.ASGITransport` — so this new functional test is the
sole `session_manager.run()` caller per process. **S2 must keep this invariant:** any additional
HTTP-level `/mcp` test must not run the app lifespan a second time on the same `mcp` singleton
(run `session_manager.run()` exactly once per process, or build a fresh `FastMCP`).

## Deviations from plan

- **Test location:** the functional handshake test lives in a new small `tests/test_mcp_transport.py`
  (one test) rather than being folded into `test_public_access.py`; the route-invariant test was
  updated in place per the plan. Keeps each file focused and terse (contract rule).
- Used the SDK's non-deprecated `streamable_http_client(url, http_client=...)` instead of the
  deprecated `streamablehttp_client(..., httpx_client_factory=...)` to avoid a DeprecationWarning.
- No fallback to Option A was needed; Option B verified working for both `/mcp` and `/mcp/`.
- `.env.example` entries added as **commented** (optional, empty defaults) consistent with the
  file's other optional `VOCKY_*` settings. Did **not** touch `docker-compose.yml` / `Makefile`
  env passthrough — deferred to when `/mcp` is publicly exposed behind a custom Host (per plan).

## Notes for the orchestrator / P7.S2

- `/mcp` is live but tool-less and unauthenticated — safe intermediate state (nothing to capture,
  nothing leaked). S2 adds the `capture_feedback` tool **and** its `vk_` credential auth together.
- Transport-security open question is resolved: DNS-rebinding protection is **on** by default with
  a localhost allowlist, extendable via `VOCKY_MCP_ALLOWED_HOSTS` / `_ORIGINS`.
- For S2's HTTP-level auth test, re-read the once-per-instance session-manager caveat above.
