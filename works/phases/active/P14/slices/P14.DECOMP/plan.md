# Plan — P14.DECOMP: decompose "Public agent feedback: agent-recorded VoC capture"

## Job

Decompose P14 into middle slices (bare folders via `new-slice`) and seed `phase.md` with the breakdown, design decisions, findings, and notes. This is a decomposition slice: create slices and record the plan-of-record in `phase.md` — do **not** implement anything, do **not** pre-fill any slice's `plan.md`.

## Intent (from `works/phases/active/P14/intent.md` — read it in full)

Third-party AI agents (changple's chat agent first, but public for anyone) record free-text user feedback (sentiment + note, e.g. 답답함/감사/긍정/부정/짜증) through the existing capture surfaces — REST `POST /api/feedback` and the MCP `capture_feedback` tool at `/mcp` — with:

1. **No sentiment enum** — free text only. Decide which existing capture fields carry sentiment + note (`message` / `comment` / `tags` — new columns only if genuinely needed).
2. **A first-class agent-vs-human marker** — a real persisted discriminator so agent-recorded feedback is queryable/filterable and dashboards can split it. You must decide the concrete design here.
3. **Public documentation** — the agent-feedback contract documented in `docs/current/api.md` and `skills/vocky-feedback/SKILL.md` (there is a byte-parity gate between the skill and its docs — find and respect it).
4. **The note argument is a hard requirement** — the capturing agent passes a free-text note alongside the sentiment.

## Design decisions DECOMP must make (and record in `phase.md`)

- **Marker design.** Today `trigger_type` is a closed enum (`src/vocky/trigger.py`: like, dislike, comment, rating, survey, manual, other) stored + indexed on `feedback_events`, and `source.integration` is free-text convention. Weigh: (a) a new `trigger_type` value (e.g. `agent`), (b) a new actor/source column (e.g. `recorded_by: agent|human`), (c) something else. Consider queryability (repository filters already support `trigger_type`), migration cost (check how schema changes are done in `src/vocky/persistence/`), API/MCP surface impact, and that dashboards must split agent vs human. Record the chosen design and the rejected alternatives with reasons in `phase.md`.
- **Field mapping** for sentiment + note onto the existing capture payload (`src/vocky/capture.py` `_normalize_capture_payload` + transport input models is the single seam — REST, MCP, and CLI all flow through it). Prefer existing fields; a new column needs explicit justification.
- **Public-surface hardening scope.** `intent.md` Notes list known considerations: prod `VOCKY_MCP_ALLOWED_HOSTS`/`VOCKY_MCP_ALLOWED_ORIGINS`, no rate limiting on `/api/feedback` and `/mcp`, unscoped `vk_` keys in third-party agent processes. Decide what is in-scope for P14 vs deferred (`defer-job` notes in phase.md for the orchestrator, or explicitly out-of-scope with rationale) — the phase's core is the contract + marker + docs; don't balloon it, but don't silently ignore the security notes either.

## Research before cutting slices

- `src/vocky/capture.py`, `src/vocky/trigger.py`, `src/vocky/mcp_server.py`, `src/vocky/api.py` (the `POST /api/feedback` route), `src/vocky/feedback/types.py`, `src/vocky/feedback/repository.py`, `src/vocky/persistence/models.py` (+ how migrations are handled in this repo).
- `docs/current/api.md`, `docs/current/data.md`, `docs/current/decisions.md` (decision D-P3-2 re key scopes), `skills/vocky-feedback/SKILL.md` and whatever enforces its byte-parity gate.
- `works/later_concerns.md` C2 Stage 4 (LangChain/LangGraph capture adapter anticipation).
- Any dashboard/query surface that would show the agent-vs-human split (e.g. `app_feedback_api.py`, `project_feedback_api.py`) — enough to know what filtering the marker must support.

## Cutting the slices

- Use `python3 scripts/workflow.py new-slice --phase P14 --slice P14.S<n> --name "..." --kind implementation --risk <low|high> --order <n>` (this is the one workflow command you may run). Bare folders only.
- Sequence roughly: schema/marker + capture-seam contract change → surface exposure (REST + MCP) → tests/verification → public docs (api.md impact note + SKILL.md; remember docs consolidation happens at REVIEW via "Doc impact" notes, so implementation slices only append those notes). Merge or split as your research dictates — keep the phase lean; this is a contract extension, not a rewrite.
- **Risk ratings are the cost lever**: `low` only for a genuinely one-to-few-line edit or pure docs prose in a single file; everything that writes real code or touches multiple files is `high`. Expect most slices here to be `high`.
- No product visual design is in scope → single-pass decomposition (no co-work slice, no DECOMP2).

## Record in `phase.md`

Seed the Decomposition section (slice list with one-line rationale each), the marker + field-mapping decisions with alternatives considered, findings from research (including the byte-parity gate mechanics and migration approach), constraints, and any deferred security items. Later slices rely on this as their shared context — make it self-sufficient.

## Deliverables

- Middle slices created (bare folders).
- `phase.md` seeded as above.
- `result.md` in this slice folder: what you created, why, and the decisions taken.
- Structured verdict.
