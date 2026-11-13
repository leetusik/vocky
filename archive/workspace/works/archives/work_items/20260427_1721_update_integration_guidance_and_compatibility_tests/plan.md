# Plan

- Work item: works/current/20260427_1721_update_integration_guidance_and_compatibility_tests
- Created at: 20260427_1721
- Phase ID: P1
- Phase: Feedback context and target semantics
- Slice ID: P1.S4
- Slice: update integration guidance and compatibility tests

## Goal

Update integration examples to show exact message targeting and broaden round-trip coverage for target fields.

## Scope

- Update `docs/action-feedback-integration.md` examples and terminology.
- Update README capture examples.
- Update packaged Admin UI `docs.json` examples.
- Add or adjust smoke/integration coverage so target fields round-trip through capture, persistence, and readback.
- Confirm legacy payloads without target fields still work.

## Context

- P1.S1 documented target semantics.
- P1.S2 added capture persistence.
- P1.S3 exposed target fields in review flows.

## Milestones

1. Inspect integration docs, README examples, docs.json, and smoke/integration tests.
2. Update examples to include `target_type`, `target_id`, `target_role`, and `target_text`.
3. Add target round-trip coverage through capture, worker persistence, and readback.
4. Run targeted tests for docs assets and integration behavior.
5. Record results and archive the work item.

## Validation

- Targeted pytest for integration/readback and Admin UI docs asset checks.

## Risks / open questions

- Keep examples backward-compatible and avoid implying target fields are required.

## Docs to update

- `docs/action-feedback-integration.md`
- `README.md`
- `src/vocky/admin_assets/docs.json`
