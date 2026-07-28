# P5.F1 — Surface full copy-pasteable ids so `feedback show` / `--project` work CLI-only

## Context

Fix slice from the P5 review's `changes_requested`. The documented **`vocky feedback list → show`** journey dead-ends when driven CLI-only: `feedback list`/`search` print an **8-char truncated** feedback id (`_short()`), but `feedback show <id>` (and every `--project`/`show` consumer) needs the **full UUID**, and the server does **no** prefix matching — so `vocky feedback show d23b4b3f` fails with `feedback_id must be a valid UUID`. No CLI command surfaces a full feedback id, so an agent following the docs hits a wall. The same truncation affects project ids in `projects list` and the `usage` project listing (softer, since `projects create` prints the full id).

Read `works/phases/active/P5/phase.md` (the P5.REVIEW findings at the tail) first. **Root cause**: ids that are *command-argument handles* are rendered truncated. **Fix (chosen over client-side prefix resolution, which can be ambiguous)**: print the **full** id wherever a list feeds a command argument — the id is the actionable handle, so it must be complete and copy-pasteable. Keep other columns compact. Pure client, no backend change.

## Files & changes

**`src/vocky/cli/feedback.py`** — `_render_records` (line ~110): print the **full** `record['id']` (drop `_short()` on the feedback id — it's the handle `feedback show` consumes). The secondary project-id column may stay short (context only; full project ids come from `projects list`), but the feedback id must be full.
- `_feedback_show` (line ~174): on an `ApiError` with status `400` (e.g. `feedback_id must be a valid UUID`), map to a friendly `fail(...)`: `"'<feedback_id>' is not a valid feedback id — copy the full id from \`vocky feedback list\`."` (import `ApiError` from `vocky.cli.client` and `fail` from `vocky.cli.context`; keep the existing `cli_errors()` wrapper for everything else).

**`src/vocky/cli/projects.py`** — the project id is the handle for `projects show`, `keys mint/list/revoke --project`, and `usage --project`, so it must be full where a list emits it:
- `_projects_list` (line ~76): print the **full** `project['id']` (drop `_short()`).
- `_usage` project listing (line ~255): print the **full** `entry['id']` (drop `_short()`).
- (Credential ids in `keys list` are already full — `keys revoke` works. `_short`/`_date` stay for genuinely non-handle context; if `_short` ends up unused in a module, remove it to keep the module clean.)

No change to `keys list` (already full), `usage` credential rows (`token_prefix`, not a handle), or any server code.

## Tests (extend existing files, stay terse)

- `tests/test_cli_feedback.py`: add a **round-trip** assertion — the id printed by `feedback list` is the **full** record id (assert the full UUID appears in `list` output), and a `feedback show` case using that same full id succeeds (MockTransport). Optionally assert the friendly message on a `400`.
- `tests/test_cli_projects.py`: assert `projects list` prints the **full** project id (so `projects show` / `--project` are reachable).

Keep additions minimal — one or two cases per file.

## Verification (run the code)

- `uv run pytest tests/test_cli_feedback.py tests/test_cli_projects.py` (and full `uv run pytest`) green.
- Live against `http://127.0.0.1:8000` (throwaway `VOCKY_CONFIG_DIR`, fresh account, capture one feedback via a `vk_` key): `vocky feedback list` prints a full id; **copy that exact id** into `vocky feedback show <id>` → renders the record (the previously-broken step). `vocky projects list` prints a full id that `vocky projects show <id>` / `vocky usage --project <id>` accept. `vocky feedback show not-a-uuid` → the friendly message, exit 1. If the server is unreachable, say so and rely on the unit tests.
- `python3 scripts/workflow.py validate` passes.

## Notes for the executor
- Pure client — no server/model/endpoint change; do not touch `src/vocky/admin_assets/docs.json`.
- `README.md` / `docs/cli.md` already describe `feedback list → show`; the fix makes that documented flow actually work, so **no doc edit is needed** — but if any example there shows a truncated id as if copy-pasteable, correct it. Append a one-line **"Doc impact"** note only if you change docs; otherwise note "no durable-doc change (fixes behavior to match the already-written docs)". Do **not** run `doc-new-version`.
- Write `result.md`; do not commit or transition status (the orchestrator does both). After this lands, the re-review consolidates the durable-doc versions.
