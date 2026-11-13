# P5.REVIEW result — Phase review: CLI & Agent-First Onboarding

## Re-review after P5.F1 — Verdict: `pass`

The first pass returned `changes_requested` for one issue (below). **P5.F1** (`done`,
commit `2a570ee`) fixed it, and this re-review confirms the gap is closed and the
phase validates green as a whole. **Docs consolidated** (this pass only). No commit,
no status transition — the orchestrator records the verdict via `review-phase`.

### Issue 1 — confirmed closed

`vocky feedback list`/`search` now print the **full** feedback id (the `feedback show`
handle) — `src/vocky/cli/feedback.py:_render_records` drops `_short()` on the record
id and keeps only the project-id column short. `projects list` and the `usage` project
listing print the **full** project id (the `--project`/`projects show` handle). And
`feedback show <bad-id>` maps the server's UUID-`400` to a friendly hint
(`'<id>' is not a valid feedback id — copy the full id from \`vocky feedback list\`.`),
exit 1.

Verified two ways:
- **Unit tests (F1-added round-trip):** `test_list_id_round_trips_into_show` (the id
  `feedback list` prints is fed into `feedback show`, which renders),
  `test_show_maps_invalid_id_to_friendly_hint`, and `test_projects_list_prints_full_id`.
- **Live** against `http://127.0.0.1:8000` (throwaway `VOCKY_CONFIG_DIR`, fresh account):
  `projects list` → `bdb2723e-…` full id accepted by `projects show`/`usage --project`;
  captured feedback via a minted `vk_` key → `feedback list` printed the full 36-char id
  `12391f7b-b354-…` (project column short `bdb2723e`), and `feedback show <that full id>`
  rendered the record — **the previously-dead step now works**. `feedback search "결제"`
  (Korean) returned the same full id; `feedback show not-a-uuid` → friendly hint, exit 1.

### Re-validation (whole phase)

| Command | Result |
|---------|--------|
| `uv run pytest` | **190 passed** in ~8s (was 187 + 3 F1 cases) |
| `uv run vocky --version` | `0.1.0` ✓ |
| `uv run vocky --help` + `projects`/`keys`/`feedback --help` | render, match the documented surface ✓ |
| Entry-point swap | `pyproject`: `vocky = vocky.cli:main`, `vocky-server = vocky.main:main`; `Dockerfile`/`docker-compose.yml` use `vocky-server`/`vocky-worker` ✓ |
| Pure-client scope (`e350aae..HEAD`, excl. `works/`) | only `src/vocky/cli/*`, `tests/test_cli_*`, packaging (`pyproject.toml`/`uv.lock`/`Dockerfile`/`docker-compose.yml`), `README.md`, `docs/cli.md` — no server/model/endpoint change ✓ |
| `src/vocky/admin_assets/docs.json` | untouched across the phase (incl. F1) ✓ |
| README stale-model sanity | only the two explicit "is retired" `VOCKY_API_AUTH_TOKEN` notes; no live static-token usage ✓ |
| `python3 scripts/workflow.py validate` | `Workflow validation passed.` ✓ |

Objective met (full signup→login→credential-setup→use flow from the terminal, no
website), genuinely agent-first (headless `--password-stdin`, `--base-url`,
`VOCKY_CONFIG_DIR`, generic-401, errors→stderr/success→stdout, config file `0600`).

### Durable-doc versions consolidated (this pass)

| Doc | New version | Delta |
|-----|-------------|-------|
| `experience` | **v0008** | CLI onboarding journey (signup→project→key→capture→read as `vocky` commands), the "for coding agents" headless contract, show-once key; points to `docs/cli.md` as the full reference |
| `product` | **v0007** | the `vocky` CLI is a first-class user surface alongside the web app; the whole spine is completable from the terminal without the website (Status + First MVP + Product Surface Roles) |
| `operations` | **v0003** | the `vocky-server` server-entry rename; CLI install (`uv tool install .` / `uvx` / in-repo `uv run vocky`; PyPI publish is P6) and its `~/.config/vocky/config.json` (`0700`/`0600`, `VOCKY_CONFIG_DIR`) session store |
| `architecture` | **v0007** | the CLI as a new pure-client surface over `/auth/*`+`/app/*` (Typer app in `src/vocky/cli/`, no backend change), mirroring the web-app client framing; console-script rename |
| `security` | **v0006** | the CLI's on-disk 30-day session token at `~/.config/vocky/config.json` (`0600`) — the first filesystem-resident vocky session credential; holds the session token, mints `vk_` keys for `/api/*` |

