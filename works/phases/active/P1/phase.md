# Phase P1: Relicense & Agent-Capture Retirement

_Intent: see [intent.md](intent.md)._

## Objective

Relicense vocky from AGPL-3.0 to MIT and retire the MCP/agent-decided capture feature — remove the MCP server wiring, tools, config, and related docs — refocusing the product on human-triggered REST feedback as the base for the SaaS pivot.

## Context

## Decomposition

Three middle slices, ordered so the code change (S2) lands before the doc scrub (S3); risk picks the executor tier.

- **P1.S1 — Relicense to MIT** · `implementation` · risk **low** · order 1. Fully mechanical, three declaration files only (`LICENSE`, `pyproject.toml:11`, `README.md:380`). No judgment, no code behavior — literal plan-follower tier.
- **P1.S2 — Retire MCP/agent-capture from the system** · `implementation` · risk **high** · order 2. The core, load-bearing change: whole-file deletes plus surgical edits to shared files (app routing/lifespan, config, auth, capture, query-common), dependency + env + admin-asset + smoke rewrite, and test cleanup. One coherent unit that must end with a green suite and no `mcp` import under `src/`. High risk = top tier because `app.py` routing/lifespan is load-bearing and the removal spans many shared files.
- **P1.S3 — Scrub MCP from README & ancillary docs** · `implementation` · risk **medium** · order 3. Prose accuracy only, no code; runs after S2 so docs match the shipped surface. Rewrite README's "MCP Surface" and every MCP reference to REST-only; rewrite/remove `docs/local-public-access.md` and `docs/changple5-apply.md`. Medium (not low) because it needs judgment about what prose to keep vs. cut. Must NOT touch `docs/current/*.md` or `docs/versions/*` (those are consolidated at REVIEW).
- **P1.REVIEW** (pre-existing) — validates all slices together and consolidates the four durable-doc versions on a pass.

## Findings & Notes

Removal map from three parallel Explore passes, recorded here so downstream slices don't re-discover it.

**License map (S1).** Only three files carry the license: `LICENSE` (full AGPL-3.0 text → replace with standard MIT text), `pyproject.toml:11` (`license = { text = "AGPL-3.0-only" }` → `{ text = "MIT" }`), `README.md:380` (`## License` section body → reword to MIT). No source-file headers, no durable docs reference the license. Copyright holder (operator-confirmed) = **`Copyright (c) 2026 Vocky`**.

**MCP removal (S2).**
- *Clean whole-file deletes:* `src/vocky/mcp_server.py`; the four agent tools `src/vocky/tools/{capture_feedback,list_feedback,list_liked_conversations,summarize_feedback}.py`; `tests/test_mcp_integration.py`.
- *Surgical edits (remove MCP, keep the rest):*
  - `src/vocky/app.py` — **load-bearing**: drop the `mcp` import, the root `Mount("/", app=mcp.streamable_http_app())`, `MCPBearerAuthMiddleware`, and unwrap `lifespan()` down to redis/engine disposal only.
  - `src/vocky/config.py` — remove the 3 `mcp_*` fields + their 3 properties.
  - `src/vocky/auth.py` — remove `is_mcp_path` + `MCPBearerAuthMiddleware`.
  - `src/vocky/capture.py` — remove `McpCaptureFeedbackInput`, `normalize_mcp_payload`, the `CaptureFeedbackInput` alias.
  - `src/vocky/tools/query_feedback_common.py` — **keep the file**; remove `from mcp.types import ...` + `error_result()`.
  - Keep `src/vocky/tools/__init__.py`.
- *Dependency / env / assets:* remove `mcp[cli]` from `pyproject.toml`; remove the `VOCKY_MCP_*` block from `.env.example`, `docker-compose.yml`, and the `Makefile` `EXPORTED_ENV_VARS`; in `src/vocky/admin_assets/docs.json` remove the MCP nav row, the `mcp-tools` section, the `VOCKY_MCP_AUTH_TOKEN` row, and the MCP public-access row.
- *Smoke (operator-confirmed rewrite):* `src/vocky/smoke.py` + the `vocky-smoke` entry — rewrite the MCP flow to a minimal REST smoke (`POST /api/feedback` → `GET /api/feedback`); keep the script entry so `make smoke` / `make verify` stay meaningful.
- *Test cleanup → suite green:* `tests/test_public_access.py`, `tests/test_admin_ui.py`, `tests/test_capture_validation.py`, `tests/test_query_validation.py`.
- *Verify (S2 exit):* `uv run pytest` green; `uv run python -c "import vocky.app"` succeeds with `mcp` uninstalled; `grep -rE "import mcp|from mcp" src/` empty.

**REST surface that STAYS (do not remove).** `api.py` (`POST`/`GET /api/feedback`, attachment download), `admin_api.py`, `attachments_api.py`, `admin_ui.py`; shared `capture_queue.py`, `worker.py`, `feedback/`, `persistence/`, `storage/`, `channel.py`, `trigger.py`.

**Gotcha.** `mcp` is reachable from REST-served code only via `capture.py` and `tools/query_feedback_common.py`. Once those two are edited and the whole-file deletes are done, the `mcp[cli]` dependency drops safely — verify with the grep above before removing it.

**Decisions (operator-confirmed at the plan gate).** Smoke → minimal REST rewrite (not deletion); copyright holder → `Vocky`.

S1 done: relicensed to MIT (LICENSE + pyproject + README); no durable-doc impact.

## Doc impact

Running list of durable-truth changes to consolidate into new doc versions at **P1.REVIEW** (never per slice):

- `api` — remove the MCP tool/streamable-http surface; document REST feedback (`POST`/`GET /api/feedback`) as the human-triggered capture surface. (from S2/S3)
- `architecture` — drop MCP server mount, `MCPBearerAuthMiddleware`, and the MCP branch of app routing/lifespan; REST is the sole ingress. (from S2)
- `product` — refocus the product on human-triggered REST feedback; the AI-agent-decided capture feature is retired. (from S2/S3)
- `experience` — remove MCP/agent-capture from the described operator/user experience. (from S2/S3)

## Constraints

## Open Questions

-
