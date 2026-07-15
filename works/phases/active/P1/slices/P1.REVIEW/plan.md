# P1.REVIEW — Phase review + durable-doc consolidation

> Native plan for the **P1.REVIEW** slice (`review`, → `slice-executor-high`). You validate the
> whole phase, review it against the objective / `intent.md`, and — **only if the review passes** —
> consolidate the phase's Doc-impact notes into new durable-doc versions. You write **docs only,
> never source**. You never commit and never transition slice/phase status; the orchestrator records
> your verdict with `review-phase`. Return a structured `review_verdict` (`pass` /
> `changes_requested` / `blocked`).

## Context

P1 relicensed vocky AGPL-3.0 → MIT and retired the MCP / AI-agent-decided capture feature,
refocusing on human-triggered REST feedback. Three implementation slices are done:
- **S1** — relicensed to MIT (`LICENSE`, `pyproject.toml`, `README.md`).
- **S2** — retired MCP from the system (deletes + surgical edits to `app.py`/`config.py`/`auth.py`/
  `capture.py`/`query_feedback_common.py`, dropped `mcp[cli]`, stripped `VOCKY_MCP_*` env, scrubbed
  the runtime `admin_assets/docs.json`, rewrote `vocky-smoke` to REST, fixed tests). S2's executor
  ran the **full DB-backed suite green (132 passed)** in-sandbox.
- **S3** — scrubbed `README.md` to REST-only.
- **F1** — a first review pass returned `changes_requested`: `make verify`'s `package-check` was red
  because S2's `docs.json` scrub dropped a required REST string. Fix slice **P1.F1** restored it and
  its executor confirmed `make verify` **fully green (package-check + smoke + 132 tests)**. **This is
  the re-review** — expect validation clean now; verify it yourself, then proceed to consolidation.

Read `works/phases/active/P1/phase.md` (objective, Findings & Notes, the S2/S3 notes, and the **Doc
impact** list) and `works/phases/active/P1/intent.md` (confirmed operator intent) before judging.

## Step 1 — Validate the whole phase

Run the consolidated behavioral + integrity validation and record each result in `result.md`:

- **State integrity:** `python3 scripts/workflow.py validate` → passes.
- **Relicense (S1):** `grep -riE "AGPL|Affero|GNU|Public License" LICENSE pyproject.toml README.md`
  → no AGPL/Affero/GNU hits (README `## License` heading is fine); `pyproject.toml` shows
  `license = { text = "MIT" }`; `LICENSE` is MIT.
- **MCP-free (S2):** `grep -rinE "import mcp|from mcp|mcp\.|streamable_http|FastMCP" src/ tests/`
  → empty; `grep -rniE "VOCKY_MCP|mcp-tools" src/ .env.example docker-compose.yml Makefile` → empty;
  no `Mount("/", …)` root catch-all in `app.py`.
- **README (S3):** `grep -inE "\bmcp\b|/mcp|VOCKY_MCP|capture_feedback|list_feedback|summarize_feedback|list_liked_conversations" README.md`
  → empty.
- **Behavioral suite:** bring the stack up and run the full verification — `make bootstrap` (if the
  stack isn't already up) then `make verify` (package-check + REST smoke + full pytest). Report the
  pytest count and the REST smoke result. **If Docker/Postgres/Redis are not available in your
  sandbox**, fall back to `uv run pytest --collect-only -q` + the DB-free unit tests
  (`test_capture_validation.py`, `test_query_validation.py`, `test_public_access.py`,
  `test_admin_ui.py`) and state explicitly in `result.md` that the DB-backed suite could not be
  re-run here (S2 already ran it green) — do not claim green without running it.

## Step 2 — Review against objective & intent

Confirm the phase delivered its objective (`phase.md` line 7) and `intent.md`'s confirmed scope:
- License is MIT everywhere it's declared; nothing still claims AGPL.
- The MCP server, the four agent tools, MCP config/env/deps, and the `/mcp` surface are gone; the
  REST feedback surface (`POST`/`GET /api/feedback`, attachments, Admin REST, Admin Web UI, worker/
  queue/persistence) is intact and tested.
- `README.md` and the runtime `admin_assets/docs.json` reflect the REST-only reality.
- No source/behavior regressions beyond the intended removal.

Decide the verdict:
- **`pass`** — validation clean and objective met → proceed to Step 3 (consolidate docs).
- **`changes_requested`** — fixable gaps; list them as concrete proposed fix slices (`P1.Fn`) in
  your return. **Do not** consolidate docs.
- **`blocked`** — an impediment you can't resolve (e.g. infra truly unavailable AND a real
  correctness doubt). Explain. **Do not** consolidate docs.