`api.md` unchanged (v0006) — the CLI is a pure client, no contract change. `rebuild-docs`
regenerated `docs/current/*`; `docs` and `validate` confirm the new versions.

### Commands run (re-review)

`uv run pytest` (190 passed); `uv run vocky --version|--help` + group help; live spine at
`http://127.0.0.1:8000` (signup `--password-stdin` → projects create/list/show → keys mint →
`curl POST /api/feedback` 202 / no-key 401 → feedback list/search/show + the bad-id hint →
usage --project); `python3 scripts/workflow.py validate`; five `doc-new-version` + `rebuild-docs`.

**Deviations:** none. (As in the first pass, the `git diff main` scope check was run against
the phase's real base `e350aae..HEAD` since P5 is committed on `main`.)

---

## First pass (historical) — Verdict: `changes_requested`

**Verdict: `changes_requested`.** The phase is otherwise excellent — the headline
onboarding + credential spine works flawlessly and headlessly, the CLI is a clean
pure client, and the docs are corrected — but there is one real, reproducible
coherence gap in the documented `feedback` read group that should be fixed before
the phase is sealed and the `experience.md` "onboarding journey" is versioned.
Because the verdict is not `pass`, **no durable docs were versioned** (per the
review contract), and I made no commit and no status transition.

## Validation — commands run and outcomes

| Command | Result |
|---------|--------|
| `uv run pytest` | **187 passed** in 7.84s (full suite green) |
| `uv run vocky --version` | `0.1.0` ✓ |
| `uv run vocky --help` | Renders; lists all groups (signup/login/logout/whoami/usage/projects/keys/feedback) ✓ |
| `uv run vocky projects --help` | `list` / `create` / `show` — matches documented surface ✓ |
| `uv run vocky keys --help` | `mint` / `list` / `revoke` (each `--project`) ✓ |
| `uv run vocky feedback --help` | `list` / `search` / `show` ✓ |
| Entry-point swap | `pyproject [project.scripts]`: `vocky = "vocky.cli:main"`, `vocky-server = "vocky.main:main"`; `Dockerfile` CMD `vocky-server`; `docker-compose.yml` app `command: vocky-server`, worker `vocky-worker` ✓ |
| `python3 scripts/workflow.py validate` | `Workflow validation passed.` ✓ |
| `src/vocky/admin_assets/docs.json` | untouched across the phase and clean in the tree ✓ |

### Pure-client scope check

`git diff --stat main` is empty because P5 was committed **directly on `main`**
(the six P5 commits `cd80f22..fa70931` sit on top of P9; the repo works on `main`,
so `main` == HEAD). The correct phase range is `e350aae..HEAD` (P5.DECOMP's parent).
That diff, excluding `works/*`, touches **only**: `src/vocky/cli/*` (all new),
`tests/test_cli_*.py` (new), packaging (`pyproject.toml`, `uv.lock`, `Dockerfile`,
`docker-compose.yml`), `README.md`, and `docs/cli.md`. **No server endpoint,
middleware, auth, or model change** — the pure-client constraint holds.

### README stale-model sanity check

No residual stale claims: `grep` finds no "single-tenant" framing and no live
static-token usage; the only `VOCKY_API_AUTH_TOKEN` mentions are the two explicit
"is retired" notes. `/api/*` examples use `Authorization: Bearer vk_…`;
`VOCKY_ADMIN_AUTH_TOKEN` retained for `/admin/api/*`.

### Tests are small

`test_cli_auth.py` 130, `test_cli_feedback.py` 157, `test_cli_foundation.py` 114,
`test_cli_projects.py` 138 lines — 4–5 terse cases each, per the repo rule.

### Live spine spot-run (server reachable at http://127.0.0.1:8000)

Ran the documented spine once with a throwaway `VOCKY_CONFIG_DIR`, fresh account:
- `printf 'password12345' | vocky signup --email … --password-stdin` → signed up +
  workspace auto-created; **config file written `0600`** (verified).
- `vocky projects create` → project id `fed60a35-…` (full id printed).
- `vocky keys mint --project <id>` → show-once warning line + `vk_…` key.
- `curl POST /api/feedback` with the `vk_` key + `feedback_value: 2` (Korean
  message) → `202 {status:"accepted"}`; **no-key POST → `401`** (mandatory auth).
- After worker persistence: `vocky feedback list` and `vocky feedback search "결제"`
  both returned the record (Korean substring round-trips); `vocky usage --project`
  → `1 total (0 liked, 1 disliked)` + keys shown by prefix only.

The onboarding + capture + list/search + usage path is verified working headlessly.

## Review against objective / intent

- **Objective — terminal onboarding + credential setup + use, no website:** met for
  the core spine. signup → login/whoami → projects → keys (show-once `vk_`) → capture
  → usage all work from the terminal.
- **Agent-first:** genuinely so — headless `--password-stdin` (password never on
  argv), `--base-url` / `VOCKY_BASE_URL`, isolated `VOCKY_CONFIG_DIR`, generic-401,
  errors→stderr / success→stdout, exit codes. Confirmed live.
- **Guide docs:** `README.md` (public Docs target) refreshed to the multi-tenant/`vk_`
  model with a CLI quickstart + "For coding agents"; `docs/cli.md` is a solid
  self-contained reference with per-step raw-HTTP equivalents. Good.
- **Pure client:** confirmed (scope check above).

## Issue found (numbered) — why `changes_requested`

**Issue 1 — the documented `feedback list → feedback show` flow is unreachable via
CLI-only use; `--project`/`show` can't consume a listed id.**

`vocky feedback list` / `search` render each record's id via `_short(...)` — an
**8-char truncation** (`src/vocky/cli/feedback.py:111`). But `vocky feedback show
<FEEDBACK_ID>` (and `--project`, `projects show`, `keys --project`, `usage
--project`) require the **full UUID**. There is **no CLI command that surfaces a
full feedback record id** (capture returns a `request_id`, not the record id), so a
user or agent who finds a record via `feedback list`/`search` cannot then `feedback
show` it through the CLI.

Reproduction (live, this review):
```
$ vocky feedback list --project <id>
d23b4b3f  dislike  fed60a35  2026-07-18  결제가 안돼요 …
$ vocky feedback show d23b4b3f
feedback_id must be a valid UUID          # raw server-400, exit 1 — dead end
```

Why it matters for this phase specifically: the [S4]/[S5] "Doc impact" notes slate
`experience.md` to document the onboarding journey **including `vocky feedback
list/search/show`**. Versioning that now would enshrine a `list → show` step that
cannot be completed via the CLI alone. The projects family has the same truncation
(`projects list` shows short ids) but is softer, because `projects create` prints
the full id at creation time; feedback has no such escape hatch. The only current
workaround is dropping to raw HTTP `GET /app/feedback` — which cuts against the
"fully usable from the terminal" thesis. `feedback show` itself works correctly when
given a full id (S4 verified live); the defect is purely the id-recovery/copy-paste
path.

### Proposed fix slice

- **P5.F1 — Make listed ids drive the id-consuming commands** (`kind: fix`,
  `risk: medium`). Restore the `feedback list/search → feedback show` and
  `list → --project` flow: e.g. surface the **full** record/project id in
  `feedback list`/`search` (and the `usage`/`projects list` id columns) so it is
  copy-pasteable, **or** resolve a unique short-id **prefix** client-side in `show`
  / `--project`; either way, map the raw `feedback_id must be a valid UUID` 400 to a
  friendly CLI message. Add/extend a terse `test_cli_feedback` case asserting the
  round-trip from a listed id into `show`. Docs-only artifacts (`README.md` /
  `docs/cli.md`) that describe the flow may need a one-line touch-up. Pure client —
  no server change. (The orchestrator writes this slice's `plan.md`; the two
  approaches above are options, not a prescription.)

## Docs

**Not versioned** — the verdict is `changes_requested`, so per the review contract
no `doc-new-version` was run. On a future `pass` (after P5.F1), the review should
consolidate the accumulated "Doc impact" notes into: `experience.md` (CLI onboarding
journey + the four command groups + "for coding agents" contract, referencing
`docs/cli.md`), `product.md` (the `vocky` CLI as a first-class user surface),
`operations.md` (the `vocky-server` rename + CLI install + `~/.config/vocky`
session store), and — reviewer judgment — brief `architecture.md` (CLI as a new
pure-client surface) and `security.md` (on-disk `0600` 30-day session token; CLI
holds the session token, mints `vk_` keys for `/api/*`). `api.md` needs no change.

## Deviations from plan
None. The plan's `git diff --stat main` check was interpreted against the phase's
actual base (`e350aae..HEAD`) since P5 was committed directly on `main`; the
pure-client conclusion is unchanged.
