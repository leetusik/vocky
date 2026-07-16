# Phase P7: Agent-Capture Revival (MCP write-only)

_Intent: see [intent.md](intent.md)._

## Objective

Reintroduce the retired agent-decided feedback capture as a write-only MCP surface: agents linked to a project's Vocky MCP endpoint save user feedback at their own judgement via a single capture_feedback tool, feeding the same feedback queue/store as REST. Scoped by P2 per-project credentials and aligned with P3's v2 capture shape; the three retired read tools stay retired.

## Context

Revives the agent-decided feedback capture retired in P1, **write path only**, re-aligned to the P2/P3 surface (per-project `vk_` credentials + P3 project-scoped v2 capture), not a verbatim restore of the retired code. The three retired read tools stay retired; reads remain REST-only. Retired code lives in commit `9550179` (its parent `9550179^` is the last tree that still had the MCP files) — a recoverable template, not a target to restore as-is.

## Decomposition

Split by **layer**: transport foundation vs. the write path (auth binding + tool + pipeline). The credential→project→tool binding lives with the tool (S2) because the tool is the only thing that needs `project_id`, and the natural end-to-end test exercises auth + tool + pipeline together. DECOMP (this slice) verified the plan's research against the current tree and the retired commit — all findings hold — and kept the recommended **2-slice** shape (no split of S2). REVIEW stays last, never pre-planned here.

| Slice | Name | Kind | Risk → tier | Order | Depends on |
|---|---|---|---|---|---|
| `P7.S1` | MCP transport foundation: `mcp[cli]` dep, FastMCP server module, `/mcp` mount, `session_manager` lifespan | implementation | `medium` → mid | 1 | — |
| `P7.S2` | `capture_feedback` write tool + per-project `vk_` credential auth + capture-pipeline integration + integration test | implementation | `high` → high | 2 | `P7.S1` |

**Rationale.**
- **S1 (medium → mid):** structural but templated from recoverable retired code (`9550179^:src/vocky/mcp_server.py`, `9550179^:src/vocky/app.py`). Touches `pyproject.toml`+`uv.lock` (re-add `mcp[cli]`), a new `mcp_server.py`, `app.py` routes+lifespan (add the `/mcp` Mount + nest `session_manager.run()`), and the "no root/catch-all mount" test. Stands the transport up with **no tool/auth yet**. Not fully mechanical (lifespan nesting + test update require judgement) → not `low`.
- **S2 (high → high):** the crux. Resolves both design questions the intent deferred (auth binding + input model), wires the tool through the transport-neutral capture seam, stamps `project_id` from the credential, adds **one small** integration test. Novel per-project MCP auth wiring at the ASGI/sub-app boundary is genuinely high-risk → top tier.
- **Why not split S2 into auth + tool+pipeline:** the auth binding is only meaningful once a tool reads the credential back off the scope, and the end-to-end capture test needs auth + tool + pipeline present together. Splitting would fragment that single coherent test. If S2's planning finds the `/mcp` credential-auth binding heavier than expected, the S2 orchestrator may still split off an `S3` at order 3 — but the default is the 2-slice shape.

## Findings & Notes

_Seeded by `P7.DECOMP` (research pre-gathered in the DECOMP plan, spot-checked read-only against the current tree + `9550179^`; all findings confirmed). Each later slice appends when it finishes._

### The capture seam (transport-neutral, already project-aware) — confirmed

A non-REST caller needs exactly: build a `CreateFeedbackEvent` → set `project_id` → `await get_capture_queue().enqueue_feedback(event)`. Everything downstream (queue serialize/deserialize, worker, service, repository, `feedback_events`) already round-trips `project_id` — **no engine or schema change**.
- `CreateFeedbackEvent` — `src/vocky/feedback/types.py:11-38`; `project_id: UUID | None = None` at **line 17** (confirmed). Also already carries `attachment_ids` (line 38).
- `get_capture_queue().enqueue_feedback(payload)` — `src/vocky/capture_queue.py:225,292-295`.
- REST reference path to mirror — `src/vocky/api.py:90-111`: parse → `RestCaptureFeedbackInput.model_validate` → `normalize_rest_payload` → **`normalized.payload.project_id = get_request_credential(request).project_id`** (`api.py:99`, injected *after* normalization) → `enqueue_feedback` → `202` via `serialize_capture_receipt`. Confirmed verbatim.

