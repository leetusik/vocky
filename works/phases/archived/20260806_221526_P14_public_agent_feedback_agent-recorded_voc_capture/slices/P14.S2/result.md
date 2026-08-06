# Result — P14.S2: Expose `recorded_by` on every read, filter, and dashboard surface

**Status: done.** Every read surface now returns `recorded_by`, every list surface can
filter on it, and the dashboard carries it as a URL-driven filter + a typed field + one
detail-page row. No new rendered form control was added.

## What landed

### Backend — the filter

| Place | Change |
| --- | --- |
| `feedback/types.py:FeedbackQueryFilters` | `recorded_by: str \| None = None`, placed after `source_integration` to mirror `FeedbackEventRecord`'s field order. |
| `feedback/repository.py:_apply_filters` | The uniform predicate `if filters.recorded_by is not None: ... == filters.recorded_by`, inserted in the same relative position. |
| `tools/query_feedback_common.py` | New `normalize_recorded_by_filter`, built exactly on the `normalize_trigger_type_filter` template. |

`normalize_recorded_by_filter` **delegates to `vocky.recorded_by.normalize_recorded_by`**
rather than importing `ALLOWED_RECORDED_BY` and re-implementing the membership check —
see *Deviations*. Net effect is what the phase asked for and slightly stronger: the read
side reuses the vocabulary, the trim/blank-collapse rule, **and** the public error string
(`recorded_by must be one of: agent, human`) from one module.

### Backend — both normalizers, both serializers

- `admin_api.normalize_list_query` → covers `/admin/api/feedback`, `/app/feedback`
  (`app_feedback_api` imports it), and `/api/project/feedback` (`project_feedback_api`
  imports it). Verified all three import sites still resolve to this one function.
- `api.normalize_user_feedback_query` → the separate `GET /api/feedback` duplicate.
- `tools/query_feedback_common.serialize_record` → emits `"recorded_by"` (admin / app —
  through `_serialize_app_record`, which spreads it / project).
- `api.serialize_user_feedback_record` → the duplicate, likewise.

Field position in both serializers: right after `source_integration`, matching
`FeedbackEventRecord`.

