# Plan

- Work item: works/current/20260424_1305_lock_generic_env_surface_and_access_model
- Created at: 20260424_1305
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S1
- Slice: lock generic env surface and self-host access model

## Context

- `P1.DECOMP` is complete and archived, so `P1.S1` is now the next active slice.
- The current operator surface still mixes local smoke configuration with an old undocumented `APP_BASE_URL` alias and does not expose publish-host controls or an explicit external base URL for remote access.
- The user-provided phase plan defines the env contract that later Compose, Make, and documentation slices must implement consistently.

## Goal

Lock the operator-facing environment variable model so local bind behavior, Docker host publishing, and optional external access each have a clear and stable responsibility.

## Scope

- In scope:
- Update `.env.example` to define the new `*_PUBLISH_HOST` variables and the optional `VOCKY_EXTERNAL_BASE_URL`.
- Update `Makefile` variable defaults and exported env handling so the new env surface is first-class and the legacy `APP_BASE_URL` alias is removed.
- Mark `P1.S1` active in the backlog and record the slice result in this work item.
- Out of scope:
- Docker Compose port mapping changes, which belong to `P1.S2`.
- New Tailscale helper targets, which belong to `P1.S3`.
- Broad documentation rewrites, which belong to `P1.S4`.

## Approach

Separate the env contract into three concerns: process bind settings (`VOCKY_HOST`, `VOCKY_PORT`), host exposure controls (`*_PUBLISH_HOST` plus ports), and external verification or access (`VOCKY_EXTERNAL_BASE_URL`). Reflect that contract in the example env file and the Makefile export surface so later slices can consume it consistently.

## Affected Files

- `.env.example`
- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1305_lock_generic_env_surface_and_access_model/plan.md`
- `works/current/20260424_1305_lock_generic_env_surface_and_access_model/result.md`

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- The repo already has a `VOCKY_BASE_URL` local verification path, so the new external URL variable must not replace or confuse that default path.
- Removing `APP_BASE_URL` should not break any documented or supported workflow because it is currently just an internal compatibility alias.

## Verification Plan

- Inspect the updated `.env.example` and `Makefile` to confirm the new env variables exist with the expected defaults and exports.
- Use `make -pn` against `.env.example` where helpful to confirm `VOCKY_BASE_URL` still defaults locally and `VOCKY_EXTERNAL_BASE_URL` is surfaced separately.

## Planned Commits

- None.
