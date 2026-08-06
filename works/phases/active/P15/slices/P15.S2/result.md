# Result — P15.S2: Knowledge — system internals

**Status: done.** The second explainer of the new-maintainer series is published to the personal KB.

## What was produced

One `/explain` run (topic mode, no `here`, executed inline by the orchestrator):

- **Title:** "Vocky System Internals: Architecture, Code Map, Data Model, and Contracts"
- **KB location:** `vocky/2026-08-06-vocky-system-internals-architecture-code-map-data-model-and-contracts.html` (slugged from the title), document id 26, **v1**
- **URL:** https://knowledge.hi2vi.com/documents/26
- **Save state:** `201`, committed, `push_pending: true` (normal)
- **Research section:** **included** — the trigram-search design has a real external comparison surface. Cited: PostgreSQL pg_trgm docs (index classes, LIKE/ILIKE acceleration, no-extractable-trigram degeneration) and PGroonga's pg_trgm comparison (the `KEEPONLYALNUM` non-ASCII/locale caveat). Next steps proposed: an EXPLAIN-based CI/smoke assertion for the Korean index path, documenting the locale dependency in operations.md, queue-depth visibility, and a PR-template item for the five-place capture-field checklist.

## Coverage

Grounded in `architecture.md` v0012 (full), `data.md` v0005 (full), `backend.md` v0007 (full), `api.md` v0013 (surfaces + auth contract + shared rules), and the `src/vocky/` + `alembic/versions/` listings. Covers: runtime shape (app/worker/Redis/Postgres, 5-container prod, worker-shares-api-image, /mcp as in-process Mount); the layering triads; the async capture pipeline with an SVG diagram (enqueue-is-the-last-checkpoint, upload-first attachment linking, P13 alert containment); the two scope chokepoints (`resolve_credential_project_ids` tuple-never-None, `_apply_query_filters` set-based scoping); the Korean-safe trigram search and its byte-for-byte lock-step rule; the one-field-five-places queue-serializer trap (+ the MCP flat-parameter sixth); the `recorded_by` seam discipline; the module map table; the 9-table data model + 12-migration chain (pinned head, never-"-1" downgrade rule, migrate-before-code); contract essences per surface; three load-bearing subtleties (IntegrityError nesting, the two duplicated normalize pairs, the owner-email join anchor). 5-question quiz.

## Coverage sufficiency (per the phase's open question)

One run **was** enough for this grouping at the depth a series read warrants: the explainer teaches the architecture, the invariants, and every trap the docs flag as load-bearing. What it deliberately does not reproduce is `api.md`'s full per-endpoint field catalogue (685 lines) — that is reference material, and the explainer points at the contract essences instead. No re-split needed.

## Notes for later slices

- None new beyond S1's live-status staleness finding (already in `phase.md`).