**Untouched on purpose:** `FeedbackMetricsQuery` and the two `usage_api` filter
constructions (no marker-specific metrics), the Admin PATCH allowlist (`recorded_by` is
provenance, D1), and `cli/feedback.py` (`feedback show` prints a curated subset that does
not include `trigger_type` either — consistent with S1's CLI decision; see phase notes).

### Web dashboard (URL-driven only)

- `web/src/lib/vocky/types.ts`: `VockyFeedback.recorded_by: string | null` (the record
  interface is named `VockyFeedback`, not `VockyFeedbackRecord` as phase.md wrote it), and
  `VockyFeedbackQuery.recorded_by?: "agent" | "human"` — the literal-union treatment
  `trigger_type` gets.
- `web/src/app/(app)/feedback/page.tsx`: `recorded_by` added to `PARAM_KEYS` (so
  blank ⇒ absent still holds, and it survives a filter submit + pagination) and narrowed in
  `toQuery` alongside the other enum params. **`FORM_FIELD_KEYS` untouched** — no new
  rendered control.
- `web/src/app/(app)/feedback/[feedbackId]/page.tsx`: one `<Field>` row before the
  Trigger row. `Field` renders `children ?? <Empty />`, so a `null` marker shows the same
  em-dash the neighbouring nullable fields show — no null handling of its own needed.
- `web/src/content/feedback.ts`: the `recordedBy: "Recorded by"` label the row needs.
- `web/tests/vocky-app.test.ts`: the `FEEDBACK` fixture gained `recorded_by: "agent"`, and
  the param-encoding test now sends `recorded_by=agent` and asserts it reaches the URL.

### Tests (terse, existing files only — no new files)

- `tests/test_query_validation.py` — one new case: accepts `" agent "` (trimmed) and
  `"human"`, `None`/blank ⇒ `None` (no filter, never "only unspecified rows"), `"robot"`
  ⇒ `FeedbackQueryValidationError` with the shared message.
- `tests/test_admin_api.py` — the existing like/dislike list fixture now seeds
  `recorded_by = 'agent'` on the like row and leaves the dislike row `NULL`, so one fixture
  covers both states: asserts the serialized field (`"agent"` and `null`) and that
  `?recorded_by=agent` narrows the list to one record. The validation-errors test gained the
  400 case.
- `tests/test_user_feedback_api.py` — the duplicated normalizer + serializer are proved
  independently: `_seed_feedback` gained a `recorded_by` kwarg, the scope test seeds
  `"human"`, asserts the field round-trips, and a second request with `recorded_by=agent`
  returns `[]` (an ignored filter would have returned the row).

## Validation

| Command | Result |
| --- | --- |
| `uv run pytest tests/test_query_validation.py -q` | **11 passed** |
| `uv run pytest tests/test_admin_api.py tests/test_user_feedback_api.py tests/test_app_feedback_api.py tests/test_project_feedback_api.py -q` | **36 passed** |
| `make test` (full suite, live compose stack + `TEST_DATABASE_URL`) | **238 passed** (S1 left 237; +1 = the new validator case) |
| `make check-skill-parity` | PASS (untouched by this slice, run as a guard) |
| `cd web && npm test` | **78 passed / 10 files** |
| `cd web && npm run typecheck` | clean |
| `cd web && npm run lint` | clean |
| `cd web && npm run format:check` | clean (after `npx prettier --write` on the one file it flagged — see below) |
| `python3 scripts/workflow.py validate` | Workflow validation passed |

Everything ran locally; nothing was skipped. The compose stack (`vocky-postgres`,
`vocky-redis`, `vocky-app`, `vocky-worker`) was already up.

CI installs web deps with **pnpm**; I used the local `npm`/`npx` (no lockfile change —
`git status` shows no `web/package-lock.json` or `pnpm-lock.yaml` diff).

Prettier reformatted the multi-line destructure in `toQuery` in
`web/src/app/(app)/feedback/page.tsx` (5 names no longer fit one line). That is the only
formatting churn; `format:check` is green.

## Deviations from `plan.md`

1. **`normalize_recorded_by_filter` delegates instead of importing `ALLOWED_RECORDED_BY`.**
   The plan said to import the tuple; the template it also told me to follow
   (`normalize_trigger_type_filter`) delegates to `vocky.trigger.normalize_trigger_type` and
   re-raises. Delegating satisfies S1's actual constraint ("never re-declare the
   vocabulary") more completely — the tuple, the trim/blank rule, and the error string are
   all reused — while importing the tuple alone would have meant hand-writing a second
   membership check and a second copy of the message. `RecordedByValidationError` and
   `normalize_recorded_by` are imported; `ALLOWED_RECORDED_BY` is reached through them.

2. **One existing test assertion was edited** — `tests/test_admin_api.py`'s
   `test_admin_list_feedback_preserves_legacy_channel_filter` asserts the whole serialized
   record as an exact dict, so it gained `"recorded_by": None`. The plan's "existing test
   assertions stay untouched" cannot hold for a full-record snapshot when the design
   requires the serializer to emit a new key. I re-read the design as the phase constraint
   demands: **additivity here is a client-contract property, and it holds** — the JSON gains
   one nullable key, no key changes meaning or type, and no existing client breaks. The
   snapshot is a test-side mirror of the serializer, not a client. It is the only such
   assertion in the suite (checked: it is the sole full-record exact-dict comparison across
   `tests/` and `web/tests/`); the `"recorded_by": None` line is the entire edit, and its
   `null` value is itself the additivity proof.

3. **`web/src/content/feedback.ts` was edited** (not listed in the plan's file set). The
   detail row needs a label, and every other `Field` reads its label from this file. Copy
   for an established metadata row — not visual design, and no control was added.

No other deviations. Scope held: no metrics change, no PATCH-allowlist change, no
`FORM_FIELD_KEYS` change, no new test files, no doc versions, no commits, no status
transitions.

## Notes for later slices

Recorded in `phase.md` under "Landed in `P14.S2`" — the short version: S3's live round-trip
can now assert the filtered read (`?recorded_by=agent`) on all four REST surfaces, and S4
has three concrete README spots to update (the capture-payload examples, the trigger-fields
paragraph at ~L264, and the admin-list-filters sentence at ~L446) plus the open CLI
question.
