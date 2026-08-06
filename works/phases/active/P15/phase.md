# Phase P15: New-maintainer knowledge base

_Intent: see [intent.md](intent.md)._

## Objective

Give a new maintainer full understanding of vocky through a series of /explain knowledge explainers saved to the operator's personal knowledge base (DECOMP surveys docs/current and the codebase and cuts one slice per knowledge topic, as many as full coverage requires), plus a slice that audits README.md and updates whatever is stale.

## Context

The corpus a new maintainer must absorb: eleven `docs/current/*.md` (~3,750 lines), a 476-line `README.md`,
~9,900 lines of Python under `src/vocky/`, a Next.js app in `web/`, a production deploy kit (`compose.prod.yml`,
`deploy/`, `.github/workflows/`), a 32-file pytest suite, and a 33KB agentic-workspace contract (`CLAUDE.md`).
Phases P1→P14 are archived history; P15 is the first phase whose product is understanding rather than code.

## Decomposition

**Four `knowledge` slices** (one `/explain` explainer each, written to be read **in order** as a short series)
plus one docs-only README audit last.

| id | name | kind | risk | order | scope in one line |
|---|---|---|---|---|---|
| `P15.S1` | Knowledge: the product and its user-facing surfaces | knowledge | low | 1 | What vocky is and how it is used: problem, users, the six surfaces, field taxonomy and terminology, the web app, the CLI, and the agent skill |
| `P15.S2` | Knowledge: system internals — architecture, backend code map, data model, API contracts | knowledge | low | 2 | How it actually works: runtime shape, the capture pipeline, the `src/vocky/` module map, the schema and migrations, and the wire contracts of every route group |
| `P15.S3` | Knowledge: security, operations, and QA | knowledge | low | 3 | How it is kept safe and kept running: identity/tenancy/credential scope, the config surface, the production topology and deploy/rollback, the test suites and CI gates |
| `P15.S4` | Knowledge: decisions, history, and the agentic workspace | knowledge | low | 4 | Why it is this way and how to change it: the `D-*` record, the P1→P14 arc, the honest current state, and the phase/slice workflow this repo is driven by |
| `P15.S5` | Audit and refresh README.md | implementation | low | 5 | Audit the 476-line README against current reality; fix only what is stale, wrong, or missing — not a rewrite |

**Why this cut.** Four substantial explainers, each answering one question a new maintainer asks in order —
*what is it and how is it used* (S1) → *how does it work* (S2) → *how is it secured and operated* (S3) →
*why is it like this and how do I change it* (S4). The series is deliberately short enough to read end-to-end.

Mapping to the corpus (each doc lands in exactly one explainer, so overlap stays minimal):

- **S1** ← `product.md`, `experience.md`, `frontend.md`, `docs/cli.md`, `skills/vocky-feedback/SKILL.md`
- **S2** ← `architecture.md`, `backend.md`, `data.md`, `api.md`, the `src/vocky/` tree, `alembic/`
- **S3** ← `security.md`, `operations.md`, `qa.md`, `Makefile` / compose files / `deploy/` / `.github/workflows/`
- **S4** ← `decisions.md`, `docs/index.json` version trail, `CLAUDE.md` / `scripts/workflow.py` / `works/`

Two grouping calls worth recording:

- **Clients live with the product (S1), not with the internals (S2).** The web app and the CLI add *no*
  backend capability — both are pure clients of surfaces that already existed (`D-P4-*`, P5) — so they belong
  to the "how vocky is used" story, and S2 stays a clean server-internals explainer.
- **Security sits with operations (S3), not with architecture (S2).** The highest-consequence facts
  (credential scope, the fail-closed admin guard, the rate limiter's single-worker invariant, `/mcp` host
  allowlisting) are all things an operator must *configure and verify*, so pairing them with the deploy
  topology and the CI gates makes one coherent "keep it safe and running" read.

`P15.S5` is independent of the knowledge series and placed last on purpose: S1–S4 are exactly the audit that
surfaces what the README gets wrong. The already-known staleness is recorded below, so S5 does not strictly
depend on that ordering.

