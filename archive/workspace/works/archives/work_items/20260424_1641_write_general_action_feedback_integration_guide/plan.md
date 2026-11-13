# Plan

- Work item: works/current/20260424_1641_write_general_action_feedback_integration_guide
- Created at: 20260424_1641
- Phase ID: P2
- Phase: Liked conversation retrieval and integration handoff
- Slice ID: P2.S2
- Slice: write general action feedback integration guide

## Context

Vocky now supports explicit action feedback capture and a liked-only MCP read tool. Tracked public docs need a generic integration guide that any agent product can use without mentioning a private client app.

## Goal

Add a public guide explaining how client apps should call Vocky for like/dislike actions and how AI agents should retrieve liked conversations for few-shot examples.

## Scope

- In scope: New tracked integration guide, README link, and API docs for `list_liked_conversations`.
- Out of scope: Changple5-specific handoff content and Admin REST docs.

## Approach

Create `docs/action-feedback-integration.md` with MCP endpoint setup, capture payload shape, recommended client behavior, liked few-shot retrieval, and boundaries. Update README and `docs/api.md` to reference the tool.

## Affected Files

- `docs/action-feedback-integration.md`
- `docs/api.md`
- `README.md`

## Reference Docs To Review

- `docs/api.md`
- `README.md`

## Risks and Open Questions

- Keep the guide public and general; Changple-specific details belong in the gitignored handoff doc.

## Verification Plan

- Review docs for generic wording and consistency with implemented MCP contracts.
- Run focused MCP integration tests to ensure the documented tool exists.

## Planned Commits

- Not committing unless requested.
