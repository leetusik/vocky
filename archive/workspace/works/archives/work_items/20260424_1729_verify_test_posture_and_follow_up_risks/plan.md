# Plan

- Work item: works/current/20260424_1729_verify_test_posture_and_follow_up_risks
- Created at: 20260424_1729
- Phase ID: P1
- Phase: Review fast-built feedback MCP/Admin backlog
- Slice ID: P1.S4
- Slice: verify test posture and follow-up risks

## Context

P1 reviews the fast-built feedback MCP/Admin work. P1.S2 and P1.S3 found no required MCP or Admin REST contract corrections. P1.S4 verifies the overall test posture and remaining operational risks before the required backlog snapshot fix and phase review.

## Goal

Run the required baseline verification, inspect test coverage and operational risk coverage at a practical level, and decide whether any additional fix slices are needed before `P1.REVIEW`.

## Scope

- In scope:
  - Full pytest baseline.
  - Existing tests by behavior area.
  - Operational risk coverage for queueing, worker persistence, auth, public access, migrations, MCP contracts, Admin REST contracts, and smoke flow.
  - Backlog/work-item updates for this verification slice.
- Out of scope:
  - Adding new feature coverage unless a required gap is found.
  - Repeating detailed MCP/Admin contract audits already completed in P1.S2 and P1.S3.
  - Implementing optional hardening outside the reviewed MVP contract.

## Approach

1. Run `uv run pytest -q`.
2. Inspect the test suite organization and compare covered behavior against the documented architecture/API risks.
3. Check whether any remaining risk is actionable enough to require a `P1.F2+` fix slice before phase review.
4. Record verification results and follow-up decision in `result.md`.

## Affected Files

- `tests/`
- `pyproject.toml`
- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1729_verify_test_posture_and_follow_up_risks/plan.md`
- `works/current/20260424_1729_verify_test_posture_and_follow_up_risks/result.md`

## Reference Docs To Review

- `docs/product.md`
- `docs/architecture.md`
- `docs/api.md`
- `README.md`

## Risks and Open Questions

- Tests may pass while leaving known operational gaps; record residual risk explicitly.
- If the full baseline fails, add a targeted fix slice instead of masking the failure in this audit.
- The phase already has mandatory `P1.F1`; only add more fix slices for required corrections.

## Verification Plan

- Run `uv run pytest -q`.
- Inspect test files and major assertions by behavior area.
- Record whether P1.F2+ slices are needed.

## Planned Commits

- None planned for this verification slice unless the user later asks for a commit.
