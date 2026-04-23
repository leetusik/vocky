# Architecture

## Status

This architecture is intentionally lightweight. Vocky does not have production code yet, but the first MVP boundaries are now defined so the next build phases can implement against a shared target.

## Current Repo Shape

- `README.md`: product-facing project overview
- `AGENTS.md`: coding-agent workflow rules
- `docs/`: stable reference documents
- `works/`: backlog, active work items, archives, and templates
- `scripts/`: workflow helpers

## First MVP System Shape

The first MVP should be built from these parts:

- An MCP-facing feedback capture layer that accepts feedback events from agent products
- A storage layer that preserves raw feedback plus the metadata needed for retrieval and basic aggregates
- A minimal review/query API that returns stored records and simple counts or trends

## MVP Boundaries

- Self-hosted and single-tenant
- MCP is the only ingestion surface in the MVP
- No automatic classification or summarization in the MVP
- No dashboard UI in the MVP
- No managed-cloud or multi-tenant architecture in the MVP

## MVP Data Expectations

- Each stored record should preserve raw feedback content plus the metadata needed for review, such as source identity, available conversation context, creation time, and optional caller-provided tags or attributes.
- The storage layer only needs to support the retrieval and aggregate queries required by the review/query API; it does not need analytics-warehouse style modeling for the first MVP.

## Architecture Constraints

- Keep public contracts explicit in `docs/api.md`.
- Keep durable technical context here, not in transient work items.
- Keep execution history under `works/`.
- Prefer small slices and explicit review loops over large untracked changes.
- Avoid locking runtime or schema details earlier than necessary.

## Open Questions

- Exact runtime and framework choices
- Concrete storage engine and schema
- Auth and permission boundaries for self-hosted deployments
- Which query filters and aggregate dimensions should be included in the first implemented API version
