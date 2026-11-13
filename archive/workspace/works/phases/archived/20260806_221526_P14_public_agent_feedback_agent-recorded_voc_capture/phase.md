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

### Landed in `P14.S1` — the write path (read this before S2/S3/S4)

- **Migration `20260805_1200_add_feedback_recorded_by`** (revises `20260728_1200`, now head).
  Nullable `feedback_events.recorded_by TEXT` + `ix_feedback_events_recorded_by`, mirrored
  downgrade, **no DB CHECK constraint** — the vocabulary is application-validated like
  `trigger_type`/`channel`, so a third actor kind costs one constant and no migration. Verified
  reversible (`downgrade -1` → `upgrade head`).
- **Validator: `src/vocky/recorded_by.py`** — `ALLOWED_RECORDED_BY = ("agent", "human")`,
  `RecordedByValidationError`, `normalize_recorded_by()`. Public error string, quotable in docs:
  `recorded_by must be one of: agent, human`. **S2 must import `ALLOWED_RECORDED_BY` for the filter
  validator rather than re-declaring the vocabulary.**
- **All five write-path places threaded**, plus `persistence/models.py` (column + index) and
  `FeedbackEventRecord`. `FeedbackEventRecord.recorded_by` carries a `None` **default** (its
  siblings have none) — required for additivity, because `tests/test_notifications.py` builds the
  full field dict; `kw_only=True` makes the mid-list default legal. Do not "tidy" that default away.
- **MCP:** the flat `recorded_by` parameter was added to `tools/capture_feedback.py` — adding the
  field to the input model alone does **not** publish it in the tool schema. `normalize_mcp_payload`
  stamps `MCP_DEFAULT_RECORDED_BY = "agent"` when the normalized value is `None` (omitted *or*
  blank); explicit wins; REST stays `NULL`. `_normalize_capture_payload` remained transport-neutral.
- **Not touched by S1, still S2's:** `FeedbackQueryFilters`, `_apply_filters`, both serializers,
  both list-query normalizers, the web types. `recorded_by` stays **out of** the Admin PATCH
  allowlist permanently (provenance, not a review field).
- **The CLI (`vocky capture`) was deliberately not extended.** `cli/capture.py:_build_payload`
  hand-builds a subset body (no `trigger_type`, no `channel` either), so this matches its existing
  scope. If S4's public docs imply a CLI marker, raise it as an explicit follow-up.
- **Trap found and fixed — relevant to every future migration in this repo.**
  `tests/test_accounts_provisioning.py::test_org_credentials_migration_round_trip` used
  `command.downgrade(config, "-1")` to undo *the org-credentials migration*. A new head silently
  retargets that relative step: it failed with `UniqueViolation: uq_projects_tenant_id` and
  cascaded into **50 failures across 12 files** (a misaligned session DB, not 50 real bugs). Fixed
  by pinning the target by name (`"20260716_1600"`); no assertion, seed, or fixture changed. Any
  future migration would have hit the same wall — `data.md`'s migration guidance should say
  "pin downgrade targets by revision, never `-1`".
- **Suite state after S1:** full `uv run pytest` = **237 passed** (clean-tree baseline 225).
  `alembic check` reports only the known pre-existing `ix_feedback_events_search_trgm` drift — no
  `add_column`/`add_index`, i.e. the new column and index match the ORM model exactly.

### Landed in `P14.S2` — the read path (read this before S3/S4)

- **Filter validator: `query_feedback_common.normalize_recorded_by_filter`.** It
  **delegates** to `vocky.recorded_by.normalize_recorded_by` and re-raises as
  `FeedbackQueryValidationError`, exactly like `normalize_trigger_type_filter` wraps
  `normalize_trigger_type`. (DECOMP's note said "import `ALLOWED_RECORDED_BY`"; delegating
  reuses the vocabulary **and** the trim/blank rule **and** the error string from the one
  module, so nothing is re-declared. Same outcome, one fewer copy.) Blank/absent ⇒ **no
  filter** — there is deliberately no way to select *only* the unspecified (`NULL`) rows;
  if a dashboard ever needs a three-way split it needs a new sentinel, not a tweak here.
- **Four REST surfaces confirmed covered by two edits.** `app_feedback_api` and
  `project_feedback_api` both `import normalize_list_query from vocky.admin_api` (verified
  at their call sites), so the admin edit really does cover three surfaces; `api.py`'s
  duplicate pair (`normalize_user_feedback_query` + `serialize_user_feedback_record`) is
  the only other place, and it has its own test now.