### Design question 1 — MCP credential→project auth binding (the crux; resolve in S2)

- Verify path confirmed: `get_accounts_service().get_active_credential_by_token_hash(sha256_hex(token))` — `auth.py:119-125` → `accounts/service.py:228` → repository filters `revoked_at IS NULL`. Returns `ProjectCredentialRecord` (`accounts/types.py:85-95`) which carries **`project_id` (line 90) but NOT `tenant_id`** — confirmed. Capture only needs `project_id`, so no `get_project` / tenant lookup is required.
- `ProjectCredentialAuthMiddleware` (`auth.py:95-148`) guards `/api/*` **only** (`is_api_path`, `auth.py:30-33`), stashes the record at `PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"` (`auth.py:21,135`; read via `get_request_credential`, `auth.py:151-159`) and best-effort stamps `last_used_at` (`auth.py:139-146`, swallows `AccountsPersistenceError`). `/mcp` is **not** covered today.
- **Recommended direction (final call in S2):** a host-level middleware guarding `/mcp` that reuses `get_active_credential_by_token_hash` + `sha256_hex` and stashes into the **same** scope key. FastMCP's `streamable_http_app()` mounts as a sub-app, so host-level middleware runs before the mount dispatches and the tool handler can read the credential back off the ASGI scope. Mirror the `last_used_at` best-effort stamp. **To verify in S2:** exactly how a FastMCP tool reaches the scope (expected `ctx.request_context.request.scope[...]`). Alternative to weigh: FastMCP's native bearer-auth provider. Retired precedent to consult: `is_mcp_path` + `MCPBearerAuthMiddleware` in `git show 9550179^:src/vocky/auth.py` — confirmed present but it used a **static** `VOCKY_MCP_AUTH_TOKEN`; replace with the `vk_` per-project path. The static token is **not** revived.

### Design question 2 — input model (resolve in S2)

