# Plan

- Work item: works/current/20260427_1712_add_explicit_feedback_target_capture_model
- Created at: 20260427_1712
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S2
- Slice: add explicit feedback target capture model

## Goal

Persist optional exact-target metadata from MCP and REST capture payloads without breaking existing clients or queued jobs.

## Scope

- Add `target_type`, `target_id`, `target_role`, and `target_text` to capture validation and normalized capture inputs.
- Add target fields to MCP tool wiring, REST parsing, queue serialization/deserialization, service dataclasses, repository writes/reads, and the SQLAlchemy model.
- Add Alembic migration `20260427_1600_add_feedback_target_fields.py` with nullable text columns and no new indexes.
- Keep old capture payloads and old serialized queue jobs compatible by defaulting missing target keys to `None`.
- Add focused validation, queue, and persistence tests for the new fields.

## Context

- P1.S1 documented target semantics.
- Target fields are optional captured metadata, not filters and not Admin-editable in this slice.
- Existing clients must continue to work with omitted target fields.

## Milestones

1. Inspect current validation, queue, service, repository, model, migration, and test patterns.
2. Implement target fields through capture persistence.
3. Add/adjust focused tests for validation, queue compatibility, and persistence.
4. Run the targeted test set for touched behavior.
5. Record results and archive the completed work item.

## Validation

- Targeted `uv run pytest` for validation, queue, and persistence tests touched in this slice.

## Risks / open questions

- Need to preserve Redis deserialization compatibility for jobs enqueued before this schema change.
- Need to avoid adding indexes or target filters in this phase.

## Docs to update

- None planned beyond the S1 reference-doc updates unless implementation exposes a doc mismatch.
