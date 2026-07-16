# Plan — P7.S1: MCP transport foundation

## Context

Phase **P7** revives the retired agent-capture feature as a **write-only** MCP surface. The DECOMP split it into two slices; this is **P7.S1** (risk `medium`), the **transport foundation**: stand up a FastMCP Streamable-HTTP `/mcp` endpoint mounted in the Starlette host, with its `session_manager` lifespan and transport-security config — **no tool and no auth yet** (both land in S2). Standing the transport up separately de-risks the dependency/lifespan/mount wiring before S2 tackles the novel per-project credential auth + tool. Full context and confirmed research: `works/phases/active/P7/phase.md` and `intent.md`.

**Safe intermediate state:** S1 ships `/mcp` **tool-less** (lists zero tools) and **unauthenticated** (the existing `ProjectCredentialAuthMiddleware` guards `/api/*` only). This leaks nothing and can capture nothing — there is no tool. S2 adds the `capture_feedback` tool **and** its credential auth **together**, so the endpoint is never capture-capable without auth.

## Scope

**In:** `mcp[cli]` dependency; a tool-less `src/vocky/mcp_server.py`; the `/mcp` mount + `session_manager` lifespan in `app.py`; re-added MCP transport-security settings in `config.py`; the route-invariant test update; optional `.env.example` entries.
**Out (→ S2):** the `capture_feedback` tool, per-project `vk_` credential auth for `/mcp`, and the protocol-aware tool-call handler (`make_error_result` / `install_protocol_aware_call_handler`). Do not implement any capture logic in S1.

## Implementation

