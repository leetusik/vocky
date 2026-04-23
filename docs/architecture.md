# Architecture

## Status

This architecture is intentionally lightweight. Vocky does not have production code yet, so this file records the current repo shape and the intended system boundaries without locking the implementation too early.

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `docs/`: stable reference documents
- `works/`: backlog, active work items, archives, and templates
- `scripts/`: workflow helpers

## Intended System Shape

Vocky is expected to grow into a system with these broad parts:

- an MCP-facing feedback capture layer
- a storage layer for structured feedback and metadata
- a classification and summarization layer
- reporting or analytics surfaces for review and trends

## Architecture Constraints

- Keep public contracts explicit in `docs/api.md`.
- Keep durable technical context here, not in transient work items.
- Keep execution history under `works/`.
- Prefer small slices and explicit review loops over large untracked changes.

## Open Questions

- exact runtime and framework choices
- storage schema and tenancy model
- auth and permission boundaries
- where the managed and self-hosted split should be enforced
