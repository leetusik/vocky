# Phase P14: Public agent feedback: agent-recorded VoC capture

_Intent: see [intent.md](intent.md)._

## Objective

Let third-party AI agents publicly record free-text user feedback (sentiment plus note) through the existing capture surfaces (MCP and REST), with a first-class agent-vs-human marker, documented for public adoption.

## Context

This is a **contract extension, not a rewrite**. Everything the phase needs already exists: one transport-neutral capture seam (`src/vocky/capture.py`), one queue → worker → `feedback_events` path, one shared read serializer, and a published public skill. P14 adds **one new persisted column** and documents the agent-capture convention on top of fields that already exist.

Downstream consumer: **changple5 P63**, which connects to vocky's public `/mcp` via `langchain-mcp-adapters`. P14 must land first.

---

## Decomposition

Single-pass decomposition — **no product visual design is in scope**, so there is no `co-work` slice and no `DECOMP2`. See "Explicitly out of scope" below for the design line we are deliberately not crossing.

| Slice | Name | Risk | Why it exists |
| --- | --- | --- | --- |
| `P14.S1` | Persist the `recorded_by` agent marker through the capture path | high | The whole **write** path: migration + ORM column + shared types + repository + queue round-trip + the `capture.py` normalization seam + the MCP tool parameter. After S1 an agent can record a marked event through REST **and** MCP and it lands in Postgres. |
| `P14.S2` | Expose `recorded_by` on every read, filter, and dashboard surface | high | The whole **read** path: the filter normalizer, the repository predicate wiring on the read side, the two record serializers (which cover four REST surfaces), and the web TypeScript plumbing so the dashboard can actually split agent vs human. |
| `P14.S3` | End-to-end verification of agent-recorded capture | high | The phase's proof: full suite, migration up/down reversibility, and a live round-trip through the running stack (REST + `/mcp` → worker → row → filtered read). Also records the prod rollout ordering. |
| `P14.S4` | Public agent-feedback documentation: SKILL.md, README, doc impact | high | The public contract. `skills/vocky-feedback/SKILL.md` **and** its byte-identical served copy `web/public/SKILL.md`, plus README's capture-field docs, plus the "Doc impact" notes the REVIEW slice consolidates. |

Sequencing rationale: write path → read path → proof → publish. Docs land **after** the proof so the public contract documents what is demonstrably true.

Every slice is `high` because every one writes real code or spans more than one file; S4 edits three files and is the public contract itself, so it is not a `low` docs-prose edit.

---

## Design decisions (made at DECOMP, plan of record)

### D1 — The marker is a new `feedback_events.recorded_by` column (`agent` | `human` | NULL)

**Decision.** Add a nullable, indexed `recorded_by TEXT` column to `feedback_events`, validated against a **closed** two-value vocabulary — `agent`, `human` — with `NULL` meaning *unspecified* (every pre-P14 row, and any caller that does not state it). Index `ix_feedback_events_recorded_by`. Validation mirrors `src/vocky/trigger.py` exactly (a tiny module with `ALLOWED_*`, an error type, and a `normalize_*` that trims, collapses blank → `None`, and rejects anything else).

**Why, and the alternatives rejected:**

