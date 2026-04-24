# Plan

- Work item: works/current/20260424_1018_verify_fresh_self_hosted_flow
- Created at: 20260424_1018
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S3
- Slice: verify fresh self-hosted flow

## Context

- `P4.S1` and `P4.S2` aligned the Make workflow, README, `.env.example`, and durable local-operator notes around the copied root `.env`.
- This slice must validate the documented flow from a fresh Compose project and fresh volume, then record the exact successful commands used for bootstrap, smoke, and pytest.
- The current workstation already has an unrelated PostgreSQL container publishing host port `5432`, so verifying the repo’s default host-port choices must avoid interfering with external projects.

## Goal

Prove the documented self-hosted workflow from a clean Compose state, confirm the happy path and granular fallback path work, and record exact successful commands with enough context to make the verification reproducible.

## Scope

- In scope:
- Run the documented Compose-first flow from a clean project state and fresh volume using a disposable verification environment.
- Confirm `make bootstrap`, `make smoke`, `make test`, `make verify`, and `make compose-down` work as intended without startup races.
- Confirm the test workflow still targets a dedicated disposable database instead of the primary app database.
- Make any minimal verification-driven adjustments required to keep the documented default flow viable without interfering with unrelated local services.
- Update `works/backlog.md` for `P4.S3` and capture the results here.
- Out of scope:
- New MCP behavior, schema changes, or automatic startup migrations.
- Final phase review, which belongs to `P4.REVIEW`.

## Approach

Use a temporary clean checkout for verification so the repo can be exercised from `cp .env.example .env` without mutating the user’s existing local `.env`. If the current default host-port choices block clean verification or drift from the repo’s own test defaults, make the smallest repo-level adjustment needed, then rerun the fresh-state validation and record the exact successful commands.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1018_verify_fresh_self_hosted_flow/plan.md`
- `works/current/20260424_1018_verify_fresh_self_hosted_flow/result.md`
- Additional repo files only if verification uncovers necessary workflow or documentation drift.

## Reference Docs To Review

- `README.md`
- `.env.example`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- A clean verification run needs isolation from unrelated local Docker projects and host-port collisions.
- If verification forces a repo-default port change, the docs and config surface must stay consistent with that change.
- The exact successful commands should be recorded in their final working form, not the earlier failing attempts.

## Verification Plan

- Check host-port availability relevant to the documented defaults.
- Run the documented happy path from a temporary clean checkout and fresh Compose volume.
- Run the granular fallback path and confirm `make smoke` no longer races startup.
- Reconfirm the test-database isolation behavior through the successful `make test` path.

## Planned Commits

- None.
