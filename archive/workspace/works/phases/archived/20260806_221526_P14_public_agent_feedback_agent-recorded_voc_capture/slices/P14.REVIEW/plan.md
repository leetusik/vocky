# Plan — P14.REVIEW: Phase review and durable-doc consolidation

## Job

Review phase P14 as a whole and, only on a passing verdict, consolidate its durable-doc changes. Read in full: `works/phases/active/P14/phase.md` (the decisions D1–D4, all cross-slice notes, the complete Doc impact list, Open Questions), `intent.md`, and each slice's `result.md` (DECOMP, S1–S4). P14 is **not** in parallel mode — consolidation happens here.

## 1. Validate all slices together

- `make test` (baseline 238 passed), `make check-skill-parity`, web suite (`cd web && npm test`, `npm run typecheck`, `npm run lint`, `npm run format:check`).
- `uv run alembic check` — only the known pre-existing `ix_feedback_events_search_trgm` drift is acceptable.
- `uv run alembic current` — head `20260805_1200`.
- `make smoke` if the compose stack is up (it was left healthy by S3); skip with a note if it isn't — S3's live evidence stands.
- `python3 scripts/workflow.py validate`.

## 2. Judge against the objective

The bar is `phase.md`'s Objective + `intent.md`'s Confirmed Intent:

- Free-text sentiment + note (no enum) → `message`/`comment`, note passable on every capture surface — the hard requirement.
- First-class agent-vs-human marker (`recorded_by`), queryable/filterable, MCP defaults `"agent"`, REST stays `NULL`, additive for every existing client.
- Publicly documented for third-party adoption: SKILL.md (byte-parity), README, `docs/cli.md`; S3's must-nots respected (no `q` documented off `/app/feedback`, no CLI marker flag).
- Check each slice's `result.md` claims against the actual tree where cheap to do (spot-check, not re-implementation).
- Review the Doc impact list for completeness against the phase's real changes — S4 swept it; verify the sweep, don't redo it.

Known context, not findings: the two D4 hardening deferrals are **already filed** as deferred jobs D9 and D10 by the orchestrator (`works/deferred/open/`) — that Open Question is resolved. The remaining Open Question (server-enforcing `comment` when `recorded_by == "agent"`) is an **operator decision** — surface it in your summary, do not decide it or count it as a finding.

## 3. On a passing verdict only — consolidate docs

Turn the Doc impact list into doc versions (you may run `doc-new-version` in this slice — the only slice that may):

- `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source P14.REVIEW` — one version per affected doc, consolidating ALL of that doc's P14 notes into a single new version. Write the new version file content under `docs/versions/<doc>/` per the repo's existing version-file pattern (check how previous versions were authored — read a recent one first), never hand-editing `docs/current/*.md` (regenerate via the workflow's `rebuild-docs` if that is the established mechanism — check `python3 scripts/workflow.py docs` / how P13 did it).
- Expected docs from the list: `api.md`, `data.md`, `architecture.md`, `decisions.md` (D-P14-1/2/3), `security.md`, `operations.md`, `qa.md`, `frontend.md`, `experience.md`, `product.md`, `backend.md`. Consolidate faithfully — every listed line lands somewhere; don't invent beyond the notes + the tree.
- After versioning: `python3 scripts/workflow.py rebuild-docs` (if that is the regeneration step) and `python3 scripts/workflow.py validate`.

On `changes_requested` or `blocked`: complete validation and judgment first so the whole picture arrives in one cycle, then STOP before any consolidation — return numbered findings and proposed fix slices (id suggestion `P14.F<n>`, name, what to fix).

## Deliverables

- `result.md` in this slice folder: validation results, judgment rationale, findings (if any), the consolidation record (doc versions created, if passing).
- Return a structured verdict: `review_verdict: pass|changes_requested|blocked`, numbered findings + proposed fix slices when not passing, `doc_versions:` list (or none), and the fixed pointer `explain: not written — run /explain for this phase`.
- Do not run `review-phase`, `finish-slice`, or any other state transition — the orchestrator records the verdict.
