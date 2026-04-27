# Plan

- Work item: works/current/20260427_1456_review_self_hosted_packaging_polish_rerun
- Created at: 20260427_1456
- Phase ID: P5
- Phase: Self-hosted packaging and polish
- Slice ID: P5.REVIEW
- Slice: phase review

## Goal

Rerun the P5 phase review after `P5.F1` and close the phase only if all local and dry-run external verification gates pass.

## Scope

- Re-run the review checks that failed previously.
- Confirm no new scope or docs regressions were introduced by `P5.F1`.
- If the gate passes, mark P5 done, archive this work item, and rotate the completed backlog.

## Context

- The first P5 review found blank `VOCKY_HTTP_USER_AGENT` handling broke `make verify`.
- `P5.F1` normalized blank smoke/readiness user-agent values to the default.

## Milestones

1. Run Compose config validation.
2. Run full `make verify`.
3. Dry-run external verification target and close/rotate if all pass.

## Validation

- `docker compose config --quiet`
- `make verify`
- `make -n external-verify VOCKY_EXTERNAL_BASE_URL=https://vocky.example.com`

## Risks / open questions

- Live external verification remains skipped unless a real public origin is intentionally configured.

## Docs to update

- None planned.
