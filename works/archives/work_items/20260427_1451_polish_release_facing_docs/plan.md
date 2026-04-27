# Plan

- Work item: works/current/20260427_1451_polish_release_facing_docs
- Created at: 20260427_1451
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S4
- Slice: polish release-facing docs

## Goal

Align release-facing documentation around the current self-hosted setup, Admin UI workflows, packaged asset verification, local/full verification commands, and public custom-domain access.

## Scope

- Update `README.md`.
- Update durable reference docs under `docs/` where the self-hosted workflow or API/static boundary needs clearer current-state wording.
- Update packaged in-app docs JSON under `src/vocky/admin_assets/docs.json`.
- Do not edit ignored local/private runbooks such as `docs/local-public-access.md`.

## Context

- P5.S1 added build-time container sync and bootstrap readiness confirmation.
- P5.S2 added `make package-check` and included it in `make verify`.
- P5.S3 added generic `external-smoke` and `external-verify` targets with Tailscale aliases.
- Existing docs mostly describe the right surfaces, but they still need the final verification and external-target wording.

## Milestones

1. Refresh README local development, access mode, Cloudflare, and verification wording.
2. Refresh durable docs for packaging/verification and public access guidance.
3. Refresh in-app docs JSON so operators see the current commands.

## Validation

- `uv run python -m json.tool src/vocky/admin_assets/docs.json >/dev/null`
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py`

## Risks / open questions

- Keep docs generic and avoid copying local secrets or ignored runbook details.
- Avoid documenting non-contractual internals in `docs/api.md` unless they affect consumers.

## Docs to update

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md` if consumer-facing Admin/static boundary wording needs a small update
- `src/vocky/admin_assets/docs.json`
