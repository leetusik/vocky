# Result

- Work item: works/current/20260427_1246_remove_tenant_wording_from_ui_docs
- Created at: 20260427_1246
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.F1
- Slice: remove tenant wording from UI docs
- Review status: passed
- Reviewer: Codex
- Next action: Archive this work item and rerun `P2.REVIEW`.

## Outcome

Replaced the `single-tenant` phrase in `src/vocky/admin_assets/docs.json` with deployment-oriented self-hosting wording that avoids tenant-model language in the in-app UI docs.

## Deviations from plan

None.

## Validation run

- `rg -n "tenant|account|billing|organization" src/vocky/admin_assets` - no matches.
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q` - passed, 15 tests.

## Files changed

- `src/vocky/admin_assets/docs.json`
- `works/backlog.md`

## Docs updated

- `src/vocky/admin_assets/docs.json` only.

## Roadmap updates

- Mark `P2.F1` complete in `works/backlog.md` after archiving and rerun `P2.REVIEW`.

## Retrospective

- The scan is now clean for the managed-SaaS wording terms in Admin UI assets.
