# Result — P12.DECOMP

Decomposed phase P12 into **seven middle slices** (`P12.S1`–`P12.S7`, orders 1–7) and filled
`works/phases/active/P12/phase.md` with the breakdown, the ordering rationale, the routing decision for
every item `intent.md` said must be included or explicitly routed, the durable findings later slices need,
the phase constraints, and five open questions.

No code was written, no doc was versioned, no status was transitioned, nothing was committed.
Every created slice folder holds **`slice.json` only** — no `plan.md` was pre-filled.

## What was created

| Slice | Kind | Risk | Order | depends_on |
|---|---|---|---|---|
| `P12.S1` Decide the fate of `/admin/api/*` and `VOCKY_ADMIN_AUTH_TOKEN` | implementation | medium | 1 | — |
| `P12.S2` Repo hygiene sweep: retired token refs, prettier debt, vestigial design-token names | implementation | **low** | 2 | — |
| `P12.S3` Rate-limit the public `/auth/*` surface (D5) | implementation | medium | 3 | — |
| `P12.S4` Production bring-up at `vocky.hi2vi.com` (operator-gated) | **co-work** | **high** | 4 | S1, S3 |
| `P12.S5` Postgres backups, log rotation and basic metrics | implementation | medium | 5 | S4 |
| `P12.S6` Extend `ci.yml` with a Postgres-backed pytest job | implementation | medium | 6 | S2 |
| `P12.S7` Author `docs/current/qa.md` | implementation | medium | 7 | S6 |

**One pass only** — no `P12.DECOMP2`, no build inventory: P12 contains no product visual design. `P12.S4` is
`co-work` because it is an **infra/operator gate** (orchestrator inline, operator in the loop), explicitly
**not** a `design-cowork` round; that is recorded in `phase.md` § Context and § Constraints.

## Risk-rating rationale (risk selects the executor tier)

- **`low` — only `P12.S2`.** Three mechanical, greppable edits with zero behavior change (`Makefile:15`
  retired-token export, `prettier --write` over 14 files, a same-hex rename of five design tokens across
  `globals.css` + 6 usage sites), each provable by grep plus the standard web gate. Its plan must enumerate
  files and the exact new token names — a literal plan-follower must not invent them (Open Question 3).
- **`medium` — S1, S3, S5, S6, S7.** Each is bounded but needs judgment: a decision landed in code (S1), a
  limiter with a real client-IP correctness trap (S3), backup/rotation authoring plus an on-box runbook
  (S5), a CI job with service containers and a two-database test contract whose first run may not be green
  (S6), and authoring a whole durable doc from evidence (S7). Noted for the orchestrator: **if the operator
  chooses "retire" at S1's gate, bump S1 to `high`** — it becomes a ~500-line module removal touching app
  wiring, middleware, tests, config, compose and `.env.prod.example`.
- **`high` — only `P12.S4`.** First-ever execution of the entire deploy chain against real infrastructure,
  four operator gates, and a plan that must iterate rather than succeed first time.

## Surprises found while reading the P6 spec and the repo

1. **`AdminBearerAuthMiddleware` is fail-open.** `src/vocky/auth.py:84-109` guards `/admin/api/*` only
   `if self.token`; `config.py:39` defaults the token to `""`; `compose.prod.yml:104` uses a plain
   `${VOCKY_ADMIN_AUTH_TOKEN}` (not `${...:?err}`), and Compose substitutes an **empty string with a
   warning** for an unset variable rather than failing. A missing or typo'd `.env` line therefore ships
   **nine unauthenticated `/admin/api/*` routes** (including `PATCH`/`DELETE` on any feedback record)
   reachable by every co-tenant container on `changple_shared_network`. This reframes `P12.S1` from a
   tidy-up into a pre-launch security decision, and is why S1 is ordered first.
2. **`operations.md`'s "a missing value must fail loudly on the box" is false as written.** Only
   `POSTGRES_PASSWORD` fails loudly, and only by the `postgres:17` image's grace. A blank `SESSION_SECRET`
   throws inside `web/src/lib/env.ts` at **request time**, and the web healthcheck fetches `/` (the static
   landing), which never reads it — so a blank session secret **passes `deploy.sh`'s health gate** and
   fails only at first login. Recorded as a required addition to S4's smoke: an authenticated round-trip,
   not just `/healthz` + `/`.
3. **`intent.md`'s "CI has never existed" predates P11.** `.github/workflows/ci.yml` already exists
   (P11.S4, three jobs) and its own header says *"P12 is expected to add a job to this same file, not start
   a new one."* S6 is scoped to **extend** it. Its two documented exclusions are exactly the two things P12
   was asked to decide, so S2 (fix prettier) + S6 (add the gate + the Postgres pytest job) close both.
4. **Two of the three "stale artifacts" in `intent.md` are already fixed.** No `README.md` line presents
   the retired `VOCKY_API_AUTH_TOKEN` as current (lines 187 and 351 describe it correctly as retired), and
   **no "PyPI publishing is P6 / until then" caveat survives** in `README.md` or `docs/cli.md` — P11 already
   dropped it (`PyPI` greps clean in both). Only `Makefile:15` is genuinely stale, so S2's stale-artifact
   work shrank to one line.
5. **The prettier debt is 14 files, not 12–13** (re-measured with `pnpm exec prettier --check .`).
   `web/.prettierignore` excludes `public/`, so fixing it cannot disturb the served `install.sh` /
   `SKILL.md` byte-parity gate.
