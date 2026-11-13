# Result

- Work item: works/current/20260424_1305_lock_generic_env_surface_and_access_model
- Created at: 20260424_1305
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S1
- Slice: lock generic env surface and self-host access model
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.S2` to move Docker host publishing onto the new `*_PUBLISH_HOST` variables.

## Summary

Locked the operator env surface around three separate concerns: process bind settings, Docker host publish addresses, and optional external access URLs.

## Changes Made

- Added `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, and `REDIS_PUBLISH_HOST` to `.env.example` with loopback defaults so host exposure is now explicit instead of implied.
- Added the optional `VOCKY_EXTERNAL_BASE_URL` example entry for remote access through Tailscale Serve or another reverse proxy.
- Removed the undocumented `APP_BASE_URL` compatibility alias from `Makefile` and exported the new env variables so later slices can consume them consistently.
- Marked `P1.S1` active in the backlog while this slice was in progress.

## Files Changed

- `.env.example`
- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1305_lock_generic_env_surface_and_access_model/plan.md`
- `works/current/20260424_1305_lock_generic_env_surface_and_access_model/result.md`

## Verification Performed

- `ENV_FILE=.env.example make -pn | rg '^(VOCKY_BASE_URL|VOCKY_EXTERNAL_BASE_URL|VOCKY_PUBLISH_HOST|POSTGRES_PUBLISH_HOST|REDIS_PUBLISH_HOST)[[:space:]]*[:?]?='`
- `rg -n "APP_BASE_URL" Makefile .env.example README.md docs src tests`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Update `docker-compose.yml` so the new publish-host variables actually control host exposure.

## Commit References

- None.
