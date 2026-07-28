# P11.S4 result — canonical skill, served copy, parity gate, first CI workflow

## What shipped

1. **`skills/vocky-feedback/SKILL.md`** (canonical, 119 lines, 7,975 bytes) — a new top-level, non-dot
   `skills/` directory (verified free of any prior `skills/` entry via `git ls-files`). Frontmatter is
   `name` / `description` / `allowed-tools`, three unquoted single-line scalars, `---`-delimited, in that
   order, matching the in-tree convention. `disable-model-invocation` is deliberately omitted (this is an
   end-user product skill, unlike 14 of the 16 repo-workflow skills). The `description` carries a hard
   negative trigger in the `design-cowork` idiom ("NOT for general note-taking, drafting tickets for
   another tracker, or capturing anything the user has not asked to send anywhere"). `allowed-tools` is a
   scoped inline list: `Bash(curl:*), Bash(vocky capture:*), Bash(vocky keys:*), Read`. Body opens `# vocky-feedback`.

   Section headings (H2, numbered):
   1. Set up the two-variable contract
   2. Verify before you capture anything
   3. Path A — capture with the CLI (primary, one command)
   4. Path B — raw REST (no vocky install required)
   5. Path C — `/mcp` (alternative transport, not detailed here)
   6. Error handling — branch by branch
   7. Report back

2. **`web/public/SKILL.md`** — a committed byte-identical copy (verified with `cmp`, not generated at
   build time).

3. **`web/.prettierignore`** — added `public/` (was previously uncovered; only `pnpm-lock.yaml`, `.next/`,
   `out/`, `build/`, `node_modules/` were ignored). Without this, prettier's markdown reflow would rewrite
   `web/public/SKILL.md` and break byte parity the moment anyone runs `pnpm format`.

4. **`scripts/skill_parity.py`** — stdlib-only, `#!/usr/bin/env python3`, `from __future__ import
   annotations`, a spec-as-docstring, a `main()`, exit code is the contract (`0` pass / `1` fail via
   `raise SystemExit(...)`, mirroring `scripts/wait_for_health.py`). Compares
   `skills/vocky-feedback/SKILL.md` (canonical) against `web/public/SKILL.md` (served) as full-file bytes.
   Two `FAIL —` failure modes (missing file, byte mismatch with a `cp` fix hint); one `PASS —` success
   line. Left non-executable (`rw-r--r--`), matching `wait_for_health.py`'s own permission bits.

5. **`Makefile`** — added `check-skill-parity` to the `.PHONY` line and a `check-skill-parity:
   python3 scripts/skill_parity.py` target (plain `python3`, no `uv run`/`uv sync` — this script has no
   project dependencies, unlike `wait-ready`'s `uv run python` form).

6. **`.github/workflows/ci.yml`** — the repo's first push/pull_request gate (`deploy-production.yml` stays
   `workflow_dispatch`-only). Header comment explains the workflow's role and its two deliberate
   exclusions. `on: push: branches: [main]` + `pull_request:`; top-level `permissions: contents: read`.
   Three jobs, each `runs-on: ubuntu-latest`, Title Case job names, sentence-case step names,
   `shell: bash` + `set -euo pipefail` on every inline script, `actions/checkout@v4`:
   - **Skill Parity** — `python3 scripts/skill_parity.py`.
   - **Installer Syntax** — `bash -n web/public/install.sh` (mirrors the deploy workflow's "Validate
     deploy helpers" precedent).
   - **Web (lint, typecheck, test)** — Node 22 via `actions/setup-node@v4`, pnpm 10.28.2 via
     `corepack enable && corepack prepare pnpm@10.28.2 --activate` (matching `web/Dockerfile:11`, not
     `pnpm/action-setup`), `pnpm install --frozen-lockfile` (matching `web/Dockerfile:17`), then
     `pnpm lint`, `pnpm typecheck`, `pnpm test`.

   **Deliberately excluded, and why** (both recorded in the header comment and here so the review doesn't
   read them as oversights):
   - No `pnpm exec prettier --check .` / `format:check` job — 12 pre-existing failures in files this slice
     has no business touching (verified unchanged below).
   - No pytest job — needs a live Postgres a bare GitHub runner doesn't have; P12 adds it with a service
     container. The three-job shape (independent jobs, no shared setup step) is meant to make that
     addition a new job, not a rewrite.

## Validation — verbatim output

1. `python3 scripts/skill_parity.py`
   ```
   PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.
   ```
   exit 0.

2. **Red-then-green proof** (a gate never seen failing is not a verified gate):
   ```
   $ printf 'X' >> web/public/SKILL.md && python3 scripts/skill_parity.py
   FAIL — web/public/SKILL.md is not a byte-for-byte copy of skills/vocky-feedback/SKILL.md. Fix: cp skills/vocky-feedback/SKILL.md web/public/SKILL.md
   exit 1
   $ cp skills/vocky-feedback/SKILL.md web/public/SKILL.md && python3 scripts/skill_parity.py
   PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.
   exit 0
   ```

3. `cmp skills/vocky-feedback/SKILL.md web/public/SKILL.md` → no output, identical (exit 0).

4. `make check-skill-parity`:
   ```
   python3 scripts/skill_parity.py
   PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.
   ```
   exit 0.

5. From `web/`:
   - `pnpm lint` → exit 0, clean.
   - `pnpm typecheck` → exit 0, clean.
   - `pnpm test` → `Test Files 5 passed (5)`, `Tests 61 passed (61)`, exit 0 — unchanged from the S1/S2/S3
     baseline; adding files to `public/` did not change the app build.

6. `pnpm exec prettier --check .` from `web/` → still **exactly 12** pre-existing failures
   (`README.md`, `src/app/(app)/projects/[projectId]/actions.ts`, `src/app/apple-icon.tsx`,
   `src/app/opengraph-image.tsx`, `src/lib/bff.ts`, `src/lib/env.ts`, `src/lib/session.ts`,
   `src/lib/vocky/auth.ts`, `tests/auth-routes.test.ts`, `tests/session-guards.test.ts`,
   `tests/session.test.ts`, `tests/vocky-auth.test.ts`), exit 1 as before. `public/SKILL.md` is **not**
   among them — confirms the `.prettierignore` addition works.

7. **Clean-checkout lockfile check**: `rm -rf` on scratch/backup paths was denied by the sandbox's
   permission system, but `mv` was allowed, so the real rehearsal ran: moved `web/node_modules` aside
   (`mv web/node_modules web/node_modules.bak.<pid>`), then from `web/`:
   ```
   $ pnpm install --frozen-lockfile
   Lockfile is up to date, resolution step is skipped
   Packages: +392
   ...
   Done in 2.3s using pnpm v10.28.2
   ```
   exit 0 — the committed `web/pnpm-lock.yaml` installs clean with no drift from zero prior
   `node_modules`. Re-ran `pnpm lint` / `pnpm typecheck` / `pnpm test` against the freshly installed tree
   to confirm it is fully usable, not just present: all exit 0, 61/61 tests (the backup directory,
   `node_modules.bak.<pid>`, briefly caused a stray `tsc` failure by being included in the typecheck scan —
   moved out of `web/` entirely, after which typecheck was clean again). The backup was moved to the
   session scratchpad, not deleted or left in the repo; `web/node_modules` now holds only the fresh install
   and remains untracked/gitignored as before (`git status` shows no diff under `web/node_modules`).

8. `bash -n web/public/install.sh` → exit 0.

9. **Workflow YAML lint**: plain `python3 -c "import sys, yaml"` failed (`ModuleNotFoundError: No module
   named 'yaml'` — PyYAML not on the bare interpreter, as the plan anticipated). Fell back to
   `uv run python -c "import yaml,pathlib;yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text());print('yaml ok')"`
   → printed `yaml ok`, confirming the file parses as valid YAML.

10. `uv run pytest -q` → `209 passed in 9.24s`, unchanged from the S2/S3 baseline (this environment has a
    live Postgres, so 0 errors as expected — no delta introduced by this slice, which touched no Python
    application code).

11. `python3 scripts/workflow.py validate` → `Workflow validation passed.`

## What was NOT proven (state plainly, per the plan)

- **The workflow has never executed on a GitHub runner.** It cannot — it hasn't been pushed, and GitHub
  `main` is 45 commits behind local (per `phase.md`'s hand-off section). Every check above was run locally
  against the same commands the workflow's steps invoke, not the workflow itself under `act` or on a real
  runner.
- **`/SKILL.md` has never been fetched from a live origin.** The site is not deployed
  (`docs/current/experience.md:14`); `https://vocky.hi2vi.com/SKILL.md` reads `404` today and is expected
  to flip to `200` only after P12's bring-up, per the phase's armed flip probes.

## Deviations from `plan.md`

- **Resolved an internal ambiguity in the plan's own wording, in favor of the more specific statement.**
  Part 1's "Content" section opens with "Author it in knowledge's idiom … Numbered H2 steps. Two capture
  paths, REST primary," but the very next paragraphs label the CLI "Path A — the CLI (primary, one
  command)" and REST "Path B … for an agent with no vocky install." I treated "REST primary" as an
  imprecise carry-over from describing knowledge's own skill (which has no CLI at all) and followed the
  explicit, vocky-specific "Path A … primary" instead — consistent with `phase.md`'s "S2 done" notes,
  which frame `vocky capture` as the first-class consumer `VOCKY_API_TOKEN` was built for. The skill leads
  with the CLI (step 3) and documents REST second (step 4). Flagging this for the review in case the
  intended reading was actually REST-first.
- No other deviations. Validation step 7's move-`node_modules`-aside rehearsal ran exactly as the plan
  describes once `mv` (rather than the initially-denied `rm -rf`) was used to relocate the backup — see
  validation step 7 above for the transcript.
- Everything else — file locations, frontmatter shape, error-handling table, CI job/step shape, the
  `.prettierignore` fix, the Makefile target — was implemented exactly as specified, verified line-by-line
  against `src/vocky/capture.py`, `src/vocky/api.py`, `src/vocky/auth.py`, `src/vocky/cli/context.py`,
  `src/vocky/cli/projects.py`, `src/vocky/mcp_server.py`, `src/vocky/tools/capture_feedback.py`,
  `web/public/install.sh`, and `pyproject.toml` before writing the skill.

## Doc impact

Appended one line to `phase.md`'s `## Doc impact` section (see there) — this slice changes durable truth
in several places (a published end-user skill, the first CI gate, the CLI-primary two-variable agent
contract). No `doc-new-version` was run; no `docs/current/*.md` file was hand-edited.

## Not committed

No `git commit`/`git add`/`git push` was run. No slice or phase status was changed (`slice.json`'s
`status` remains whatever the orchestrator set before dispatch).
