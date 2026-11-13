# Later Concerns

## Purpose

- Capture rough product, architecture, workflow, and research concerns before they become scheduled backlog work.
- Preserve the original thought, even when it is not yet ready for a phase or slice.
- Refine concerns later into `works/deferred.md` entries or active `works/backlog.md` phases when they become actionable.

## Usage

- Add a new concern with the next stable concern ID, such as `C1`, `C2`, or `C3`.
- Keep the raw thought intact first; add refinement notes below it later.
- Do not treat this file as active execution order. Active backlog work still belongs in `works/backlog.md`.
- If a concern becomes a concrete parked job, add or update a matching entry in `works/deferred.md`.

## Concern Template

```md
### C<N>: <short title>

- Concern ID: `C<N>`
- Status: raw
- Source: <user request | implementation work | review>
- Captured at: YYYY-MM-DD
- Backlog readiness: not ready
- Related deferred job: none

#### Raw Thought

<preserve the thought here>

#### Refinement Notes

- <questions, constraints, candidate backlog shape, or follow-up notes>
```

## Concerns

### C1: Trajectory-aware feedback for fine-tuning export

- Concern ID: `C1`
- Status: raw
- Source: user request
- Captured at: 2026-04-29
- Backlog readiness: not ready
- Related deferred job: `D1`

#### Raw Thought

Vocky may need to improve the feedback capture field/model because one of the main product features could be fine-tuning data export. The exported data may be formed automatically from user feedback.

Single LLM-call fine-tuning data is straightforward, but multi-process or multi-agent trajectory fine-tuning is more complicated. Feedback capture may need to evolve so Vocky can support trajectory fine-tuning data export later.

#### Refinement Notes

- Avoid solving this only by making one feedback field larger.
- Consider separating user feedback from captured agent trajectory data.
- Explore whether feedback targets need to include trajectory-level and trajectory-step-level targets in addition to message, conversation, and surface targets.
- Define export modes separately from capture, such as single-response SFT, conversation SFT, tool-use trajectory data, and preference data.
- Add human review/export eligibility gates before automatic training data export.

### C2: Concrete app development path for solid feedback context

- Concern ID: `C2`
- Status: refined
- Source: user request
- Captured at: 2026-04-29
- Backlog readiness: ready for decomposition
- Related deferred job: none

#### Raw Thought

Vocky needs a clearer product development path around "solid" feedback capture. The capture model should identify who gave feedback, what explicit action triggered capture, what exact message or surface was reviewed, and what surrounding agent process context is available.

Users may want to inspect how an agent reached an answer: visible conversation context, tool calls, referenced documents, retrieval snippets, prompts or safe prompt summaries, and execution steps. At the same time, Vocky should avoid requiring clients to expose raw private chain-of-thought or sensitive internal prompt material. The app should help integrations send useful context without forcing every client team to design perfect instrumentation from scratch.

#### Refinement Notes

- Treat `user_id` as a first-class caller-owned identity field. Keep `session_id` only as optional runtime or browser correlation context for compatibility and anonymous flows.
- Add an explicit trigger concept so capture can distinguish the displayed feedback summary from the event that caused capture. Candidate fields: `trigger_type`, `trigger_message`, and optional structured trigger metadata.
- Preserve the existing distinction between `message`, `comment`, `target_*`, `messages`, `used_context`, `source_metadata`, and `attributes`, but document their roles more tightly.
- Do not store or encourage raw hidden chain-of-thought. Prefer process summaries, tool-call traces, retrieval context, cited documents, prompt summaries, and redacted execution metadata.
- Keep MCP and REST writing into the same canonical feedback store. MCP should remain optimized for agent-runtime capture and richer agent context; REST should remain optimized for explicit product/UI feedback and authenticated product-user context.
- Build the development path in stages:
  - Stage 1: identity and trigger hardening. Add `user_id`, trigger fields, validation, storage, indexes, read filters, Admin visibility, and updated MCP/REST docs.
  - Stage 2: structured agent context. Define a stable schema for agent runs, tool calls, referenced documents, retrieval snippets, process summaries, and safe prompt/context snapshots.
  - Stage 3: review UX for context. Make Admin detail views explain target, trigger, user, conversation, tool calls, docs, and context without requiring raw JSON reading.
  - Stage 4: optional framework adapters. Add LangChain and LangGraph integrations that collect callbacks/events and populate Vocky's context schema automatically, while keeping Vocky core framework-agnostic.
  - Stage 5: privacy and controls. Add redaction guidance, field-level sensitivity conventions, retention/export controls, and operator review gates before data is reused.
  - Stage 6: learning/export workflows. Promote reviewed feedback into examples, preference data, conversation SFT data, and trajectory/tool-use datasets only after explicit human eligibility review.
- Candidate future backlog phases:
  - Solid feedback identity and trigger contract
  - Structured agent context capture model
  - Admin context inspection UX
  - LangChain/LangGraph capture adapter
  - Reviewed dataset export and eligibility gates
