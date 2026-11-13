# Result — P13.DECOMP

Phase P13 decomposed into **five middle slices**, single pass (no visual design in this phase, so no
`co-work` round and no `DECOMP2`). `phase.md` seeded with the breakdown, both required decisions, the
verified codebase facts, the constraints, and a "Doc impact" section for later slices to append to.

## Slices created (bare folders — no `plan.md` pre-filled)

| Slice | Order | Risk | Depends on | Scope |
|---|---|---|---|---|
| `P13.S1` | 1 | medium | — | owner-email recipient resolution (accounts repository + service) |
| `P13.S2` | 2 | medium | S1 | SMTP settings + feedback alert notifier module |
| `P13.S3` | 3 | medium | S2 | worker post-persist alert hook + DI wiring + failure containment |
| `P13.S4` | 4 | medium | S3 | SMTP env/compose/deploy plumbing (prod + dev) |
| `P13.S5` | 5 | medium | S4 | production bring-up: changple5 SMTP credentials + live alert verification |

Each folder contains only `slice.json`, as required.

## Cut rationale (short form; full version in `phase.md`)

The chain is **recipient → notifier → hook → plumbing → bring-up**, chosen so every slice builds on
landed code and never has to stub a future slice. The plan's suggested shape put settings + notifier +
the owner query in one slice; I split the owner query out as S1 instead, because it is the phase's
multi-tenant correctness hot spot (a wrong join mails one org's feedback to another org's owner) and
because its validation surface is different from the rest (it is the only DB-backed slice). S5 exists
as its own slice rather than an operator note on S4 because the credentials are readable only on the
box — a permission boundary that already blocked once at phase creation — so it ends in a clean
`needs_operator` handoff with a runbook, leaving S4 to land purely as repo config.

All five are `risk: medium`; none is fully mechanical. S4 is the closest call and still is not `low`:
both `compose.prod.yml` and `.env.prod.example` assert an "exactly three secrets, all `${VAR:?}`"
invariant in prose, and the SMTP secret is deliberately optional, so the interpolation form is a
judgment call with prose consequences in several places.

## Decisions made (rationale recorded in `phase.md`)

1. **SMTP client — stdlib `smtplib` + `email.message.EmailMessage` inside `asyncio.to_thread`.**
   No new dependency anywhere, not even in the `server` extra. One short message per event on a
   single-owner product does not justify `aiosmtplib`; stdlib already covers SSL/STARTTLS/AUTH. The
   blocking send must stay isolated in one small function so it is swappable later.
2. **Failure containment — swallow-and-log, no notify DLQ.** The notifier call sits *outside* the
   persistence `try:` block, wrapped in its own `try/except Exception` that logs and returns; it never
   reaches `requeue_job` / `dead_letter_job`. The trap is structural: `_handle_persistence_failure`
   retries the whole capture job, so any escaping exception duplicates an already-committed feedback
   row. Accepted tradeoff: a failed alert is lost and visible only in worker logs — a retry/outbox is a
   `defer-job` candidate for `P13.REVIEW`, not speculative machinery now.
3. **(Bonus, guidance for S4) Secret placement/form** — SMTP vars on the `worker` service only (sole
   sender, preserving compose's per-service secret isolation); prod uses the `${VAR:?}` box-secret
   form (fail loud — production intends alerts on), dev `docker-compose.yml` uses `:-` empty defaults
   so a local stack starts with alerts cleanly disabled.

## Research findings worth flagging (all in `phase.md`)

- **`tests/test_worker.py`'s three existing feedback-service doubles all return `None`.** S3's hook
  must treat a `None` record as "nothing to notify", alongside the `project_id is None` skip that
  `FeedbackEventRecord.project_id: UUID | None` already forces. Done that way every existing worker
  test passes untouched; done naively they all break.
- **Nothing forbids two `role='owner'` rows per tenant** (`TenantMemberModel` is unique only on
  `(tenant_id, user_id)`), so S1 needs a deterministic oldest-wins tie-break rather than `.one()`.
- **`deploy/deploy.sh` carries no secret list** — it only asserts `.env` exists — so the SMTP secret
  needs no deploy-script change; compose's `${VAR:?}` is the single enforcement point.
- **`make test` needs a live Postgres** with distinct `DATABASE_URL` / `TEST_DATABASE_URL`; slice plans
  should say so, and a slice that cannot reach a DB should report it rather than claim a green suite.

## Validation

| Command | Outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **passed** — "Workflow validation passed." |
| `ls -a works/phases/active/P13/slices/P13.S1 …/P13.S5` | passed — each new folder holds `slice.json` only, no pre-filled `plan.md` |

Read-only research (no writes): `src/vocky/worker.py`, `config.py`, `accounts/repository.py`,
`accounts/service.py`, `feedback/service.py`, `feedback/types.py`, `persistence/models.py`,
`tests/test_worker.py`, `tests/conftest.py`, `pyproject.toml`, `Makefile`, `compose.prod.yml`,
`docker-compose.yml`, `.env.prod.example`, `deploy/deploy.sh`, `docs/current/backend.md`.

## Doc impact

None — decomposition changed no durable truth. A forward-looking note was recorded in `phase.md`'s
"Doc impact" section naming the areas the phase is expected to touch (`backend.md`, `architecture.md`,
`operations.md`, possibly `qa.md`) so `P13.REVIEW` knows where to look.

## Deviations from `plan.md`

Two, both within the plan's explicit "you own the final cut" latitude:

1. **Five slices instead of the suggested ~3–4**, and the owner-email query moved out of the
   settings/notifier slice into its own first slice (S1) — rationale above.
2. **The operator-gated bring-up is a full slice (S5)**, not an operator note attached to another
   slice. The plan offered both options; a dedicated slice keeps S4 purely repo-side and gives the
   `needs_operator` handoff (and the operator's live-email confirmation) its own acceptance record.

No other deviations. No commits, no status transitions, no `doc-new-version` — `new-slice` was the only
workflow command run besides `validate`.
