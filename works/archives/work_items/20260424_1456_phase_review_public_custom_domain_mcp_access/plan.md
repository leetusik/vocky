# Plan

- Work item: works/current/20260424_1456_phase_review_public_custom_domain_mcp_access
- Created at: 20260424_1456
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.REVIEW
- Slice: phase review

## Context

All middle slices are complete and archived. The phase added public Host/Origin allowlists, direct `/mcp` routing, optional bearer auth, authenticated public smoke support, and Cloudflare custom-domain documentation.

## Goal

Review the completed phase and close it only if the code, docs, backlog, and verification results support client-ready public MCP access at `https://vocky.example.com/mcp` once external Cloudflare setup is completed.

## Scope

- In scope:
  - Verify focused public access tests.
  - Verify lockfile consistency.
  - Run the broader test suite when the local database is available.
  - Check Makefile public/external verification command expansion.
  - Review docs for stale route/auth/deployment wording.
  - Mark the phase done only if review passes.
- Out of scope:
  - Creating Cloudflare account state or changing registrar nameservers.
  - Live public smoke against `vocky.example.com` before the tunnel and DNS are active.

## Approach

Run automated checks first, then inspect docs and backlog consistency. If a blocking issue appears, add a fix slice instead of closing review.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1456_phase_review_public_custom_domain_mcp_access/plan.md`
- `works/current/20260424_1456_phase_review_public_custom_domain_mcp_access/result.md`

## Reference Docs To Review

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Risks and Open Questions

- Full integration tests require a reachable PostgreSQL instance.
- Public Cloudflare verification remains manual until DNS/tunnel setup is complete.

## Verification Plan

- `uv lock --check`
- `uv run pytest tests/test_public_access.py -q`
- `uv run pytest -q`
- `VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com VOCKY_MCP_AUTH_TOKEN=test make -n tailscale-verify`
- `rg` checks for public settings and stale redirect wording.

## Planned Commits

- `feat(mcp): support public custom-domain access`
