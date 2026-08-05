# Intent — P14

- Captured at: 2026-08-05T14:34:38+09:00
- Origin: operator

## Original Input (verbatim)

> changple production succesfully create account and project, and link human feedback. now it's time to link real agent feedback. /create-phase for both changple5, and vocky.
> ----
> 1. research how changple like langchain system based agents will add those 3rd party tool. maybe MCP would be the best option, but you should research it.
> 2. make sure we offer publically support the feature. agent will decide to store the user feedback.(답답함, 감사, 긍정, 부정, 짜증, etc.)
> 3. when a agent using this tool make sure they can add argument. so that it can leave a note about the user feedback.

## Confirmed Intent (refined + clarified)

Vocky publicly supports **agent-recorded feedback**: a third-party AI agent (changple's chat agent being the first real consumer, but the feature is public for anyone) decides mid-conversation to record user feedback it observes — 답답함, 감사, 긍정, 부정, 짜증, and the like — together with a free-text note, so product operators can hear the raw voice of the customer.

Concretely for vocky:

- **No sentiment enum.** The operator explicitly chose free text over a fixed vocabulary: the agent stores the user's feedback as free-form text (sentiment + note). DECOMP decides which existing fields carry it (`message` / `comment` / `tags` — new columns only if genuinely needed).
- **First-class agent-vs-human marker.** Vocky persists a real discriminator (exact design — e.g. a new `trigger_type` value or an actor/source field — decided in DECOMP) so agent-recorded feedback is queryable/filterable and dashboards can split agent vs human feedback. Today the transport is not stored and `source.integration` is free-text convention only.
- **Publicly supported and documented.** The agent-feedback contract is part of the public surface — both REST `POST /api/feedback` and the MCP `capture_feedback` tool at `/mcp` — documented in `docs/current/api.md` and `skills/vocky-feedback/SKILL.md` (byte-parity gate) so any third-party agent product can adopt it the way changple does.
- **The note argument is a hard requirement**: whatever mapping DECOMP picks, the capturing agent must be able to pass a free-text note about the user feedback alongside the sentiment.

## Clarifications Resolved

- Q: How should the changple agent call vocky (native tool → backend proxy, native tool → vocky direct, or MCP via langchain-mcp-adapters)? — A: **MCP, as a public consumer** — "just like any user that using vocky in public." Changple connects to vocky's public `/mcp` endpoint via `langchain-mcp-adapters`, dogfooding the public surface. (The changple-side setup is its own phase in the changple5 repo: P63.)
- Q: Should the sentiment vocabulary be a fixed enum (English slugs or Korean labels), enum + escape hatch, or free text? — A: **Free text, no enum** — "just let agent store a user feedback that occurs from the user. so that the operators can hear the voice of customers. so that improve the product."
- Q: Should vocky persist a first-class agent-vs-human distinction? — A: **Yes — first-class marker.**

## Notes

- Ordering: this phase (the public contract + marker) lands **before** changple5's P63, which consumes it.
- Known public-MCP considerations to weigh during this phase: prod `VOCKY_MCP_ALLOWED_HOSTS`/`VOCKY_MCP_ALLOWED_ORIGINS` must include the public host or `/mcp` 401s; `/api/feedback` and `/mcp` currently have **no rate limiting**; a `vk_` key has no permission scopes (capture + read + PATCH + DELETE, decision D-P3-2) — worth revisiting now that keys will live in third-party agent processes.
- `works/later_concerns.md` C2 Stage 4 already anticipated a LangChain/LangGraph capture adapter; this phase is its natural continuation.
- The single seam for any contract change is `src/vocky/capture.py` (`_normalize_capture_payload` + the transport input models) — REST, MCP, and CLI all flow through it.
