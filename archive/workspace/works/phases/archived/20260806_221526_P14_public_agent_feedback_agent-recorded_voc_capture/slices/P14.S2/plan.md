# Plan — P14.S2: Expose `recorded_by` on every read, filter, and dashboard surface

## Job

Implement the whole **read** path for the `recorded_by` marker. Read `works/phases/active/P14/phase.md` in full first — decisions D1–D3, "The read path", "The web dashboard", the S1 cross-slice notes, and "Constraints for every slice" are your spec. S1 already landed the column, the `vocky.recorded_by` validator, and the write path; after S2 every list/read surface returns the field and can filter on it, and the dashboard can split agent vs human via the URL.

## Scope

1. **Typed filters** — `feedback/types.py:FeedbackQueryFilters` gains `recorded_by: str | None = None`; `repository._apply_filters` gains the uniform predicate (`if filters.recorded_by is not None: ... == filters.recorded_by`).
2. **Filter validator** — in `tools/query_feedback_common.py`, add `normalize_recorded_by_filter` following the `normalize_trigger_type_filter` template, **importing `ALLOWED_RECORDED_BY` from `vocky.recorded_by`** (S1's note: never re-declare the vocabulary).
3. **Query normalizers — both of them** (phase.md warns they're duplicated):
   - `admin_api.normalize_list_query` — one edit covers `/admin` list, `/app/feedback`, and `/api/project/feedback`.
   - `api.normalize_user_feedback_query` — the separate end-user `GET /api/feedback` normalizer.
4. **Serializers — both of them**: `tools/query_feedback_common.serialize_record` (shared by admin/app/project) and `api.serialize_user_feedback_record` (the duplicate) each emit `recorded_by`.
5. **Web dashboard (URL-driven only — no new form control, see phase.md "Explicitly out of scope")**:
   - `web/src/lib/vocky/types.ts`: add to `VockyFeedbackRecord`; extend `VockyFeedbackQuery` the same way `trigger_type` is done (literal union `"agent" | "human"`).
   - `web/src/app/(app)/feedback/page.tsx`: add `recorded_by` to `PARAM_KEYS` (blank ⇒ absent stays load-bearing) and to `toQuery`; **do not touch `FORM_FIELD_KEYS`**.
   - `web/src/app/(app)/feedback/[feedbackId]/page.tsx` (~line 228): one row in the existing detail metadata list rendering `record.recorded_by` (handle null as the neighboring fields do).
   - `web/tests/vocky-app.test.ts`: extend the record fixture.
6. **Tests, terse, existing files**: extend `tests/test_query_validation.py` (filter accepts `agent`/`human`, rejects junk, absent ⇒ no filter) and whichever existing file covers list-serialization round-trips (assert the field appears and filtering narrows results). Minimal high-value cases; no new test files.

## Out of scope / must-nots

- **No new rendered form control** — a visible agent/human filter chip is design-cowork territory. URL param + typed field + detail-row only.
- No marker-specific metrics (`FeedbackMetricsQuery` untouched).
- Admin PATCH allowlist untouched — `recorded_by` is provenance (D1).
- Live E2E proof is S3; docs/SKILL.md are S4.
- Additivity: responses gain one field; existing clients and existing test assertions stay untouched.

## Validation

`uv run pytest` targeted files, then the full `make test` if the stack is up (S1 left it green at 237 passed — `.env` + compose stack, see phase.md "Environment"). Web: run the web test suite the way the repo does (check `web/package.json` scripts; likely `npm test` / `vitest` from `web/`), plus the repo's web lint/typecheck target if one exists. If anything cannot run locally, say so in the verdict rather than skipping silently.

## Deliverables

- Code + tests as above.
- `result.md` in this slice folder (free-form).
- Append cross-slice notes and any one-line "Doc impact" notes to `phase.md` (expected: api.md — every read surface returns + filters `recorded_by`; frontend.md — dashboard query param and detail row, if frontend.md documents that surface).
- Structured verdict.
