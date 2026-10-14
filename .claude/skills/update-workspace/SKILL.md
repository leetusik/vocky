---
name: update-workspace
description: Update the current repo's agentic-workspace machinery to the latest upstream cornerstone, preserving your phases, slices, and docs.
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit, Write, Glob, Grep, Bash
disable-model-invocation: true
---

# update-workspace

Update the CURRENT repo's agentic-workspace machinery to the latest upstream cornerstone, preserving your own work. Explicit-invocation only. Run this when the cornerstone has changed since you adopted or last synced and you want this repo to match the current version. (For first-time adoption use `/retrofit` instead.)

What it changes: it OVERWRITES machinery (`scripts/workflow.py`, the `.claude/agents/` subagents, every skill under `.claude/skills/`, `works/templates/*`), additively MERGES `.claude/settings.json`, and refreshes the `CLAUDE.md` contract. It PRESERVES everything under `works/` except templates (your state, phases, slices, deferred jobs) and all of `docs/` (your versioned docs). It never commits.

**Nested personal install.** If `workflow/.agentic-nested.json` exists under the current directory, this is a private (nested) install, the default layout since v50: the engine and state live in the nested git repo `workflow/`, and the skills and agents sit untracked in the host's `.claude/`. Run this skill from the host root (never from inside `workflow/`). Every step below applies, and the steps marked **(nested)** differ. Instead of merging `.claude/settings.json` and refreshing `CLAUDE.md`, a nested update merges `.claude/settings.local.json`, refreshes `workflow/CLAUDE.workspace.md` and the managed block in `CLAUDE.local.md`, and never touches a tracked file. **The installer detects the layout itself**, so steps 5 and 7 run the same plain `--update` command for a nested and an at-root install, with no `--nested` or `--at-root`; it refuses, writing nothing, when it finds both layouts at once or when a flag contradicts the one it found. (A downstream still carrying the v49 text of this skill can keep running `--update --nested`: it matches a nested install and works.)

Preflight (read-only):

1. Confirm a git repo: `git rev-parse --is-inside-work-tree`. If the working tree is dirty (`git status --porcelain` is non-empty), tell the operator and recommend committing or stashing first, so the update lands as a clean, reviewable diff. **(nested)** The update writes only inside `workflow/` and to untracked host files, so check `git -C workflow status --porcelain` instead, and leave the host's own branch and changes alone.
2. Confirm this repo already has the workspace: `works/state.json` (or any `works/phases/active/*/phase.json`) AND `scripts/workflow.py` must exist (**nested:** and `workflow/.agentic-nested.json`). If not, STOP — this repo has not adopted the workspace; use `/retrofit` instead.
3. If `works/.workspace-version.json` exists, read it and report the last-synced commit and time so the operator knows the starting point. Also read its `workspace_version` — the integer version this repo is on (call it **N**). If that key is absent, this repo is **pre-versioning** (adopted before workspace versions existed); note that and treat N as "pre-versioning" in the preview below.

Fetch upstream:

4. Shallow-clone the cornerstone to a temp dir and capture its HEAD commit:

   ```sh
   tmp="$(mktemp -d)"
   git clone --depth 1 https://github.com/leetusik/bootstrap_agentic_workspace.sh.git "$tmp"
   ref="$(git -C "$tmp" rev-parse HEAD)"
   ```

   The clone is a full checkout, so read the upstream version straight from it: the top `## v<M>` heading in `$tmp/CHANGELOG.md` is the **upstream version M**, and the entries under each `## v` describe what that version brings.

Preview the diff (this is the "check what is different" step):

5. First report the version gap, then show the file change-list.

   **Version gap** — compare your local version **N** (from step 3) with the upstream version **M** (the top `## v<M>` in `$tmp/CHANGELOG.md`):
   - N < M: report "workspace vN → upstream vM" and print every `## v` entry in `$tmp/CHANGELOG.md` newer than N (vN+1 … vM) — that is exactly what this sync brings, including any **Migration notes**.
   - Pre-versioning (no local `workspace_version`): say the repo is pre-versioning, then show the upstream `## v` entries and point the operator to `$tmp/CHANGELOG.md` for the full file.
   - N == M: say "already on vM; any file diff below is unreleased upstream drift".

   **File change-list** — run the freshly-cloned installer in dry-run update mode from the repo root; it writes nothing and prints the change-list:

   ```sh
   sh "$tmp/bootstrap_agentic_workspace.sh" . --update --dry-run
   ```

   **(nested)** The same command, run from the host root, detects the nested install (its banner says `(nested, detected)`); it also lists the untracked host files it would change and the clash renames it keeps.

   Show the operator the change-list: machinery files that would be updated (with +added/-removed counts) or added, settings merged, how many files are preserved and unchanged, and any stale workspace skills upstream has dropped.

