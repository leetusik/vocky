# Result — P7.REVIEW: phase review + durable-doc consolidation

**Verdict: `pass`.** Phase P7 (Agent-Capture Revival — MCP write-only) meets its objective
and `intent.md` with no regressions or gaps. All of P7's behavior validates green together,
and the phase's accumulated Doc-impact notes were consolidated into new durable-doc versions.

## 1. Validation (all slices together)

| Check | Command | Result |
|---|---|---|
| Full suite (consolidated S1+S2 behavior) | `uv run pytest` | **169 passed** |
| Write-path proof + `/mcp` 401 guard + `is_mcp_path` | `uv run pytest tests/test_mcp_transport.py tests/test_public_access.py` | **6 passed** |
| State integrity | `python3 scripts/workflow.py validate` | **passed** (re-run after doc consolidation: still passed) |
| Write-only surface | `mcp.list_tools()` at import | **`['capture_feedback']`** — the three retired read tools are NOT revived |

- The transport test (`tests/test_mcp_transport.py`) is the end-to-end proof: an authed
  streamable-HTTP `capture_feedback` call enqueues a job whose `payload.project_id` equals the
  authenticating credential's `project_id` (and survives the queue serialize→deserialize round trip).
- `tests/test_public_access.py` proves `/mcp` is 401-guarded identically to `/api/*`
  (missing/unknown key → 401, seeded key → 200) and covers `is_mcp_path` (incl. `/mcprofile` → False).
- Used `uv run pytest` (not the Docker `make verify`), matching what the slices ran; no failure
  warranted deeper investigation.

## 2. Review against objective / intent.md / code

Confirmed against the source (`mcp_server.py`, `tools/capture_feedback.py`, `auth.py`, `app.py`,
`capture.py`, `config.py`) and `phase.md` Findings — every intent point holds:

- **Write-only tool only.** `capture_feedback` is the sole `@mcp.tool`; `list_tools()==["capture_feedback"]`.
  No read tools, no `query_feedback_common` read paths revived. Reads remain REST/`/app`-only. ✔
- **`/mcp` authed by per-project `vk_` credential (whole endpoint).** `ProjectCredentialAuthMiddleware`
  predicate is `is_api_path(p) or is_mcp_path(p)`; `is_mcp_path` matches `/mcp` and `/mcp/…`. The
  `initialize` handshake is covered. Missing/unknown/revoked → generic 401; static `VOCKY_MCP_AUTH_TOKEN`
  stays retired (config carries only `mcp_allowed_hosts`/`_origins`). ✔
- **Capture feeds the shared queue/store stamping `project_id`; no separate storage path; no schema change.**
  The tool builds `McpCaptureFeedbackInput` → `normalize_mcp_payload` → reads the stashed credential off
  `ctx.request_context.request` via `get_request_credential` → sets `payload.project_id = credential.project_id`
  → `get_capture_queue().enqueue_feedback(...)` (same pipeline as REST). Reuses `feedback_events.project_id`;
  no migration. ✔
- **Aligned to P3's v2 shape.** Thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` (empty subclass,
  no `attachment_ids`); same normalization/serialization seam as REST. ✔
- **`/api/*` auth unchanged; `install_protocol_aware_call_handler` installed; no half-done source.**
  The middleware predicate *adds* `/mcp` via OR (does not remove `/api/*`); the public-access test still
  proves `/api/feedback` 401/200. `install_protocol_aware_call_handler(mcp)` is present and required (it
  passes the tool's raw `CallToolResult` through as `ServerResult` and keeps unknown-tool a protocol error).
  The `/mcp` Mount is last in the route list; `session_manager.run()` is nested in the host lifespan. ✔

No regressions found. No `changes_requested` items.

## 3. Durable-doc consolidation (pass only)

Seven new versions created via `doc-new-version --source P7.REVIEW`, edited in the returned version
files, then `rebuild-docs` regenerated `docs/current/*` + `docs/index.json` (state `validate` re-passed):

| Doc | New version | What it captures |
|---|---|---|
| architecture | `v0005` | New "MCP Write-Only Capture Surface" section (mount + `session_manager` lifespan nesting, transport security, whole-endpoint auth, the tool pipeline); flipped the "MCP retired" framing in Status / Runtime Shape / MVP Boundaries; folded `mcp[cli]` dep + `VOCKY_MCP_ALLOWED_HOSTS/_ORIGINS` into Configuration Surface |
| api | `v0005` | New "MCP Capture Tool (`capture_feedback`)" contract (flat inputs, `source` nested, no `attachment_ids`, capture-receipt output, `isError` results) + the `/mcp` per-project `vk_` auth model; flipped the "MCP retired" Status line; added to MVP Surfaces |
| security | `v0004` | `/mcp` under the broadened mandatory ingest guard (same 401 + `last_used_at` as `/api/*`); new "MCP Endpoint Transport Security (P7)" (DNS-rebinding on); static token stays retired |
| product | `v0005` | Agent-decided write-only capture story returns; new "MCP capture" product-surface role; updated Status + First MVP list |
| experience | `v0005` | New "Agent Capture Over MCP (write-only)" how-to (client shape, `capture_feedback` example, `vk_` auth, async receipt semantics) |
| decisions | `v0004` | D-P7-1 write-only scope; D-P7-2 auth-binding via broadened middleware + scope-read (not FastMCP `TokenVerifier`), static token retired; D-P7-3 thin `McpCaptureFeedbackInput`; D-P7-4 transport security on |
| backend | `v0003` | New "MCP Capture Backend (P7)" (`mcp_server.py`, `tools/capture_feedback.py`, `is_mcp_path`, `McpCaptureFeedbackInput`/`normalize_mcp_payload`); updated App Wiring (`/mcp` Mount + lifespan nesting, broadened middleware) + Config Change (MCP allowlist settings + `mcp[cli]`) |

**Not versioned:** `data` (unchanged — reuses `feedback_events.project_id`, no migration). `operations`
(a bootstrap placeholder that tracks no dep/exposure truth today — per the plan, the config/env was folded
into architecture's Configuration Surface rather than creating an empty-delta operations version).

**Ancillary prose (direct edits, not versioned):**
- `docs/local-public-access.md` — rewrote the `/mcp` auth from the static `VOCKY_MCP_AUTH_TOKEN` to minting
  and sending a per-project `vk_` key; write-only smoke (`capture_feedback` only); client Bearer header +
  transport now `streamable_http`; 401 troubleshooting rewritten for the credential model.
- `docs/changple5-apply.md` — MCP is write-only (`capture_feedback` only); removed the retired
  `list_liked_conversations` section; REST + MCP auth updated to the mandatory per-project `vk_` model.

## Deviations from plan

- Three `doc-new-version` runs (architecture, security, decisions, backend) initially used long summaries
  whose derived filenames exceeded the macOS 255-byte filename limit — architecture failed at creation,
  and security's file could not be edited (the Edit tool's temp suffix overflowed). Recreated architecture,
  security, decisions, and backend with shorter summaries (index reverted cleanly first for the three that
  had already written index entries). No content impact — the shorter summary only shortens the version slug.
- Otherwise none. No source changes; no state transitions; no commits (left to the orchestrator).