### 1. Dependency — `pyproject.toml` + lock
Add `"mcp[cli]>=1.27.0,<2.0.0"` to `[project].dependencies` (the official SDK's bundled FastMCP — `from mcp.server.fastmcp import FastMCP`, matching the retired pin). Then `uv lock` and `uv sync`. Python is already `>=3.12,<3.14`.

### 2. `src/vocky/config.py` — re-add MCP transport-security settings only
Port from `git show 9550179^:src/vocky/config.py`, re-adding **only** the allowlist pieces (`parse_csv_setting` already exists in the current file):
- fields: `mcp_allowed_hosts` (alias `VOCKY_MCP_ALLOWED_HOSTS`, default `""`) and `mcp_allowed_origins` (alias `VOCKY_MCP_ALLOWED_ORIGINS`, default `""`).
- properties: `mcp_allowed_host_values` / `mcp_allowed_origin_values` (both `parse_csv_setting(...)`), which `mcp_server.py` consumes.
- **Do NOT** re-add `mcp_auth_token` or `api_auth_token` — the static-token model is retired; per-project `vk_` credentials replace it (auth is S2).

### 3. `src/vocky/mcp_server.py` — NEW, transport only
Port from `git show 9550179^:src/vocky/mcp_server.py` but **tool-less**:
- Keep: imports (`FastMCP`, `TransportSecuritySettings`, `Settings`/`get_settings`), `DEFAULT_MCP_ALLOWED_HOSTS`/`_ORIGINS`, `append_unique`, `make_transport_security_settings`, and the module-level `mcp = FastMCP(app_name, instructions=…, host, port, json_response=True, stateless_http=True, streamable_http_path=<per step 4>, transport_security=make_transport_security_settings(settings))`.
- **Omit (→ S2):** the four `from vocky.tools import …` side-effect imports, `make_error_result`, `install_protocol_aware_call_handler`, and its call. A FastMCP server with zero tools is valid — `tools/list` returns empty; `initialize` handshakes normally.
- **Transport security is re-added by default** (DNS-rebinding protection on, localhost allowlist, extendable via the env vars). This is the resolved decision from the DECOMP open question — safe for both local and public deployments; operators add their public Host/Origin via env.

### 4. `src/vocky/app.py` — mount + lifespan (the crux)
- Imports: add `Mount` to the `starlette.routing` import; add `from vocky.mcp_server import mcp`.
- **Lifespan:** wrap the existing `try/yield/finally` (lines 35-43) in `async with mcp.session_manager.run():` — the exact retired pattern (`9550179^:src/vocky/app.py`). This MUST wrap the whole app lifetime or Streamable-HTTP 500s at request time. Single nesting; no multi-lifespan orchestration.
- **Mount:** add the MCP mount as the **last** route in `create_app()`'s `routes=[…]`. The FastMCP sub-app already serves at its `streamable_http_path`, so external `/mcp` = mount-path + inner-path. Two correct shapes:
  - **Recommended (Option B — clean sub-path):** `Mount("/mcp", app=mcp.streamable_http_app())` with `streamable_http_path="/"`. Route path becomes `/mcp` (not `""`), so the "no root catch-all" invariant (`assert "" not in route_paths`) still holds. Watch trailing-slash behavior on `/mcp` vs `/mcp/`.
  - **Fallback (Option A — retired-exact):** `Mount("/", app=mcp.streamable_http_app())` (kept last) with `streamable_http_path="/mcp"`. Proven to work, but reintroduces a **root** catch-all mount (path `""`) → requires inverting the test assertion (step 6) and relying on route order so core routes match first.
  - **Decide by verification:** implement Option B and confirm `/mcp` actually serves the MCP `initialize` handshake with the installed `mcp` version; if the sub-path mount / trailing-slash / session-manager wiring fights it, fall back to Option A and adjust the test. Never let the mount shadow the core routes.
- **No MCP auth middleware in S1** (S2). Leave the two existing middlewares untouched.

### 5. `.env.example` (+ optional passthrough)
If `.env.example` documents optional `VOCKY_*` settings (it does for the others), add `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS` (empty defaults, one-line comment noting the safe localhost default when unset). `docker-compose.yml` / `Makefile` env passthrough is only needed when publicly exposing `/mcp` behind a custom Host — may defer to when exposure is configured; note it rather than over-scoping S1.

### 6. `tests/test_public_access.py` — update the route-invariant test
`test_core_rest_and_admin_routes_are_registered_without_a_catch_all_mount` (lines 128-147):
- **Option B:** add `assert "/mcp" in route_paths`; **keep** `assert "" not in route_paths`; rewrite the stale comment (MCP is back, mounted at `/mcp`, so the no-root-catch-all invariant still holds).
- **Option A:** replace `assert "" not in route_paths` with an assertion that the only root mount is the MCP sub-app and it is the **last** route (so it can't shadow core routes); update the comment.

## Verification (lightweight, end-to-end where it counts)

- `uv sync` installs `mcp`; `uv run python -c "import vocky.app"` constructs the app (mount + lifespan wiring valid).
- **One terse functional test** that the mount actually serves MCP: stand up `create_app()` **as an async/context-managed app so the lifespan runs** `session_manager.run()`, then drive the `/mcp` `initialize` handshake and assert a valid init result + `tools/list == []`. Known gotchas to handle:
  - Lifespan must run (use the app as a context manager / ASGI-lifespan) or the Streamable-HTTP app 500s.
  - **DNS-rebinding protection rejects unknown Host** — use base_url `http://127.0.0.1` (matches `127.0.0.1:*`) or add the test host to `VOCKY_MCP_ALLOWED_HOSTS`.
  - Prefer the **MCP SDK's** streamable-http client (or the in-process `create_connected_server_and_client_session(mcp)` memory session) over hand-rolled JSON-RPC.
  - Fallback if the HTTP handshake proves too fiddly for S1: verify with the in-process memory session (server initializes, zero tools) + the route-registration test, and defer full HTTP-mount verification to S2's integration test — document the deviation in `result.md`.
- Full suite green: `make test` (or `uv run pytest`), especially `tests/test_public_access.py`.
- `python3 scripts/workflow.py validate` (state integrity).
- Append a one-line **Doc impact** note to `phase.md` for what S1 changed (architecture: `/mcp` FastMCP mount + `session_manager` lifespan restored; operations: `mcp[cli]` dep + MCP allowlist env). **Do NOT** run `doc-new-version` — the REVIEW consolidates.

## Critical files

- `pyproject.toml`, `uv.lock` — add `mcp[cli]`.
- `src/vocky/config.py` — re-add MCP allowlist settings/properties.
- `src/vocky/mcp_server.py` — **new**, tool-less FastMCP server + transport security.
- `src/vocky/app.py` — `Mount` the sub-app + nest `session_manager.run()` in the lifespan.
- `tests/test_public_access.py` — evolve the route-invariant test.
- `.env.example` — optional MCP allowlist vars.
- Reference templates (git): `git show 9550179^:src/vocky/{mcp_server.py,app.py,config.py}`.

## Executor notes

- Risk `medium` → `slice-executor-mid` (opus @ xhigh). Escalate to `high` only if the mount / `session_manager` / streamable-HTTP wiring cannot be made to serve `/mcp` with either documented option.
- Keep `/mcp` **tool-less and no-auth** — do not pull the `capture_feedback` tool, the credential auth, or the protocol-aware call handler forward from S2.
- Never commit, never transition slice/phase status, never `doc-new-version`. Write a free-form `result.md`; append cross-slice notes + the Doc-impact one-liner to `phase.md`.
