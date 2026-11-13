# Plan

- Work item: works/current/20260424_1306_make_compose_host_exposure_env_driven
- Created at: 20260424_1306
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S2
- Slice: make compose host exposure env-driven

## Context

- `P1.S1` is complete, so the env surface now exposes `VOCKY_PUBLISH_HOST`, `POSTGRES_PUBLISH_HOST`, `REDIS_PUBLISH_HOST`, and `VOCKY_EXTERNAL_BASE_URL`.
- `docker-compose.yml` still publishes ports using only the port numbers, so the new publish-host variables do not affect actual host exposure yet.
- The phase plan requires local verification to remain portable while Docker host publishing becomes explicitly loopback-by-default.

## Goal

Make Docker Compose publish the app, PostgreSQL, and Redis ports on configurable host interfaces without changing the app's internal bind address.

## Scope

- In scope:
- Update `docker-compose.yml` port mappings for `app`, `postgres`, and `redis` to use the new `*_PUBLISH_HOST` variables.
- Preserve the in-container app bind address at `0.0.0.0` and keep the existing port defaults.
- Mark `P1.S2` active in the backlog and record the slice result in this work item.
- Out of scope:
- New Tailscale helper targets and external verification commands, which belong to `P1.S3`.
- Operator-facing documentation rewrites, which belong to `P1.S4`.

## Approach

Use Docker's `HOST:PORT:CONTAINER_PORT` mapping form so the host interface and port are independently configurable from `.env`, while the container environment continues to bind the app process to `0.0.0.0`.

## Affected Files

- `docker-compose.yml`
- `works/backlog.md`
- `works/current/20260424_1306_make_compose_host_exposure_env_driven/plan.md`
- `works/current/20260424_1306_make_compose_host_exposure_env_driven/result.md`

## Reference Docs To Review

- `.env.example`
- `README.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- Compose interpolation must keep the existing published ports while changing only the host interface defaults.
- `VOCKY_HOST` must remain an application-process setting, not become overloaded as the Docker host publish interface.

## Verification Plan

- Run `docker compose config` with the default `.env.example` surface and confirm the rendered port mappings use `127.0.0.1`.
- Re-run `docker compose config` with overridden `*_PUBLISH_HOST` values to confirm each service reflects the configured host interface independently.

## Planned Commits

- None.
