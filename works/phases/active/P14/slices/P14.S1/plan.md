# Plan — P14.S1: Persist the `recorded_by` agent marker through the capture path

## Job

Implement the whole **write** path for the `recorded_by` marker per the phase's plan of record — read `works/phases/active/P14/phase.md` in full first (decisions D1–D3, "The capture path, end to end", "Migrations", "Constraints for every slice" are your spec). After this slice an agent can record a marked event through REST **and** MCP and it lands in Postgres.

## Scope (write path only)

1. **Migration** — new nullable `feedback_events.recorded_by TEXT` + index `ix_feedback_events_recorded_by`, downgrade mirrored. Template: `alembic/versions/20260429_1620_add_identity_trigger_fields.py`. Current head `20260728_1200`; new revision named per the repo convention (`YYYYMMDD_HHMM_<slug>` — use today's date, 2026-08-05).
2. **Validator** — a tiny module mirroring `src/vocky/trigger.py` exactly (closed vocabulary `("agent", "human")`, error type, `normalize_recorded_by` that trims, collapses blank → None, rejects anything else). Own module beside `trigger.py` (e.g. `src/vocky/recorded_by.py`) unless you find a strong existing home.
3. **Thread the field through the five write-path places** (phase.md lists them; missing one silently drops the field):
   - `capture.BaseCaptureFeedbackInput` (`recorded_by: str | None = None`)
   - `capture._normalize_capture_payload` → normalize via the validator (transport-neutral — no defaulting here)
   - `feedback/types.py:CreateFeedbackEvent`
   - `capture_queue._serialize_payload` **and** `_deserialize_payload` (the silent-loss trap)
   - `feedback/repository.create_feedback_event` (`FeedbackEventModel(...)`) **and** `_to_record`; also `persistence/models.py` column + `__table_args__` index, and `feedback/types.py:FeedbackEventRecord`
4. **MCP** — add the explicit flat `recorded_by` parameter to `tools/capture_feedback.py` (the base model alone does not expose it over MCP) and implement D2: `normalize_mcp_payload` stamps `"agent"` when the caller omits it; explicit value wins; `normalize_rest_payload` untouched (REST default stays `None`).
5. **Tests, kept terse, in existing files**: `tests/test_persistence.py` — bump the pinned head revision (line ~45) and add the new index to the expected list, in this same slice; extend `test_capture_validation.py` (validator accept/reject/blank), `test_capture_queue.py` (round-trip carries the field), `test_capture_api.py` (REST accepts + omission → None), `test_mcp_transport.py` (tool advertises the param; omission → `"agent"`, explicit wins). Minimal high-value cases only — no new test files.

## Out of scope

Read path, filters, serializers, dashboard (S2); live end-to-end proof (S3); docs/SKILL.md (S4). Admin PATCH allowlist gains nothing — `recorded_by` is provenance (D1).

## Constraints

- **Additivity is the acceptance bar**: every existing client unchanged when it never mentions `recorded_by`; if an existing test assertion needs editing, stop and re-read D1–D3.
- Transport knowledge stays out of `_normalize_capture_payload`.
- Known pre-existing `alembic check` drift (`ix_feedback_events_search_trgm`) is not yours to fix.

## Validation

`uv` for everything Python. The suite needs a running stack: `make compose-up` (or `make bootstrap`) plus `DATABASE_URL`/`TEST_DATABASE_URL` — check `.env`/Makefile for how the repo provides them. Run `uv run alembic upgrade head` and the targeted test files (or `make test` if it's quick enough); migration downgrade/upgrade reversibility can be spot-checked here but full E2E proof belongs to S3. If the local stack cannot be brought up, say so in the verdict rather than skipping silently.

## Deliverables

- Code + migration + tests as above.
- `result.md` in this slice folder (free-form): what changed, file list, test results, anything S2 must know.
- Append durable cross-slice notes and any one-line "Doc impact" notes to `phase.md` (expected: data.md — column/index/migration head; api.md — capture contract gains `recorded_by`; decisions.md — D-P14-1/D-P14-2 material).
- Structured verdict.
