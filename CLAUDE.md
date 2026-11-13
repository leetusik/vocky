# CLAUDE.md — vocky

vocky is a multi-tenant feedback service: products capture voice-of-customer feedback with a `vk_` key over REST (`/api/*`) or a write-only MCP endpoint (`/mcp`), and read it back through the web app, the `vocky` CLI or the API.
This repo is **source-only and frozen** until the hi2vi platform has taken over its feedback module; after that it is archived. Change nothing here unless asked.

## Layout

- `src/vocky/`: the Starlette server (`vocky-server`), the capture worker (`vocky-worker`), the `vocky` CLI and the smoke client (`vocky-smoke`).
- `web/`: the Next.js web app (pnpm; `lint`, `typecheck`, `test`, `build`).
- `skills/vocky-feedback/SKILL.md`: the product's end-user agent skill. `web/public/SKILL.md` is a byte-for-byte copy, held by `scripts/skill_parity.py`.
- `alembic/`: the database migrations (`uv run alembic upgrade head`).
- `deploy/`: the production deploy, backup and rollback scripts.
- `tests/`: the pytest suite.
- `archive/workspace/`: the old agentic-workspace records, frozen and read-only (see its `README.md`).

## Commands (from the README)

- `cp .env.example .env`, then `make bootstrap` (sync, compose up, migrate, wait for health).
- `make test`: the pytest suite (`uv run pytest`); `TEST_DATABASE_URL` must point at a separate disposable database.
- `make verify`: the REST smoke flow, then the pytest suite, against the running stack.
- `make check-skill-parity`: `python3 scripts/skill_parity.py`.
- In `web/`: `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`.

## Rules

- `archive/workspace/` is frozen: never edit it. No workflow engine runs in this repo; the work is planned in the hi2vi workspace.
- Keep `skills/vocky-feedback/SKILL.md` and `web/public/SKILL.md` identical.
