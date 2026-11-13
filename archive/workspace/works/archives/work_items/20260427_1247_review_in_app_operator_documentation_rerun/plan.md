# Plan

- Work item: works/current/20260427_1247_review_in_app_operator_documentation_rerun
- Created at: 20260427_1247
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.REVIEW
- Slice: phase review rerun

## Goal

Rerun the P2 phase review after `P2.F1` and close the phase only if route/auth boundaries, packaging, content, UI structure, and tests pass.

## Scope

- Recheck Admin UI route/auth boundaries and static docs asset behavior.
- Recheck docs content coverage and the tenant/account/billing/organization scan for Admin UI assets.
- Build a wheel and confirm `index.html`, `app.css`, `app.js`, and `docs.json` are packaged.
- Run focused tests and the full test suite.

## Context

- The initial `P2.REVIEW` requested `P2.F1` after finding tenant-model wording in `docs.json`.
- `P2.F1` is complete and archived.
- No contract changes are expected.

## Milestones

1. Run content/route inspections.
2. Run focused tests and build/package verification.
3. Run full suite and record review outcome.

## Validation

- `rg -n "tenant|account|billing|organization" src/vocky/admin_assets`
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`
- `uv build --wheel`
- Wheel contents check for Admin assets
- `uv run pytest`

## Risks / open questions

- Full-suite verification may require local PostgreSQL/Redis dependencies; record the exact failure if unavailable.

## Docs to update

- None planned.
