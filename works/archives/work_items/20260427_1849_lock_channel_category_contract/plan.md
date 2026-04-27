# Plan

- Work item: works/current/20260427_1849_lock_channel_category_contract
- Created at: 20260427_1849
- Phase ID: P3
- Phase: Channel categories and Admin adjustability
- Slice ID: P3.S1
- Slice: lock channel category contract

## Goal

Lock the durable product, architecture, and API contract for channel categories before runtime validation, storage, Admin UI, or example/test changes.

## Scope

- Update `docs/product.md`, `docs/architecture.md`, and `docs/api.md`.
- Define `channel` as nullable/default-none with built-in categories `web`, `mobile`, and `support`.
- Document that new captures and Admin edits should use an allowed category or null once implementation lands.
- Document that read filters should keep exact matching for built-in and legacy stored channel values.
- Document that existing arbitrary stored channel strings remain readable and exact-filterable for compatibility.
- Update `works/backlog.md` to link this work item and move `P3.S1` through in-progress to done.
- Do not change runtime code, migrations, tests, README examples, or packaged Admin UI docs in this slice.

## Context

- P3.DECOMP identified `channel` as free text across capture validation, read filters, Admin REST patching, persistence, and Admin UI controls.
- The selected category model is a built-in enum, not deployment config or an Admin-managed category list.
- The selected legacy policy preserves existing stored strings while constraining new writes and edits.
- Later slices will implement validation/storage policy, Admin category-aware controls, and compatibility/example coverage.

## Milestones

1. Mark `P3.S1` in progress and link this work item from `works/backlog.md`.
2. Update product terminology and direction for nullable channel categories.
3. Update architecture docs for storage compatibility, validation policy, read filters, and Admin adjustability.
4. Update public/Admin API contracts for allowed categories, null handling, legacy compatibility, and error behavior.
5. Validate the changed docs and close the slice.

## Validation

- Inspect the edited docs for consistent channel category wording.
- Run targeted `rg "channel"` checks across durable docs.
- Inspect `works/backlog.md` after updates.
- No code tests are required for this docs-only slice.

## Risks / open questions

- Risk: Documentation could imply category management UI or config exists. Keep P3 to a fixed built-in category set and record management as out of scope for this slice.
- Risk: Legacy arbitrary values could break old records if described as invalid for reads. Preserve readability and exact filtering for stored legacy values.

## Docs to update

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
