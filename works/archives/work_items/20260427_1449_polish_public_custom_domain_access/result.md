# Result

- Work item: works/current/20260427_1449_polish_public_custom_domain_access
- Created at: 20260427_1449
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S3
- Slice: polish public custom-domain access
- Review status: not reviewed
- Reviewer: n/a
- Next action: Start `P5.S4` with `scripts/start_work.sh P5 P5.S4 polish_release_facing_docs`.

## Outcome

Added primary `external-smoke` and `external-verify` Make targets driven by `VOCKY_EXTERNAL_BASE_URL`. Kept `tailscale-smoke` and `tailscale-verify` as compatibility aliases that route through the generic external targets. Refreshed `.env.example` comments so Cloudflare Tunnel or another HTTPS reverse proxy is the primary public custom-domain path, with Tailscale Serve still documented as supported through aliases.

## Deviations from plan

None.

## Validation run

- `make -n external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`
- `make -n tailscale-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`
- `uv run pytest tests/test_public_access.py`
- Live `make external-verify` skipped because this run did not configure an intentional reachable `VOCKY_EXTERNAL_BASE_URL`.

## Files changed

- `.env.example`
- `Makefile`
- `works/backlog.md`
- `works/current/20260427_1449_polish_public_custom_domain_access/plan.md`
- `works/current/20260427_1449_polish_public_custom_domain_access/result.md`

## Docs updated

- `.env.example` external-access guidance.

## Roadmap updates

- `P5.S3` moved to `done`.

## Retrospective

- Generic external verification is now the primary public-access workflow, while existing Tailscale commands remain available for users who already rely on them.
