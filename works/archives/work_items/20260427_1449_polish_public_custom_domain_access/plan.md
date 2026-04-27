# Plan

- Work item: works/current/20260427_1449_polish_public_custom_domain_access
- Created at: 20260427_1449
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S3
- Slice: polish public custom-domain access

## Goal

Make public custom-domain verification use generic external-access Make targets keyed by `VOCKY_EXTERNAL_BASE_URL`, while preserving the existing Tailscale target names as compatibility aliases.

## Scope

- Add primary `external-smoke` and `external-verify` Make targets.
- Keep bearer-token behavior unchanged by reusing the existing smoke client and env variables.
- Keep existing `tailscale-*` targets where practical as aliases.
- Update `.env.example` guidance around Cloudflare Tunnel or another HTTPS reverse proxy.

## Context

- Current Makefile has `tailscale-smoke` and `tailscale-verify` targets that already use `VOCKY_EXTERNAL_BASE_URL`.
- P5’s plan calls for generic external/custom-domain targets to become primary.
- External verification should be skipped unless `VOCKY_EXTERNAL_BASE_URL` is configured.

## Milestones

1. Add generic external verification targets and alias the old Tailscale names.
2. Refresh `.env.example` external access comments around custom-domain HTTPS proxy usage.
3. Dry-run or validate external targets without requiring a live public deployment.

## Validation

- `make -n external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`
- `uv run pytest tests/test_public_access.py`

## Risks / open questions

- Do not run a live external smoke unless a real public URL is intentionally configured and reachable.
- Avoid leaking local `.env` secrets in outputs or docs.

## Docs to update

- `.env.example` only in this slice; release-facing docs are scheduled for `P5.S4`.
