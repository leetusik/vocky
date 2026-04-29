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
