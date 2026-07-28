# P5.REVIEW — Phase review: CLI & Agent-First Onboarding

## Re-review (after P5.F1)

This is the **re-review**. The first review returned `changes_requested` for one issue — the documented `vocky feedback list → show` journey dead-ended because list rows printed 8-char truncated ids. **P5.F1** (now `done`, commit `2a570ee`) fixed it: `feedback list`/`search`, `projects list`, and the `usage` project listing now print **full copy-pasteable ids**, plus a friendly message for a malformed feedback id; F1 verified the round-trip live and reported 190 tests green. **Confirm that fix closed the gap** (`feedback list` full id → `feedback show <id>` renders; `feedback show <bad>` → friendly hint, exit 1; `projects list` full id accepted by `projects show`/`usage --project`), then proceed with the full validation + review + (on pass) doc consolidation below. Everything else already passed last round.

## Context

Final slice of **P5**. All five implementation slices are `done` and committed (foundation → auth → projects/keys/usage → feedback read → guide docs) plus the P5.F1 fix. This slice validates the whole phase together, reviews it against the objective / `intent.md` / durable docs, and — **only on a passing review** — consolidates the accumulated "Doc impact" notes into new durable-doc versions. You (`slice-executor-high`) are the one slice permitted to run `doc-new-version`.

Read `works/phases/active/P5/phase.md` in full first — especially the "Doc impact" list (the durable-truth deltas to consolidate) and the S1–S5 cross-slice notes. Also read `works/phases/active/P5/intent.md` and `phase.json` (the objective).

**Objective**: "Ship a vocky CLI so a user can sign up, log in, and configure credentials from Claude Code or Codex, with agent-readable help/guide docs so vocky is fully usable without visiting the website." **Intent**: agent-first onboarding — a coding agent drives the whole flow headlessly, no website needed.

## What to do

**1. Validate the phase as a whole** (behavioral validation is consolidated here — the orchestrator trusted each slice's `done` and only ran state `validate`):
- `uv run pytest` — full suite must pass (S5 reported 187 passing).
- CLI reality check: `uv run vocky --version` (→ `0.1.0`), `uv run vocky --help`, and each group's help (`projects`/`keys`/`feedback --help`) render and match the documented surface.
- Entry-point swap intact: `vocky` = CLI, `vocky-server` = server (pyproject `[project.scripts]`; `Dockerfile`/`docker-compose.yml` use `vocky-server`).
- If the local server at `http://127.0.0.1:8000` is reachable, spot-run the documented spine once (throwaway `VOCKY_CONFIG_DIR`): `vocky signup --password-stdin` → `projects create` → `keys mint` → `curl POST /api/feedback` with the `vk_` key → `vocky feedback search`. If unreachable, note it and rely on the unit suite (S2–S5 each already ran it live).
- `python3 scripts/workflow.py validate` — state integrity.

**2. Review against objective / intent / docs.** Confirm: the CLI delivers the full signup→login→credential-setup→use flow from the terminal (objective met); it's genuinely **agent-first** (headless `--password-stdin`, `--base-url`, `VOCKY_CONFIG_DIR`, no interactive-only paths); the guide docs (`README.md` + `docs/cli.md`) let a user/agent operate vocky without the website; it stayed a **pure client** (verify `git diff --stat main` touches only `src/vocky/cli/*`, `tests/test_cli_*`, packaging files, `README.md`, `docs/cli.md`, `works/*` — no server/model/endpoint change); tests are small per the repo rule; nothing touched `src/vocky/admin_assets/docs.json`. Sanity-check the refreshed README for residual stale-model claims.

**3. On a passing review, consolidate durable-doc versions** — `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "…" --source P5.REVIEW`, then edit **only** the new `docs/versions/<doc>/vNNNN_*.md` file, then `python3 scripts/workflow.py rebuild-docs`. Per the `phase.md` "Doc impact" list:
- **`experience.md`** — the CLI onboarding journey (signup→project→key→capture→read as `vocky` commands, the "for coding agents" contract, show-once key), noting `docs/cli.md` as the full hand-written reference.
- **`product.md`** — the `vocky` CLI is a first-class user surface alongside the web app; the whole spine is completable from the terminal without the website.
- **`operations.md`** — the `vocky-server` server-entry rename; CLI install (`uv tool install .` / `uvx` / in-repo `uv run vocky`; PyPI publish is P6) and its `~/.config/vocky/config.json` (`0700`/`0600`, `VOCKY_CONFIG_DIR`) session store.
- Reviewer judgment on two the slices flagged "no contract change" — decide and, if warranted, version briefly: **`architecture.md`** (the CLI as a new pure-client surface, mirroring the web-app "client of `/auth`+`/app`, no backend change" framing) and **`security.md`** (the on-disk 30-day session token at `0600`; the CLI holds the session token — not the `vk_` key — while minting `vk_` keys for `/api/*`). `api.md` needs **no** change. Follow the durable-doc rules in `docs/README.md`; keep each new version tight and accurate.

**4. Return a `review_verdict`** (`pass` / `changes_requested` / `blocked`) with a short rationale, and for `changes_requested` the specific fix slices to create.

## Constraints
- **Review-authored changes are docs-only, and only on a pass**: new `docs/versions/<doc>/…` files via `doc-new-version` + `rebuild-docs`. **No source edits, no `README.md`/`docs/cli.md` edits** (already correct), **no** hand-edits to `docs/current/*` (generated).
- Do **not** commit and do **not** transition slice/phase status — the orchestrator records the verdict via `review-phase` (which transitions both the phase and this REVIEW slice) and commits.

## Verification
- `uv run pytest` green; CLI `--help` correct; `python3 scripts/workflow.py validate` passes.
- `python3 scripts/workflow.py docs` shows the new versions after consolidation; `rebuild-docs` regenerated `docs/current/*.md`.
