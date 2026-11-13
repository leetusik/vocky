# Plan

- Work item: works/current/20260424_1016_document_self_hosted_runbook_and_config
- Created at: 20260424_1016
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S2
- Slice: document self-hosted runbook and config

## Context

- `P4.S1` aligned the Make-based operator workflow around the copied root `.env`, added `bootstrap` and `verify`, and made `make smoke` wait for readiness.
- The README still presents custom port overrides as the default path and uses the outdated `APP_BASE_URL` environment variable in its smoke instructions.
- `docs/architecture.md` does not yet describe the root `.env` as the primary local config source or document the dedicated `TEST_DATABASE_URL` requirement for pytest.

## Goal

Update the self-hosted runbook and durable config notes so the default flow is `.env`-driven and Compose-first on the standard local ports, with explicit migration and test-database guidance.

## Scope

- In scope:
- Update `README.md` to present `cp .env.example .env`, `make bootstrap`, `make verify`, and `make compose-down` as the supported happy path.
- Update `README.md` so port overrides are optional edits to `.env`, the migration step is explicit, and the granular fallback commands still exist.
- Update `.env.example` and `docs/architecture.md` as needed to clarify the local config surface, optional `VOCKY_BASE_URL` override, and the requirement that `TEST_DATABASE_URL` target a separate disposable database.
- Mark `P4.S2` active in `works/backlog.md` and record the result here.
- Out of scope:
- Fresh-install execution evidence, which belongs to `P4.S3`.
- Any MCP contract or database-schema changes.
- Automatic app-startup migrations or non-Compose-first workflow redesign.

## Approach

Rewrite the README local setup into a clear self-hosted quick-start and fallback section, update the durable architecture notes for the `.env`-driven local workflow, and adjust `.env.example` comments so the copied config file itself warns about the dedicated test database and optional base-URL override.

## Affected Files

- `README.md`
- `.env.example`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1016_document_self_hosted_runbook_and_config/plan.md`
- `works/current/20260424_1016_document_self_hosted_runbook_and_config/result.md`

## Reference Docs To Review

- `README.md`
- `.env.example`
- `docs/architecture.md`
- `works/backlog.md`

## Risks and Open Questions

- The runbook needs to stay honest about the explicit migration step even though `make bootstrap` wraps it.
- The README should distinguish the supported Make-based operator flow from the secondary direct-process flow.
- `.env.example` should clarify optional overrides without reintroducing config drift between `VOCKY_PORT` and the base URL used by smoke checks.

## Verification Plan

- Re-read the updated README and architecture notes for consistency with the Make targets added in `P4.S1`.
- Dry-run the documented fallback commands where helpful and confirm `.env.example` parses cleanly as a Make include file.

## Planned Commits

- None.
