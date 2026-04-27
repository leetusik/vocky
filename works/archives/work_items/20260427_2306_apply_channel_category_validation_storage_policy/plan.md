# Plan

- Work item: works/current/20260427_2306_apply_channel_category_validation_storage_policy
- Created at: 20260427_2306
- Phase ID: P3
- Phase: Channel categories and Admin adjustability
- Slice ID: P3.S2
- Slice: apply channel category validation and storage policy

## Goal

Implement the shared channel-category write policy accepted in P3.S1 across MCP capture, REST capture, and Admin REST patch writes while preserving legacy stored channel readability and exact-match filtering.

## Scope

- Add shared channel-category constants and write normalization.
- Apply validation to MCP capture, REST capture, and Admin REST patch inputs.
- Keep query filters permissive exact-match text filters so legacy stored values remain discoverable.
- Avoid migrations, database enum constraints, queue format changes, or read-side constraints.

## Context

- P3.S1 defined nullable default-none channel semantics and built-in MVP categories `web`, `mobile`, and `support`.
- Existing docs already describe the desired public contract; this slice makes runtime behavior match it.
- Persistence remains nullable `TEXT` for backward compatibility with older arbitrary channel values.

## Milestones

1. Inspect current capture/Admin validation paths and channel query handling.
2. Add a shared channel write normalizer with the required error message.
3. Wire the normalizer into MCP/REST capture and Admin REST patch behavior.
4. Add focused backend tests for accepted, blank, invalid, and legacy-read channel cases.
5. Run targeted pytest for changed behavior.

## Validation

- `uv run pytest` for focused backend tests covering capture, Admin REST, and legacy channel filtering.

## Risks / open questions

- Need to distinguish write validation from read/filter normalization so older stored channel strings remain accessible.
- Admin REST patch may need partial-update semantics to preserve omitted fields while still allowing blank channel to clear the value.

## Docs to update

- None planned for this slice; P3.S4 owns public examples and broader documentation updates.
