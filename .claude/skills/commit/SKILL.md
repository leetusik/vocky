---
name: commit
description: Group pending changes by topic into focused conventional commits.
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git add:*), Bash(git reset:*), Bash(git commit:*), Bash(git -C workflow status:*), Bash(git -C workflow diff:*), Bash(git -C workflow log:*), Bash(git -C workflow add:*), Bash(git -C workflow reset:*), Bash(git -C workflow commit:*)
disable-model-invocation: true
---

# commit

Inspect pending changes, group them by logical topic, and create one focused commit per group using `type(scope): summary` (imperative, no trailing period).

Never push, force-push, use `git add -A`, or skip hooks unless explicitly asked.

**Nested personal install** (`workflow/.agentic-nested.json` exists). The host and `workflow/` are two separate git repos, so a slice is two commits:
- product changes go to the host, on the operator's ticket branch, in the host's conventions (commits, branches and pull requests) that `python3 scripts/workflow.py nested-convention` prints. Add Claude `Co-Authored-By` trailers only when it says `allowed`, and put no phase or slice IDs, `workflow/` paths or workspace files in the message;
- state changes go to the nested repo with `git -C workflow ...`, in this workspace's convention;
- never stage `workflow/`, `CLAUDE.local.md` or the workspace's `.claude/` files into the host.
