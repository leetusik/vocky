# Plan

- Work item: works/current/20260427_1708_lock_feedback_context_terminology
- Created at: 20260427_1708
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S1
- Slice: lock feedback context terminology

## Goal

Define the context and target terminology for feedback capture before changing the storage or API implementation.

## Scope

- Update `docs/product.md`, `docs/api.md`, and `docs/architecture.md`.
- Clarify that `conversation_id` identifies the conversation or thread.
- Clarify that `session_id` is optional runtime or user-session scope.
- Define explicit target fields for the exact reviewed message or product surface.
- Clarify that `message` remains the required human-readable feedback summary/display text.
- Define `messages` as surrounding conversation context and `used_context` as agent-used context.

## Context

- P1.DECOMP selected a flat nullable target model: `target_type`, `target_id`, `target_role`, and `target_text`.
- This slice is documentation-only and should not change runtime behavior.

## Milestones

1. Update product terminology and capture goals.
2. Update architecture data expectations and storage model notes.
3. Update API capture/read contract language for context and target semantics.
4. Record results and archive the completed work item.

## Validation

- Documentation review by inspection.

## Risks / open questions

- Avoid documenting target fields as implemented until the later code slices land.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
