# Plan — P7.DECOMP: decompose "Agent-Capture Revival (MCP write-only)"

## Context

This is the **P7.DECOMP** decomposition slice. Phase P7 revives the AI-agent MCP feedback-capture feature retired in P1, but **write path only**: agents linked to a project's Vocky MCP endpoint save user feedback at their own judgement via a single `capture_feedback` tool, feeding the same queue/store as REST. Re-aligned to the P2/P3 surface (per-project `vk_` credentials + P3's project-scoped v2 capture shape) — **not** a verbatim restore. The three retired read tools (`list_feedback`, `summarize_feedback`, `list_liked_conversations`) stay retired; reads remain REST-only. (Source: `intent.md`.)

**Your job (executor = `slice-executor-high`)** is narrow: **create the middle slices (bare folders) and seed `phase.md`** with the breakdown, findings, and doc-impact notes. Do **not** implement code, do **not** pre-fill the new slices' `plan.md`, and do **not** run `doc-new-version` (durable docs are versioned once, at the review). Set each middle slice's `--risk` deliberately — risk selects the executor tier and is the phase's main cost lever. You may run `new-slice`. You must **not** commit or transition slice/phase status — the orchestrator does that.

The research below (from three exploration passes) is pre-gathered; confirm the seam and finalize the breakdown quickly, then create the slices and seed the notebook.

## Recommended decomposition (2 implementation slices)

Validate against your own read; you may adjust. Recommended shape — split by layer: **transport foundation** vs. **the write path (auth binding + tool + pipeline)**. The credential→project→tool binding lives with the tool because the tool is the only thing that needs `project_id`, and the natural end-to-end test exercises auth+tool+pipeline together.

| Slice | Name | Kind | Risk → tier | Order | Rationale |
|---|---|---|---|---|---|
| `P7.S1` | MCP transport foundation: re-add `mcp[cli]` dep, FastMCP server module, mount `/mcp`, compose `session_manager` lifespan | implementation | `medium` → mid | 1 | Structural but templated (retired code is a recoverable pattern). Touches `pyproject.toml`+lock, a new `mcp_server.py`, `app.py` routes+lifespan, and the test that asserts "no root mount". Stands the transport up; no tool/auth yet. Not fully mechanical → not `low`. |
| `P7.S2` | `capture_feedback` write tool + per-project `vk_` credential auth + capture-pipeline integration + integration test | implementation | `high` → high | 2 (depends_on `P7.S1`) | The crux. Resolves the two design questions the intent deferred (auth binding, input-model reuse), wires the tool through the transport-neutral capture seam, stamps `project_id` from the credential, and adds one small integration test. High-risk novel auth wiring → top tier. |

Existing `P7.REVIEW` stays last (never pre-planned here). Result: DECOMP + S1 + S2 + REVIEW.

**Latitude:** if research shows the `/mcp` credential-auth binding is heavy enough to warrant isolation, split S2 into S2 (auth binding) + S3 (tool + pipeline + test) at order 3. Recommended default is the 2-slice shape above.

## Key findings to record in `phase.md`

Seed the phase notebook (Decomposition + Findings/Notes + a "Doc impact" list) with these, so S1/S2 build on them:

**The capture seam (transport-neutral, already project-aware).** A non-REST caller needs exactly: build a `CreateFeedbackEvent` → set `project_id` → `await get_capture_queue().enqueue_feedback(event)`. Everything downstream (queue serialize/deserialize, worker, service, repository, `feedback_events`) already round-trips `project_id`.
- `CreateFeedbackEvent` — `src/vocky/feedback/types.py:11-38` (has `project_id: UUID | None = None`, line 17).
- `get_capture_queue().enqueue_feedback(payload)` — `src/vocky/capture_queue.py:225,292-295`.
- REST reference path to mirror — `src/vocky/api.py:90-111`: parse → `RestCaptureFeedbackInput.model_validate` → `normalize_rest_payload` → **`normalized.payload.project_id = get_request_credential(request).project_id`** (`api.py:99`, injected *after* normalization) → `enqueue_feedback` → `202` via `serialize_capture_receipt`.

