# P1.DECOMP — Decompose Phase P1 (Relicense & Agent-Capture Retirement)

> Native plan for the **P1.DECOMP** decomposition slice, executed by **`slice-executor-high`**.
> Your job: **create the three middle slices as bare folders** (`new-slice` ×3) and **seed
> `phase.md`** with the breakdown, findings, and Doc-impact list below. Do **not** pre-fill any
> middle slice's `plan.md`, edit source, delete files, or run `doc-new-version` — those happen
> later, slice by slice. You never commit and never transition slice/phase status (other than the
> `new-slice` calls this plan directs). Write your `result.md` and append your `phase.md` notes,
> then return your verdict.

## Context

P1 is the first phase of the vocky SaaS pivot. It has two deliverables (per `intent.md`):
1. **Relicense** AGPL-3.0 → MIT (full open source).
2. **Retire the MCP / AI-agent-decided feedback capture feature** entirely — remove the MCP
   server, tools, config, and related docs — refocusing the product on **human-triggered REST
   feedback** as the base for P2–P6. Git history keeps the removed code recoverable.

Three parallel Explore passes produced a complete map (recorded as Findings below). The MCP path
is **mounted into the same Starlette app** as REST (no separate process/port) and shares the
capture/queue/worker/persistence layers, so removal = whole-file deletes **plus** surgical edits
to a handful of shared files. The relicense is 3 declaration files only.

**Operator decisions (confirmed at the plan gate):**
- MIT copyright holder → **`Copyright (c) 2026 Vocky`**.
- `vocky-smoke` → **rewrite to a minimal REST smoke** (keep `make verify`/`make smoke` meaningful).

## Task — create three middle slices (bare folders only)

Run exactly these three commands, then record the breakdown in `phase.md`:

```
python3 scripts/workflow.py new-slice --phase P1 --slice P1.S1 \
  --name "Relicense to MIT" --kind implementation --risk low --order 1
python3 scripts/workflow.py new-slice --phase P1 --slice P1.S2 \
  --name "Retire MCP/agent-capture from the system" --kind implementation --risk high --order 2
python3 scripts/workflow.py new-slice --phase P1 --slice P1.S3 \
  --name "Scrub MCP from README & ancillary docs" --kind implementation --risk medium --order 3
```

Do **not** create `plan.md` inside any of these folders — the orchestrator writes each slice's
plan at its own turn. Risk is set deliberately (it picks the executor tier).

### P1.S1 — Relicense to MIT · risk **low**
Fully mechanical. Scope (for the phase.md breakdown, not a pre-filled plan):
- `LICENSE` — replace the entire AGPL-3.0 text with standard **MIT License** text, copyright line
  `Copyright (c) 2026 Vocky`.
- `pyproject.toml:11` — `license = { text = "AGPL-3.0-only" }` → `license = { text = "MIT" }`.
- `README.md:380` — reword the `## License` section body to MIT.
- Doc impact: none (license absent from every durable doc).

### P1.S2 — Retire MCP/agent-capture from the system · risk **high**
The core, load-bearing change; one coherent unit that must end with a **green test suite** and
**no `mcp` import under `src/`**. Scope:
- **Delete whole files:** `src/vocky/mcp_server.py`; `src/vocky/tools/capture_feedback.py`,
  `list_feedback.py`, `list_liked_conversations.py`, `summarize_feedback.py`;
  `tests/test_mcp_integration.py`.
- **Surgical edits (remove MCP, keep the rest):** `src/vocky/app.py` (drop the mcp import, the
  root `Mount("/", app=mcp.streamable_http_app())`, `MCPBearerAuthMiddleware`, and unwrap
  `lifespan()` to redis/engine disposal only — **load-bearing routing/lifespan change**);
  `src/vocky/config.py` (remove 3 `mcp_*` fields + 3 properties); `src/vocky/auth.py` (remove
  `is_mcp_path` + `MCPBearerAuthMiddleware`); `src/vocky/capture.py` (remove
  `McpCaptureFeedbackInput`, `normalize_mcp_payload`, the `CaptureFeedbackInput` alias);
  `src/vocky/tools/query_feedback_common.py` (**keep** — remove `from mcp.types import ...` +
  `error_result()`); keep `src/vocky/tools/__init__.py`.