6. STOP and let the operator review and approve. Do not apply without approval.

Apply (after the operator approves):

7. Run the same installer in update mode, recording the upstream commit so provenance is tracked (this also stamps the upstream `workspace_version` M into `works/.workspace-version.json`):

   ```sh
   SYNCED_COMMIT="$ref" sh "$tmp/bootstrap_agentic_workspace.sh" . --update
   ```

   **(nested)** The same command, run from the host root; the installer detects the layout.

Verify:

8. The installer's update already ran `validate` / `rebuild` (or `next` for a repo without the docs subsystem) and printed the result. It preserves the repo-root `executors.toml` but refreshes the generated `slice-executor-*` agent files from upstream, so **always** run `python3 scripts/workflow.py sync-agents` after an update to re-apply the preserved per-row overrides. Then run `python3 scripts/workflow.py next` to confirm the current state under the refreshed engine. **Coming from a pre-v23 workspace:** the `low` tier is retired (routing is two-tier now — `risk: low` goes to `slice-executor-mid`, everything else to `slice-executor-high`). The update flags the stale `.claude/agents/slice-executor-low.md` instead of deleting it, so remove it by hand, and drop any `[claude.low]` block from `executors.toml` — `sync-agents` now rejects that section. **Coming from a pre-v31 workspace:** this workspace ships Claude Code only. The update flags the `.agents` and `.codex` trees, `AGENTS.md`, and `AGENTS.workspace.md` as stale machinery; it never deletes, so remove them by hand — an `AGENTS.md` your project maintains for other tools is yours to keep, and nothing here writes it any more. A leftover `[codex.*]` table in `executors.toml` is a hard error: `executors.toml line <n>: Codex support was removed in workspace v31 — this workspace ships Claude Code only, so drop this section`. **Coming from a pre-v32 workspace:** phases you already have carry no `acceptance` block, so they stay legacy and pass exactly as before; opt a **live** phase into the new operator acceptance gate with `python3 scripts/workflow.py accept-gate <P> --require` (never a `done` one — `validate` would then report it as done with an uncleared gate). `--update` never touches `docs/`, so the seeded `## Operator Runtime` manifest and the rewritten `## Regression Checklist` (the product's cumulative smoke list, re-run by every later phase inside its own boundary — `phase-scope <P>` names the changed files — and whole only by an operator-created QA phase, since v41) reach fresh installs only: add both to your own operations/qa docs with `doc-new-version` — copying the seed text from `installer/payloads/doc_bodies/` in the upstream clone — and fill the manifest in, or the first slice claiming real-browser verification will stop `pending` asking you for it. **Coming from a pre-v42 workspace:** a phase runs on the current checkout, exactly as it always did; the per-phase git worktree (`.claude/worktrees/P<N>-<slug>`, branch `phase/P<N>-<slug>`) is opt-in, reached by asking for it — `worktree` on `/do-next-slice` / `/do-whole-phase`, or `python3 scripts/workflow.py parallel-start <P>` by hand. `.git/info/exclude` gains `.claude/worktrees/` on the first `parallel-start` — nothing to do by hand, and `.gitignore` is untouched. Integration merges locally by default (`git merge --no-ff` after `parallel-gate`); push → PR → CI is the remote variant, and the seeded CI `parallel-gate` job still runs on `phase/*` PRs if you use it. Nothing else to run. **Coming from a v42 workspace:** the default reversed — v42 put every phase in its own worktree at first execution, v43 puts it back on the current checkout unless you ask. Two commands retired into no-ops that write nothing: `parallel-skip <P>` and `new-phase --on-main` (there is nothing left to pin, so a docs phase needs neither). Phases already stamped `execution: {"mode": "parallel"}` keep running in their worktrees and integrate unchanged; phases carrying v42's `execution: {"mode": "default"}` pin keep it and still validate — `parallel-start` refuses them rather than override a deliberate pin, so delete that block from `phase.json` by hand if you later want one in a worktree. Nothing else to run.

Report and clean up:

9. Summarize what was updated / added / merged / preserved and any flagged stale skills or machinery (from the installer's printed summary — e.g. agent files upstream has retired, which you remove manually), and show `git status`. **(nested)** Show `git -C workflow status` for the refresh to commit, and `git status --porcelain` in the host, which the update must leave as it was. Do NOT commit automatically — the operator reviews the diff and tells you when to commit. Remove the temp clone: `rm -rf "$tmp"`.