- **Field position convention:** `recorded_by` sits immediately after `source_integration`
  in `FeedbackQueryFilters`, in `_apply_filters`, and in **both** serializers, mirroring
  `FeedbackEventRecord`. Keep any future read-side addition mirroring the record too.
- **One existing assertion had to change** —
  `tests/test_admin_api.py::test_admin_list_feedback_preserves_legacy_channel_filter`
  compares the whole serialized record as an exact dict, so it gained `"recorded_by": None`.
  It is the **only** full-record exact-dict assertion in `tests/` or `web/tests/` (checked),
  and its `null` value is itself the additivity proof. Additivity is a client-contract
  property (responses gain one nullable key); a serializer snapshot is a mirror of the
  serializer, not a client. Any future capture/read field will hit exactly this one line.
- **Web:** the record interface is **`VockyFeedback`**, not `VockyFeedbackRecord` as the
  DECOMP note wrote it. `recorded_by` went into `PARAM_KEYS` + `toQuery` (narrowed like the
  other enum params) and into the detail page's metadata list; `FORM_FIELD_KEYS` was **not**
  touched — no rendered control, per "Explicitly out of scope". The row needed a label, so
  `web/src/content/feedback.ts` gained `detail.fields.recordedBy: "Recorded by"`. `Field`
  renders `children ?? <Empty />`, so `null` already shows the em-dash — no null handling
  was written.
- **Prettier will reformat `toQuery`'s destructure** — it now has five names and no longer
  fits one line. CI runs `format:check`, so run `prettier --write` on
  `web/src/app/(app)/feedback/page.tsx` after touching it. (CI installs web deps with
  **pnpm**; S2 used local `npm`/`npx` and changed no lockfile.)
- **The CLI read path was deliberately left alone.** `cli/feedback.py`'s `feedback show`
  prints a curated subset that omits `trigger_type` too, and `_list_params` exposes no enum
  filter — so adding a marker there is a scope change, matching S1's `vocky capture`
  decision. **Open item for S4:** if public docs imply a CLI marker (read *or* write), raise
  it as an explicit follow-up rather than widening the CLI.
- **Concrete work S4 inherits in README.md:** the capture-payload/response JSON examples
  (~L113, ~L367, ~L399 and `docs/cli.md` ~L266) now under-describe the response, the
  trigger-fields paragraph (~L264) is the natural home for "who recorded it vs why capture
  happened", and the admin-list-filters sentence (~L446) enumerates the filterable fields
  and must gain `recorded_by`.
- **Suite state after S2:** full `make test` = **238 passed** (S1 left 237; +1 is the new
  validator case). Web: `npm test` 78 passed, `typecheck` / `lint` / `format:check` clean.
  `make check-skill-parity` PASS. `workflow.py validate` passed.
- **Still S3's / S4's:** the live round-trip (S3 can now assert `?recorded_by=agent`
  narrowing on all four REST surfaces after an MCP capture) and the public docs.

### Landed in `P14.S3` — the live proof (read this before S4/REVIEW)

Full evidence in `slices/P14.S3/result.md`. The durable lessons:

- **Rebuild the compose images before believing any "live" result.** `make compose-up` rebuilds,
  but the containers found running were 7 days old and predated S1/S2 — a live round-trip against
  them would have silently tested pre-P14 code. Always `make compose-up` (it passes `--build`) at
  the start of a verification slice.
- **The contract is proven end to end, not just in-process.** One real authenticated MCP session
  against the container's `/mcp` produced the full matrix, confirmed in Postgres:
  MCP-omitted ⇒ `agent`, MCP-explicit `human` ⇒ `human`, REST-explicit ⇒ `human`,
  REST-omitted ⇒ `NULL`. The marker survives the hand-written Redis serialize/deserialize pair.
  `?recorded_by=agent` narrows correctly on `/api/feedback`, `/admin/api/feedback`, and
  `/app/feedback`; the unfiltered read still returns the `NULL` row (additivity); a bad value 400s
  with the same string capture returns.
- **D3 verified empirically.** `pg_trgm` finds the Korean sentiment in `message` (`감사`,
  `도움이 되었어요`) *and* the Korean note in `comment` (`수출 흐름`), with a clean negative control,
  and search composes with `?recorded_by=agent`. **`q` exists on `/app/feedback` only** —
  `app_feedback_api.py:133` is the codebase's sole assignment to `filters.search`. S4 must not
  document `q` on the admin, project, or `/api/feedback` surfaces.
