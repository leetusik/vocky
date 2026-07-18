# P5.F1 result — surface full copy-pasteable ids so `feedback show` / `--project` work CLI-only

## Outcome

`done`. The documented `vocky feedback list → show` journey (and `projects list → show`/`--project`)
now works CLI-only. Fix is pure client — no server/model/endpoint change, `admin_assets/docs.json`
untouched.

## Changes

**`src/vocky/cli/feedback.py`**
- `_render_records`: prints the **full** `record['id']` (dropped `_short()` on the feedback id — it's
  the handle `feedback show` consumes and the server does no prefix matching). The secondary
  project-id column stays short (context only; full project ids come from `projects list`), so
  `_short` is still used and remains defined.
- `_feedback_show`: wraps the `GET /app/feedback/{id}` call in `try/except ApiError`; on status
  `400` (e.g. the server's `feedback_id must be a valid UUID`) it maps to a friendly
  `fail("'<id>' is not a valid feedback id — copy the full id from \`vocky feedback list\`.")`;
  every other error re-raises to keep surfacing the server detail via `cli_errors`. Added imports:
  `ApiError` from `vocky.cli.client`, `fail` from `vocky.cli.context`.

**`src/vocky/cli/projects.py`**
- `_projects_list`: prints the **full** `project['id']` (dropped `_short()`).
- `_usage` project listing: prints the **full** `entry['id']` (dropped `_short()`).
- `_short` became unused in the module and was removed. `_date` stays (still used by list/keys/usage).
- Left `keys list` (already full id) and `usage` credential rows (`token_prefix`, not a handle) alone.

**Tests**
- `tests/test_cli_feedback.py`: `test_list_renders_row_and_cursor_hint` now asserts the **full**
  `FEEDBACK_ID` (not the 8-char prefix); dropped the now-unused `_short` helper. Added
  `test_list_id_round_trips_into_show` (the full id printed by `list` is fed into `show`, which
  renders) and `test_show_maps_invalid_id_to_friendly_hint` (a raw UUID-400 → the friendly hint,
  exit 1).
- `tests/test_cli_projects.py`: added `test_projects_list_prints_full_id` (the first token of a
  `projects list` row equals the full UUID).

## Verification

- `uv run pytest tests/test_cli_feedback.py tests/test_cli_projects.py` → **12 passed**.
- `uv run pytest` (full) → **190 passed** (was 187; +3 new cases).
- `python3 scripts/workflow.py validate` → **Workflow validation passed.**
- **Live round-trip ran** against `http://127.0.0.1:8000` (reachable) with a throwaway
  `VOCKY_CONFIG_DIR` + fresh account:
  - `vocky projects list` → `bba04d59-6efe-4569-87e2-92e1ff808e37  p5f1-proj  (created 2026-07-18)`
    (full id); that exact id accepted by `vocky projects show <id>` and `vocky usage --project <id>`.
  - Captured one feedback via a minted `vk_` key (`POST /api/feedback` → 202); after worker
    persistence `vocky feedback list` printed the full id
    `1623a069-b354-4049-abb6-a77ac08cb35a` (len 36; project column stayed short `bba04d59`), and
    `vocky feedback show 1623a069-b354-4049-abb6-a77ac08cb35a` (the copied full id) rendered the
    record — the previously-broken step now works.
  - `vocky feedback show not-a-uuid` →
    `'not-a-uuid' is not a valid feedback id — copy the full id from \`vocky feedback list\`.`,
    exit 1.

## Doc impact

No durable-doc change — this fixes behavior to match the already-written `README.md` / `docs/cli.md`,
which describe `feedback list → show` and use `<FEEDBACK_ID>` / `<PROJECT_ID>` placeholders (no
literal truncated id shown as copy-pasteable, so nothing to correct). No `doc-new-version` run.

## Deviations

None. Implemented the "print full ids" option the plan chose (over client-side prefix resolution).
