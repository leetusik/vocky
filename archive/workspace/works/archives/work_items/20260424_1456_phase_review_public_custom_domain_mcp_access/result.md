# Result

- Work item: works/current/20260424_1456_phase_review_public_custom_domain_mcp_access
- Created at: 20260424_1456
- Phase ID: P1
- Phase: Public custom-domain MCP access
- Slice ID: P1.REVIEW
- Slice: phase review
- Review status: passed
- Reviewer: self
- Next action: Archive the review work item and rotate the completed backlog cycle.

## Summary

Reviewed the completed public custom-domain MCP access phase. The implementation passes focused and full tests, the lockfile is consistent, public Make verification expands to `https://vocky.example.com` when provided as a Make variable, and docs cover the Cloudflare/registrar setup plus authenticated client usage.

## Changes Made

- Confirmed no fix slices are required.
- Removed an unrelated FastMCP `log_level` coupling found during review to avoid changing existing lowercase log-level behavior.

## Files Changed

- `src/vocky/mcp_server.py`
- `works/backlog.md`
- `works/current/20260424_1456_phase_review_public_custom_domain_mcp_access/plan.md`
- `works/current/20260424_1456_phase_review_public_custom_domain_mcp_access/result.md`

## Verification Performed

- `uv lock --check`
- `uv run pytest tests/test_public_access.py -q`
- `uv run pytest -q`
- `git diff --check`
- `make -n tailscale-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com VOCKY_MCP_AUTH_TOKEN=test`
- `rg -n "Some clients may follow|Host.: 127.0.0.1|VOCKY_MCP_AUTH_TOKEN|VOCKY_MCP_ALLOWED_HOSTS|vocky.example.com|/mcp/" README.md docs/product.md docs/architecture.md docs/api.md .env.example Makefile docker-compose.yml src tests`

## Review Findings

- The phase passes review.
- A shell-prefixed `VOCKY_EXTERNAL_BASE_URL=... make ...` can be overridden by the included `.env`; use `make ... VOCKY_EXTERNAL_BASE_URL=...` for one-off overrides, or set `.env` directly.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`

## Follow-Ups

- Complete the external Cloudflare and registrar setup outside the repo, then run `make tailscale-verify` with `VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`.

## Commit References

- Pending.
