# Plan — P7.REVIEW: phase review + durable-doc consolidation

## Context

This is **P7.REVIEW**, the final slice of phase **P7 (Agent-Capture Revival — MCP write-only)**. Both implementation slices are done and committed: S1 stood up the tool-less `/mcp` FastMCP transport; S2 added the write-only `capture_feedback` tool with per-project `vk_` credential auth, proven end-to-end (an authed streamable-HTTP capture call enqueues with the authenticating credential's `project_id`; full suite 169 passed). The review **validates all of P7 together**, reviews it against the objective / `intent.md` / docs, and — **only on a passing review** — consolidates the phase's accumulated "Doc impact" notes (`phase.md`) into new durable-doc versions.

## What to do

### 1. Validate all slices together (behavioral — the review is where this is consolidated)
- `uv run pytest` — full suite; **expect 169 passed** (the consolidated behavioral check for S1+S2).
- `uv run pytest tests/test_mcp_transport.py tests/test_public_access.py` — the write-path proof (authed MCP `capture_feedback` → enqueued `project_id == cred.project_id`) + the `/mcp` 401 guard + `is_mcp_path` cases (**6 passed**).
- `python3 scripts/workflow.py validate` — state integrity.
- Confirm **write-only**: at import, `mcp.list_tools()` returns exactly `["capture_feedback"]` — the three retired read tools are NOT revived.
- (Use `uv run pytest`, not the heavier Docker `make verify`, unless a failure warrants deeper investigation — match what the slices ran.)

### 2. Review against the objective, `intent.md`, and the code
Confirm the phase's intent is met and the code matches the recorded decisions (`phase.md` Findings):
- Write-only `capture_feedback` only; reads remain REST-only (no read tools, no `query_feedback_common` read paths revived).
- `/mcp` authenticates via a per-project `vk_` credential (whole endpoint, initialize included); the static `VOCKY_MCP_AUTH_TOKEN` stays retired.
- Capture feeds the **shared** transport-neutral queue/store (`enqueue_feedback` → worker → `feedback_events`), stamping `project_id` from the credential read off the ASGI scope; **no separate storage path, no DB schema change**.
- Aligned to P3's v2 capture shape; input model is the thin `McpCaptureFeedbackInput` (no `attachment_ids` in the MCP schema).
- Spot-check for regressions: the broadened `ProjectCredentialAuthMiddleware` still guards `/api/*` unchanged; `install_protocol_aware_call_handler` is installed; no source left in a half-done state.

### 3. On a PASSING review — consolidate durable docs (docs only; never source)
`doc-new-version` is permitted **only** in this review slice. Create a new version per doc whose durable truth changed, via `python3 scripts/workflow.py doc-new-version --doc <d> --summary "..." --source P7.REVIEW`, writing the updated content into the new version file (never hand-edit `docs/current/*`). Per the `phase.md` Doc-impact list:
- **architecture** — MCP revived as a write-only capture surface: `/mcp` FastMCP Streamable-HTTP mount + `session_manager` lifespan nesting; the MCP write path feeds the shared capture queue stamping `project_id`; flip the "MCP retired" framing. Fold the new config/env (`mcp[cli]` dep, `VOCKY_MCP_ALLOWED_HOSTS/_ORIGINS`) into the **Configuration Surface** section here.
- **api** — new `capture_feedback` MCP tool contract (flat inputs, `source` nested, no `attachment_ids`; capture-receipt output) + the `/mcp` per-project `vk_` auth model; flip the "MCP retired" API status line.
- **security** — `/mcp` requires a valid non-revoked per-project `vk_` credential (broadened `ProjectCredentialAuthMiddleware`, same 401 + `last_used_at` as `/api/*`); DNS-rebinding transport security on by default; static token stays retired.
- **product** + **experience** — the agent-decided, write-only capture story returns (agents linked to a project's `/mcp` endpoint save feedback with the project's `vk_` key); update the MVP-boundary/non-goal lines that say MCP capture is retired.
- **decisions** — record the P7 decisions: auth-binding = broadened middleware + scope-read (not FastMCP `TokenVerifier`); input-model = thin subclass; transport-security on; write-only scope kept.
- **backend** — new `src/vocky/mcp_server.py` + `src/vocky/tools/capture_feedback.py` + the re-added `install_protocol_aware_call_handler`.
- **operations** — only if the ops doc genuinely tracks the changed truth (the dep/exposure story); otherwise the config surface folds into architecture (executor's judgment — don't create an empty-delta version).
- **NOT `data`** — unchanged (reuses `feedback_events.project_id`; no migration).
- **Ancillary prose (direct edits, NOT `doc-new-version`):** `docs/local-public-access.md` and `docs/changple5-apply.md` still describe the old static-token `/mcp` model — update them to the `vk_` per-project model (flagged by DECOMP + reconfirmed by S2).
- Run `python3 scripts/workflow.py rebuild-docs` if needed so `docs/current/*` and `docs/index.json` reflect the new versions.

### 4. Close out
Write a free-form `result.md` (validation evidence, review findings, the doc versions created), append a final note to `phase.md`, and **return a `review_verdict`** of `pass` / `changes_requested` / `blocked`. On `changes_requested`, list concrete proposed fix slices instead of consolidating docs.

## What NOT to do
- No source changes (this slice touches docs only — the versioned doc set plus the two ancillary prose files).
- No `finish-slice` / `review-phase` / commits / status transitions — the orchestrator records the verdict.
- Do not version `data`.

## Verification
- The review's own validation (full suite green + `validate` + `list_tools()==["capture_feedback"]`) is the behavioral verification.
- On a `pass`, the orchestrator records the verdict with `review-phase P7` (which marks the phase `done` and closes this REVIEW slice), then commits the docs + state.
