# Result

- Work item: works/current/20260427_1241_add_self_hosting_and_public_domain_guides
- Created at: 20260427_1241
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.S3
- Slice: add self-hosting and public-domain guides
- Review status: passed
- Reviewer: Codex
- Next action: Archive this work item and run `P2.REVIEW`.

## Outcome

Added in-app operator guide topics for local self-hosting and public custom-domain deployment. The guides cover `.env`, `make bootstrap`, `/admin`, Admin token use, `make verify`, teardown, direct-run fallback commands, `https://vocky.example.com`, `VOCKY_EXTERNAL_BASE_URL`, MCP host/origin allowlists, and all three bearer-token variables.

## Deviations from plan

None.

## Validation run

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q` - passed, 15 tests.

## Files changed

- `src/vocky/admin_assets/docs.json`
- `tests/test_admin_ui.py`
- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `works/backlog.md`

## Docs updated

- `README.md` now describes the Admin UI in-app operator documentation as implemented and points local operators to `/admin`.
- `docs/product.md` now includes in-app operator documentation in the current product status and MVP scope.
- `docs/architecture.md` now records packaged operator docs assets as part of the Admin Web UI architecture.
- `docs/api.md` was intentionally unchanged because no contract changed.

## Roadmap updates

- Mark `P2.S3` complete in `works/backlog.md` after archiving.

## Retrospective

- The in-app docs now cover both API/auth reference and practical operator setup, so the phase is ready for the review gate.
