# Plan — P15.S2: Knowledge — system internals (architecture, backend code map, data model, API contracts)

Second of the four-explainer series (see `../../phase.md`). Executed **inline by the orchestrator** — `/explain` is main-thread-only; no executor dispatched.

## What this slice produces

One `/explain` run in topic mode → the operator's personal KB (project `vocky`), no `here` flag. Repo writes limited to this slice's `result.md` + a `phase.md` note.

## Topic

*How vocky actually works* — the second question a new maintainer asks:

- Runtime shape: FastAPI app, Redis-backed capture queue, background worker, PostgreSQL; the async capture pipeline (REST/MCP → enqueue → worker → `feedback_events`), enqueue as the last write-path checkpoint.
- The `src/vocky/` module map: app wiring/lifespan (incl. nested MCP session manager), route modules per surface, domain packages `feedback/` + `accounts/` (types / repository / service layering), persistence, storage, notifications.
- Data model: tables, conventions, migrations (`alembic/`); the `pg_trgm` Korean-safe search expression that must stay byte-for-byte in lock-step with its index.
- API contracts: the wire shape of every route group (`/auth`, `/app`, `/api`, `/api/project`, `/mcp`, `/admin/api`), the `_apply_query_filters` read chokepoint, the MCP tool's hand-copied flat parameter list.

Topic string:

> vocky system internals for a maintainer: the FastAPI runtime shape and async capture pipeline (REST and MCP into a Redis queue, background worker persisting to PostgreSQL feedback_events), the src/vocky module map and accounts/feedback domain layering, the data model and alembic migrations including the pg_trgm Korean-safe search index, and the API contracts of every route group

## Reading set (from `phase.md` §Sources — S2)

Docs: `docs/current/architecture.md`, `backend.md`, `data.md`, `api.md` (685 lines — headers + key contracts, not exhaustive prose).
Code (grounding, not exhaustive): `src/vocky/app.py`, `capture.py`, `capture_queue.py`, `worker.py`, route modules list, `feedback/` + `accounts/` package shape, `persistence/models.py`, `mcp_server.py`, `alembic/versions/` listing.

## Steps

1. Read the docs above (api.md selectively); skim the code for grounding.
2. Web-research judgment: decide at research time; internals of a private system likely skip-by-judgment, but the pipeline/queue design has an external comparison surface — decide and record.
3. Author the interactive HTML explainer (Background / Intuition / Code / [Best practices] / Quiz) per the explain skill's contract; check KB for a prior doc with this subject first (expected none beyond doc 25, which is a different subject).
4. POST to the KB API; on 201 record url/version.
5. Write `result.md`; append a one-line note to `phase.md` (plus any durable findings).

## Done means

Explainer #2 exists in the KB; `result.md` records where. If one run cannot do the grouping justice, say so in `result.md` per the phase's open question — do not silently thin coverage.
