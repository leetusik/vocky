# Plan

- Work item: works/current/20260427_1241_add_self_hosting_and_public_domain_guides
- Created at: 20260427_1241
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.S3
- Slice: add self-hosting and public-domain guides

## Goal

Add in-app operator guides for local self-hosting and public custom-domain deployments, then update durable status docs to reflect that in-app Admin UI docs now exist.

## Scope

- Add `docs.json` topics for local self-hosting and public custom-domain setup using generic examples only.
- Cover `.env`, `make bootstrap`, `/admin`, Admin token use, `make verify`, teardown, direct-run commands, `https://vocky.example.com`, `VOCKY_EXTERNAL_BASE_URL`, MCP allowed hosts/origins, and all three auth tokens.
- Update README, `docs/product.md`, and `docs/architecture.md` for completed in-app operator documentation. Leave `docs/api.md` unchanged unless a contract mismatch is found.
- Extend Admin UI docs tests with representative hosting/domain strings.

## Context

- P2.S1 created the Docs framework and P2.S2 populated API/auth reference topics.
- Durable docs already describe Compose-first local operation and public custom-domain deployment; this slice mirrors those operator essentials into the UI.
- No API, auth, database, MCP, REST, or worker contract changes are planned.

## Milestones

1. Add local self-hosting and public-domain topics to `docs.json`.
2. Update durable status docs for the completed in-app documentation capability.
3. Add representative string coverage and run focused tests.

## Validation

- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py -q`

## Risks / open questions

- Keep public-domain examples generic and avoid personal domain or account-specific details.
- Keep README/product/architecture updates status-oriented rather than changing `docs/api.md` contracts.

## Docs to update

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
