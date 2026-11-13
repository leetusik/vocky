# Plan

- Work item: works/current/20260429_1624_define-identity-trigger-contract
- Created at: 20260429_1624
- Phase ID: P1
- Phase: Feedback Field and Role Contract
- Slice ID: P1.S2
- Slice: define identity and trigger contract

## Goal

Define the accepted identity and trigger capture contract before implementation, keeping MCP capture and public REST capture on one shared field set and making Admin REST/read behavior explicit.

## Scope

- Update durable reference docs only: `docs/product.md`, `docs/architecture.md`, and `docs/api.md`.
- Specify `user_id`, `trigger_type`, `trigger_message`, and `trigger_metadata` responsibilities, validation, read filters, and response exposure.
- Keep the contract compatible with existing `session_id`, `message`, `comment`, target fields, context fields, and metadata fields.
- Do not change runtime code, migrations, Admin assets, README examples, or tests in this slice.

## Context

- P1.S1 already documented the surface role split and current field taxonomy.
- The new fields are accepted/planned in this slice and will be implemented in P1.S3.
- `user_id` is caller-owned identity; `session_id` remains runtime/browser/session correlation.
- Trigger fields describe the user action or product event that caused capture, not the primary feedback `message` or user `comment`.

## Milestones

1. Add identity and trigger terminology to product documentation.
2. Extend architecture field responsibilities, storage expectations, read model, and constraints.
3. Extend API contracts for shared trigger rules, capture inputs, read filters, and record responses.

## Validation

- Review docs for consistency and run `git diff --check`.

## Risks / open questions

- Avoid documenting trigger fields as implemented before the P1.S3 code lands.
- Keep Admin metrics limited to ingest-time windows and avoid adding trigger/user dimensions there.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