**Design question 1 — MCP credential→project auth binding (the crux; resolve in S2).**
- Verify path: `get_accounts_service().get_active_credential_by_token_hash(sha256_hex(token))` (`auth.py:119-125` → `accounts/service.py:228-244` → `accounts/repository.py:176-187`, filters `revoked_at IS NULL`). Returns `ProjectCredentialRecord` (`accounts/types.py:85-95`) carrying **`project_id` but not `tenant_id`** (capture only needs `project_id`, so no `get_project` lookup required).
- `ProjectCredentialAuthMiddleware` (`auth.py:95-148`) guards `/api/*` **only** (`is_api_path`, `auth.py:30-33`), stashing the record at `PROJECT_CREDENTIAL_SCOPE_KEY="vocky.project_credential"` (`auth.py:21,135`, read via `get_request_credential`, `auth.py:151-159`) and best-effort stamping `last_used_at` (`auth.py:139-146`). `/mcp` is **not** covered.
- **Recommended direction (final call in S2):** a host-level middleware guarding `/mcp` that reuses `get_active_credential_by_token_hash` + `sha256_hex` and stashes into the same scope key; because FastMCP's `streamable_http_app()` is mounted as a sub-app, host-level middleware runs before the mount dispatches, so the tool handler can read the credential back off the ASGI scope. Mirror the `last_used_at` stamping. **To verify in S2:** how a FastMCP tool reaches the scope (expected: `ctx.request_context.request.scope[...]`). Alternative to weigh: FastMCP's native bearer-auth provider. Retired precedent to consult: `is_mcp_path` + `MCPBearerAuthMiddleware` in `git show 9550179^:src/vocky/auth.py` (that used a *static* token — replace with the `vk_` per-project path).

**Design question 2 — input model (resolve in S2).** Hierarchy in `src/vocky/capture.py`: `BaseCaptureFeedbackInput` (32-55, shared, no `project_id`/`attachment_ids`) → `RestCaptureFeedbackInput` (58-64, adds `attachment_ids`). `_normalize_capture_payload` (252-287) is transport-neutral, typed on the base, reads `getattr(raw,"attachment_ids",None)` (282). **Recommended:** revive a thin `McpCaptureFeedbackInput(BaseCaptureFeedbackInput)` + a `normalize_mcp_payload` wrapper next to `normalize_rest_payload` — avoids advertising `attachment_ids` in the MCP tool schema (agents have no upload flow); no engine change needed. P1 stripped the old `McpCaptureFeedbackInput`/`normalize_mcp_payload`.

