# Result

- Work item: works/current/20260424_1454_document_cloudflare_custom_domain_setup
- Created at: 20260424_1454
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.S4
- Slice: document Cloudflare custom-domain setup
- Review status: complete
- Reviewer: self
- Next action: Start `P1.REVIEW` to verify the full phase.

## Summary

Documented the public custom-domain deployment path for `vocky.example.com`, including Cloudflare onboarding, registrar nameserver changes, Cloudflare Tunnel routing, Vocky env settings, public smoke verification, and bearer-token client usage.

## Changes Made

- Updated README with public access settings, Cloudflare Tunnel setup, registrar nameserver steps, tunnel config, and authenticated MCP client example.
- Updated architecture docs with the new MCP route, Host/Origin allowlist, bearer-token setting, and public custom-domain operator mode.
- Updated API docs to state that public self-hosted MCP requests should use `Authorization: Bearer <VOCKY_MCP_AUTH_TOKEN>`.
- Updated product direction to include protected public self-hosted deployments.

## Files Changed

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`
- `works/current/20260424_1454_document_cloudflare_custom_domain_setup/plan.md`
- `works/current/20260424_1454_document_cloudflare_custom_domain_setup/result.md`

## Verification Performed

- `rg -n "redirect|/mcp/|VOCKY_MCP_AUTH_TOKEN|VOCKY_MCP_ALLOWED_HOSTS|vocky.example.com|Cloudflare|registrar" README.md docs/product.md docs/architecture.md docs/api.md .env.example Makefile docker-compose.yml`
- `uv run pytest tests/test_public_access.py -q`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Follow-Ups

- Run `P1.REVIEW`.

## Commit References

- Pending.
