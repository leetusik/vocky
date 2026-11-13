# Plan — P15.S4: Knowledge — decisions, history, and the agentic workspace

Fourth and last explainer of the series (see `../../phase.md`). Executed **inline by the orchestrator** — `/explain` is main-thread-only; no executor dispatched.

## What this slice produces

One `/explain` run in topic mode → personal KB (project `vocky`), no `here` flag. Repo writes limited to `result.md` + a `phase.md` note.

## Topic

*Why vocky is the way it is, and how to change it* — the `D-*` decision record, the P1→P14 phase arc, the honest current state (live at vocky.hi2vi.com; nothing on PyPI; installer from the site), and the agentic workspace this repo is driven by (backlog routes / slice folder explains / docs are versioned truth; orchestrator + slice-executor tiers; phase-level doc versioning at review; parallel mode; the workflow commands).

Topic string:

> vocky's decision record, project history, and the agentic workspace that drives this repo: the D-* decisions and the P1-P14 phase arc, what is genuinely true today versus aspirational, and the phase/slice workflow - orchestrator and slice-executor tiers, versioned durable docs consolidated at phase review, deferred jobs, and parallel mode

## Reading set (from `phase.md` §Sources — S4)

- `docs/current/decisions.md` (every `D-*` entry), `docs/index.json` (version trail), `works/backlog.md` + `works/deferred.md`, `works/phases/archives/` phase **names only** (do not deep-read).
- `CLAUDE.md`/`AGENTS.md` (already fully in context — the contract), `scripts/workflow.py` (structure only), `.claude/skills/` listing, `executors.toml`, `docs/README.md` (versioning rules).
- The `## Status` headers of `docs/current/*.md` are already read (S1–S3) — reuse.

## Steps

1. Read decisions.md; skim index.json, deferred.md, archive names, executors.toml, docs/README.md, skills listing.
2. Web-research judgment: this subject is repo-private machinery and project history — expect **skip-by-judgment** (no meaningful external comparison surface for a personal workspace's process); decide at research time.
3. Check KB for a prior doc on the subject (expected none). Author the HTML explainer.
4. POST to the KB API; record url/version.
5. Write `result.md`; append the `phase.md` note.

## Done means

Explainer #4 in the KB; `result.md` records where. The series is then complete end-to-end.
