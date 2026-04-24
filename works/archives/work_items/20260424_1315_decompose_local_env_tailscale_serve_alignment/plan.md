# Plan

- Work item: works/current/20260424_1315_decompose_local_env_tailscale_serve_alignment
- Created at: 20260424_1315
- Phase ID: P1
- Phase: Align local .env for Tailscale Serve
- Slice ID: P1.DECOMP
- Slice: decompose phase

## Context

- The active backlog was rotated after the last completed phase and is back on the template placeholder.
- The checked-out `.env` is still on the older local shape and is missing the current repo defaults for `REDIS_URL`, `*_PUBLISH_HOST`, and `VOCKY_EXTERNAL_BASE_URL`.
- Local `tailscale status --json` shows this node's MagicDNS name is `node.tailcb4e82.ts.net`, and `tailscale serve status` currently reports no serve config.

## Goal

Create a small tracked phase to align the real local `.env` with the repo's current Tailscale-aware operator surface and the current node's MagicDNS URL.

## Scope

- In scope:
- Replace the placeholder `P1` backlog entry with a concrete phase for local `.env` alignment.
- Add a focused implementation slice to update `.env` and a review slice to verify it.
- Record this decomposition in the work item artifacts.
- Out of scope:
- Runtime code changes, documentation changes, or starting Tailscale Serve itself.

## Approach

Keep the phase minimal: decompose it, update the real `.env` using the current repo defaults plus the detected MagicDNS hostname, then review the resulting config with non-invasive Make and Tailscale checks.

## Affected Files

- `works/backlog.md`
- `works/current/20260424_1315_decompose_local_env_tailscale_serve_alignment/plan.md`
- `works/current/20260424_1315_decompose_local_env_tailscale_serve_alignment/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `.env.example`
- `works/backlog.md`

## Risks and Open Questions

- The user's `.env` is a real local operator file, so this phase should touch only the minimal keys needed to make it fit the current Tailscale Serve workflow.
- `tailscale serve` itself should not be started during decomposition.

## Verification Plan

- Re-read `works/backlog.md` and confirm the phase objective and slices match this local `.env` alignment task.

## Planned Commits

- None.