6. **57 commits are unpushed**, which makes `git push` a hard prerequisite of the bring-up rather than an
   afterthought: the on-box gate ancestor-verifies against fetched `origin/main`, the installer resolves
   GitHub `main` (installing today would deliver a **pre-P10** CLI), and `ci.yml` has never run on a runner.
   Recorded as a fourth operator gate on S4 (`CLAUDE.md` forbids pushing unasked).
7. **D5 cannot be promoted through the normal path.** `promote-deferred` calls `create_slice`, which
   hard-fails on an existing slice directory, and a decomposition executor may run only `new-slice` — so
   creating `P12.S3` closed the `deferred → promoted` route for D5. `phase.md` records the fallback for
   `P12.REVIEW`: `drop-deferred D5 --reason "Resolved by P12.S3: …; not abandoned"`, since there is no
   `resolved` status.
8. **Box reachability from an executor sandbox is unverified.** Reading `~/.ssh/config` was refused by the
   permission classifier, so no `ssh oracle-cloud` probe was attempted. The decomposition assumes every
   box-touching step is orchestrator/operator-run until proven otherwise — one reason S4 is `co-work` and
   S5 is scoped to author rather than install (Open Question 4).
9. **The two unused design tokens are duplicates.** `--color-archive-olive` and `--color-archive-cream`
   have no usage in `web/src` beyond their declaration, and P8's audit already recorded them as exact
   value-collisions with `muted` and `surface-soft`/`surface-band` — so S2 may be able to **delete** rather
   than rename them.

## Routing of every deferred job (complete sweep of `works/deferred/open/`)

`D5` → `P12.S3` (own slice, pre-launch). `D1`, `D2`, `D3`, `D4`, `D6` → **stay deferred**, each with a
stated reason in `phase.md` § Routing decisions. No P12 slice touches the `/api/*` attachment surface, so
D4's trigger does not fire; D2's revisit condition (a non-owner feedback view) is still unmet; D3 and D6 are
out of scope per `intent.md`; D1 is product direction, not hardening.

## Doc impact

No durable-truth source change was made by this slice, but the reading surfaced two doc corrections
`P12.REVIEW` should fold in regardless of what the middle slices do. Appended to `phase.md` § Doc impact:

> **P12.DECOMP** (no source change): (a) `operations.md` § "Box secrets" claims *"None has a `:-` default: a
> missing value must fail loudly on the box"*, which is **false as written** (Compose substitutes an empty
> string with a warning for a plain `${VAR}`; only `POSTGRES_PASSWORD` fails loudly, and only because the
> `postgres:17` image refuses to initialize without it); (b) `operations.md` § "`.github/workflows/ci.yml`"
> records **14** prettier failures while `intent.md` says 12–13 — 14 is the measured number.

`phase.md` also states the **`qa.md`-via-`result.md` convention** so `P12.S7`'s later plan inherits it: S7
authors the full intended `qa.md` body inside its own `result.md` plus a "Doc impact" line pointing at it,
and `P12.REVIEW` consolidates it verbatim into a new `qa` doc version.

## Validation

| Command | Outcome |
|---|---|
| `python3 scripts/workflow.py validate` | **PASS** — `Workflow validation passed.` |
| `python3 scripts/workflow.py next` | **PASS** — `next_slice=P12.S1` (the first new middle slice) |
| `ls works/phases/active/P12/slices/*/` | **PASS** — S1–S7 each contain `slice.json` and **no** `plan.md` |
| `pnpm exec prettier --check .` (in `web/`, read-only measurement) | 14 files reported — recorded as a finding, nothing changed |

## Deviations from `plan.md`

1. **`P12.S3` was created with `new-slice`, not `promote-deferred`.** The plan lists D5 as "in scope, must
   land before/with the bring-up"; `promote-deferred` is not a command a decomposition executor may run, and
   it also appends a "Promoted Deferred Context" section to the new slice's `plan.md`, which would violate
   the "bare folders, never pre-fill `plan.md`" rule. Consequence and remedy recorded in `phase.md`.
2. **The design token-rename was folded into the mechanical `P12.S2` rather than given its own slice.** The
   plan allowed "standalone mechanical slice **or** defer it", with the hard constraint being *not folded
   into a visual slice*. S2 is not a visual slice — it is the phase's mechanical sweep — and a separate
   dispatch for ~10 lines of same-hex rename was not proportionate. The constraint is honored and restated
   in `phase.md`.
3. **`P12.S3`'s `depends_on` was corrected by hand.** It was created with `--depends-on P12.S2` by mistake;
   there is no real dependency between the hygiene sweep and the rate limiter, so the `depends_on` array in
   `works/phases/active/P12/slices/P12.S3/slice.json` was edited back to `[]` (advisory field only;
   `validate` passes).
4. **The plan's `README.md:161` / "PyPI publishing is P6" sweep items were verified as already fixed** and
   dropped from S2's scope rather than carried forward (evidence in the Surprises section above).
5. **`intent.md`'s post-launch placement of the CI slice was followed, but flagged.** Ordering S6 after the
   bring-up means the 108 never-run DB-backed tests first execute after production has already been
   migrated. Rather than override the confirmed intent, this is raised as **Open Question 1** for the
   operator to settle at S4's plan gate (fractional `--order` makes the move free).
6. **No `ssh` probe of the box was performed.** The plan did not ask for one, but the decomposition wanted
   it to decide whether S5 could be dispatched; the attempt to read `~/.ssh/config` was blocked by the
   permission classifier and was not worked around. Recorded as Open Question 4.
