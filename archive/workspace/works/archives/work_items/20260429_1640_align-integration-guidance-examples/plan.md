# Plan

- Work item: works/current/20260429_1640_align-integration-guidance-examples
- Created at: 20260429_1640
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.S4
- Slice: align integration guidance and examples

## Goal

Update integration-facing guidance and examples so MCP and REST callers know when to send `user_id`, trigger fields, target fields, process context, and metadata after the P1.S3 implementation.

## Scope

- Update `README.md`, `docs/action-feedback-integration.md`, and `src/vocky/admin_assets/docs.json`.
- Show `user_id`, `trigger_type`, `trigger_message`, and `trigger_metadata` in examples where they add useful context.
- Clarify that raw hidden chain-of-thought should not be sent; callers should send summaries, tool traces, retrieval snippets, prompt summaries, and redacted execution metadata.
- Keep examples on the shared capture field set without REST-only aliases, split endpoints, or new review APIs.

## Context

- P1.S3 implemented the fields, storage, filters, and Admin UI visibility.
- Public REST remains capture-only; Admin REST remains the review/management surface.
- Trigger fields describe why capture happened; target fields describe what was reviewed.

## Milestones

1. Inspect existing public and operator docs examples.
2. Update README quickstart and field guidance.
3. Update action-feedback integration guidance and packaged Admin docs examples.
4. Run focused docs/UI asset checks.

## Validation

- `uv run pytest tests/test_admin_ui.py`
- `git diff --check`

## Risks / open questions

- Avoid using raw chain-of-thought examples or implying browser-direct unauthenticated ingestion.

## Docs to update

- `README.md`
- `docs/action-feedback-integration.md`
- `src/vocky/admin_assets/docs.json`
