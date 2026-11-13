# Result

- Work item: works/current/20260424_1018_verify_fresh_self_hosted_flow
- Created at: 20260424_1018
- Phase ID: P4
- Phase: Harden the self-hosted MVP
- Slice ID: P4.S3
- Slice: verify fresh self-hosted flow
- Review status: passed
- Reviewer: Codex
- Next action: Start `P4.REVIEW` to check backlog, Make targets, `.env` behavior, README instructions, and the recorded fresh-install evidence for drift.

## Summary

Verified the documented self-hosted workflow from a temporary clean checkout and fresh Compose volumes, confirmed both the happy path and granular fallback path work, and made one verification-driven config adjustment by moving the default published PostgreSQL host port in `.env.example` to `55432` to avoid collisions with common local Postgres stacks and to align with the existing pytest default.

## Changes Made

- Created a temporary clean verification checkout from the current repo, copied `.env.example` to `.env`, and ran the documented Compose-first workflow against disposable Compose project names and fresh volumes.
- Confirmed `make bootstrap`, `make verify`, `make compose-up`, `make migrate`, `make smoke`, `make test`, and `make compose-down` all succeed in that clean environment.
- Confirmed the supported smoke flow no longer races startup because `make smoke` waits for `/healthz` before running the MCP smoke script.
- Confirmed the test workflow still requires a dedicated test database by triggering the `check-test-db` guard with Make command-line overrides.
- Updated `.env.example` and `README.md` so the default published PostgreSQL host port is `55432`, which matches the repository’s pytest default and avoids the host-port collision found during verification.
- Marked `P4.S3` active in `works/backlog.md`.

## Files Changed

- `README.md`
- `.env.example`
- `works/backlog.md`
- `works/current/20260424_1018_verify_fresh_self_hosted_flow/plan.md`
- `works/current/20260424_1018_verify_fresh_self_hosted_flow/result.md`

## Verification Performed

- Checked the host-port constraint that blocked the earlier `5432` default on this workstation:
  - `lsof -nP -iTCP:8000 -sTCP:LISTEN`
  - `lsof -nP -iTCP:5432 -sTCP:LISTEN`
- Created and used a temporary clean verification checkout:
  - `mktemp -d /tmp/vocky-p4-verify.XXXXXX`
  - `rsync -a --exclude '.git' --exclude '.env' ./ /tmp/vocky-p4-verify.LkV3Og/`
  - `cd /tmp/vocky-p4-verify.LkV3Og && cp .env.example .env`
- Happy-path verification on a fresh Compose project and fresh volume:
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-happy docker compose down -v --remove-orphans`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-happy make bootstrap`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-happy make verify`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-happy make compose-down`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-happy docker compose down -v --remove-orphans`
- Granular fallback verification on a second fresh Compose project and fresh volume:
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular docker compose down -v --remove-orphans`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular make compose-up`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular make migrate`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular make smoke`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular make test`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular make compose-down`
  - `cd /tmp/vocky-p4-verify.LkV3Og && COMPOSE_PROJECT_NAME=vocky-p4-granular docker compose down -v --remove-orphans`
- Confirmed the dedicated-test-database guard trips before pytest when forced to the primary database:
  - `cd /tmp/vocky-p4-verify.LkV3Og && make DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky TEST_DATABASE_URL=postgresql+psycopg://vocky:vocky@127.0.0.1:55432/vocky test`

## Review Findings

- None.

## Blocking Findings

- None.

## Reference Docs Updated

- `README.md`
- `.env.example`

## Follow-Ups

- Run the dedicated phase review and close `P4` if no drift remains.

## Commit References

- None.
