# Plan — P7.S2: `capture_feedback` write tool + per-project `vk_` credential auth

## Context

Phase **P7** revives the retired agent-capture as a **write-only** MCP surface. S1 stood up the tool-less `/mcp` transport; this is **P7.S2** (risk `high`), **the write path** — the crux of the phase. It resolves the two design questions the intent deferred (auth binding, input model), wires a single `capture_feedback` MCP tool through the transport-neutral capture seam, stamps `project_id` from the authenticating per-project `vk_` credential, and requires that credential on `/mcp`. After S2, an agent configured with a project's `vk_` key at the Vocky `/mcp` endpoint can save feedback into the same queue/store as REST. Full context: `works/phases/active/P7/phase.md` + `intent.md`.

All findings below were verified read-only against the current tree and the installed `mcp==1.28.1`.

## Design decisions (resolved by research)

1. **Input model — thin subclass.** Re-add `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` (empty subclass) + a `normalize_mcp_payload` wrapper in `capture.py`, exactly as the retired code. `_normalize_capture_payload` (`capture.py:252`) is already transport-neutral and guards `attachment_ids` via `getattr`, so the thin subclass drops in with no engine change and keeps `attachment_ids` out of the MCP tool schema (agents have no upload flow).
2. **Auth binding — broaden the existing middleware.** Add `is_mcp_path` and broaden `ProjectCredentialAuthMiddleware` (`auth.py:111-148`) to guard `is_api_path(path) or is_mcp_path(path)`. This reuses, verbatim, the `vk_` resolution (`get_active_credential_by_token_hash(sha256_hex(token))`), the 401, the `scope[PROJECT_CREDENTIAL_SCOPE_KEY]` stash, and the best-effort `last_used_at` stamp. The **whole** `/mcp` endpoint requires a valid key (initialize included) — matching "agents linked to a project's endpoint authenticate with the project's key". The mount runs *after* the app-level middleware, so the middleware sees the full `/mcp` path and its scope mutation propagates into the mounted sub-app.
3. **Tool → credential (the verified crux).** The tool takes a `ctx: Context` parameter (FastMCP injects it, excludes it from the tool schema). `ctx.request_context.request` is the Starlette `Request` — the low-level server sets it at `mcp/server/lowlevel/server.py:760-771` (`RequestContext(..., request=request_data)`) for HTTP transports. So the tool reads the stashed credential with the **existing** `get_request_credential(ctx.request_context.request)` and sets `payload.project_id = credential.project_id` before enqueue (mirroring the REST path at `api.py:99`). The integration test's `project_id` assertion is the empirical proof this binding works.
4. **Protocol-aware call handler — required.** Re-add `make_error_result` + `install_protocol_aware_call_handler` to `mcp_server.py` and call it. It is not optional polish: the tool returns a raw `mcp.types.CallToolResult`, and this handler is what passes that through (`if isinstance(results, CallToolResult): return ServerResult(results)`); it also keeps unknown-tool a protocol error.

## Implementation

### 1. `src/vocky/capture.py` — re-add the MCP input model + normalizer
- `class McpCaptureFeedbackInput(BaseCaptureFeedbackInput): """Raw feedback capture input received through MCP."""` (empty; **no** `attachment_ids`).
- `def normalize_mcp_payload(raw: McpCaptureFeedbackInput) -> NormalizedCaptureFeedback: return _normalize_capture_payload(raw)` — beside `normalize_rest_payload`. (The retired `CaptureFeedbackInput = McpCaptureFeedbackInput` alias is not needed.)

### 2. `src/vocky/auth.py` — guard `/mcp`
- Add `def is_mcp_path(path: str) -> bool: return path == "/mcp" or path.startswith("/mcp/")` (beside `is_api_path`).
- Change the `ProjectCredentialAuthMiddleware.__call__` predicate (line 112) to `... and (is_api_path(p) or is_mcp_path(p))`.
- Update the middleware and `get_request_credential` docstrings to say `/api/*` **and** `/mcp` (both now carry the resolved credential on the scope).

### 3. `src/vocky/tools/capture_feedback.py` — NEW (the tool)
Port the retired `9550179^:src/vocky/tools/capture_feedback.py` and add the credential binding:
- Imports: `from mcp.server.fastmcp import Context`; `from vocky.mcp_server import mcp`; `McpCaptureFeedbackInput, normalize_mcp_payload, CaptureFeedbackSourceInput, CaptureFeedbackValidationError, serialize_capture_receipt` from `vocky.capture`; `CaptureQueueError, get_capture_queue` from `vocky.capture_queue`; `get_request_credential` from `vocky.auth`; `CallToolResult, TextContent` from `mcp.types`.
- Local `error_result(message) -> CallToolResult(isError=True)` helper (as retired).
- `@mcp.tool(name="capture_feedback")` async with the retired **flat parameter list** (only `source` nested), plus a trailing `ctx: Context`. Body: build `McpCaptureFeedbackInput(...)` → `normalize_mcp_payload` (→ `error_result` on `CaptureFeedbackValidationError`) → **`normalized.payload.project_id = get_request_credential(ctx.request_context.request).project_id`** → `await get_capture_queue().enqueue_feedback(...)` (→ `error_result("capture queue unavailable")` on `CaptureQueueError`) → return `CallToolResult` with `structuredContent = serialize_capture_receipt(...).model_dump(mode="json")` and the `"Accepted feedback capture {id}"` text block. Defensive: if `ctx.request_context.request is None`, return an `error_result` (should never happen — auth is enforced at the middleware).

