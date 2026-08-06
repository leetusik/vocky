# Plan — P15.S1: Knowledge — the product and its user-facing surfaces

First of the four-explainer new-maintainer series (see `../../phase.md` §Decomposition). Executed **inline by the orchestrator** — `/explain` is a main-thread-only user-level skill, so no executor is dispatched (phase execution rule).

## What this slice produces

One `/explain` run in **topic mode**, saved to the operator's personal KB (`/Users/sugang/projects/personal/knowledge` via `~/.config/knowledge-kb/config.json`). **No `here` flag** — personal-KB only, per confirmed intent. No repo code changes; the only repo writes are this slice's `result.md` and the `phase.md` note.

## Topic

Answer the new maintainer's first question — *what is vocky and how is it used* — covering the whole merged grouping in one explainer:

- What vocky is: the problem, target users, first-MVP scope, non-goals.
- The six product surfaces as roles: `/auth`, `/app`, `/api`, `/api/project`, `/mcp`, Admin REST.
- Field taxonomy and terminology: org/tenant naming, project vs org `vk_` keys, `recorded_by` provenance.
- The clients: the Next.js web app (app router groups, landing, round-01 design system), the Typer CLI, the `vocky-feedback` agent skill and its two-env-var contract, the hosted `curl | bash` installer.

Topic string for the run (single invocation):

> vocky, the developer-feedback capture product: what it is and how it is used — the problem and target users, the six product surfaces (/auth, /app, /api, /api/project, /mcp, admin REST) as roles, field taxonomy and terminology (orgs, projects, vk_ keys, recorded_by), the Next.js web app, the Typer CLI, and the vocky-feedback agent skill with its two-env-var contract

## Reading set (from `phase.md` §Sources — S1)

- Docs: `docs/current/product.md`, `docs/current/experience.md`, `docs/current/frontend.md`, `docs/cli.md`, `skills/vocky-feedback/SKILL.md`
- Code: `web/src/` (router groups `(app)`/`(auth)`, `components/landing/*`), `src/vocky/cli/` (`app.py`, `auth.py`, `projects.py`, `feedback.py`, `capture.py`), `web/public/install.sh`

## Steps

1. Invoke `/explain` with the topic string above (no `here`; let the skill's research default stand).
2. Verify the explainer landed in the personal KB.
3. Write `result.md`: topic, invocation, KB output path, coverage notes, anything the later slices should know.
4. Append a one-line cross-slice note to `phase.md` §Findings & Notes if the run surfaced anything durable.

## Done means

The explainer exists in the personal KB and `result.md` records where.
