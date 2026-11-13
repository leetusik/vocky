# Plan

- Work item: works/current/20260424_1633_add_action_feedback_storage_model
- Created at: 20260424_1633
- Phase ID: P1
- Phase: Explicit action feedback capture
- Slice ID: P1.S1
- Slice: add action feedback storage model

## Context

The current `feedback_events` table stores message, source, IDs, timestamps, tags, source metadata, and attributes. Action feedback needs first-class persisted fields for like/dislike value, optional comment, channel, conversation messages, and used context. The existing async queue and MCP capture contract will be updated in the next slice.

## Goal

Add the storage/domain foundation for explicit action feedback while preserving compatibility with existing feedback rows and read surfaces.

## Scope

- In scope: SQLAlchemy model fields, Alembic migration, transport-neutral dataclasses, repository mapping, and query filter support needed by later MCP/Admin reads.
- Out of scope: MCP tool input changes, docs, Admin REST routes, and Changple handoff.

## Approach

Add nullable/defaulted columns so existing rows remain valid: `feedback_value`, `comment`, `channel`, `messages`, and `used_context`. Use JSONB arrays for `messages` and `used_context`, defaulting to empty arrays. Add indexes for fields expected to be filtered often, especially `feedback_value` and `channel`.

## Affected Files

- `src/vocky/persistence/models.py`
- `src/vocky/feedback/types.py`
- `src/vocky/feedback/repository.py`
- `alembic/versions/*`
- Focused persistence/query tests

## Reference Docs To Review

- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Existing rows will have `feedback_value = null`; liked retrieval should ignore those later, while Admin REST can still return them.
- JSON context shape should be preserved as client-supplied objects without schema-specific parsing.

## Verification Plan

- Add/update tests for persistence round-trips and query filtering by feedback value/channel.
- Run the focused persistence/query tests after implementation.

## Planned Commits

- Not committing unless requested.