- **Migration reversibility re-verified against a live DB with rows**, pinning both ends by
  revision id (`downgrade 20260728_1200` → `upgrade head`), column + index restored verbatim.
- **D4 item 1 verified, with a real gotcha.** With `VOCKY_MCP_ALLOWED_HOSTS=vocky.hi2vi.com` (the
  exact `compose.prod.yml:143` value) a full authenticated MCP session — initialize, tools/list,
  capture — succeeds from that non-localhost `Host`; without it the same request is `421 Invalid
  Host header`. **No `Origin` header was sent by any non-browser client and none was required**, so
  leaving `VOCKY_MCP_ALLOWED_ORIGINS` unset is confirmed correct.
  - **Local `docker-compose.yml` does NOT forward `VOCKY_MCP_ALLOWED_HOSTS`/`_ORIGINS` to the `app`
    service**, even though `.env` sets them and `VOCKY_EXTERNAL_BASE_URL` points at a tailscale
    host. So `/mcp` over the local stack's external URL 421s today, while REST is unaffected (the
    allowlist guards `/mcp` only). Prod is fine (`compose.prod.yml:143`). Not a P14 regression and
    not fixed here — S4's SKILL.md self-hosting paragraph should stay accurate about it, and it is
    a candidate follow-up for local dev parity.
  - **Probing gotcha:** `POST /mcp` with a spoofed `Host` and `follow_redirects=True` sends the
    request **off-box** — the `307` `Location` for `/mcp` → `/mcp/` is built from the spoofed Host,
    so the first probe hit the real public deployment and came back `401`. Probe `/mcp/` directly
    with redirects **off**.
- **One product change: a terse `src/vocky/smoke.py` guard** — the reference payload now sends
  `"recorded_by": "human"` and the existing round-trip assertion gained one clause. It is the only
  check that exercises app → Redis → worker → Postgres → read against a **deployed** environment
  (`make smoke` / `external-smoke` / the deploy gate), which is exactly where a dropped queue field
  hides. No new file, no new harness. Any future capture field should extend this same payload.
- **Prod rollout ordering:** migrate before deploying code that reads the column; nullable + no
  backfill ⇒ instant, non-blocking, no lock window. `deploy/deploy.sh` already does this (step 6
  migrate, step 7 `up -d`), so **P14 needs no operational change**, and `deploy/rollback.sh`'s
  "does not re-migrate / assumes additive migrations" stance is safe for this migration.
- **Gate state after S3:** `make test` **238 passed** (unchanged before and after the smoke edit),
  `make check-skill-parity` PASS, `alembic check` = the known trigram drift only,
  `workflow.py validate` passed, `make smoke` passed. Stack left healthy, ad-hoc drivers left in the
  session scratchpad (never committed), the ad-hoc :8011 server stopped.

### Landed in `P14.S4` — the public contract (read this before REVIEW)

Docs only; no `src/` change. Full detail in `slices/P14.S4/result.md`.

- **`skills/vocky-feedback/SKILL.md` gained one new section and grew from 7 numbered steps to 8.**
  The new **step 3, "What goes in which field"**, sits *before* the three transport paths on purpose
  — the field mapping decides the payload for all of them — so Path A/B/C shifted to 4/5/6, the error
  table to 7, and "Report back" to 8. The two in-text `see the table in step 6` references were
  repointed. Content: D3's mapping table (sentiment verbatim → `message`; the agent's note →
  `comment`, "treat as required whenever an agent is the one recording"; `recorded_by` the marker;
  `source.integration` explicitly *not* the marker), the `null` = *unspecified* rule, the per-transport
  default (`/mcp` ⇒ `agent`, REST/CLI ⇒ `null`, explicit always wins), and a `json` payload example.
- **The renumber broke exactly one assertion:** `web/tests/skill-preview-ssr.test.ts:41` pins the
  **last section heading** (`## 7. Report back` → `## 8. Report back`) as its "the whole file shipped,
  nothing truncated" probe. One line, no semantic change. **Any future SKILL.md section
  insertion/renumbering hits this same line** — it is the SKILL.md analogue of S2's single exact-dict
  assertion. The line/byte counts next to it are computed from the file at test time, so they never
  need touching.
