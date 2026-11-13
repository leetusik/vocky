# Result

- Work item: works/current/20260427_1451_polish_release_facing_docs
- Created at: 20260427_1451
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.S4
- Slice: polish release-facing docs
- Review status: not reviewed
- Reviewer: n/a
- Next action: Start `P5.REVIEW` with `scripts/start_work.sh P5 P5.REVIEW review_self_hosted_packaging_polish`.

## Outcome

Aligned README, durable docs, and packaged in-app operator docs around the current Compose-first self-hosted workflow, Admin UI static/API boundaries, `make package-check`, `make verify`, and generic public custom-domain verification through `external-smoke` and `external-verify`.

## Deviations from plan

None.

## Validation run

- `uv run python -m json.tool src/vocky/admin_assets/docs.json >/dev/null`
- `uv run pytest tests/test_admin_ui.py tests/test_public_access.py`
- `make package-check`

## Files changed

- `README.md`
- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `src/vocky/admin_assets/docs.json`
- `tests/test_admin_ui.py`
- `works/backlog.md`
- `works/current/20260427_1451_polish_release_facing_docs/plan.md`
- `works/current/20260427_1451_polish_release_facing_docs/result.md`

## Docs updated

- README local development, access modes, Cloudflare/public custom-domain verification, and reverse proxy guidance.
- Product direction for verifiable self-hosted release workflow.
- Architecture runtime and workflow notes for build-time container sync, package checks, bootstrap readiness, and external verification.
- API Admin REST notes for the static Admin UI versus protected Admin REST boundary.
- Packaged Admin UI operator docs.

## Roadmap updates

- `P5.S4` moved to `done`.

## Retrospective

- Public docs and in-app docs now point operators at the same verification commands the repository actually runs.
