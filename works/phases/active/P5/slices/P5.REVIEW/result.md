# P5.REVIEW result — Phase review: CLI & Agent-First Onboarding

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
