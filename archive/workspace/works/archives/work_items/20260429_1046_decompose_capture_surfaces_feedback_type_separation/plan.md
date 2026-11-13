# Plan

- Work item: works/archives/work_items/20260429_1046_decompose_capture_surfaces_feedback_type_separation
- Created at: 20260429_1046
- Phase ID: P1
- Phase: Clarify capture surfaces and feedback type separation
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Goal

Break P1 into concrete implementation slices that clarify MCP versus REST capture intent and make message versus non-message feedback reviewable through `target_type` while preserving one canonical feedback table.

## Scope

- Update only backlog/work-item execution artifacts for decomposition.
- Add concrete middle slices between `P1.DECOMP` and `P1.REVIEW`.
- Do not implement code, migrations, UI changes, docs changes, or tests in this slice.

## Context

- P1 is currently planned with only mandatory decomposition and review slices.
- The agreed direction is MCP agent-decided VoC capture, REST-first explicit product/UI capture, and single-table storage using `target_type` as the discriminator.
- Later implementation should preserve existing tool names, REST paths, capture fields, and the shared queue/service/storage path.

## Milestones

1. Link this decomposition work item from the active backlog.
2. Add middle slices for durable contract docs, read filtering/indexing, Admin UI/operator docs, and public guidance/coverage.
3. Mark `P1.DECOMP` complete while leaving implementation slices and `P1.REVIEW` open.

## Validation

- Inspect `works/backlog.md` and confirm P1 contains `P1.S1` through `P1.S4` before `P1.REVIEW`.
- Confirm this slice has no product code, schema, UI, public docs, or test implementation changes.

## Risks / open questions

- Slice boundaries should be narrow enough that each later implementation step can complete and review independently.
- Target-type filtering must be planned without introducing a table split or new persisted feedback-kind field.

## Docs to update

- None in this decomposition slice.
- Later implementation slices should update `docs/product.md`, `docs/architecture.md`, `docs/api.md`, README, action integration guidance, and packaged Admin docs as appropriate.