_(Superseded: an earlier pass of this decomposition cut ten narrower knowledge slices; the operator asked for
3–5 substantial ones instead, and those eleven bare folders were deleted and replaced by the five above. If a
later run finds an explainer too long, the natural re-split is S2 → architecture/flow vs code-map/schema.)_

## Findings & Notes

### Execution rule — `knowledge` slices are run inline, never dispatched

`/explain` is a **user-level** Claude Code skill (`~/.claude/skills/explain/`, not in this repo), so it exists
only on the main thread. Every `kind: knowledge` slice here is therefore run **inline by the orchestrator**,
like a `co-work` design slice — never handed to a `slice-executor`. `--risk low` on those slices is nominal
bookkeeping only; it does **not** mean "dispatch to `slice-executor-mid`". Only `P15.S5` (the README audit)
is dispatched normally.

`/explain` specifics worth knowing before the first knowledge slice:
- Invoke in **topic mode**: `/explain <topic>` — the topic is everything left after trailing flag words.
- Trailing flags: `here` also writes a copy into this project (**do not use it** — the confirmed intent is
  personal-KB only), `research` / `no-research` force the web-research section on/off.
- Output is one self-contained interactive HTML page: Background, Intuition, Code, "Best practices & next
  steps", and a 5-question quiz.
- The KB is **configured and present**: `~/.config/knowledge-kb/config.json` (`kb_root`, `api`, `site` keys)
  resolves to `/Users/sugang/projects/personal/knowledge`, which has an `mkdocs.yml`. No operator setup needed.
- Each explainer is one `/explain` run; because the merged topics are broad, name the topic explicitly enough
  that the skill researches the whole grouping (the source lists below are what each run should cover).

### Sources per knowledge topic (merged)

**S1 — the product and its user-facing surfaces**
- Docs: `product.md` (all of it — Summary, First MVP, Target Users, Non-Goals, Product Surface Roles,
  Current Field Taxonomy, Terminology, "Agent-recorded feedback", "The agent-skill surface"),
  `experience.md` (the integrator walkthroughs: onboarding, REST capture, MCP capture, read/search, usage,
  the web app, the CLI, the two-variable agent contract), `frontend.md` (app location/stack, directory shape,
  the round-01 design system, page + component inventory, the landing), `docs/cli.md` (328-line CLI reference).
- Code/files: `web/src/` (app router groups `(app)` / `(auth)`, `components/landing/*`),
  `src/vocky/cli/` (Typer app: `app.py`, `auth.py`, `projects.py`, `feedback.py`, `capture.py`),
  `skills/vocky-feedback/SKILL.md` (the published agent skill), `web/public/install.sh` (`curl | bash`).
- Anchors: the six surfaces (`/auth`, `/app`, `/api`, `/api/project`, `/mcp`, Admin REST) as *product roles*;
  org/tenant naming; project vs org `vk_` keys; `recorded_by`; the two-env-var agent contract.

**S2 — system internals (architecture, backend code map, data model, API contracts)**
- Docs: `architecture.md` (Runtime Shape, Two-Track API, Capture Storage Model, Async Capture and Attachment
  Linking, Query Read Model, File Storage Subsystem, Feedback Alert Hook, MCP surface, Repo Shape),
  `backend.md`, `data.md` (tables, conventions, the migration list), `api.md` (685 lines — the contract
  catalogue for every route group).
- Code: `src/vocky/app.py` (route wiring + lifespan, incl. the nested `mcp.session_manager.run()`),
  `capture.py`, `capture_queue.py`, `worker.py`, `notifications.py`, `db.py`, `redis_client.py`,
  the route modules (`api.py`, `app_api.py`, `app_feedback_api.py`, `project_feedback_api.py`,
  `admin_api.py`, `attachments_api.py`, `usage_api.py`, `auth_api.py`), the domain packages
  `feedback/` + `accounts/` (`types` / `repository` / `service` layering), `persistence/models.py`,
  `storage/`, `mcp_server.py`, `tools/capture_feedback.py`, `alembic/versions/`.
- Anchors: REST/MCP → Redis queue → worker → `feedback_events`; enqueue is the last write-path checkpoint;
  the `_apply_query_filters` read chokepoint; the `pg_trgm` Korean-safe search expression that must stay
  byte-for-byte in lock-step with its index; the MCP tool's hand-copied flat parameter list.