## Step 3 — Consolidate durable docs (ONLY on a passing review)

The four durable docs on the Doc-impact list still describe MCP. For **each** of `api`,
`architecture`, `product`, `experience`, in this order:

1. `python3 scripts/workflow.py doc-new-version --doc <slug> --summary "<short>" --source P1.REVIEW`
   — this seeds a new `docs/versions/<slug>/vNNNN_*.md` from the current content and prints
   `edit_path=…`.
2. Edit **that new version file** (never `docs/current/*.md`, never old versions) to remove all MCP /
   agent-capture content and make it true against the shipped REST-only surface (same ground truth as
   the README: `POST /api/feedback` sole capture; scoped `GET /api/feedback`; attachment upload/
   download REST; Admin REST `/admin/api/*`; Admin Web UI `/admin`; worker/queue/Postgres; REST is the
   sole ingress; no `/mcp`, no FastMCP, no `VOCKY_MCP_*`, none of the four tool names).
3. After all four are edited, run `python3 scripts/workflow.py rebuild-docs` once, then
   `python3 scripts/workflow.py validate` (its `validate_docs` checks `docs/current` == latest
   version).

Per-doc focus (see the docs' current content for specifics):
- **api** — delete the MCP capture-tool contract and the MCP list/summary/liked-conversation tool
  contracts; keep/lead with the REST contracts (capture `POST /api/feedback` with the 202 receipt,
  scoped read `GET /api/feedback`, attachment upload/download REST, Admin REST). The field taxonomy
  is transport-neutral — keep it.
- **architecture** — the app is a Starlette host + background worker; the API is now **two-track**
  (public REST `/api/*` + Admin REST `/admin/api/*`) plus the Admin Web UI — remove the MCP `/mcp`
  track, the FastMCP process/session-manager, `MCPBearerAuthMiddleware`, and `VOCKY_MCP_*`. Capture
  path: REST → Redis queue → worker → Postgres.
- **product** — refocus on human-/product-triggered REST feedback and operator review; state the
  AI-agent-decided MCP capture is retired (recoverable via git history). Remove MCP from scope/
  terminology.
- **experience** — remove the "MCP vs REST capture surface" choice and MCP capture flow; describe
  REST capture, the scoped end-user read, and operator review/comments.

Do **not** add net-new license content to the durable docs — the relicense had no durable-doc impact
(it's not on the Doc-impact list); keep this consolidation scoped to the MCP removal + REST refocus.

## Return
A `review_verdict` with: the verdict, the validation results (pytest count / smoke / greps, and
anything deferred), the objective/intent assessment, and — on `pass` — the four new doc version ids
created. On `changes_requested`, the concrete `P1.Fn` fix slices you propose.

## Orchestrator follow-through (after this slice)
I record the verdict with `python3 scripts/workflow.py review-phase P1 --verdict <v> --reviewer
slice-executor-high --note "…"`, then `validate`, then commit. `pass` marks the phase `done` and
closes the `REVIEW` slice (no separate `finish-slice`). On `changes_requested` I create the proposed
fix slices, run them, and re-review. The phase stays in `active/` — archiving is a separate,
operator-initiated step.
