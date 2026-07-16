# Result — P7.S2: `capture_feedback` write tool + per-project `vk_` credential auth

**Status: done.** The write path is live end-to-end: an agent presenting a project's
`vk_` credential at `/mcp` calls `capture_feedback`, and the event lands on the shared
capture queue stamped with the authenticating credential's `project_id`.

## What I did (followed the plan exactly)

1. **`src/vocky/capture.py`** — re-added the thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)`
   (empty subclass, no `attachment_ids`) next to `RestCaptureFeedbackInput`, and
   `normalize_mcp_payload(...)` next to `normalize_rest_payload`. No engine change:
   `_normalize_capture_payload` already reads `attachment_ids` via `getattr`, so the MCP
   schema stays attachment-free. Did **not** revive the retired `CaptureFeedbackInput` alias
   (unneeded).
2. **`src/vocky/auth.py`** — added `is_mcp_path(path)` (`== "/mcp"` or `startswith("/mcp/")`)
   next to `is_api_path`; broadened `ProjectCredentialAuthMiddleware.__call__` to guard
   `is_api_path(p) or is_mcp_path(p)` so the **whole** `/mcp` endpoint (initialize included)
   requires a valid key, reusing verbatim the `vk_` resolution, 401, scope stash, and
   best-effort `last_used_at` stamp. Updated the middleware and `get_request_credential`
   docstrings to name `/api/*` **and** `/mcp`.
3. **`src/vocky/tools/capture_feedback.py`** — NEW. Ported the retired flat-parameter tool and
   added a trailing `ctx: Context` param (FastMCP injects it and excludes it from the tool
   schema — verified). Body builds `McpCaptureFeedbackInput` → `normalize_mcp_payload`
   (→ `error_result` on `CaptureFeedbackValidationError`) → reads the stashed credential via
   `get_request_credential(ctx.request_context.request)` and sets
   `normalized.payload.project_id = credential.project_id` → `enqueue_feedback`
   (→ `error_result("capture queue unavailable")` on `CaptureQueueError`) → returns a raw
   `CallToolResult` with `structuredContent` from `serialize_capture_receipt(...)` plus the
   `"Accepted feedback capture {id}"` text block. Defensive `None` guard on the request (never
   fires — auth is enforced at the middleware).
4. **`src/vocky/mcp_server.py`** — re-added `make_error_result` + `install_protocol_aware_call_handler`
   (required, not polish: it is what passes the tool's raw `CallToolResult` straight through as
   the `ServerResult`, and keeps unknown-tool a protocol error). Added the side-effect import of
   `vocky.tools.capture_feedback` after the `mcp = FastMCP(...)` block, then
   `install_protocol_aware_call_handler(mcp)`. Updated the module docstring (no longer "tool-less").
5. **Tests** — evolved the single `tests/test_mcp_transport.py` (sole once-per-process
   `session_manager.run()` caller) into the authed capture happy-path; added `/mcp` guard +
   `is_mcp_path` cases to `tests/test_public_access.py` (no lifespan, so it never touches
   `session_manager.run()`).

## Credential-binding path used, and the evidence it works

**Path used: the plan's primary — broadened host-level middleware + ASGI-scope read.** No
fallback to FastMCP-native `TokenVerifier` was needed.

- The app-level `ProjectCredentialAuthMiddleware` runs before the `/mcp` Mount dispatches
  (`app.py:75-76`), so its `scope[PROJECT_CREDENTIAL_SCOPE_KEY] = credential` mutation propagates
  into the mounted FastMCP sub-app.
- The low-level MCP server sets `RequestContext(..., request=request_data)` at
  `mcp/server/lowlevel/server.py:760-771` (verified in the installed `mcp==1.28.1`), so the tool
  reads the Starlette request — carrying the scope — via `ctx.request_context.request`, then
  `get_request_credential(request).project_id`.
- **Empirical proof:** the transport test drives a real authed MCP `capture_feedback` call over
  streamable HTTP (ASGITransport) and asserts
  `queued_job.payload.project_id == configured_project_credential.project_id`. That assertion
  **passes**, confirming the credential reaches the tool and stamps the correct project. The
  `project_id` also survives the queue serialize → deserialize round trip (`pop_job`).

## Verification

- `uv run pytest tests/test_mcp_transport.py tests/test_public_access.py` → **6 passed**
  (the transport test is the end-to-end write-path proof; the public-access test proves `/mcp`
  is 401-guarded identically to `/api/*` and covers `is_mcp_path`).
- `uv run pytest` (full suite) → **169 passed** (unchanged count: the transport test was evolved
  in place, and the public-access changes added assertions to existing tests rather than new
  test functions).
- `python3 scripts/workflow.py validate` → **passed**.
- Confirmed at import time that `mcp.list_tools()` returns exactly `["capture_feedback"]`
  (write-only — the three retired read tools stay retired) and the tool's input schema excludes
  both `ctx` and `attachment_ids`.

## Deviations from plan

None. Implemented exactly as specified. (Note: `ruff` is not installed in this project — CI/
`make test` runs only pytest — so no ruff run was possible; the inherited `# noqa: E402,F401`
annotations on the side-effect import are harmless.)

## Notes for the phase REVIEW

- The whole `/mcp` endpoint is now write-only + authed; the once-per-process
  `session_manager.run()` invariant is preserved (single caller in `test_mcp_transport.py`).
- Ancillary prose docs `docs/local-public-access.md` and `docs/changple5-apply.md` still describe
  the old static-token `/mcp` model and should be updated when the phase's durable docs are
  consolidated (these are non-versioned prose, flagged by DECOMP).
