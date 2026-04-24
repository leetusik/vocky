# Plan

- Work item: works/current/20260424_1308_document_generic_self_host_and_tailscale_usage
- Created at: 20260424_1308
- Phase ID: P1
- Phase: Generic self-host access
- Slice ID: P1.S4
- Slice: document generic self-host and tailscale usage

## Context

- `P1.S1` through `P1.S3` are complete, so the env surface, Compose publishing, and optional Tailscale helper targets are now implemented.
- The current README and architecture docs still describe only the local workflow and do not explain the new publish-host controls or the separate `VOCKY_EXTERNAL_BASE_URL` path for remote access.
- The phase plan explicitly requires generic operator guidance that never hardcodes one node or one raw Tailscale IP as the repo's answer.

## Goal

Document the new self-hosting model clearly for both local-only operators and Tailscale users, using generic placeholders and making the local verification path versus external access path explicit.

## Scope

- In scope:
- Update `README.md` to describe the `.env` surface, local-only defaults, optional publish-host overrides, and the new Tailscale Serve helper commands.
- Update `docs/architecture.md` to record the expanded configuration surface and the two supported operator modes.
- Keep the documentation generic and explain MagicDNS as the recommended Tailscale external URL shape.
- Mark `P1.S4` active in the backlog and record the slice result in this work item.
- Out of scope:
- MCP contract changes or `docs/api.md` updates, since the public tool surface is unchanged.
- New runtime behavior beyond what was already implemented in earlier slices.

## Approach

Refresh the product-facing README around two operator modes: local or private self-hosting on loopback by default, and optional Tailscale-backed remote access using `VOCKY_EXTERNAL_BASE_URL` plus the new helper targets. Mirror the durable config and workflow truth in `docs/architecture.md`.

## Affected Files

- `README.md`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1308_document_generic_self_host_and_tailscale_usage/plan.md`
- `works/current/20260424_1308_document_generic_self_host_and_tailscale_usage/result.md`

## Reference Docs To Review

- `.env.example`
- `Makefile`
- `docker-compose.yml`
- `README.md`
- `docs/architecture.md`
- `docs/api.md`
- `works/backlog.md`

## Risks and Open Questions

- The README must stay operator-friendly without duplicating every technical detail from `docs/architecture.md`.
- The Tailscale guidance needs to recommend MagicDNS hostnames over raw Tailscale IPs while staying generic for any self-hoster.

## Verification Plan

- Re-read the updated README and architecture docs to confirm they describe both local-only and optional Tailscale operator modes and reference the implemented env variables and Make targets accurately.
- Search the repo for hardcoded node-specific Tailscale values or raw Tailscale IPs to confirm none were introduced.

## Planned Commits

- None.
