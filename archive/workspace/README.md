# Frozen workspace archive

These are the records of the agentic workspace that used to run at this repo's root: `works/` (phases, deferred jobs, state), `docs/` (the versioned durable docs and the old design rounds) and the old root `CLAUDE.md` contract, kept as `CLAUDE.archived.md` (renamed so that Claude Code does not load an archived contract as live rules; records inside the archive still call it `CLAUDE.md`).

- Frozen at commit `52ea68e`, on workspace engine v59, with one exception: `works/state.json` and `works/index.json` hold the engine's last local rebuild of 2026-10-14 (a newer timestamp only), which was never committed before the move. Read-only: never edit anything here.
- Its open deferred jobs were re-filed in the hi2vi workspace on 2026-11-13.
- No engine runs here: the engine (`scripts/workflow.py`), the skills, the agents and the workspace CI were removed from the repo.
- Paths inside these records are relative to the old repo root (`works/…`, `docs/current/…`); read them under `archive/workspace/`.
