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

S3 done: README scrubbed to REST-only (MCP Surface section deleted; `/mcp`, FastMCP/Streamable-HTTP, the four MCP tool names, and all `VOCKY_MCP_*` env/DNS-rebinding wording removed; the two Python MCP client blocks replaced with REST `POST /api/feedback` + scoped `GET /api/feedback` examples; smoke/verify text now describes the REST smoke). Grep for MCP in README is empty; only README.md changed. Private gitignored docs (`docs/local-public-access.md`, `docs/changple5-apply.md`) left untouched per operator; durable docs deferred to REVIEW.

**S2 done: MCP/agent-capture fully retired.** The app imports with `mcp` uninstalled, `src/` is
100% MCP-free, and the **full DB-backed suite is green** (132 passed via `make test` — Postgres 55432
+ Redis 56379 + Docker were all reachable in the executor sandbox, so the suite was run here, not
deferred). Notes for downstream slices (S3, REVIEW):

- *Deleted cleanly (no surprises):* `mcp_server.py`, the 4 agent tools, `tests/test_mcp_integration.py`.
- *Surgery landed as mapped.* `app.py` final shape: routes = `/healthz` + admin API + admin UI +
  public API + attachments (**no `""` root mount** — the MCP catch-all is gone); lifespan = redis +
  engine disposal only; middleware = API + Admin bearer only. `config.py` lost the 3 `mcp_*` fields +
  3 properties; `auth.py` lost `is_mcp_path` + `MCPBearerAuthMiddleware`; `capture.py` lost
  `McpCaptureFeedbackInput`, `normalize_mcp_payload`, the `CaptureFeedbackInput` alias, **and** the
  unused generic `normalize_payload` shim (grep-confirmed dead); `query_feedback_common.py` lost the
  `mcp.types` import + `error_result()` (no retained caller). `tools/__init__.py` docstring updated
  (no longer "MCP tool modules").
- *Dependency drop is bigger than just `mcp`.* `uv.lock` also removed 17 MCP-only transitives
  (cryptography, jsonschema stack, rich/typer/shellingham, sse-starlette, httpx-sse, etc.). If S3 or
  REVIEW references the dependency surface, note the slimmer runtime footprint.
- *`docs.json` (runtime admin asset) was scrubbed of ALL MCP in S2* — not just the plan's literal
  4-item list — because the verification greps require `src/` MCP-free and `docs.json` is S2's scope
  (S3 owns only README + `docs/*.md`). New `topic_ids`: operator-overview, rest-capture, admin-rest,
  auth-tokens, local-self-hosting, public-custom-domain. `test_admin_ui.py` tracks it in lockstep.
  **S3: do not re-touch `docs.json`; it is already REST-only.**
- *Smoke is now REST* (`smoke.py`): health → `POST /api/feedback` (expect 202 `accepted` +
  `request_id`) → poll scoped `GET /api/feedback?user_id=&source_product=vocky-smoke&session_id=`
  until the worker-persisted row matches; asserts `user_id`/`target_*` round-trip; **no summarize
  step**. `make_http_user_agent`/`make_smoke_health_request` retained (public API); new helper
  `make_smoke_request_headers` adds optional `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>`.
  `make smoke`/`make verify` stay meaningful.
- *Test suite is fully green with no `mcp` under `src/`.* `test_query_validation.py` was rewritten to
  test the shared `query_feedback_common` helpers directly (they back the REST read surfaces now that
  the agent read tools are gone). Gotcha for future edits: `test_public_access.py` /
  `test_admin_ui.py` construct `create_app()` and only need `DATABASE_URL` present (from `.env`), not
  a live DB — they run DB-free.

## Doc impact

Running list of durable-truth changes to consolidate into new doc versions at **P1.REVIEW** (never per slice):

- `api` — remove the MCP tool/streamable-http surface; document REST feedback (`POST`/`GET /api/feedback`) as the human-triggered capture surface. (from S2/S3)
- `architecture` — drop MCP server mount, `MCPBearerAuthMiddleware`, and the MCP branch of app routing/lifespan; REST is the sole ingress. (from S2)
- `product` — refocus the product on human-triggered REST feedback; the AI-agent-decided capture feature is retired. (from S2/S3)
- `experience` — remove MCP/agent-capture from the described operator/user experience. (from S2/S3)

_S2 confirms all four entries still hold; S2 versioned no durable docs (correct — that is REVIEW's
job). The runtime `docs.json` admin asset was edited directly in S2 and is not a durable
`docs/current/*` doc, so it is not part of this list._

## REVIEW note (round 1 — `changes_requested`)

P1.REVIEW validated the whole phase. **Greps all clean** (S1 relicense, S2 MCP-free src/tests/env,
S3 README). **`make smoke` green** end-to-end (REST capture→persist→read against a freshly rebuilt
MCP-free app) and **`make test` = 132 passed**. But **`make verify` fails at `package-check`**: S2's
MCP scrub of `src/vocky/admin_assets/docs.json` also deleted a *REST* (non-MCP) help bullet that the
packaging validator `scripts/check_admin_ui_package.py:115` requires — the exact substring
`target_type message, conversation, or surface` (pre-S2 it was the bullet "Use target_type message,
conversation, or surface to review … separately.", removed alongside its adjacent MCP
`list_feedback/summarize_feedback` bullet). `tests/test_admin_ui.py` asserts the sibling "Any leaves
older records with unset target_type visible" but not this string, so the 132-test suite stayed green
while `package-check` went red. A review slice cannot edit source, so this is `changes_requested` with
one fix slice.

- **Proposed `P1.F1`** (`fix`, risk **low**, order ~3.5): re-add a REST-appropriate sentence containing
  `target_type message, conversation, or surface` to `docs.json` (rest-capture topic near the
  `target_type surface` guidance, or admin-rest read-filters beside the "Any leaves…" line); keep it
  MCP-free; do not change `topic_ids` or the `rest_capture_try` block. Verify `make verify` fully green
  and `grep -c "target_type message, conversation, or surface" src/vocky/admin_assets/docs.json` == 1.
- **Durable docs NOT consolidated this round** (consolidation is pass-only). The four Doc-impact areas
  (`api`, `architecture`, `product`, `experience`) stay queued for the re-review after `P1.F1`.
- **Gotcha for future slices:** `make test` (`uv run pytest`) does NOT run `package-check`; a truly
  green build requires `make verify`. `check_admin_ui_package.py` enforces docs.json content beyond
  what `test_admin_ui.py` asserts.

## Constraints

## Open Questions

-
