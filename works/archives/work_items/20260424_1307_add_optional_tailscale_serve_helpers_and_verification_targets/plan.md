# Plan

- Work item: works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets
- Created at: 20260424_1307
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S3
- Slice: add optional tailscale serve helpers and separate verification targets

## Context

- `P1.S1` and `P1.S2` are complete, so the env surface and Compose host publishing now support explicit local versus external access concerns.
- The current `Makefile` still only offers the local `smoke` and `verify` path, and it has no operator helper targets for `tailscale serve` or for running smoke checks against `VOCKY_EXTERNAL_BASE_URL`.
- The phase plan requires Tailscale to remain optional and must not make `bootstrap` or the main `verify` path depend on it.

## Goal

Add a distinct, optional Tailscale operator workflow on top of the existing local workflow, without changing the default local verification path.

## Scope

- In scope:
- Add `tailscale-serve`, `tailscale-serve-status`, and `tailscale-serve-reset` Make targets.
- Add `tailscale-smoke` and `tailscale-verify` Make targets that require `VOCKY_EXTERNAL_BASE_URL` and run the existing smoke flow against that URL.
- Keep `bootstrap` and the main local `verify` target unchanged.
- Mark `P1.S3` active in the backlog and record the slice result in this work item.
- Out of scope:
- Documentation rewrites and operator guidance, which belong to `P1.S4`.
- Any application runtime changes or MCP contract changes.

## Approach

Factor the existing smoke command into a reusable internal target, add a small guard target that fails clearly when `VOCKY_EXTERNAL_BASE_URL` is unset, and wire the new Tailscale targets around environment overrides so the external path reuses the existing health-check and MCP smoke logic.

## Affected Files

- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets/plan.md`
- `works/current/20260424_1307_add_optional_tailscale_serve_helpers_and_verification_targets/result.md`

## Reference Docs To Review

- `.env.example`
- `README.md`
- `docs/architecture.md`
- `scripts/wait_for_health.py`
- `src/vocky/smoke.py`
- `works/backlog.md`

## Risks and Open Questions

- The new external targets must fail fast and clearly when `VOCKY_EXTERNAL_BASE_URL` is missing.
- The local `verify` flow must remain unchanged so non-Tailscale self-hosters keep the current portable path.
- Recursive `make` calls need to preserve the intended base URL overrides without accidentally exporting the wrong target URL back into the local workflow.

## Verification Plan

- Use `make -n` to confirm the new Tailscale targets expand to the expected commands and do not alter the existing `bootstrap` or `verify` paths.
- Run the missing-variable guard to confirm `tailscale-smoke` fails clearly without `VOCKY_EXTERNAL_BASE_URL`.

## Planned Commits

- None.
