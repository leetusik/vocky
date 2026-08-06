# Result — P14.S1: Persist the `recorded_by` agent marker through the capture path

**Status: done.** An agent can now record a marked event through REST **and** MCP and it lands
in Postgres as `feedback_events.recorded_by`. Read path, filters, and serializers are untouched
(S2); no docs or SKILL.md changes (S4).

## What changed

### 1. Migration — `20260805_1200_add_feedback_recorded_by`

`alembic/versions/20260805_1200_add_feedback_recorded_by.py`, revises `20260728_1200`
(the previous head). Adds nullable `feedback_events.recorded_by TEXT` + index
`ix_feedback_events_recorded_by`; `downgrade()` mirrors it exactly. No backfill, no server
default, **no DB CHECK constraint** — the two-value vocabulary is validated in the application
exactly like `trigger_type`/`channel`, so a future third actor kind costs one constant and no
migration. Pre-P14 rows stay `NULL` = *unspecified*, never `human` (D1).

### 2. Validator — `src/vocky/recorded_by.py` (new)

Mirrors `src/vocky/trigger.py` byte-for-byte in shape: `ALLOWED_RECORDED_BY = ("agent", "human")`,
`RECORDED_BY_VALIDATION_ERROR`, `RecordedByValidationError`, `normalize_recorded_by()` (trim →
blank collapses to `None` → unknown value rejected). `capture.normalize_capture_recorded_by()` is
the thin adapter that re-raises it as `CaptureFeedbackValidationError`, matching
`normalize_capture_trigger_type`.

Public error string: `recorded_by must be one of: agent, human` (400 on REST, `isError` on MCP).

### 3. The five write-path places (all threaded)

| Place | File |
| --- | --- |
| raw input model (gives REST **and** MCP body parsing) | `src/vocky/capture.py:BaseCaptureFeedbackInput` |
| normalization → payload | `src/vocky/capture.py:_normalize_capture_payload` |
| transport-neutral payload | `src/vocky/feedback/types.py:CreateFeedbackEvent` |
| Redis round-trip (the silent-loss trap) | `src/vocky/capture_queue.py:_serialize_payload` **and** `_deserialize_payload` |
| persist + read-back | `src/vocky/feedback/repository.py:create_feedback_event` **and** `_to_record`; `src/vocky/persistence/models.py` column + `__table_args__` index; `feedback/types.py:FeedbackEventRecord` |

`FeedbackEventRecord.recorded_by` is declared **with a `None` default** (unlike its sibling
fields, which have none). That is deliberate and load-bearing for additivity: `tests/test_notifications.py`
builds a full `FeedbackEventRecord` field dict, and a required field would have forced an edit
there. `kw_only=True` makes the mid-list default legal.

### 4. MCP — parameter + the `"agent"` default (D2)

- `src/vocky/tools/capture_feedback.py` gained the explicit flat `recorded_by: str | None = None`
  parameter (positioned after `channel`) and hand-copies it into `McpCaptureFeedbackInput`.
  Without the flat parameter the MCP tool schema would not advertise the field at all — the new
  `tools.tools[0].inputSchema["properties"]` assertion in `test_mcp_transport.py` is the guard.
- `normalize_mcp_payload` stamps `MCP_DEFAULT_RECORDED_BY = "agent"` when the normalized value is
  `None` (covers both omitted and whitespace-blank); an explicit `"human"`/`"agent"` always wins.
  `_normalize_capture_payload` stayed transport-neutral; `normalize_rest_payload` is byte-for-byte
  unchanged, so REST keeps defaulting to `NULL`.

## Validation

All run with `.env` exported (`set -a; . ./.env; set +a`) against the running compose stack
(`vocky-postgres-1`, `vocky-redis-1` up).

| Command | Result |
| --- | --- |
| `make migrate` (`uv run alembic upgrade head`) | PASS — `20260728_1200 -> 20260805_1200` |
| `uv run alembic downgrade -1` then `uv run alembic upgrade head`; `uv run alembic current` | PASS — reversible, back at `20260805_1200 (head)` |
| `make test` / `uv run pytest` (full suite) | **PASS — 237 passed** (baseline on a stashed clean tree: 225 passed) |
| `uv run alembic check` | Only the known pre-existing drift `remove_index ix_feedback_events_search_trgm`. **No** `add_column`/`add_index` reported ⇒ the new column+index match the ORM model exactly |
| `make check-skill-parity` | PASS (untouched by this slice; CI runs it) |
| `python3 scripts/workflow.py validate` | PASS |