### 4. `src/vocky/mcp_server.py` — register the tool + re-add the handler
- Re-add `make_error_result` and `install_protocol_aware_call_handler` (from the retired template; they use `mcp.types` + the private `server._tool_manager` / `server._mcp_server.request_handlers`).
- After the `mcp = FastMCP(...)` block: `from vocky.tools import capture_feedback as _capture_feedback  # noqa: E402,F401` (side-effect registration) then `install_protocol_aware_call_handler(mcp)`.
- Update the module docstring (no longer "tool-less").

### 5. Tests — terse, and respecting the once-per-process `session_manager`
`StreamableHTTPSessionManager.run()` can be called **once per process** on the shared module-level `mcp`; S1's `tests/test_mcp_transport.py` is the sole caller. So:
- **Evolve that single test** into the capture happy-path (it already runs `mcp.session_manager.run()` once): give its `http_client` `headers={"Authorization": f"Bearer {cred.key}"}`, `monkeypatch.setattr("vocky.tools.capture_feedback.get_capture_queue", lambda: CaptureQueue(fakeredis...))`, then `initialize` → `list_tools` now asserts `capture_feedback` is present (replacing `tools.tools == []`) → `session.call_tool("capture_feedback", {...})` → assert the receipt and `queue.pop_job(...)` gives `payload.project_id == cred.project_id` plus a couple of key fields. Uses `configured_project_credential` + `monkeypatch` (pattern from `tests/test_capture_api.py`); keep the `http://127.0.0.1:8000/mcp` URL (satisfies DNS-rebinding). This test now touches the DB via the credential fixture.
- **Auth-guard test (no session manager)** in `tests/test_public_access.py`: add `is_mcp_path` cases to `test_path_auth_helpers_...`, and assert `ProjectCredentialAuthMiddleware` now guards `/mcp` — extend the existing middleware test (or add a sibling) with a dummy `/mcp` route: missing/unknown key → 401, seeded key → 200. This needs no lifespan, so it never touches `session_manager.run()`.

## Verification (end-to-end where it counts)

- `uv run pytest tests/test_mcp_transport.py tests/test_public_access.py` green — the transport test proves the **whole write path** (authed MCP `capture_feedback` call → enqueued with the correct `project_id`), which is the real end-to-end check and the empirical confirmation the credential reaches the tool.
- Full suite green: `make test` (or `uv run pytest`).
- `python3 scripts/workflow.py validate` (state integrity).
- Append **Doc impact** one-liners to `phase.md` (do NOT `doc-new-version`): `api` (`capture_feedback` MCP tool contract + `/mcp` `vk_` auth model), `security` (`/mcp` requires a per-project credential; whole endpoint authed), `architecture` (the MCP write path now feeds the shared capture queue), `product`+`experience` (agent-decided write-only capture is live), `decisions` (auth-binding = broadened middleware + scope-read; input-model = thin `McpCaptureFeedbackInput`).

## Critical files

- `src/vocky/capture.py` — `McpCaptureFeedbackInput` + `normalize_mcp_payload`.
- `src/vocky/auth.py` — `is_mcp_path` + broadened middleware predicate + docstrings.
- `src/vocky/tools/capture_feedback.py` — **new** tool (credential-stamping).
- `src/vocky/mcp_server.py` — tool import + `install_protocol_aware_call_handler`.
- `tests/test_mcp_transport.py` — evolve into the authed capture happy-path.
- `tests/test_public_access.py` — `/mcp` auth-guard + `is_mcp_path` cases.
- Reference: `git show 9550179^:src/vocky/{mcp_server.py,tools/capture_feedback.py,capture.py}`.

## Executor notes

- Risk `high` → `slice-executor-high`. The credential-reaches-the-tool binding is the one genuinely novel piece; the integration test's `project_id` assertion is the proof. If `ctx.request_context.request` is unexpectedly `None`/scope-less over streamable HTTP, the sanctioned fallback is FastMCP-native auth (a `TokenVerifier` resolving the `vk_` key, project_id carried in the access token) — but the low-level server code path (`server.py:760-771`) indicates `request` is populated, so the scope-read approach should hold. Report which one you used.
- Keep `/mcp` **write-only** — only `capture_feedback`; do not revive the three read tools or `query_feedback_common` read paths.
- Keep tests terse (contract rule) and respect the once-per-process `session_manager.run()` caveat above — do not add a second HTTP test that runs it on the shared `mcp`.
- Never commit, never transition slice/phase status, never `doc-new-version`. Write a free-form `result.md`; append cross-slice notes + Doc-impact one-liners to `phase.md`.
