# Plan

- Work item: works/current/20260424_1013_align_compose_first_operator_workflow
- Created at: 20260424_1013
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S1
- Slice: align compose-first operator workflow

## Context

- `P4.DECOMP` is complete and `P4.S1` is now the next non-done slice in the active phase.
- The current `Makefile` assumes callers inject env vars ad hoc, so `uv run alembic`, `uv run pytest`, and `uv run vocky-smoke` do not consistently follow the copied root `.env` that Compose already uses.
- The README’s supported flow currently relies on custom port overrides and `APP_BASE_URL`, while the smoke script actually reads `VOCKY_BASE_URL`.

## Goal

Make the supported local operator workflow consistently use the copied root `.env`, add happy-path helpers for bootstrap and verification, and ensure the smoke flow waits for app readiness instead of racing startup.

## Scope

- In scope:
- Update `Makefile` so the supported local commands read the root `.env` for `DATABASE_URL`, `TEST_DATABASE_URL`, `VOCKY_PORT`, `VOCKY_BASE_URL`, and Compose settings.
- Keep the granular workflow targets (`sync`, `compose-up`, `compose-down`, `compose-logs`, `migrate`, `smoke`, `test`) and add stable helper targets for `bootstrap`, `verify`, and readiness waiting.
- Mark `P4.S1` active in `works/backlog.md` and record the result in this work item.
- Out of scope:
- README or durable-doc wording changes beyond what is strictly necessary for the Makefile itself.
- New runtime behavior in the application process or automatic migrations on app startup.
- Phase-level fresh-install verification, which belongs to `P4.S3`.

## Approach

Teach `make` to include the root `.env` when present, derive the base URL from the configured port, add an explicit readiness helper that polls `/healthz`, and compose the supported happy paths as `bootstrap = sync + compose-up + migrate` and `verify = wait-ready + smoke + test`.

## Affected Files

- `Makefile`
- `works/backlog.md`
- `works/current/20260424_1013_align_compose_first_operator_workflow/plan.md`
- `works/current/20260424_1013_align_compose_first_operator_workflow/result.md`

## Reference Docs To Review

- `README.md`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- GNU Make include/export behavior needs to remain simple and portable enough for the local workflow.
- The readiness wait must fail clearly when the app never becomes healthy, rather than hiding real startup errors.
- `make test` must keep honoring a separate `TEST_DATABASE_URL` and must not silently collapse onto `DATABASE_URL`.

## Verification Plan

- Run targeted dry verification of the Makefile changes with a copied `.env`, including `make wait-ready`, `make smoke`, and `make test` in the updated flow.
- Use `make -n` where useful to confirm env-backed command expansion without mutating the stack.

## Planned Commits

- None.
