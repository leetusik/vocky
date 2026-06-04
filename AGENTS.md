# AGENTS.md

Authority: see `/CLAUDE.md`. Read it before any work in this repo.

The canonical workflow rules — phase/slice model, status, review gates, agent tool conventions — live in `CLAUDE.md`. This file is a pointer so Codex finds the policy by its native default name.

Codex subagents are configured under `.codex/agents/*.toml`; each bridges to its canonical Markdown policy under `.claude/agents/`. Edit the policy, not the bridge.
