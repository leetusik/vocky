# Result

- Work item: works/current/20260424_1308_document_generic_self_host_and_tailscale_usage
- Created at: 20260424_1308
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S4
- Slice: document generic self-host and tailscale usage
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.REVIEW` to verify the phase end to end and close it if no fix slices are needed.

## Summary

Updated the operator docs so local-only self-hosting and optional Tailscale access are both documented against the implemented env and Make surface.

## Changes Made

- Updated `README.md` to explain the new publish-host variables, the difference between `VOCKY_BASE_URL` and `VOCKY_EXTERNAL_BASE_URL`, and the optional Tailscale helper targets.
- Added a dedicated README section for local or private self-hosting versus optional Tailscale self-hosting, using generic MagicDNS placeholders instead of any node-specific values.
- Updated `docs/architecture.md` to record the expanded configuration surface and the two supported operator modes.
- Marked `P1.S4` active in the backlog while this slice was in progress.

## Files Changed

- `README.md`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1308_document_generic_self_host_and_tailscale_usage/plan.md`
- `works/current/20260424_1308_document_generic_self_host_and_tailscale_usage/result.md`

## Verification Performed

- `rg -n "tailscale|MagicDNS|VOCKY_EXTERNAL_BASE_URL|PUBLISH_HOST|100\\.71\\.247\\.59|<tailnet>|ts\\.net" README.md docs/architecture.md .env.example Makefile docker-compose.yml`
- Re-read the updated README and architecture sections to confirm the local-only and optional Tailscale paths match the implemented env and Make targets.

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `docs/architecture.md`

## Follow-Ups

- Run the explicit phase review and confirm the local verify path, Compose config rendering, and optional Tailscale target surface all pass.

## Commit References

- None.