**S3 — security, operations, and QA**
- Docs: `security.md` (all), `architecture.md` §Identity and Tenancy Layer + §Credential Project Scope +
  §Configuration Surface + §Production Deployment Topology, `operations.md` (local loop, web app config,
  the P6/P12 deploy kit), `qa.md`.
- Code/files: `src/vocky/auth.py` (`ProjectCredentialAuthMiddleware`, `resolve_credential_project_ids`),
  `accounts/{auth,security,service}.py`, `rate_limit.py`, `config.py`, `smoke.py`;
  `Makefile`, `docker-compose.yml`, `compose.prod.yml`, `.env.example`, `.env.prod.example`, `deploy/*`,
  `.github/workflows/{ci,deploy-production}.yml`, `tests/` (32 files), `web/tests/`,
  `scripts/skill_parity.py`, `scripts/wait_for_health.py`.
- Anchors: 404-never-403; `tuple[UUID, ...]`-never-`None` scope resolution as type-level enforcement;
  fail-closed Admin bearer (`503`) vs the best-effort `last_used_at` stamp (deliberate asymmetry);
  the single-uvicorn-worker invariant behind the in-memory rate limiter; five-container topology with
  migrations outside the images and rollback by image tag; the two-database test contract; CI gates.

**S4 — decisions, history, and the agentic workspace**
- Docs: `decisions.md` (every `D-*` entry, P2→P14), the `## Status` header of each `docs/current/*.md`,
  `architecture.md` §Open Questions, `docs/index.json` (the version trail — twelve `product` versions, etc.),
  `works/backlog.md` + `works/deferred.md`, `works/phases/archives/` (phase **names** only — do not deep-read).
- Files: `CLAUDE.md` / `AGENTS.md` (the contract), `scripts/workflow.py`, `.claude/skills/` (17 skills),
  `.claude/agents/` + `.codex/agents/`, `executors.toml`, `docs/README.md` (doc-versioning rules).
- Anchors: what is genuinely true today (live at `vocky.hi2vi.com` since P12; nothing on PyPI; installer
  served from the site) vs still aspirational; backlog-routes / slice-explains / docs-are-versioned-truth;
  orchestrator + `slice-executor-{mid,high}`; phase-level doc versioning at the review; parallel mode.

### Already-spotted README staleness (input to `P15.S5`, not an exhaustive list)

1. **Line 28** — "It runs locally today; the public deployment is P6." Wrong: P12 deployed
   `https://vocky.hi2vi.com` on 2026-08-04 and it is live.
2. **Lines 50–71 (Install)** — framed as "**Once** `https://vocky.hi2vi.com` is live" / "**Today, before the
   site is deployed**, install from a checkout instead". The site *is* live, so the hosted `curl … | bash`
   installer is the real primary path and the conditional framing is now backwards.
3. **Line 215 + line 231** — "`make verify` builds a fresh wheel and checks the packaged assets" and the
   `make package-check` bullet. `package-check` no longer exists in the `Makefile` (removed in P6 with the
   Admin UI); `verify` is now `smoke test`. The granular list also omits the real `make check-skill-parity`.
4. **P13 email alerts are entirely absent** — no `VOCKY_SMTP_*` mention anywhere in `README.md`, though they
   are a worker-side production feature with four+ config vars.
5. **§Current Status (line 184) / §What The Current Pre-MVP Does (line 156)** — neither mentions the live
   deployment, the published `curl | bash` installer, the `vocky-feedback` agent skill, `recorded_by`
   capture provenance, or email alerts. (`recorded_by` *is* documented later, at line 267.)
6. Cross-check the whole file against `product.md` §Status and `operations.md` before editing; the audit is
   "fix what is stale/wrong/missing", **not** a rewrite, and the README's structure should survive intact.

### Cross-slice notes from the knowledge slices

- **S1 (done):** explainer published — "Vocky: What It Is and How It Is Used", KB doc id 25 v1,
  `vocky/2026-08-06-vocky-what-it-is-and-how-it-is-used.html`. Research section skipped-by-judgment.
