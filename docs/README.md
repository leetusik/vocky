# Docs

Durable docs are versioned. Do not patch old versions.

## Categories

- `docs/current/product.md`
- `docs/current/experience.md`
- `docs/current/architecture.md`
- `docs/current/frontend.md`
- `docs/current/backend.md`
- `docs/current/data.md`
- `docs/current/api.md`
- `docs/current/operations.md`
- `docs/current/security.md`
- `docs/current/qa.md`
- `docs/current/decisions.md`

## Rules

Doc updates happen in a **docs phase the operator creates** — never per slice. A slice that changes durable truth appends a one-line note to its phase's `## Doc impact` list instead; `python3 scripts/workflow.py docs-debt` prints what is owed, and the docs phase runs the commands below over those notes.

- Read latest docs from `docs/current/*.md`.
- The agent creates updates with `python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source <phase-or-slice>`.
- Edit only the newly created version file under `docs/versions/<doc>/`.
- The agent runs `python3 scripts/workflow.py rebuild-docs` after editing the new version.
- `docs/current/*.md` is generated from the latest version and should not be manually edited.
- When a phase's notes are all consolidated: `python3 scripts/workflow.py docs-consolidated <P>` (that is also what unblocks archiving it).

## Update Triggers

- `product`: goals, users, scope, terminology, business direction
- `experience`: routes, journeys, UI behavior, copy, UX states
- `architecture`: system boundaries, components, runtime, integrations
- `frontend`: routing, components, state, data fetching, browser auth
- `backend`: server modules, services, jobs, auth/session, logging/errors
- `data`: schema, migrations, entities, indexes, storage, retention
- `api`: REST/RPC/webhook/event contracts and error shapes
- `operations`: env, deployment, local commands, jobs, monitoring, backups
- `security`: permissions, secrets, customer data boundaries, abuse controls
- `qa`: test commands, QA missions, regression checklist, acceptance style
- `decisions`: meaningful choices, tradeoffs, rejected alternatives