**Transport wiring & gotchas.**
- `create_app()` — `src/vocky/app.py:46-70`: flat `routes=[…]`, **no `Mount` today**; `lifespan` at `app.py:35-43` disposes Redis+engine on shutdown. Retired precedent (`9550179^:src/vocky/app.py`): `Mount("/mcp", app=mcp.streamable_http_app())` in routes + nest `async with mcp.session_manager.run():` around the existing `try/yield/finally` (single nesting — no multi-lifespan orchestration; `session_manager.run()` MUST wrap the app lifetime or streamable-HTTP 500s at request time).
- `tests/test_public_access.py:128-147` **asserts there is no root/catch-all mount** — must be updated when `/mcp` is added.
- Dep: `mcp[cli]` absent from `pyproject.toml`+`uv.lock`; re-add `mcp[cli]>=1.27.0,<2.0.0` (official SDK's bundled FastMCP: `from mcp.server.fastmcp import FastMCP`) and `uv lock`/`uv sync`. Python `>=3.12,<3.14`.
- Retired `mcp_server.py` (`9550179^`): `FastMCP(app_name, instructions=…, host, port, json_response=True, stateless_http=True, streamable_http_path="/mcp", transport_security=make_transport_security_settings(settings))`; tools registered by side-effect import; `install_protocol_aware_call_handler(mcp)` (unknown tool → `McpError(INVALID_PARAMS)`; tool exceptions → `CallToolResult(isError=True)`). Retired `tools/capture_feedback.py`: `@mcp.tool(name="capture_feedback")`, **flat parameter list** (only `source` nested), returns `CallToolResult` with `structuredContent={request_id, accepted_at, status:"accepted"}`.
- **Transport security decision (flag for S1):** old code had `TransportSecuritySettings` (DNS-rebinding protection + `VOCKY_MCP_ALLOWED_HOSTS`/`_ORIGINS`). Recommend re-adding a minimal, configurable version for a publicly-exposed `/mcp`; note as an S1 decision (or a deferred job if descoped). The old static `VOCKY_MCP_AUTH_TOKEN` is **not** revived (per-project credentials replace it).
- **Test reality:** the retired 847-line `tests/test_mcp_integration.py` used in-process `create_connected_server_and_client_session` which **bypasses HTTP middleware** — so credential auth must be validated on a path that actually exercises resolution (HTTP-level or a unit test of the middleware/verifier), not only the in-process tool harness. Keep the new test small (contract rule).

**Doc impact (seed the list; the REVIEW consolidates — do NOT version now).** Likely new versions: `architecture` (revive MCP as a write-only capture surface; `/mcp` mount+lifespan; MCP credential auth), `api` (new `capture_feedback` MCP contract + auth model; flip the "MCP retired" status line), `security` (MCP `vk_` auth + transport-security decision), `product` + `experience` (agent-decided write-only capture story returns), `decisions` (auth-binding, input-model, transport-security, write-only-scope decisions). Probably touched: `backend` (new `mcp_server.py` + tool module), `operations` (re-added dep, any MCP env). **`data` unchanged** (no schema change — reuses `feedback_events.project_id`). Also note (ancillary, non-versioned): `docs/local-public-access.md` and `docs/changple5-apply.md` describe the old static-token `/mcp` model and will need updating.

## What to do (concretely)

1. Read `phase.md` + `intent.md`; confirm the seam and template by spot-checking the files/commit above (read-only; use `git show 9550179^:<path>` for retired files).
2. Create the middle slices (bare folders, no `plan.md`):
   ```
   python3 scripts/workflow.py new-slice --phase P7 --slice P7.S1 \
     --name "MCP transport foundation: mcp dep, FastMCP server, /mcp mount, session_manager lifespan" \
     --kind implementation --risk medium --order 1
   python3 scripts/workflow.py new-slice --phase P7 --slice P7.S2 \
     --name "capture_feedback write tool: per-project vk_ credential auth + capture-pipeline integration + integration test" \
     --kind implementation --risk high --order 2 --depends-on P7.S1
   ```
   (If you split the write path, add `P7.S3` at order 3 and adjust names/risks.)
3. Seed `phase.md`: fill **Decomposition** (the slice table + rationale), **Findings & Notes** (the seam, both design questions with recommended directions, the gotchas), and a **Doc impact** list (above). Optionally note the transport-security open decision under Open Questions.
4. Write `result.md` (free-form) and append cross-slice notes to `phase.md`. Return a structured verdict. **No commits, no status transitions, no `doc-new-version`** — the orchestrator handles those.

## Verification (this slice produces workflow state, not runtime behavior)

- `python3 scripts/workflow.py validate` passes (`depends_on` targets exist).
- `works/backlog.md` lists `P7.S1` and `P7.S2` (bare folders, `todo`) under phase P7, with the intended risks.
- `phase.md` Decomposition + Findings sections are populated and the Doc-impact list is seeded.
- No source files changed, no new-slice `plan.md` pre-filled, no doc versions created.
