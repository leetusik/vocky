# P5.S4 — Feedback read commands — result

Added the read-only `vocky feedback` command group over the session-authed
`/app/feedback` surface, completing the CLI command surface (last implementation
slice of P5). Pure client — no backend/middleware/model change, and
`admin_assets/docs.json` untouched.

## What I built

**New `src/vocky/cli/feedback.py`** — a `feedback_app = typer.Typer(...)` group,
wired by `register(app)` → `app.add_typer(feedback_app, name="feedback")`,
following the S3 `projects.py` module shape exactly (bodies defined at module
scope, mounted in `register`, imports only `context`; `authed_client()` for every
call; `with cli_errors():` bodies; local `_short`/`_date` helpers). Three
commands:

- **`vocky feedback list`** — `--project` / `--limit` / `--cursor`. `GET
  /app/feedback` with those params. Renders newest-first via the shared
  `_render_records` (short id, `like`/`dislike`/`·` marker from `feedback_value`,
  short `project_id`, ingested date, message collapsed + truncated to ~60 code
  points — Korean-safe). Empty → `No feedback yet.` `next_cursor` present →
  trailing `— more: rerun with --cursor <next_cursor>` hint.
- **`vocky feedback search <query>`** — same options, adds `q=<query>`. Reuses
  `_render_records`. Empty → `No feedback matches "<query>".`
- **`vocky feedback show <feedback_id>`** — `GET /app/feedback/{id}`. Renders the
  full record readably (id, project, feedback word, source, channel, tags,
  target/target_text when present, event_at/ingested_at, user note, full
  message), then operator **comments** (`[author] body`) and **attachments**
  (`filename  url`) from the `{record: …}` payload. A cross-tenant/unknown id
  surfaces the server's `feedback not found` 404 via the client's `ApiError` (to
  stderr, exit 1).

Shared helpers: `_list_params` (builds `project_id`/`limit`/`cursor`),
`_render_records`, `_render_cursor_hint`, `_value_marker` (list: `·` when
unrated) / `_value_word` (show: `none` when unrated), `_truncate` (slices by code
point so Korean isn't cut mid-character). The three options are module-scope
`typer.Option(None, …)` objects reused across `list` and `search`; `--project` is
**optional** here (narrow), unlike keys' required `--project`.

**`src/vocky/cli/app.py`** — registered the group with one bottom-of-file import +
`feedback.register(app)` (kept alphabetical with the existing `auth`/`projects`
lines).

**`tests/test_cli_feedback.py`** — new, terse, 4 cases (same recipe as
`test_cli_projects.py`: `CliRunner` + `httpx.MockTransport` injected via patched
`CliContext.make_client`, `VOCKY_CONFIG_DIR`→`tmp_path`, token pre-stored):
list renders a row + the `--cursor` hint; list empty → `No feedback yet.`; search
`결제` asserts `request.url.params.get("q") == "결제"` and the Korean message
round-trips; show renders message + an operator comment + an attachment.

## Key decisions

- Defined `_short`/`_date` locally (not imported from `projects`) — the plan
  allowed either; local keeps the module self-contained and matching the
  `projects.py` pattern, and avoids a feedback→projects import edge.
- `list` sends `params or None` (no empty query string when no flags); `search`
  always sends params (it always has `q`).
- `show` prints optional fields (tags/target/target_text/event_at/user note/
  comments/attachments) only when present, so a bare record stays clean.

## Verification (all run, all green)

- **Unit tests** — `uv run pytest tests/test_cli_feedback.py tests/test_cli_projects.py tests/test_cli_auth.py tests/test_cli_foundation.py`
  → **18 passed** in 0.10s.
- **`python3 scripts/workflow.py validate`** → **Workflow validation passed.**
- **Live end-to-end against `http://127.0.0.1:8000` (server was up)** — throwaway
  `VOCKY_CONFIG_DIR` + fresh signup, created a project, minted a `vk_` key, POSTed
  two `/api/feedback` events (a Korean dislike + an English like, both `202
  accepted`), waited for worker persistence, then:
  - `vocky feedback list` → both rows (like/dislike markers, short project id,
    date, message; Korean rendered intact).
  - `vocky feedback list --project <id>` → same two rows (narrow works).
  - `vocky feedback search 결제` → the Korean dislike row only (Korean substring
    round-trips through the URL).
  - `vocky feedback search export` → the English like row only.
  - `vocky feedback search zzznope` → `No feedback matches "zzznope".`
  - `vocky feedback show <real id>` → full record rendered (dislike, source
    `s4-e2e`, target `message` / `checkout page`, ingested_at, full Korean
    message).
  - `vocky feedback show 99999999-…` (random UUID) → `feedback not found`, exit 1.

## Deviations

None. Built exactly as `plan.md` specifies.

## Doc impact (appended to phase.md — not versioned here)

Recorded the `vocky feedback list/search/show` cross-project read surface
(Korean-safe substring search, `--project` narrowing, `--cursor` keyset paging,
read-only) for REVIEW to fold into `experience.md`.

## Note for S5

With S4 done, the **whole CLI command surface now exists** (auth + projects/keys/
usage + feedback read). S5 (guide docs + README refresh) can document the real,
finished commands — the signup→project→key→capture→read walkthrough maps directly
onto `vocky signup` → `vocky projects create` → `vocky keys mint` → capture via
`vk_` → `vocky feedback list/search/show`, all verified live above.