- **Key-scope honesty (D4 item 3) landed in three places**, all saying the same thing: a `vk_` key is
  **not** capture-only (capture + read + PATCH + DELETE within its scope; an org key spans every
  project in the org), so mint a **project-bound** key for an agent runtime. SKILL.md step 1, README's
  MCP section, `docs/cli.md` §2a + the MCP section. Phrased as current reality, not a promise —
  "per-credential capture-only scopes are not implemented yet".
- **A pre-existing SKILL.md bug was fixed**: the Path C self-hosting paragraph claimed an unlisted host
  makes `/mcp` "401 regardless of the key". Per S3's live evidence it is **`421 Invalid Host header`**,
  the check is on the **`Host`** header (not `Origin`), the default allowlist is
  `127.0.0.1`/`localhost`/`[::1]`, and the key is never examined. The error table gained a `421` row
  and a `recorded_by must be one of: agent, human` row (noting MCP returns that string as an
  `isError` tool result, not an HTTP status — verified in `tools/capture_feedback.py`).
- **S3's must-nots were honored.** `q` is mentioned only ever as `/app/feedback?q=` / `vocky feedback
  search`; no admin/project/`GET /api/feedback` surface is shown with `q`. No CLI marker flag is
  implied anywhere — SKILL.md Path A and `docs/cli.md` §4 both say plainly that `vocky capture` has no
  such flag and lands `null`, and point at REST/`/mcp` when the marker matters.
- **`docs/cli.md` is hand-maintained** — confirmed: nothing generates it (no reference in `Makefile`,
  `scripts/`, or CI; it is not under `docs/current/`). Editing it directly is correct.
- **Repo-root markdown is outside prettier's scope.** `web`'s `format:check` runs `prettier --check .`
  **from `web/`**, so `README.md` and `docs/cli.md` are not checked (verified: both fail
  `prettier --check` at `HEAD` too, pre-existing). Do **not** "fix" them — a reformat would be a
  thousand-line unrelated diff. `web/public/SKILL.md` stays prettier-ignored for the parity gate.
- **Gate state after S4:** `make test` **238 passed** (unchanged — docs only), `make check-skill-parity`
  PASS, web `npm test` 78 passed / `typecheck` / `lint` / `format:check` clean,
  `workflow.py validate` passed. Every JSON body edited in README/`docs/cli.md`/SKILL.md was parsed
  with `json.loads`, and the README `httpx` example with `ast.parse`.
- **For REVIEW:** the Doc impact list below was swept against everything P14 changed and gained six
  lines (`experience.md`, `product.md`, `security.md`, `backend.md`, `decisions.md`, `qa.md`). The two
  Open Questions above are unchanged and still want an operator answer.

### Landed in `P14.REVIEW` — verdict `pass`, docs consolidated

- **Everything re-validated together and green**: `make test` 238, web `npm test` 78 / `typecheck` /
  `lint` / `format:check` clean, `make check-skill-parity` PASS, `make smoke` PASS against the live
  stack, `alembic current` = `20260805_1200 (head)`, `alembic check` = the known trigram drift only,
  `workflow.py validate` PASS. Spot-checks confirmed every slice's claims against the tree (all five
  write-path places, both read-side duplicate pairs, `recorded_by` absent from the PATCH allowlist,
  `FORM_FIELD_KEYS` untouched, SKILL.md at 8 sections, `q` documented on `/app/feedback` only).
- **Eleven doc versions created** — `api`, `data`, `architecture`, `decisions` (D-P14-1/2/3),
  `backend`, `security`, `operations`, `qa`, `frontend`, `experience`, `product`. Every line of the
  Doc impact list above landed in at least one of them; S4's completeness sweep held up.
- **`doc-new-version` slugifies the whole `--summary` into the filename**, and a long one produces a
  path that exceeds the filesystem's 255-byte name limit *once an editor appends a temp suffix* —
  the write fails with `ENAMETOOLONG` after the version and its index entry already exist. Keep
  review summaries **short** (roughly under 100 characters). Recovering means deleting the file,
  removing its `docs/index.json` entry, restoring `latest`, and re-running `rebuild-docs`.
- **A pre-existing artifact was cleaned up in the new `api.md` version**: every `api.md` version since
  `v0002` (the P1 era) ended with stray `</content>` / `</invoke>` lines — a leaked tool-call closing
  tag that had been copied forward by `doc-new-version`'s base-body carry. `v0010` drops them. No
  other doc carries the artifact.
- **The two Open Questions below are unchanged.** The comment-enforcement one is an **operator
  decision** and is deliberately not decided here; the hardening one is resolved (D9 and D10 are
  filed under `works/deferred/open/`).

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
- `data.md` — `feedback_events` gains nullable `recorded_by TEXT` + `ix_feedback_events_recorded_by`; **migration head is now `20260805_1200`** (was `20260728_1200`), reversible, no backfill, no DB CHECK (vocabulary validated in the app). (P14.S1)
- `data.md` — migration guidance: pin an alembic downgrade target **by revision id, never `"-1"`**; a relative step in a test silently retargets onto each new head (cost this slice 50 cascading failures). (P14.S1)
- `api.md` — the capture contract gains an optional `recorded_by` (`"agent"` | `"human"`, else 400 `recorded_by must be one of: agent, human`) on **REST `POST /api/feedback`** and the **MCP `capture_feedback`** tool; MCP defaults it to `"agent"` when omitted, REST leaves it `NULL` (unspecified). (P14.S1)
- `architecture.md` — the `feedback_events` base shape now carries the capture-time provenance marker `recorded_by`, orthogonal to `trigger_type`. (P14.S1)
- `api.md` — every feedback **read** surface now returns `recorded_by` (`"agent"` | `"human"` | `null` = unspecified) in the record body: Admin `/admin/api/feedback`, `/app/feedback`, `/api/project/feedback` (shared serializer) and `GET /api/feedback` (its own duplicate serializer). Additive: one new nullable key, nothing renamed or retyped. (P14.S2)
- `api.md` — all four list surfaces accept an optional `recorded_by` **query filter** (`agent` | `human`, trimmed; blank/absent = no filter — legacy `NULL` rows are not selectable); an unknown value is 400 `recorded_by must be one of: agent, human`, the same string capture returns. (P14.S2)
- `frontend.md` — the dashboard's feedback list gains `recorded_by` as a **URL-driven filter only** (`/feedback?recorded_by=agent`, preserved across filter submit and pagination); no new rendered form control (the visible chip stays design-cowork territory), plus one "Recorded by" row in the record detail page's metadata list. (P14.S2)
- `operations.md` — **prod rollout ordering for the `recorded_by` migration**: migrate **before**
  deploying code that reads the column (old-code + new-schema is safe; new-code + old-schema 500s).
  The column is nullable with no backfill and the index is a btree over an all-NULL column, so the
  migration is **instant and non-blocking** — no lock window to schedule. `deploy/deploy.sh` already
  enforces it (step 6 migrate in a one-off container, step 7 `up -d`), so **P14 requires no
  operational change**, and `deploy/rollback.sh` (which deliberately does not re-migrate) is safe
  because the migration is additive. (P14.S3)
- `data.md` — the `20260805_1200` migration is **verified reversible against a live Postgres holding
  rows**: `downgrade 20260728_1200` drops the column and `ix_feedback_events_recorded_by`,
  `upgrade head` restores both verbatim; both ends pinned by revision id. (P14.S3)
- `qa.md` — `vocky-smoke`'s reference capture payload now carries `recorded_by: "human"` and the
  round-trip assertion checks it, making the smoke the deploy-time guard for capture-field loss in
  the hand-written Redis queue serialization (the one place a field disappears silently). (P14.S3)
- `api.md` — free-text search (`?q=`, `pg_trgm`) covers the agent-capture fields with no index work
  because sentiment lands in `message` and the agent note in `comment`; verified live on Korean
  substrings, and it composes with `?recorded_by=`. Note that **`q` is accepted on `/app/feedback`
  only**, not on the admin, project, or `GET /api/feedback` surfaces. (P14.S3)
- `security.md` / `operations.md` — the public `/mcp` DNS-rebinding allowlist is confirmed live: an
  authenticated MCP session from a non-localhost `Host` succeeds only when
  `VOCKY_MCP_ALLOWED_HOSTS` lists it (else `421 Invalid Host header`), and non-browser MCP clients
  send **no `Origin`**, so leaving `VOCKY_MCP_ALLOWED_ORIGINS` unset is correct. Local
  `docker-compose.yml` does not forward either variable to `app` (prod's `compose.prod.yml` does),
  so `/mcp` over a local stack's external hostname 421s — REST is unaffected. (P14.S3)
- `experience.md` — the product integration guide is where the **public agent-capture contract** now
  lives and is the doc most out of date: its capture field list (~L112–117), its capture examples, its
  "Agent Capture Over MCP" section (~L198–232), and its end-user read filter list (~L243) all predate
  `recorded_by`. Consolidate: the field mapping (user's sentiment verbatim → `message`; the agent's
  note → `comment`, documented-required for agent capture; `source.integration` is a runtime hint,
  **not** the marker), `recorded_by` on capture + every read + every list filter, `/mcp`'s `agent`
  default vs REST's `null`, and `null` = *unspecified* (never *human*, never backfilled). (P14.S4)
- `product.md` — the published `vocky-feedback` skill (product.md's "published artifact" bullet) now
  also carries the agent-capture field mapping, the `recorded_by` marker with its per-transport
  default, and a plain-spoken key-scope statement; its numbered walk grew from **7 to 8 steps** (the
  new field-mapping step precedes the three capture paths). Still one canonical file + a byte-identical
  served copy behind the CI parity gate. (P14.S4)
- `security.md` — the public docs now **state the `vk_` key's real scope out loud**: a key is not
  capture-only (capture + read + PATCH + DELETE within its scope, and an org key spans every project in
  the org), so an agent runtime must be given a **project-bound** key, never an org key; per-credential
  capture-only scopes remain unimplemented (the deferred D-P3-2 revisit, D4 item 3). Said in SKILL.md,
  README, and `docs/cli.md`. (P14.S4)
- `backend.md` — new shared validator module **`src/vocky/recorded_by.py`** (`ALLOWED_RECORDED_BY`,
  `RecordedByValidationError`, `normalize_recorded_by`), mirroring `trigger.py`; the transport-specific
  default lives in `capture.normalize_mcp_payload` (`MCP_DEFAULT_RECORDED_BY`) while
  `_normalize_capture_payload` stays transport-neutral; the MCP tool gained an explicit flat
  `recorded_by` parameter, and `query_feedback_common.normalize_recorded_by_filter` delegates to the
  same module on the read side. (sweep gap from S1/S2, filed by P14.S4)
- `decisions.md` — **D-P14-3**: `comment` is **documented-required, not server-enforced**, for agent
  capture (enforcing it would 400 every existing client that omits it; the defensible future shape is
  "required *when* `recorded_by == agent`"), and the **CLI deliberately carries no marker flag** on
  either the write or the read side — `vocky capture` lands `null` and the public docs point at REST or
  `/mcp` when the marker matters, rather than widening the CLI. (P14.S4)
- `qa.md` — `web/tests/skill-preview-ssr.test.ts` pins the **last section heading of `SKILL.md`** as its
  no-truncation probe, so any section added to or renumbered in the skill must update that one line
  (the neighbouring line/byte counts are computed from the file and never need touching). (P14.S4)
- `decisions.md` — **D-P14-1**: the agent/human marker is a first-class nullable indexed `recorded_by` column with a closed two-value vocabulary and `NULL` = unspecified (never backfilled, never inferred, not PATCH-able); **D-P14-2**: MCP capture defaults `recorded_by` to `"agent"` while REST defaults to `NULL`, with the transport-specific default living in `normalize_mcp_payload` and `_normalize_capture_payload` staying transport-neutral. (P14.S1)

## Open Questions

- **OPEN — for the operator.** Should `comment` (the note) eventually be **server-enforced** when `recorded_by == "agent"`? DECOMP read `intent.md` as a capability requirement and chose documentation over enforcement (D3 / D-P14-3). REVIEW agrees that was the right call for P14 — enforcing it globally would 400 every existing client — and deliberately did **not** decide the follow-up. If the operator wants enforcement, the only defensible shape is "required *when* `recorded_by == "agent"`", which is a small conditional-validation slice in a later phase, not a doc change.
- **RESOLVED.** The two deferred hardening items from D4 are filed: **D9** (per-credential rate limiting on `/api/feedback` + `/mcp`) and **D10** (capture-only key scopes, revisiting D-P3-2), both `source: P14.DECOMP`, both open under `works/deferred/open/`.
- **Noted, not a P14 defect.** Local `docker-compose.yml` does not forward `VOCKY_MCP_ALLOWED_HOSTS`/`_ORIGINS` to the `app` service, so `/mcp` over a local stack's external hostname 421s (prod is correct). Recorded in `operations.md` / `security.md` as a local-dev-parity candidate; nobody has filed it as a deferred job, and the operator may want to.
