# Plan

- Work item: works/current/20260427_1246_remove_tenant_wording_from_ui_docs
- Created at: 20260427_1246
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.F1
- Slice: remove tenant wording from UI docs

## Goal

Remove tenant-model wording from the in-app Admin UI documentation so P2 can pass its review gate.

## Scope

- Replace the `single-tenant` wording in `src/vocky/admin_assets/docs.json` with equivalent self-hosted wording that avoids tenant/account/billing concepts.
- Add or rely on review scan validation to confirm no tenant/account/billing/organization wording remains in Admin UI assets.
- Run the focused Admin UI/public access tests.

## Context

- P2.REVIEW found `single-tenant` in the in-app Docs content and requested this fix.
- Durable docs may still discuss architecture boundaries such as single-tenancy; this fix is only for the Admin UI docs payload shown in-product.

## Milestones

1. Replace the in-app docs sentence.
2. Scan Admin UI assets for tenant/account/billing/organization wording.
3. Run focused tests and archive the fix.

## Validation

- `rg -n "tenant|account|billing|organization" src/vocky/admin_assets`
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`

## Risks / open questions

- Keep the wording accurate without changing the auth or API contract docs.

## Docs to update

- `src/vocky/admin_assets/docs.json` only.