- **(a) A new `trigger_type` value (`agent`) — rejected.** Cheapest by a mile (no migration; the index, the filters on four surfaces, and even the web dashboard's URL param all already exist), and it was a real contender. Rejected because `trigger_type` answers **why capture happened** (`like`/`dislike`/`comment`/`rating`/`survey`/`manual`/`other`) and the marker answers **who recorded it**. They are orthogonal dimensions, and folding one into the other is lossy: an agent recording a survey response could then say `agent` **or** `survey`, never both. The operator asked for a *first-class* discriminator; overloading an existing enum is the opposite of first-class, and unwinding it later means a data migration over live rows.
- **(b) A new `recorded_by` column — CHOSEN.** Orthogonal to every existing dimension, indexable, filterable with the exact predicate pattern `_apply_filters` already uses, and extensible (a future `system` value costs one constant). The migration is the boring shape this repo has done before (`20260429_1620` added four nullable columns + two indexes the same way). Cost is breadth, not depth: one field threaded through ~8 backend files, all mechanical.
- **(c) `source.integration` convention — rejected.** It is free text with no validation and no index, and the operator explicitly rejected convention-only ("Today the transport is not stored and `source.integration` is free-text convention only" → "**Yes — first-class marker**"). It stays what it is: the free-text runtime hint (`"langchain-mcp"`, `"claude-code"`), *not* the marker.
- **(d) A boolean `is_agent` — rejected.** Cannot express "unspecified" without a third state anyway, and cannot grow a third actor kind.
- **(e) A key in `attributes` / `source_metadata` JSONB — rejected.** Not indexed, not filterable through the typed filter set, invisible to the dashboard.

**Consequences.**
- Legacy rows are `NULL`, not `human`. Dashboards split **three** ways: agent / human / unspecified. Do not backfill and do not infer.
- `recorded_by` is **provenance, not a review field**: it is set at capture and is **not** added to the Admin PATCH allowlist (`admin_api.patch_admin_feedback`).
- It never affects scoping or auth. It is a descriptive dimension only.

### D2 — MCP capture defaults `recorded_by` to `"agent"`; REST defaults to `NULL`

**Decision.** When the caller omits `recorded_by`, `normalize_mcp_payload` stamps `"agent"`; `normalize_rest_payload` leaves it `None`. An explicit caller value always wins on both transports.

**Why.** `/mcp` is by construction the agent-runtime surface — one write-only tool, documented as "agent-decided capture" (D-P7-1), and there is no human-driven MCP client. Defaulting it is therefore *correcting* the record, not guessing; it also means the first changple agent produces correctly-marked data even if it never learns the new argument. REST is genuinely mixed (server-to-server product UI *and* the CLI/skill path an agent drives), so inferring `human` there would be wrong and inferring `agent` would be worse — `NULL` is the honest answer, and it keeps every existing REST client byte-for-byte unchanged.

**Where.** In `normalize_mcp_payload`, which today is a pure delegation to `_normalize_capture_payload` — the natural (and only MCP-specific) seam. Do **not** put transport knowledge inside `_normalize_capture_payload`.

### D3 — Sentiment → `message`, note → `comment`. No new text columns.

**Decision.** The agent-capture field mapping, documented as convention rather than enforced by new schema:

| What the agent sends | Field | Notes |
| --- | --- | --- |
| The user's feedback / sentiment, free text, verbatim where possible (답답함, 감사, 긍정, 부정, 짜증, or a whole sentence) | **`message`** | Already required + non-blank. This is "the voice of the customer". |
| The agent's free-text note about that feedback — what happened, what the user was doing, why it was recorded | **`comment`** | Schema-optional; **documented as required for agent capture** (see below). |
| `"agent"` | **`recorded_by`** | The marker (D1). |
| Optional labels the agent wants to slice by | `tags` | Optional, unchanged semantics. |
| The runtime | `source.integration` (e.g. `"langchain-mcp"`) | Unchanged, still free text, still **not** the marker. |

**Why.** No enum was the operator's explicit call, so both halves must be free text, and both belong in fields that already exist. Decisively: `message` and `comment` are **both already inside the `pg_trgm` search expression** (`coalesce(message,'') || ' ' || coalesce(comment,'') || ' ' || coalesce(target_text,'') || ' ' || coalesce(trigger_message,'')`, migration `20260716_1600`), so sentiment and note become searchable — including Korean substrings — with zero index work. A new `sentiment` or `note` column would add a migration, fragment the search target (which would then need its own migration and a lock-step change in `repository._feedback_search_target()`), and buy nothing the existing fields do not already give. `trigger_message` was considered for the note and rejected: it describes the UI/action that *caused* capture, not the recorder's commentary.

**On "the note argument is a hard requirement".** `intent.md` states it as a **capability** requirement — "the capturing agent **must be able to** pass a free-text note alongside the sentiment". So do **not** make `comment` server-side mandatory: that would 400 every existing REST/CLI/MCP client that omits it. The requirement is satisfied by (i) `comment` being present on every capture surface (it already is, on REST, MCP, and `vocky capture --comment`), and (ii) S4 documenting it as **required for agent capture** in `SKILL.md`. If the operator later wants it server-enforced, the only defensible shape is "required **when** `recorded_by == "agent"`" — record it as a follow-up, do not sneak it in here.

### D4 — Hardening scope: one item verified, two deferred

`intent.md`'s three known public-MCP considerations, decided:

1. **Prod `VOCKY_MCP_ALLOWED_HOSTS` / `VOCKY_MCP_ALLOWED_ORIGINS` — IN SCOPE, already satisfied; verify only.** `compose.prod.yml:143` already sets `VOCKY_MCP_ALLOWED_HOSTS: vocky.hi2vi.com`. `VOCKY_MCP_ALLOWED_ORIGINS` is deliberately unset and that is **correct**: MCP's transport security only checks `Origin` when the header is present, and a non-browser client (`langchain-mcp-adapters`, `claude mcp add --transport http`) sends none. **No code or config change.** S3 verifies the live `/mcp` answers a real authenticated `initialize` from a non-localhost `Host`; S4 keeps the SKILL.md self-hosting gotcha paragraph accurate.
2. **No rate limiting on `/api/feedback` and `/mcp` — DEFERRED.** `src/vocky/rate_limit.py` exists and is generic (`check_rate_limit(request, bucket=...)`), so it *looks* like a one-liner — it is not. It is keyed **per client IP**, which is exactly wrong for server-to-server agent traffic: every capture from one changple deployment shares one IP and would throttle as a single caller, while a distributed abuser evades it. Capture wants a **per-credential** bucket, and the module's single-worker in-process invariant plus its deliberate "never key on the submitted identity" trust model both need re-reasoning before that lands. That is its own piece of work with its own failure modes; bolting it onto a contract phase would balloon P14 and risk throttling the very first public consumer. **Recommended `defer-job`** (the orchestrator files it — DECOMP may not run `defer-job`): *"Rate-limit the public capture surfaces (`POST /api/feedback`, `/mcp`) per credential, not per IP"*, trigger: *"before a second third-party agent product goes live, or on the first abuse/cost incident"*, source `P14.DECOMP`.
3. **Unscoped `vk_` keys in third-party agent processes (revisit D-P3-2) — DEFERRED, but say it out loud.** This is the phase's sharpest honest risk: under D-P3-2 (narrowed by D-P10-3) one `vk_` key does capture **and** read **and** PATCH **and** DELETE across its whole scope, and an org-level key spans every project in the org. P14 puts exactly that key inside a third-party agent runtime. A capture-only scope is the right answer and is genuinely valuable now — but per-credential permission scopes touch minting, the middleware, and every `/api/*` handler; it is a phase, not a slice. **Recommended `defer-job`**: *"Per-credential permission scopes (capture-only keys) — revisit D-P3-2 now that `vk_` keys live in third-party agent processes"*, trigger: *"before recommending vocky keys be embedded in any third-party runtime the operator does not control"*, source `P14.DECOMP`. S4 must state the current reality plainly in `SKILL.md`/README rather than let a public reader assume the key is capture-only — mint a **project-bound** key for an agent, never an org key.

### Explicitly out of scope

- **Any new dashboard visual control.** The web filter form renders exactly three inputs (`q`, `project_id`, `feedback_value`); every other filter is URL-driven. S2 adds `recorded_by` as a **URL-driven filter and a typed field only** — plus one row in the detail page's existing metadata list, which is filling an established pattern, not designing. A visible agent/human filter chip or an agent-vs-human dashboard split view **is product visual design** → it belongs to Claude Design under the `design-cowork` skill, in a separate design-bearing phase. Do not author it here.
- **Backfilling legacy rows.** `NULL` stays `NULL`.
- **A sentiment enum, vocabulary, or normalization.** The operator rejected it; free text is the product decision.
- **Changple-side integration.** That is changple5 P63.
- **Prod deployment.** P12 owns deploy; S3 records the ordering constraint, it does not run a release.

---

## Findings & Notes

Research notes from `P14.DECOMP`. Later slices should not need to re-derive these.

### The capture path, end to end

`REST POST /api/feedback` (`api.py:capture_feedback`) and `MCP capture_feedback` (`tools/capture_feedback.py`) both build a transport-specific pydantic input (`RestCaptureFeedbackInput` / `McpCaptureFeedbackInput`, both subclassing `BaseCaptureFeedbackInput`), call `normalize_rest_payload` / `normalize_mcp_payload` — thin wrappers over the single `_normalize_capture_payload` — which produce a `CreateFeedbackEvent`. The route then stamps `project_id` via `resolve_capture_project`, enqueues to Redis (`capture_queue.enqueue_feedback`), and the worker persists via `FeedbackRepository.create_feedback_event`.

**A new capture field must be added in five places on the write path, and missing any one silently drops it:**

1. `capture.BaseCaptureFeedbackInput` — the raw input model (adding it here gives **REST and MCP body parsing** for free).
2. `capture._normalize_capture_payload` — the normalization call into `CreateFeedbackEvent`.
3. `feedback/types.py:CreateFeedbackEvent` — the transport-neutral payload.
4. **`capture_queue._serialize_payload` AND `_deserialize_payload`** — the Redis round-trip is a hand-written dict on both sides. **This is the easiest place in the repo to lose a field**: nothing fails, the value just never reaches the worker. `tests/test_capture_queue.py` is the guard.
5. `feedback/repository.create_feedback_event` (the `FeedbackEventModel(...)` construction) **and** `_to_record` (model → `FeedbackEventRecord`).

The **MCP tool is separate**: `tools/capture_feedback.py` declares every field as an explicit flat function parameter and hand-copies it into `McpCaptureFeedbackInput`. Adding a field to the base model does **not** expose it over MCP — the tool signature must gain the parameter too, or the MCP tool schema simply will not advertise it.

### The read path

- `feedback/repository.py:_apply_filters` (~line 562) is the **single** place every filter predicate lives; the pattern is uniformly `if filters.X is not None: statement = statement.where(Model.X == filters.X)`.
- `FeedbackQueryFilters` (`feedback/types.py`) is the typed filter set.
- **Four REST surfaces, two normalizers, two serializers:**
  - `admin_api.normalize_list_query` is reused verbatim by `app_feedback_api` (`/app/feedback`) and `project_feedback_api` (`/api/project/feedback`) — **one edit covers three surfaces**.
  - `api.normalize_user_feedback_query` (`GET /api/feedback`, the end-user self-read) is a **separate, duplicated** normalizer — it must be edited too.
  - `tools/query_feedback_common.serialize_record` is shared by admin / app (wrapped by `_serialize_app_record`, which just adds `project_id`) / project surfaces; `api.serialize_user_feedback_record` is again a **separate duplicate**.
  - Filter validators live in `tools/query_feedback_common.py` (`normalize_trigger_type_filter` is the template to copy).
- **Metrics** (`FeedbackMetricsQuery` / `/admin` dashboard metrics) deliberately supports only the ingest-time window plus the shared filters — do not add marker-specific metrics in P14.

### The web dashboard

- `web/src/lib/vocky/types.ts`: `VockyFeedbackRecord` (record shape) and `VockyFeedbackQuery` (query shape, where `trigger_type` is a literal union — extend the same way).
- `web/src/app/(app)/feedback/page.tsx`: `PARAM_KEYS` is the URL allowlist (blank ⇒ absent, load-bearing), `FORM_FIELD_KEYS` is the *rendered* form (only `q`, `project_id`, `feedback_value` — leave it alone, see "out of scope"), `toQuery` narrows non-string params.
- `web/src/app/(app)/feedback/[feedbackId]/page.tsx:228` renders `record.trigger_type` in the detail metadata list — the place to surface `recorded_by`.
- Web tests: `web/tests/vocky-app.test.ts` carries a record fixture that includes `trigger_type`.

### Migrations

- Chain lives in `alembic/versions/`, filename `YYYYMMDD_HHMM_<slug>.py`, `revision` = the `YYYYMMDD_HHMM` stem. Current head: **`20260728_1200`** (`add_org_level_credentials`).
- `20260429_1620_add_identity_trigger_fields.py` is the **exact template** for this phase: `op.add_column` nullable Text + `op.create_index`, with a mirrored `downgrade()`.
- **`tests/test_persistence.py:45` hard-codes the head revision string** (`assert migration_version == "20260728_1200"`) and lines 47–59 list every expected `feedback_events` index. Both **must** be updated in the same slice as the migration — this is the one assertion in the suite that pins the head, and `data.md` calls it out explicitly.
- Known, pre-existing `alembic check` drift: `remove_index ix_feedback_events_search_trgm` (the trigram index is intentionally unmodelled in `__table_args__`). Not a regression; any new gate must whitelist it.
- **Deployment ordering is load-bearing** (same rule `data.md` records for P10): migrate **before** deploying code that reads the new column. Old-code + new-schema is the only safe overlap; new-code + old-schema 500s. The column is nullable with no backfill, so the migration itself is non-blocking and instant.

### The SKILL.md byte-parity gate

- Canonical: `skills/vocky-feedback/SKILL.md`. Served copy: **`web/public/SKILL.md`**. `scripts/skill_parity.py` compares them **full-file, bytes including frontmatter**; `make check-skill-parity` runs it and CI runs it on every push/PR. The fix is literally `cp skills/vocky-feedback/SKILL.md web/public/SKILL.md` — **edit the canonical, then copy; never hand-edit the served copy.**
- `web/.prettierignore` excludes `public/` on purpose — a prettier markdown reflow would break parity. Do not undo it.
- The landing's skill pane reads the served file **at request time** and computes its own line/byte counts, so a longer SKILL.md needs **no** frontend change and no count edits. Never paste an excerpt or hardcode a count.
- The skill is a **shipped product artifact**, not a versioned doc under `docs/` — editing it is real implementation work in a slice, not a REVIEW-time doc version.

### Docs / durable truth touched by this phase

Per-slice rule: implementation slices append a one-line **Doc impact** note below; **only `P14.REVIEW` runs `doc-new-version`**. Expected areas: `api.md` (the marker + agent-capture convention on the REST capture, MCP tool, and shared-rules contracts), `data.md` (the new column, index, and migration head), `decisions.md` (a new `D-P14-1` for the marker design and `D-P14-2` for the free-text sentiment mapping; note that P14 *narrows nothing* but re-raises D-P3-2), `security.md` (public agent adoption puts unscoped `vk_` keys in third-party runtimes — state it), and possibly `architecture.md` (the `feedback_events` base shape lives there, not in `data.md`).

### Environment / running the suite

- Python is **`uv`**-driven: `uv run pytest`, `uv run alembic upgrade head`. The workflow manager is the exception (`python3 scripts/workflow.py`).
- `make test` requires both `DATABASE_URL` and a **separate** `TEST_DATABASE_URL`; the suite runs real Alembic migrations against a real Postgres, so `make compose-up` (redis + postgres + app + worker) is a prerequisite. `make bootstrap` = sync + compose-up + migrate + wait-ready. `make verify` = smoke + test.
- `src/vocky/smoke.py` holds the in-tree reference capture payload (`vocky-smoke` / `make-smoke`) and asserts on the round-tripped record — worth extending in S3 only if it stays terse.
- Keep test additions small (repo rule): extend the existing `tests/test_capture_validation.py`, `test_capture_api.py`, `test_capture_queue.py`, `test_mcp_transport.py`, `test_query_validation.py`, `test_persistence.py` rather than adding new files.

### Constraints for every slice

- **Additivity is the acceptance bar.** Every existing client — REST, MCP, CLI, dashboard — must keep working byte-for-byte when it never mentions `recorded_by`. The pydantic models ignore unknown fields, the column is nullable, the filter is absent-means-no-filter. If any existing test needs an assertion edit, stop and re-read the design.
- `_normalize_capture_payload` stays transport-neutral; transport-specific behavior (the MCP `agent` default) lives in `normalize_mcp_payload`.
- Never hand-edit `docs/current/*.md`; never edit `web/public/SKILL.md` directly.

---

## Constraints

- No product visual design in this phase (see "Explicitly out of scope"); anything that needs a new dashboard control stops and becomes a design-bearing follow-up.
- Migration-before-code on any deploy; nullable column, no backfill.
- `tests/test_persistence.py`'s pinned head revision must be bumped in the same slice as the migration.
- `skills/vocky-feedback/SKILL.md` and `web/public/SKILL.md` must stay byte-identical (`make check-skill-parity`).
- Durable docs are versioned once, at `P14.REVIEW`; slices append Doc impact notes only.

## Doc impact

_One line per durable-truth change; `P14.REVIEW` consolidates these into doc versions._

- (P14.DECOMP: no durable-truth change — decisions recorded above; `decisions.md` entries `D-P14-1`/`D-P14-2` are expected to be written by the implementing slices' notes and consolidated at REVIEW.)

## Open Questions

- Should `comment` (the note) eventually be **server-enforced** when `recorded_by == "agent"`? DECOMP read `intent.md` as a capability requirement and chose documentation over enforcement (D3). Worth putting to the operator at REVIEW.
- Does the operator want the two deferred hardening items (per-credential rate limiting; capture-only key scopes, D4) filed as `defer-job`s now? DECOMP cannot run `defer-job`; the recommended titles/triggers are in D4 for the orchestrator.
