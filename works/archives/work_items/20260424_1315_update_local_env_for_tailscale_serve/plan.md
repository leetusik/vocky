# Plan

- Work item: works/current/20260424_1315_update_local_env_for_tailscale_serve
- Created at: 20260424_1315
- Phase ID: P1
- Phase: Align local .env for Tailscale Serve
- Slice ID: P1.S1
- Slice: update local .env for tailscale serve

## Context

- `P1.DECOMP` is complete and archived, so `P1.S1` is now the active slice.
- The local `.env` still uses older `5432` defaults, does not define `REDIS_URL`, and does not expose the current repo's `*_PUBLISH_HOST` or `VOCKY_EXTERNAL_BASE_URL` settings.
- Local `tailscale status --json` reports this node's MagicDNS name as `node.tailcb4e82.ts.net`.

## Goal

Update the checked-out local `.env` so it matches the current repo config surface and is ready for optional `make tailscale-serve`, `make tailscale-smoke`, and `make tailscale-verify`.

## Scope

- In scope:
- Add the missing runtime and host-side env variables to `.env`.
- Align the local ports and publish-host defaults with `.env.example`.
- Set `VOCKY_EXTERNAL_BASE_URL` to this node's MagicDNS HTTPS URL.
- Mark `P1.S1` active in the backlog and record the result in this work item.
- Out of scope:
- Editing `.env.example` or other tracked repo config files.
- Starting or mutating `tailscale serve` state.

## Approach

Bring `.env` up to date with `.env.example`, keep all Docker-published services loopback-only by default, and set the external base URL to `https://node.tailcb4e82.ts.net` so the Tailscale helper targets have a concrete target.

## Affected Files

- `.env`
- `works/backlog.md`
- `works/current/20260424_1315_update_local_env_for_tailscale_serve/plan.md`
- `works/current/20260424_1315_update_local_env_for_tailscale_serve/result.md`

## Reference Docs To Review

- `.env.example`
- `Makefile`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- The local `.env` is intentionally operator-specific, so this slice should avoid unrelated normalization beyond what the current Tailscale-aware workflow needs.
- The chosen external URL assumes the current MagicDNS suffix remains valid for this node.

## Verification Plan

- Inspect the updated `.env` content directly.
- Use `ENV_FILE=.env make -pn` to confirm the Makefile resolves `VOCKY_EXTERNAL_BASE_URL`, `VOCKY_PUBLISH_HOST`, and the updated ports from the real `.env`.
- Check `tailscale serve status` remains unchanged after the `.env` edit.

## Planned Commits

- None.
