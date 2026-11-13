# Result

- Work item: works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets
- Created at: 20260424_1307
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S3
- Slice: add optional tailscale serve helpers and separate verification targets
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.S4` to document the generic local-only and optional Tailscale operator paths.

## Summary

Added an optional Tailscale operator workflow that reuses the existing health and smoke logic against an externally reachable base URL while leaving the default local path unchanged.

## Changes Made

- Added `tailscale-serve`, `tailscale-serve-status`, and `tailscale-serve-reset` Make targets for operators using Tailscale Serve.
- Factored the existing smoke command into `smoke-run` so both local and external checks reuse the same MCP smoke implementation.
- Added `tailscale-smoke` and `tailscale-verify` targets that require `VOCKY_EXTERNAL_BASE_URL` and run the external health plus smoke flow against that URL.
- Kept `bootstrap` and the main `verify` target unchanged for non-Tailscale self-hosters.
- Marked `P1.S3` active in the backlog while this slice was in progress.

## Files Changed

- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets/plan.md`
- `works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets/result.md`

## Verification Performed

- `make -n verify tailscale-serve tailscale-serve-status tailscale-serve-reset tailscale-smoke tailscale-verify`
- `VOCKY_EXTERNAL_BASE_URL= make tailscale-smoke`
- `VOCKY_EXTERNAL_BASE_URL=https://node.example.ts.net make -n tailscale-smoke tailscale-verify`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Update the README and architecture docs so local-only self-hosting and optional Tailscale access are both documented clearly with the new env and Make surface.

## Commit References

- None.
