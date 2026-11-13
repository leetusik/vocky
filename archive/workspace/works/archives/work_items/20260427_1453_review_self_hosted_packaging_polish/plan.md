# Plan

- Work item: works/current/20260427_1453_review_self_hosted_packaging_polish
- Created at: 20260427_1453
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.REVIEW
- Slice: phase review

## Goal

Review P5 end to end and close the phase only if Compose/local workflow hardening, packaged Admin UI asset verification, external custom-domain polish, release docs, and verification gates pass.

## Scope

- Inspect final changes for regressions or missed P5 requirements.
- Run phase verification commands.
- Add `P5.F*` fix slices if review finds blocking issues, then rerun review.
- If review passes, mark P5 done, archive this work item, and rotate the completed backlog.

## Context

- P5.S1 through P5.S4 are archived as done.
- `make verify` now includes `package-check`, smoke, and tests.
- Live external verification requires an intentional `VOCKY_EXTERNAL_BASE_URL`; otherwise it should be dry-run/skipped.

## Milestones

1. Inspect git diff and backlog/work-item state.
2. Run full local verification plus external target dry-run.
3. Record review result, mark phase done or add fix slices.

## Validation

- `docker compose config --quiet`
- `make verify`
- `make -n external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`

## Risks / open questions

- Full verification depends on the local Compose PostgreSQL and Redis services.
- Do not rotate the backlog unless every active phase and slice is done.

## Docs to update

- None planned unless review finds documentation issues.
