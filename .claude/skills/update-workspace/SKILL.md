---
name: update-workspace
description: Update the current repo's agentic-workspace machinery to the latest upstream cornerstone, preserving your phases, slices, and docs.
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit, Write, Glob, Grep, Bash
disable-model-invocation: true
---

# update-workspace

Update the CURRENT repo's agentic-workspace machinery to the latest upstream cornerstone, preserving your own work. Explicit-invocation only. Run this when the cornerstone has changed since you adopted or last synced and you want this repo to match the current version. (For first-time adoption use `/retrofit` instead.)

What it changes: it OVERWRITES machinery (`scripts/workflow.py`, the `.claude/agents/` and `.codex/agents/` subagents, every skill under `.claude/skills/` and `.agents/skills/`, `.codex/config.toml`, `works/templates/*`), additively MERGES `.claude/settings.json`, and refreshes the `CLAUDE.md`/`AGENTS.md` contract. It PRESERVES everything under `works/` except templates (your state, phases, slices, deferred jobs) and all of `docs/` (your versioned docs). It never commits.

Preflight (read-only):

1. Confirm a git repo: `git rev-parse --is-inside-work-tree`. If the working tree is dirty (`git status --porcelain` is non-empty), tell the operator and recommend committing or stashing first, so the update lands as a clean, reviewable diff.
2. Confirm this repo already has the workspace: `works/state.json` (or any `works/phases/active/*/phase.json`) AND `scripts/workflow.py` must exist. If not, STOP — this repo has not adopted the workspace; use `/retrofit` instead.
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

   Show the operator the change-list: machinery files that would be updated (with +added/-removed counts) or added, settings merged, how many files are preserved and unchanged, and any stale workspace skills upstream has dropped.

6. STOP and let the operator review and approve. Do not apply without approval.

Apply (after the operator approves):

7. Run the same installer in update mode, recording the upstream commit so provenance is tracked (this also stamps the upstream `workspace_version` M into `works/.workspace-version.json`):

   ```sh
   SYNCED_COMMIT="$ref" sh "$tmp/bootstrap_agentic_workspace.sh" . --update
   ```

Verify:

8. The installer's update already ran `validate` / `rebuild` (or `next` for a repo without the docs subsystem) and printed the result. Run `python3 scripts/workflow.py next` to confirm the current state under the refreshed engine. If this repo tunes the executor tiers via a repo-root `executors.toml`, re-run `python3 scripts/workflow.py sync-agents` — the update resets the `slice-executor-*` agent files to upstream defaults (`validate` warns while they drift).

Report and clean up:

9. Summarize what was updated / added / merged / preserved and any flagged stale skills or machinery (from the installer's printed summary — e.g. agent files upstream has retired, which you remove manually), and show `git status`. Do NOT commit automatically — the operator reviews the diff and tells you when to commit. Remove the temp clone: `rm -rf "$tmp"`.
