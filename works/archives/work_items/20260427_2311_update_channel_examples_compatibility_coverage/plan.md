# Plan

- Work item: works/current/20260427_2311_update_channel_examples_compatibility_coverage
- Created at: 20260427_2311
- Phase ID: P3
- Phase: Channel categories and Admin adjustability
- Slice ID: P3.S4
- Slice: update channel examples and compatibility coverage

## Goal

Update examples, operator docs, and compatibility tests so the built-in nullable channel category behavior is visible and covered end to end.

## Scope

- Update README and integration docs to describe nullable built-in channel categories, omit-by-default behavior, and valid example values.
- Update packaged Admin docs (`docs.json`) with the same category guidance.
- Keep examples on valid categories, mainly `web`, without adding custom category management wording.
- Add or adjust tests for accepted categories, rejected invalid writes, blank-to-null writes, legacy stored values remaining readable/filterable, Admin patch behavior, and Admin UI select controls where S2/S3 did not already cover enough.
- Run a broader targeted test set for docs/package-adjacent and channel compatibility coverage.

## Context

- `P3.S2` implemented runtime validation across MCP capture, REST capture, and Admin REST patch.
- `P3.S3` changed Admin UI controls to category selects and legacy-preserve behavior.
- `P3.S1` durable docs already define the contract; this slice updates user-facing examples and packaged UI docs.

## Milestones

1. Search docs/examples/assets for stale free-text or arbitrary channel guidance.
2. Patch README, integration docs, and packaged Admin docs to reflect category behavior.
3. Add any missing compatibility tests for REST blank-to-null, Admin UI docs copy, and legacy query coverage.
4. Run targeted channel/docs/UI/backend tests and package asset check if needed.

## Validation

- `uv run pytest` for targeted channel, Admin REST, Admin UI, MCP, and docs/package-adjacent tests.
- `make package-check` if packaged asset/docs changes need verification.

## Risks / open questions

- Packaged docs JSON must remain valid and package-check must still find expected asset content.

## Docs to update

- `README.md`
- `docs/action-feedback-integration.md`
- `src/vocky/admin_assets/docs.json`
