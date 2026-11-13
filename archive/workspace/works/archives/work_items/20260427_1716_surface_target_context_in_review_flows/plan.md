# Plan

- Work item: works/current/20260427_1716_surface_target_context_in_review_flows
- Created at: 20260427_1716
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S3
- Slice: surface target context in review flows

## Goal

Return and display exact feedback target context in review flows while leaving filtering and edit behavior unchanged.

## Scope

- Add target fields to MCP `list_feedback` and `list_liked_conversations` response models and serializers.
- Add target fields to Admin REST list/detail serializers.
- Show concise target metadata in the Admin UI list.
- Add a read-only Target section in the Admin UI detail view.
- Keep browser edit fields limited to `feedback_value`, `comment`, `channel`, and `tags`.
- Add focused API/MCP/Admin UI tests for records with and without target fields.

## Context

- P1.S2 added target capture persistence and service record fields.
- Target context is review metadata in this phase, not a query filter or editable review field.

## Milestones

1. Inspect Admin UI rendering and test patterns.
2. Add target fields to MCP and Admin REST serializers.
3. Render target metadata in Admin UI list and detail views.
4. Add focused regression tests.
5. Run targeted verification and archive the work item.

## Validation

- Targeted pytest for MCP read, Admin REST, and Admin UI tests touched by this slice.

## Risks / open questions

- Keep target display useful without crowding list rows.
- Ensure records without target fields render cleanly.

## Docs to update

- None planned unless implementation reveals a reference-doc mismatch.
