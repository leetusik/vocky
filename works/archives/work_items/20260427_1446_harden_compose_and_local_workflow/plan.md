# Plan

- Work item: works/current/20260427_1446_harden_compose_and_local_workflow
- Created at: 20260427_1446
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S1
- Slice: harden Compose and local workflow

## Goal

Make the default self-hosted Compose/local workflow reliable and quicker to start by moving container dependency sync to image build time, avoiding runtime sync in app and worker commands, keeping loopback publish defaults, and making bootstrap wait for readiness after migrations.

## Scope

- Update Docker/Compose/Make workflow files needed for local runtime hardening.
- Keep the default publish host behavior loopback-only.
- Preserve the app, worker, Redis, PostgreSQL, migration, smoke, and pytest workflow.
- Do not change Admin UI packaging or public custom-domain docs in this slice except where Make target wiring requires it.

## Context

- P5.DECOMP scheduled this as the first implementation slice.
- Current Compose app and worker commands run `uv sync --frozen` at container startup.
- `make bootstrap` currently stops after `sync`, `compose-up`, and `migrate`, without readiness confirmation.
- The phase plan expects `docker compose config`, `make bootstrap`, and `make smoke` validation for this slice.

## Milestones

1. Move container dependency installation to Docker build time and switch app/worker runtime commands to `uv run --no-sync`.
2. Update `make bootstrap` so it finishes only after the service reports ready.
3. Run focused workflow validation and mark `P5.S1` complete.

## Validation

- `docker compose config --quiet`
- `make bootstrap`
- `make smoke`

## Risks / open questions

- Local Docker may already have running services or occupied ports; preserve existing user-owned configuration and report any local environment blockers.
- `make bootstrap` may be slower because it rebuilds the image after Dockerfile changes.

## Docs to update

- None planned for this slice.
