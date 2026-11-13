# Result

- Work item: works/current/20260424_1306_make_compose_host_exposure_env_driven
- Created at: 20260424_1306
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S2
- Slice: make compose host exposure env-driven
- Review status: passed
- Reviewer: Codex
- Next action: Start `P1.S3` to add optional Tailscale serve and external verification helpers on top of the new env surface.

## Summary

Moved Docker host publishing for the app, PostgreSQL, and Redis onto explicit publish-host environment variables while keeping the in-container runtime unchanged.

## Changes Made

- Updated the `app`, `postgres`, and `redis` Compose port mappings to use `${*_PUBLISH_HOST}:${PORT}:${CONTAINER_PORT}` with loopback defaults.
- Preserved the existing default published ports and left the app container bound to `0.0.0.0` through its internal environment.
- Marked `P1.S2` active in the backlog while this slice was in progress.

## Files Changed

- `docker-compose.yml`
- `works/backlog.md`
- `works/current/20260424_1306_make_compose_host_exposure_env_driven/plan.md`
- `works/current/20260424_1306_make_compose_host_exposure_env_driven/result.md`

## Verification Performed

- `docker compose --env-file .env.example config | rg -n 'published:|host_ip:|target:'`
- `VOCKY_PUBLISH_HOST=0.0.0.0 POSTGRES_PUBLISH_HOST=10.0.0.5 REDIS_PUBLISH_HOST=192.168.1.9 docker compose --env-file .env.example config | rg -n 'published:|host_ip:|target:'`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- None.

## Follow-Ups

- Add operator-facing Make targets for Tailscale Serve status, reset, smoke, and verify flows that use `VOCKY_EXTERNAL_BASE_URL`.

## Commit References

- None.
