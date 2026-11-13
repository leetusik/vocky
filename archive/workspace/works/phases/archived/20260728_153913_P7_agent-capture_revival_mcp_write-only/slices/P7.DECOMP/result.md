# Result — P7.DECOMP

Decomposed phase P7 ("Agent-Capture Revival — MCP write-only") into two implementation
slices plus the pre-existing REVIEW, and seeded the phase notebook with the verified
research. No code changed; no status transitions; no doc versions created.

## Verification of the plan's research (read-only spot-check)

Confirmed every load-bearing finding against the current tree and the retired commit
`9550179^` (the last tree that still had the MCP files). All held:

- Capture seam is transport-neutral and already project-aware: `CreateFeedbackEvent.project_id`
  at `src/vocky/feedback/types.py:17`; REST reference path stamps `project_id` from the
  credential **after** normalization at `src/vocky/api.py:99`.
- `ProjectCredentialRecord` (`src/vocky/accounts/types.py:85-95`) carries `project_id` (line 90)
  but **not** `tenant_id` — so MCP capture needs no tenant/`get_project` lookup.
- `ProjectCredentialAuthMiddleware` (`src/vocky/auth.py:95-148`) guards `/api/*` only
  (`is_api_path`, lines 30-33); `/mcp` is uncovered today. Scope key
  `PROJECT_CREDENTIAL_SCOPE_KEY = "vocky.project_credential"` (line 21).
- `get_active_credential_by_token_hash` / `touch_credential_last_used` exist in
  `src/vocky/accounts/service.py` (lines 228, 265).
- `app.py:46-70` has a flat `routes=[…]` with **no `Mount`**; `lifespan` at 35-43.
- `tests/test_public_access.py:128-147` asserts `"" not in route_paths` (no root catch-all mount).
- `mcp[cli]` is **absent** from `pyproject.toml` (and lock).
- Input hierarchy confirmed in `src/vocky/capture.py`: `BaseCaptureFeedbackInput` (32-55) →
  `RestCaptureFeedbackInput` (58-64, adds `attachment_ids`); `_normalize_capture_payload` (252),
  `normalize_rest_payload` (290). The old `McpCaptureFeedbackInput` / `normalize_mcp_payload` are
  gone from `capture.py` (P1 strip) but still referenced by the retired
  `9550179^:src/vocky/tools/capture_feedback.py` — a recoverable template.
- Retired `9550179^:src/vocky/auth.py` had `is_mcp_path` + `MCPBearerAuthMiddleware` using a
  **static** `VOCKY_MCP_AUTH_TOKEN` (to be replaced by the per-project `vk_` path).
- Retired `9550179^:src/vocky/mcp_server.py` shape (FastMCP + `make_transport_security_settings`)
  and `9550179^:src/vocky/tools/capture_feedback.py` (flat-param `@mcp.tool`, `CallToolResult`)
  confirmed as templates.

## Decomposition (final)

Kept the plan's recommended **2-slice** shape (no S2 split). The write path's auth binding,
tool, and pipeline are cohesive and share a single end-to-end test; splitting would fragment it.

| Slice | Name | Kind | Risk → tier | Order | Depends on |
|---|---|---|---|---|---|
| `P7.S1` | MCP transport foundation: `mcp[cli]` dep, FastMCP server, `/mcp` mount, `session_manager` lifespan | implementation | `medium` → mid | 1 | — |
| `P7.S2` | `capture_feedback` write tool + per-project `vk_` credential auth + capture-pipeline integration + integration test | implementation | `high` → high | 2 | `P7.S1` |

Both created as **bare folders** (only `slice.json`, no `plan.md`). `P7.REVIEW` remains last,
not pre-planned. Risks set deliberately: S1 medium (templated-but-structural, not mechanical →
not low), S2 high (novel per-project MCP auth at the ASGI/sub-app boundary → top tier).

## Notebook seeded (`phase.md`)

- **Decomposition**: slice table + rationale, including why S2 is not pre-split (with the S3
  escape hatch left to S2 planning).
- **Findings & Notes**: capture seam (file:line refs), design question 1 (auth binding, recommended
  host-level `/mcp` middleware reusing the same scope key), design question 2 (thin
  `McpCaptureFeedbackInput` + `normalize_mcp_payload`), transport wiring & gotchas (mount/lifespan
  nesting, the no-root-mount test, the `mcp[cli]` dep, retired-code shapes), and the test-harness
  caveat (in-process harness bypasses HTTP middleware → validate auth on a real resolution path).
- **Constraints**: write-only, re-alignment not restore, reuse capture pipeline, no schema change,
  terse tests, `uv` for deps, docs versioned only at REVIEW.
- **Doc impact** list: architecture, api, security, product, experience, decisions, backend,
  operations (data expected unchanged); plus ancillary prose docs `local-public-access.md` and
  `changple5-apply.md`.
- **Open Questions**: transport-security decision (S1), FastMCP scope access (S2), possible S2→S3 split.

## Validation

- `python3 scripts/workflow.py validate` → **passed** ("Workflow validation passed."); `depends_on`
  target `P7.S1` exists.
- `works/backlog.md` now lists `P7.S1` (medium) and `P7.S2` (high) as `todo` under phase P7, with
  `P7.REVIEW` last. Next slice: `P7.S1`.
- Both slice folders contain only `slice.json` (bare — no `plan.md` pre-filled).

## Deviations

None. Kept the recommended 2-slice shape; no source files changed; no doc versions created.
