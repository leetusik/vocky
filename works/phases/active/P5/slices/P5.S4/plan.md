# P5.S4 — Feedback read commands (`/app/feedback`)

## Context

Fourth slice of **P5** (the last implementation slice). Add the read-only `feedback` command group so a signed-in user can find and read feedback across **all their projects** from the terminal — the last piece of "fully usable without the website." Session-authed over `/app/feedback` (Korean-safe substring search). Pure client — no backend change.

Read `works/phases/active/P5/phase.md` first (Findings, Constraints, S1–S3 notes). Read-only by design: **no** management verbs (PATCH/DELETE/comments) — those live on the `vk_`-keyed `/api/project/feedback` and are out of P5 scope.

Follows the S3 module shape exactly (`src/vocky/cli/projects.py`): a `typer.Typer()` group + `register(app)`, `ctx.obj.authed_client()`, `with cli_errors():`, and the same compact output helpers (`_short` for ids, `_date` for timestamps — define locally or import from `projects`).

Backend contract (from `phase.md` Findings / `docs/current/api.md`): `GET /app/feedback` cross-project list/search — query `q` (free-text substring, Korean-safe), `project_id` (narrow to one owned project), `limit`, `cursor`, plus standard filters → `{records:[<record + project_id>, ...], next_cursor?}`; each record has `id, message, feedback_value(1 like/2 dislike/null), comment, channel, tags, target_*, source_product, ingested_at, project_id, …`. `GET /app/feedback/{id}` → `{record: <record + project_id + comments[] + attachments[]>}`. 404 (never 403) on a cross-tenant/unknown id; 400 on a malformed `project_id`.

## Approach

**New `src/vocky/cli/feedback.py`** — a `feedback_app = typer.Typer(...)` group with three commands, wired by `register(app)` → `app.add_typer(feedback_app, name="feedback")`:

- **`vocky feedback list`** — options `--project <id>` (narrow to one owned project), `--limit <n>`, `--cursor <c>`. `GET /app/feedback` with those params. Render newest-first via a shared `_render_records(records)`: one line per record — short id, a like/dislike/`·` marker from `feedback_value`, short `project_id`, ingested date, and the `message` truncated to ~60 chars. Empty → `No feedback yet.` When `next_cursor` is present, print a trailing hint: `— more: rerun with --cursor <next_cursor>`.
- **`vocky feedback search <query>`** — argument `query`; same `--project`/`--limit`/`--cursor`. `GET /app/feedback` with `q=<query>` (+ params). Reuses `_render_records`. Empty → `No feedback matches "<query>".`
- **`vocky feedback show <feedback_id>`** — argument `feedback_id`. `GET /app/feedback/{id}`. Print the full record readably: id, project_id, feedback_value (like/dislike/none), source_product, channel, tags, target_type/target_text when present, created/ingested, the user `comment`, the full `message`, then any **operator comments** (author + body, oldest-first) and **attachments** (filename + relative `url`). 404 detail ("feedback not found") surfaces via the client's `ApiError`.

Then register from the bottom of `src/vocky/cli/app.py`: `from vocky.cli import feedback; feedback.register(app)`.

`feedback_value` → text: `1`→`like`, `2`→`dislike`, `null`→`·`/`none`. Truncate `message` by character slice (Korean-safe — Python slices by code point).

## Files
- `src/vocky/cli/feedback.py` — **new**; `feedback` group (`list`/`search`/`show`) + `register`.
- `src/vocky/cli/app.py` — register `feedback`.
- `tests/test_cli_feedback.py` — **new**, small.

## Tests (keep small — one terse file)

`tests/test_cli_feedback.py`: `CliRunner` + `httpx.MockTransport` + `VOCKY_CONFIG_DIR`→`tmp_path` with a token pre-stored; inject the transport by monkeypatching the client factory (same seam as `tests/test_cli_projects.py`). ~4 cases:
- `feedback list` → renders a record row **and** the `--cursor` hint when `next_cursor` is returned.
- `feedback list` empty → `No feedback yet.`
- `feedback search 결제` → the request carries `q=결제` (assert in the handler) and renders the match (Korean round-trips).
- `feedback show <id>` → renders the message plus an operator comment / attachment from the `{record: …}` payload.

## Verification (run the code end-to-end)

The local server is up at `http://127.0.0.1:8000`. Using a throwaway `VOCKY_CONFIG_DIR` + a fresh signed-up account, mint a `vk_` key, POST one `/api/feedback` with that key (or reuse `vocky-smoke`'s flow) so there's a record, then:
- `uv run vocky feedback list` → shows the row (+ cursor hint if paged).
- `uv run vocky feedback search <word-in-message>` → returns the match; a nonsense query → the empty-match line.
- `uv run vocky feedback show <id>` → the full record renders; a random UUID → "feedback not found", exit 1.
- `uv run pytest tests/test_cli_feedback.py tests/test_cli_projects.py tests/test_cli_auth.py tests/test_cli_foundation.py` all green.
- `python3 scripts/workflow.py validate` passes.

## Notes for the executor
- Read-only — no management verbs, no server/`admin_assets` change.
- Append a one-line **"Doc impact"** note to `phase.md` (the `vocky feedback list/search/show` cross-project read surface, Korean-safe search) for REVIEW to fold into `experience.md`. Do **not** run `doc-new-version`.
- With S4 done, the whole CLI command surface exists; note in `result.md` that S5 (guide docs + README) can now document the real, finished commands. Do not commit or transition status.