- **S2 (done):** explainer published — "Vocky System Internals: Architecture, Code Map, Data Model,
  and Contracts", KB doc id 26 v1. Research section included (pg_trgm sources); one run sufficed for
  the merged grouping — no re-split needed.
- **S3 (done):** explainer published — "Vocky Security, Operations, and QA", KB doc id 27 v1.
  Research section included (OWASP password-storage + session-management cites). One run sufficed.
  Confirmed the S1 staleness is confined to `product.md`/`experience.md` — `operations.md`/`qa.md`
  are internally consistent about the live status.
- **S4 (done):** explainer published — "Vocky Decisions, History, and the Agentic Workspace", KB doc
  id 28 v1. Research skipped-by-judgment (repo-private process/history). **The four-explainer series
  is complete: KB docs 25 → 26 → 27 → 28 in reading order.**
- **S5 (done):** all six known-staleness items fixed in `README.md` (476 → 481 lines): live-deployment
  wording, the install-section framing flip, the `make verify`/`package-check`→`check-skill-parity`
  correction, `VOCKY_SMTP_*` added, and §What It Does/§Current Status brought up to date (live status,
  installer, `vocky-feedback` skill, `recorded_by` cross-ref, email alerts). No new "Doc impact" note —
  every added fact already matches accurate `docs/current/operations.md`; the README's alignment with the
  genuinely-stale `product.md`/`experience.md` lines was already flagged separately by S1's finding above.
- **S1 finding — stale live-status text inside `docs/current/` itself:** `product.md` v0012 (§Status
  line 22 "nobody outside this repo can use vocky … does not answer", §Distribution line 94 "both
  currently not yet true") and `experience.md` v0013 (line 14 blockquote "There is no hosted vocky
  yet", §The Web App line 346 "`vocky.hi2vi.com` is **not live**") still carry pre-P12 wording that
  contradicts the updated live-since-2026-08-04 text in the same files. Same root cause as the README
  staleness S5 will fix. Fixing these means new doc versions — one for the REVIEW slice to weigh as
  doc impact (or the operator to schedule), not for S5, whose scope is README.md only.

### Other survey notes

- Repo entry points (`pyproject.toml` `[project.scripts]`): `vocky` (CLI) → `vocky.cli:main`,
  `vocky-server` → `vocky.main:main`, `vocky-worker`, `vocky-smoke`. Package is a lean-CLI /
  `[server]`-extra split; nothing is published to PyPI.
- Non-`docs/current` docs that still matter: `docs/cli.md` (328 lines, the CLI/agent reference),
  `docs/local-public-access.md` (517), `docs/changple5-apply.md` (267, an integration write-up),
  `docs/reference/design/` (design artifacts).
- The production edge vhost left this repo at P12.S4 — it lives in `leetusik/edge` as
  `edge/conf.d/vocky.conf`; `deploy/vocky.conf.md` is only the pointer. Relevant to S3 and S4.

## Constraints

- Knowledge explainers are saved to the operator's **personal KB** via `/explain`, not committed to this repo.
  Nothing under `docs/` or `works/` should gain explainer content (each knowledge slice still writes its own
  `result.md` recording the topic, the `/explain` invocation, and where the explainer landed).
- Knowledge slices produce **no code change**; the only repo-file change in this phase is `README.md` (S5),
  plus the per-slice `plan.md` / `result.md` / `phase.md` bookkeeping.
- Scope is the **new-maintainer** audience only. End-user and contributor-facing knowledge was explicitly
  deferred out of P15 (see `intent.md` §Notes).
- Keep the series short and substantial: four explainers, readable end-to-end. Do not re-split a topic into
  extra slices mid-phase without the operator asking.

## Open Questions

- Does the README audit (S5) rise to a **durable-truth** change requiring a doc version at review? The
  README is not under `docs/`, so probably not on its own — but if the audit uncovers a factual drift that
  also contradicts `docs/current/*.md`, that *is* a "Doc impact" note for the review to consolidate. S5
  should decide explicitly and record it either way.
- S2 and S3 are the two heavy explainers (S2 spans ~1,500 doc-lines plus the code map; S3 spans ~970 doc-lines
  plus the deploy kit). If one `/explain` run cannot do a grouping justice, say so in that slice's `result.md`
  rather than silently thinning the coverage.
