# Intent — P7

- Captured at: 2026-07-15T16:51:04+09:00
- Origin: operator

## Original Input (verbatim)

> p1 just finished but actually, I want to make MCP feature back. only post, the agents that linked to Vocky MCP will able to save user feedback by their own judgement.

## Confirmed Intent (refined + clarified)

Revive the agent-decided feedback-capture path retired in P1 — the "this for later" agent-capture the original SaaS-pivot request explicitly deferred ("focus on restapi that only triggered by real human not ai agents feedbacks (this for later, drop existing feature for now)"). This phase brings back **only the write path**.

- **Write-only:** restore only the `capture_feedback` MCP tool (POST). The three retired read/query tools — `list_feedback`, `summarize_feedback`, `list_liked_conversations` — stay retired; all reads remain REST-only.
- **Agent-decided capture:** agents *linked to a project's Vocky MCP endpoint* save user feedback *at their own judgement*, feeding the same shared queue/store as the REST `POST /api/feedback` path — no separate storage path (the capture pipeline is already transport-neutral from `capture.py` onward: build a `CreateFeedbackEvent` → `get_capture_queue().enqueue_feedback(...)` → worker → `feedback_events`).
- **Scoped to the SaaS tenancy model:** the MCP endpoint authenticates via **P2's per-project credentials** (not the old static `VOCKY_MCP_AUTH_TOKEN`), and the capture payload targets **P3's v2 capture shape** — this is a re-alignment to the new surface, not a verbatim restore of the retired code.
- **Placement:** new phase **P7 at execution order 3.5** — runs right after P3, before P4/P5/P6, so the web app (P4), agent-first onboarding (P5), and landing (P6) can incorporate the agent-capture story.

## Clarifications Resolved

- Q: Given P2–P6 already exist as planned phases, where should the MCP revival go? — A: New phase P7 inserted right after P3, at order 3.5 (before P4). It depends on P2 (per-project credentials) and P3 (v2 capture API), and should land before the web/onboarding/landing phases.
- Q: The retired MCP feature had four tools (1 write + 3 read) — which come back? — A: Write only — `capture_feedback`. The three read tools stay retired; reads remain REST-only.

## Notes

_Deliberately left to `P7.DECOMP` — not decided here:_

- How an MCP credential binds to a P2 project/tenant (auth model), and whether to reuse `RestCaptureFeedbackInput` / `normalize_rest_payload` or revive a thin MCP-specific input model subclassing `BaseCaptureFeedbackInput`.
- MCP server/transport wiring (FastMCP Streamable HTTP mount at `/mcp` + `session_manager` lifespan in `app.py`) and re-adding the `mcp[cli]` dependency. The retired code in commit `9550179` (`src/vocky/mcp_server.py`, `src/vocky/tools/capture_feedback.py`, `tests/test_mcp_integration.py`) is a recoverable template but must be re-aligned to the P2/P3 surface, not restored as-is.
- Hard dependency on P2 and P3 being done first — enforced by `order 3.5`; P7 does not affect next-slice selection until then (current pointer stays at P2.DECOMP).