Full-suite reversibility is additionally exercised for free: `test_org_credentials_migration_round_trip`
downgrades below the new migration and upgrades back to head inside the suite.

No Python lint gate exists in this repo (`ruff` is not installed; CI runs skill-parity, web
lint/typecheck/test, and pytest only).

## Deviation from `plan.md` — one, and why it was unavoidable

**`tests/test_accounts_provisioning.py::test_org_credentials_migration_round_trip` had to be
edited** (one line + comment): it called `command.downgrade(config, "-1")` to undo *the org
credentials migration*, which only worked while `20260728_1200` was head. Any new migration —
this one or a future one — silently retargets that relative step onto the new head, and it then
failed with `UniqueViolation: uq_projects_tenant_id`, cascading into **50 failures across 12
files** (a downgraded/misaligned session DB, not 50 real bugs).

Fixed by pinning the target by name: `command.downgrade(config, "20260716_1600")` (the revision
*before* org credentials), with a comment explaining why relative steps are wrong here. The test's
seeds and every assertion are unchanged, and the closing `upgrade(config, "head")` restores the
whole chain including the new migration.

This is a **revision anchor**, not an assertion edit — the additivity bar in `phase.md`
("if any existing test needs an assertion edit, stop and re-read the design") is intact: no
existing assertion, fixture, or client behavior changed anywhere. Worth flagging to REVIEW as a
latent trap that would have bitten the next migration in any phase.

## Tests added (terse, all in existing files)

- `test_persistence.py` — pinned head bumped `20260728_1200` → **`20260805_1200`**, `ix_feedback_events_recorded_by`
  added to the expected index list, plus one new test `test_recorded_by_persists_and_defaults_to_null`
  (marked row persists `agent`; unmarked row is SQL `NULL`).
- `test_capture_validation.py` — parametrized REST normalization (`agent` / ` human ` / blank / `None`),
  rejection of an unknown value, and parametrized MCP defaulting (omitted → `agent`, blank → `agent`,
  explicit `human` wins, ` agent ` trims).
- `test_capture_queue.py` — a round-trip test carrying `recorded_by`, plus one assertion in the
  existing legacy-job test that a job serialized before the field existed deserializes to `None`.
- `test_capture_api.py` — one test covering all three REST behaviors: explicit ` agent ` trims and
  reaches the queue, omission enqueues `None`, `"robot"` → 400 with the exact detail string.
- `test_mcp_transport.py` — two assertions appended to the suite's single MCP session test (it is
  the sole caller of `mcp.session_manager.run()`, so a second transport test was deliberately not
  added): the tool schema advertises `recorded_by`, and the existing call — which omits it —
  enqueues `"agent"`.

## What S2 (read path) must know

1. `FeedbackEventRecord.recorded_by` **already exists** and is populated by `_to_record`. S2's job
   there is only the two serializers (`tools/query_feedback_common.serialize_record` and the
   duplicated `api.serialize_user_feedback_record`), not the record type.
2. Copy `vocky.recorded_by.normalize_recorded_by` for the **filter** validator in
   `tools/query_feedback_common.py` (template: `normalize_trigger_type_filter`) — do not re-derive
   the vocabulary; import `ALLOWED_RECORDED_BY`.
3. `_apply_filters` (`feedback/repository.py`, ~line 600, right beside the `trigger_type` predicate)
   takes the same one-line `if filters.X is not None:` shape. `FeedbackQueryFilters` in
   `feedback/types.py` was **not** touched by S1 — the field is S2's to add.
4. The dashboard splits **three** ways (agent / human / unspecified). `NULL` must render as
   "unspecified", never as "human".
5. `recorded_by` is **not** in the Admin PATCH allowlist and must not be added — provenance, not a
   review field (D1).

## Other observations

- **The CLI (`vocky capture`) was deliberately left alone.** `src/vocky/cli/capture.py:_build_payload`
  hand-builds a *subset* body (no `trigger_type`, no `channel`, no target fields), so omitting
  `recorded_by` is consistent with its existing scope, and the plan scoped S1 to REST + MCP. If S4's
  public docs want an agent to be able to use the CLI path with a marker, that is a small explicit
  follow-up, not a silent gap.
- `src/vocky/smoke.py`'s reference payload was not extended — S3 owns that call.
- Deployment ordering (recorded in the migration docstring, for S3): **migrate before deploying
  code**. The column is nullable with no backfill, so the migration is instant and non-blocking,
  and old-code + new-schema is safe.