- Confirmed hierarchy in `src/vocky/capture.py`: `BaseCaptureFeedbackInput` (32-55, shared, **no** `project_id`/`attachment_ids`) → `RestCaptureFeedbackInput` (58-64, adds `attachment_ids`). `_normalize_capture_payload` (252) is transport-neutral, typed on the base, reads `getattr(raw, "attachment_ids", None)`. `normalize_rest_payload` (290) is a thin wrapper.
- **Recommended:** revive a thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` + a `normalize_mcp_payload` wrapper next to `normalize_rest_payload` — keeps `attachment_ids` out of the MCP tool schema (agents have no upload flow); no engine change. P1 stripped the old `McpCaptureFeedbackInput` / `normalize_mcp_payload` (confirmed absent from current `capture.py`; the retired `9550179^:src/vocky/tools/capture_feedback.py` still imports them, so it is a recoverable template).

### P7.S1 — transport foundation shipped (mount decision + caveats)

- **Mount = Option B, verified.** `Mount("/mcp", app=mcp.streamable_http_app())` + server
  `streamable_http_path="/"`. Host route path is `/mcp` (non-empty) → the "no root catch-all"
  invariant still holds (`assert "" not in route_paths` kept; added `assert "/mcp" in route_paths`).
  No fallback to Option A needed.
- **mcp 1.28.1** installed via `mcp[cli]>=1.27.0,<2.0.0`. FastMCP API matches the retired template
  (`streamable_http_app()`, `session_manager`, `TransportSecuritySettings{enable_dns_rebinding_protection,allowed_hosts,allowed_origins}`).
- **Lifespan nesting is mandatory.** `streamable_http_app()` builds a sub-Starlette with its **own**
  lifespan that a host `Mount` does **not** trigger; the host must nest `async with mcp.session_manager.run():`
  around its whole lifetime or `/mcp` 500s at request time. Done in `app.py`'s `lifespan`.
- **Trailing slash:** bare `/mcp` 307-redirects to `/mcp/` (inner route `/`); MCP clients follow
  redirects by default, so both paths handshake. Real clients can use the `/mcp` URL as-is.
- **DNS-rebinding Host gotcha:** the allowlist matcher requires a **port** — `127.0.0.1:*` matches
  `127.0.0.1:8000` but **not** portless `127.0.0.1`. Tests/clients must send a Host with a port
  (or add the public host to `VOCKY_MCP_ALLOWED_HOSTS`).
- **Session-manager is once-per-instance (S2 must respect this).** `StreamableHTTPSessionManager.run()`
  raises if called twice on the same instance, and the module-level `mcp` singleton is shared across
  tests. No existing test drives the full app lifespan (`test_admin_ui`: `TestClient` without `with`;
  `test_credentials_api`: bare `ASGITransport`), so the new `tests/test_mcp_transport.py` is the sole
  runner. Any S2 HTTP-level `/mcp` test must run `session_manager.run()` exactly once per process
  (or construct a fresh `FastMCP`).
- **Config:** re-added only `mcp_allowed_hosts` / `mcp_allowed_origins` (+ their `_values` properties).
  `mcp_auth_token` / `api_auth_token` stay **retired** — per-project `vk_` auth (S2) replaces them.
- Full suite green: **169 passed**; `validate` passes.

### Transport wiring & gotchas (mostly S1)

- `create_app()` — `src/vocky/app.py:46-70`: flat `routes=[…]`, **no `Mount` today** (confirmed); `lifespan` at `app.py:35-43` disposes Redis + engine on shutdown. Retired precedent (`9550179^:src/vocky/app.py`): `Mount("/mcp", app=mcp.streamable_http_app())` in routes + nest `async with mcp.session_manager.run():` around the existing `try/yield/finally`. Single nesting — no multi-lifespan orchestration; `session_manager.run()` **must** wrap the app lifetime or streamable-HTTP 500s at request time.
- `tests/test_public_access.py:128-147` (`test_core_rest_and_admin_routes_are_registered_without_a_catch_all_mount`) **asserts `"" not in route_paths`** — the retired MCP was mounted at `/` normalized to empty. Adding `/mcp` uses a non-empty path so it need not break the assertion, but the test's intent/comment must be revisited so it still guards against an accidental root catch-all. Confirmed at those lines.
- Dep: `mcp[cli]` **absent** from `pyproject.toml` (confirmed — no `mcp` entry) and `uv.lock`. Re-add `mcp[cli]>=1.27.0,<2.0.0` (official SDK's bundled FastMCP: `from mcp.server.fastmcp import FastMCP`) and `uv lock` / `uv sync`. Python `>=3.12,<3.14`. Use `uv` (project rule), not pip.
- Retired `mcp_server.py` (`9550179^`) confirmed shape: `FastMCP(app_name, instructions=…, host, port, json_response=True, stateless_http=True, streamable_http_path="/mcp", transport_security=make_transport_security_settings(settings))`; `make_transport_security_settings` builds `TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=…, allowed_origins=…)` from `DEFAULT_MCP_ALLOWED_HOSTS/_ORIGINS` + settings; tools registered by side-effect import; `install_protocol_aware_call_handler(mcp)` (unknown tool → `McpError(INVALID_PARAMS)`; tool exceptions → `CallToolResult(isError=True)`). Retired `tools/capture_feedback.py`: `@mcp.tool(name="capture_feedback")`, **flat parameter list** (only `source` nested as `CaptureFeedbackSourceInput`), returns `CallToolResult` with `structuredContent={request_id, accepted_at, status:"accepted"}`.
- **Test-harness caveat:** the retired 847-line `tests/test_mcp_integration.py` used in-process `create_connected_server_and_client_session`, which **bypasses HTTP middleware** — so credential auth must be validated on a path that actually exercises resolution (HTTP-level, or a unit test of the middleware/verifier), **not** only the in-process tool harness. Keep the new test small (contract rule: terse, minimal high-value cases).

## Constraints

- Write path only — no read tools (`list_feedback`, `summarize_feedback`, `list_liked_conversations` stay retired; reads remain REST-only).
- Re-alignment, not a verbatim restore: per-project `vk_` credentials (not static `VOCKY_MCP_AUTH_TOKEN`), P3 v2 project-scoped capture shape.
- Reuse the transport-neutral capture pipeline (`capture.py` → `enqueue_feedback` → worker → `feedback_events`); no separate storage path; **no DB schema change** (reuse `feedback_events.project_id`).
- Keep tests terse (contract rule); use `uv` for Python deps.
- Durable docs are versioned **only at REVIEW** — S1/S2 append to the Doc impact list below, never run `doc-new-version`.

## Doc impact

_Seeded by `P7.DECOMP`; S1/S2 append one-liners as they change durable truth. The REVIEW slice consolidates these into new doc versions on a passing review — do NOT version now. `data` is expected unchanged (no schema change)._

- **architecture** — revive MCP as a write-only capture surface: `/mcp` FastMCP Streamable HTTP mount + `session_manager` lifespan nesting; MCP credential auth at the sub-app boundary.
- **api** — new `capture_feedback` MCP tool contract + its auth model; flip the "MCP retired" status line.
- **security** — MCP per-project `vk_` credential auth; transport-security (DNS-rebinding / allowed hosts+origins) decision for a publicly-exposed `/mcp`.
- **product** + **experience** — the agent-decided, write-only capture story returns.
- **decisions** — auth-binding, input-model, transport-security, and write-only-scope decisions.
- **backend** — new `mcp_server.py` + tool module.
- **operations** — re-added `mcp[cli]` dep; any new MCP env vars (allowed hosts/origins).
- Ancillary (non-versioned prose, not doc-set versions): `docs/local-public-access.md` and `docs/changple5-apply.md` describe the old static-token `/mcp` model and will need updating.
- **[P7.S1]** architecture — `/mcp` FastMCP Streamable-HTTP mount restored (`Mount("/mcp")` + inner `streamable_http_path="/"`) with `session_manager.run()` nested in the host lifespan; still tool-less + unauthenticated. operations — re-added `mcp[cli]` dep (`mcp==1.28.1`) and MCP DNS-rebinding allowlist env (`VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS`, localhost always allowed). security — transport-security decision confirmed: DNS-rebinding protection **on** by default, localhost allowlist, extendable via env (auth still deferred to S2).

## Open Questions

- **Transport security for a public `/mcp` (decide in S1):** re-add a minimal, configurable `TransportSecuritySettings` (DNS-rebinding protection + `VOCKY_MCP_ALLOWED_HOSTS` / `_ORIGINS`) for the publicly-exposed endpoint, or descope to a deferred job? Recommend re-adding the minimal version. The old static `VOCKY_MCP_AUTH_TOKEN` is **not** revived regardless (per-project credentials replace it).
- **FastMCP scope access (verify in S2):** confirm the exact way a tool handler reads the ASGI scope for the stashed credential (expected `ctx.request_context.request.scope[PROJECT_CREDENTIAL_SCOPE_KEY]`); if that path is unavailable, fall back to FastMCP's native bearer-auth provider.
- **Possible S2 split:** if S2 planning finds the `/mcp` credential-auth binding heavy enough to isolate, split off `P7.S3` (tool + pipeline + test) at order 3, leaving auth binding in S2 — default remains the 2-slice shape.