- **`pyproject.toml`** — remove the `mcp[cli]` dependency.
- **Env wiring** — remove the `VOCKY_MCP_*` block from `.env.example`, `docker-compose.yml`,
  `Makefile` `EXPORTED_ENV_VARS`.
- **Runtime admin asset** `src/vocky/admin_assets/docs.json` — remove the MCP nav row, the
  `mcp-tools` section, the `VOCKY_MCP_AUTH_TOKEN` row, and the MCP public-access row.
- **`src/vocky/smoke.py` + `vocky-smoke`** — rewrite the MCP flow to a minimal REST smoke
  (`POST /api/feedback` → `GET /api/feedback`); keep the script entry + `make smoke`/`make verify`.
- **Test cleanup → suite green:** `tests/test_public_access.py`, `tests/test_admin_ui.py`,
  `tests/test_capture_validation.py`, `tests/test_query_validation.py`.
- **Verify:** `uv run pytest` green; `uv run python -c "import vocky.app"` succeeds with `mcp`
  uninstalled; `grep -rE "import mcp|from mcp" src/` empty.
- **Doc impact:** `api`, `architecture`, `product`, `experience` need new versions at REVIEW.

### P1.S3 — Scrub MCP from README & ancillary docs · risk **medium**
Prose accuracy, no code; runs after S2. Scope: rewrite `README.md`'s "MCP Surface" and every MCP
reference to the REST-only surface; rewrite/remove `docs/local-public-access.md` and
`docs/changple5-apply.md`. **Do NOT touch `docs/current/*.md` or `docs/versions/*`.**

### After the middle slices — P1.REVIEW (already exists)
Planned when reached; validates all slices and consolidates the 4 durable-doc versions.

## Seed `phase.md` with

- **Decomposition** section: the three slices with the risk rationale.
- **Findings & Notes** section (the removal map, so downstream slices don't re-discover it):
  - *License map:* only `LICENSE`, `pyproject.toml:11`, `README.md:380` carry the license; no
    source headers, no durable docs. Holder = `Vocky`.
  - *Clean MCP deletes:* `mcp_server.py`, the 4 agent tools, `tests/test_mcp_integration.py`.
  - *Surgical MCP files:* `app.py` (load-bearing), `config.py`, `auth.py`, `capture.py`,
    `tools/query_feedback_common.py` (keep — strip `mcp.types`/`error_result`).
  - *REST surface that STAYS:* `api.py` (`POST`/`GET /api/feedback`, attachment download),
    `admin_api.py`, `attachments_api.py`, `admin_ui.py`; shared `capture_queue.py`, `worker.py`,
    `feedback/`, `persistence/`, `storage/`, `channel.py`, `trigger.py`.
  - *Gotcha:* `mcp` is reachable from REST-served code only via `capture.py` and
    `query_feedback_common.py`; after those two edits + the deletes, `mcp[cli]` drops safely.
  - *Decisions:* smoke → REST rewrite; copyright → `Vocky`.
- **Doc impact** running list: `api`, `architecture`, `product`, `experience` → new versions at
  REVIEW (remove MCP, refocus on human REST capture).

## Verification of this DECOMP slice

- `python3 scripts/workflow.py next` shows `P1.S1`, `P1.S2`, `P1.S3` exist.
- `python3 scripts/workflow.py validate` passes.
- `phase.md` contains the Decomposition, Findings & Notes, and Doc-impact content above.
- Each middle slice folder holds **only** `slice.json` (no pre-filled `plan.md`).
