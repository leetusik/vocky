# Plan — P14.S3: End-to-end verification of agent-recorded capture

## Job

Prove the phase's contract works live, end to end. Read `works/phases/active/P14/phase.md` in full first (D1–D3, D4 item 1, the S1/S2 cross-slice notes, "Environment / running the suite"). S1+S2 landed the write and read paths; suite baseline is **238 passed**. This slice is verification-first: it should add little or no product code.

## What to prove (against the live local stack)

Bring the stack up per phase.md ("Environment"): `make compose-up` / `make bootstrap` with `.env` providing `DATABASE_URL` + separate `TEST_DATABASE_URL`; `make wait-ready`. Then:

1. **Full suite + static gates**: `make test` (expect ≥238), `make check-skill-parity`, `uv run alembic check` (only the known pre-existing `ix_feedback_events_search_trgm` drift is acceptable).
2. **Migration reversibility**: `uv run alembic downgrade 20260728_1200` → `upgrade head` → `alembic current` back at `20260805_1200 (head)` (pin targets by revision id, never `-1` — S1's lesson).
3. **REST round-trip**: `make smoke` (the existing `vocky-smoke` REST loop) still passes untouched; then a live `POST /api/feedback` carrying `recorded_by: "human"` (explicit value on REST) and one omitting it → worker persists → read back shows `"human"` and `null` respectively.
4. **MCP round-trip — the phase's headline**: the smoke tool is REST-only, so drive `/mcp` yourself: provision a project-bound `vk_` key (the smoke's `_provision_ingest_key` walk in `src/vocky/smoke.py` shows how), then a real authenticated MCP session (JSON-RPC `initialize` + `tools/call capture_feedback` — `tests/test_mcp_transport.py` shows the shapes) with a sentiment in `message` (use a Korean value, e.g. 감사) and a note in `comment`, **omitting `recorded_by`** → the persisted row must show `recorded_by = "agent"` (the D2 default); a second call with explicit `recorded_by: "human"` must win over the default.
5. **Filtered reads**: after the captures, `?recorded_by=agent` narrows correctly on at least the admin list and `GET /api/feedback` (S2 wired four surfaces; spot-check at least two), and the `pg_trgm` search finds the Korean sentiment/note text (D3's rationale).
6. **MCP host check (D4 item 1, verify only)**: confirm a real authenticated `initialize` succeeds with a non-localhost `Host` header when `VOCKY_MCP_ALLOWED_HOSTS` includes it (drive it against the local stack by setting the env/Host pair — no config file changes; `compose.prod.yml` itself is not to be edited).

## How to capture the evidence

- Ad-hoc driving scripts/curl belong in the session scratchpad or inline shell — **not** committed to the repo. If a small permanent guard earns its keep, the only sanctioned home is extending `src/vocky/smoke.py` and only if it stays terse (phase.md's rule); adding an MCP leg to the smoke is optional, judge the cost — do not build a new harness.
- Record the actual commands and observed outputs (trimmed) in `result.md` — this slice's deliverable IS the evidence.
- Record the **prod rollout ordering** as a note + Doc impact line (operations/data docs): migrate before deploying code that reads the column; nullable + no backfill ⇒ the migration is instant and non-blocking.

## Constraints

- No dashboard work, no docs/SKILL edits (S4), no rate limiting, no key scopes.
- Leave the stack in a clean state (test rows are fine in the dev DB; don't wreck `.env` or compose state).
- If the stack cannot come up, or docker isn't available, set the verdict to `needs_operator` with exactly what you need rather than faking evidence.

## Deliverables

- `result.md` with the evidence (commands + outputs), any code that was added (expected: none or a terse smoke extension).
- Cross-slice notes + Doc impact lines appended to `phase.md` (expected: operations.md/data.md — rollout ordering; possibly qa.md if it catalogs verification runs).
- Structured verdict.
