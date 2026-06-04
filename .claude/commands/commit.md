---
description: Group pending changes by topic and create one focused commit per group, following the project's commit convention.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git reset:*), Bash(git restore:*), Bash(git commit:*)
---

Group the current pending changes into topic-focused commits, then create one commit per group following the `type(scope): summary` convention from CLAUDE.md.

Steps:

1. Inspect repo state in parallel:
   - `git status` (no `-uall`) to see tracked and untracked files.
   - `git diff` and `git diff --staged` to see all pending content.
   - `git log -n 10 --oneline` to match this repo's commit style.

2. Read the actual diffs of changed files so you understand intent before grouping. Group by **topic / logical change**, not by directory — one feature, one bug fix, one doc update, one refactor. Files that share intent go together even if they live in different folders.

3. Skip files that look sensitive (e.g. `.env`, credentials, large binaries). If staged accidentally, leave them out and warn the user at the end.

4. For each group, in order:
   - Reset the index (`git reset` with no args) so only this group's files are staged.
   - Stage that group's files explicitly by path. Never use `git add -A` or `git add .`.
   - Draft a `type(scope): summary` message using imperative voice, no trailing period, focused on **why** when non-obvious. Supported types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `build`, `perf`, `revert`.
   - Commit using a HEREDOC so the message formats correctly. End with a `Co-Authored-By:` trailer naming the assisting agent if the user wants attribution; otherwise omit.
   - If a pre-commit hook fails: do **not** `--amend`. Fix the underlying issue, re-stage, create a **new** commit for that group.

5. After all groups are committed, run `git status` once more to confirm a clean tree (or to surface anything intentionally left unstaged).

6. Report the resulting commits as a short list: `<short-sha> <message>` per line, plus any files you deliberately did not commit and why.

Rules:

- Never push. Never force-push. Never run destructive git commands (`reset --hard`, `clean -f`, `checkout .`) to "tidy up" before committing — preserve all user changes.
- Never skip hooks (`--no-verify`) or signing flags unless the user explicitly asks.
- Never amend an existing commit unless the user explicitly asks.
- Do not create empty commits. Drop groups that end up empty after filtering.
- If everything is one cohesive change, a single commit is fine — don't fabricate splits.
- If grouping is genuinely ambiguous, ask the user once before committing.
