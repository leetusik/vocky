# Result

- Work item: works/current/20260424_1016_document_self_hosted_runbook_and_config
- Created at: 20260424_1016
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S2
- Slice: document self-hosted runbook and config
- Review status: passed
- Reviewer: Codex
- Next action: Start `P4.S3` to verify the documented self-hosted flow from a fresh Compose state and record the exact successful commands.

## Summary

Updated the self-hosted runbook and durable configuration notes so the default local path is `cp .env.example .env`, `make bootstrap`, `make verify`, and `make compose-down`, with explicit migration and dedicated test-database guidance.

## Changes Made

- Rewrote the README local development section around the `.env`-driven Compose-first workflow and documented the default published ports, explicit migration step, and granular fallback commands.
- Updated the README to describe port overrides as optional edits to `.env` instead of per-command env prefixes.
- Updated `.env.example` so it explicitly warns that `TEST_DATABASE_URL` must target a separate disposable database and makes `VOCKY_BASE_URL` an optional override instead of a required default setting.
- Updated `docs/architecture.md` to document the root `.env` as the shared local config surface and to describe the supported `make bootstrap` / `make verify` operator flow.
- Marked `P4.S2` active in `works/backlog.md`.

## Files Changed

- `README.md`
- `.env.example`
- `docs/architecture.md`
- `works/backlog.md`
- `works/current/20260424_1016_document_self_hosted_runbook_and_config/plan.md`
- `works/current/20260424_1016_document_self_hosted_runbook_and_config/result.md`

## Verification Performed

- `make -n verify`
- `ENV_FILE=.env.example make -n verify`
- `ENV_FILE=.env.example make -pn | rg '^VOCKY_BASE_URL[[:space:]]*[:?]?='`
- Re-read the updated `README.md`, `.env.example`, and `docs/architecture.md` for consistency with the `P4.S1` Make targets.

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `.env.example`
- `docs/architecture.md`

## Follow-Ups

- Run the documented workflow from a fresh Compose project and volume, then record the exact successful bootstrap, smoke, and pytest commands in `P4.S3`.

## Commit References

- None.
