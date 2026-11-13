# Plan — P15.DECOMP

## Goal

Decompose P15 ("New-maintainer knowledge base") into middle slices. The phase's confirmed intent (see `../../intent.md`): give a **new maintainer** full understanding of vocky through a series of `/explain` knowledge explainers saved to the operator's personal knowledge base, plus one slice that audits `README.md` and fixes whatever is stale. Topics are yours to decide by surveying the workspace.

## What to do

1. **Survey for topic selection.** Read `docs/current/*.md` (all eleven docs), `README.md`, and skim the codebase structure (top-level layout, `pyproject.toml`, entry points, key packages) enough to judge what a brand-new maintainer must understand to own this project. Do not deep-read every file — this is topic scoping, not the explainers themselves.

2. **Cut the knowledge topic list.** Choose as many knowledge topics as full coverage genuinely requires — one slice per topic. Aim for topics that partition the system with minimal overlap (e.g. product purpose & user-facing behavior; architecture & data flow; backend internals; frontend; data model; operations/deploy; QA/security; the agentic workspace machinery — adjust to what the survey actually shows). Prefer fewer, well-scoped topics over many thin ones; a new maintainer should be able to read the series end-to-end.

3. **Create the middle slices** with `new-slice`, in reading order via `--order`:
   - One slice per knowledge topic: `--kind knowledge --risk low`, name like "Knowledge: <topic>". **These slices are never dispatched to an executor** — the orchestrator runs them inline on the main thread because `/explain` is a main-thread-only skill (recorded in `intent.md`). The `--risk low` is nominal; note this execution rule explicitly in `phase.md` so later runs of the loop know.
   - One README slice: `--kind implementation --risk low` (docs-only), name like "Audit and refresh README.md". Scope: audit `README.md` (476 lines, last touched 2026-08-05) against current reality and update only what is stale, wrong, or missing — not a rewrite. Place it where you judge best (independent of the knowledge series; last is fine).
   - Bare folders only — never pre-fill any new slice's `plan.md`.

4. **Seed `phase.md`:**
   - Fill **Decomposition** with the slice table (id, name, kind, risk, order, one-line scope) and the rationale for the topic cut.
   - Fill **Findings & Notes** with what the survey learned that later slices need: for each knowledge topic, which `docs/current` docs and code areas its explainer should draw from; the inline-execution rule for `knowledge` slices; anything already-known-stale spotted in README.md (as input to the README slice).
   - Add any real constraints or open questions you hit.

5. **Write `result.md`** in this slice's folder: what you created, the topic rationale in brief, and anything the orchestrator should know.

## Constraints

- You may run `python3 scripts/workflow.py new-slice ...` (allowed during a decomposition slice) — but no other state transitions, no commits.
- No implementation work, no explainers written, no README edits.
- `/explain` explainers go to the operator's personal KB, not the repo — the knowledge slices themselves will handle that later; irrelevant to you beyond scoping.
- Keep `phase.md` notes durable and lean.

## Verdict

Return `done` with the usual structured fields when the slices exist and `phase.md` is seeded.
