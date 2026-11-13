# P11.DECOMP — result

Cut phase P11 into middle slices (first of **two** decomposition passes, because P11 both designs and
builds) and seeded `phase.md`. No source file was touched.

## What was created

Six bare slice folders, exactly as `plan.md` specified — each holds **only `slice.json`**; no `plan.md`
or `result.md` was pre-filled anywhere.

| Slice | Order | Kind | Risk | Depends on |
|---|---|---|---|---|
| `P11.S1` | 1 | implementation | low | — |
| `P11.S2` | 2 | implementation | medium | — |
| `P11.S3` | 3 | implementation | medium | — |
| `P11.S4` | 4 | implementation | medium | `P11.S2` |
| `P11.S5` | 5 | **co-work** | high | `P11.S4` |
| `P11.DECOMP2` | 6 | decomposition | high | `P11.S5` |

`--kind co-work` was accepted without complaint (`scripts/workflow.py` treats `--kind` as a free string —
`workflow.py:1063`), so no stop-and-report was needed. `P11.S5` therefore stays off the executor dispatch
path, per `design-cowork`.

**No build slices were cut.** Per the two-pass rule, `phase.md` carries a **build inventory** (four items,
plus the copy-payload apply-time note) instead; `P11.DECOMP2` cuts the build slices from the landed
design.

## `phase.md` now carries

The operator's three fixed decisions dated 2026-07-29 · the verified grounded facts with `file:line`
citations (capture contract, CLI, web/serving, design, the `git+` shipping caveat, the three env-var
blockers) · the slice table with ordering and risk rationale · the six slice **intents** (written as
intents for the orchestrator to plan later, explicitly not as plans) · the build inventory · the P12
hand-off with three armed flip probes · the explicit out-of-scope list · standing constraints and open
questions · and an empty `## Doc impact` heading at the end for later slices to append to.

## Verification of the plan's "Grounded facts" — and four corrections

Every citation in the plan's *Grounded facts* section was checked against the tree before being written
into `phase.md`. **All the substantive claims held.** Four line pointers were wrong and are corrected in
`phase.md` (§ "Citation corrections made by `DECOMP`"):

1. **`auth.py:130-133`** — cited for "`vk_` is never validated as a prefix". Those lines are a docstring
   about per-request project-scope caching. The actual evidence is **`auth.py:183` — `sha256_hex(token)`**
   inside `ProjectCredentialAuthMiddleware.__call__` (class at `:144`). *Claim stands.*
2. **`capture.py:274`** — cited for the `source.product` non-blank guard. `:274` is the **`message`**
   guard; `source.product` is at **`:275`**. Also the nested `source` **field** is declared at `:38`
   (`:37` is `message: str`). *Claim stands.*
3. **`section-ids.ts:8-13`** — that is the `SECTION_IDS` **map**; the `SectionId` **type** alias is at
   `:15`. *Claim stands* (a new section must still add its id there; only 3 ids exist today).
4. **`docs/cli.md:9-21`** — the Install section is `:9-19`. *Claim stands.*

Everything else was exact, including: `landing.ts:57` (`vk_live_9f3c…`), `:59`
(`"source_product": "checkout-web"`), `:11-13` (the false rationale comment); `hero.tsx:27-30` and
`:72-74`; `page.tsx:32-46`; `next.config.ts:43,55`; `Dockerfile:40`; `vocky.conf:282-288`;
`vitest.config.ts:30-33` (5 files / **61** tests confirmed); `.dockerignore:9`; `capture.py:27-31,80-81,84-89,325+`;
`app_api.py:241,320`; `auth.py:66-81,171-174`; `context.py:61-62,66-84`; `config_store.py:25-40,66-91`;
`client.py:103-106`; `operations.md:124`; `experience.md:14`; `frontend.md:84-89,229-231,269-270`;
`SIGNOFF.md:10` (project id + 30 cards); `types.ts:231,329`; `smoke.py:141`;
`tools/capture_feedback.py:36-37`.

Also independently confirmed: **exactly five** `os.environ`/`getenv` reads in `src/vocky/**`;
**`VOCKY_API_TOKEN` appears nowhere** in the tree outside `works/`; `web/public/` holds only `.gitkeep`;
`.github/workflows/` holds only `deploy-production.yml`, whose sole trigger is `workflow_dispatch`
(no `ci.yml` exists); `docs/reference/design/rounds/` holds only `01-brand-app-landing` (so round 02 is
next); `dist/` still holds the `0.1.0` artifacts and `pyproject.toml:7` still reads `0.1.0`.

## Two things found that the plan did not name

1. **A working nested-`source` reference already exists in-tree.** `src/vocky/smoke.py:112` posts
   `"source": {"product": "vocky-smoke", "integration": "make-smoke"}` and asserts the 202 receipt — the
   exact shape S1 must depict and S2 must build. Recorded in `phase.md`. (And `smoke.py:141`'s top-level
   `source_product` was verified in context to be a **query param** on `GET /api/feedback`, confirming the
   plan's "read path is correct, don't fix it" instruction.)
2. **Two stale install docs.** `docs/cli.md:11` ("PyPI publishing is planned (P6)") and `README.md:50`
   ("PyPI publishing is P6") are stale twice over — `intent.md` moved the publish to P11, and operator
   decision 1 then took PyPI off P11 entirely in favour of `curl | bash`. Recorded in `phase.md` as a
   finding for whichever slice ships the installer (S3) or the skill (S4); `DECOMP` writes no source, so
   nothing was changed. **Nothing was appended to `## Doc impact`** — no durable-truth change has landed
   yet.
3. **Hero body sanity check** (bonus, for S1's plan): `capture.py:34-57` confirms `feedback_value`,
   `target_type`, and `tags` are all valid **top-level** capture fields. Only `source_product` is wrong in
   the hero body — S1 must not "fix" the others.

## Validation

| Command | Result |
|---|---|
| `python3 scripts/workflow.py validate` | **pass** — "Workflow validation passed." |
| `python3 scripts/workflow.py next` | **pass** — `next_slice=P11.S1` |
| `works/backlog.md` inspection | **pass** — all six slices listed with the intended kind/order; `P11.S5` shows `co-work` |
| per-slice `slice.json` dump (kind/risk/order/depends_on) | **pass** — matches the plan's table exactly |
| bare-folder check (`ls -A` each new slice dir) | **pass** — every new folder contains only `slice.json` |
| `git status --short` | **pass** — changes confined to `works/` (`backlog.md`, `deferred.md`, `events.jsonl`, `index.json`, `state.json`, `phases/active/P11/**`) |

## Deviations from `plan.md`

None in substance. The only departures are the four corrected line citations above, made under the plan's
own instruction to "verify each before recording it; flag any disagreement in `phase.md` rather than
silently deviating."

## For the orchestrator

- **Next slice is `P11.S1`** (`low` risk → `slice-executor-low`). It is the one fully mechanical slice in
  the phase, and it must land **before** the `P11.S5` design gate: Claude Design reads the real repo, so
  the hero must be truthful before the handoff.
- **`P11.S5` is `co-work` and must be run inline on the main thread** — never dispatched (no executor has
  `DesignSync`). Two commits, `pending` in between.
- **`P11.DECOMP2` must not be pre-planned** — it is planned from the *landed* design, and `plan only`
  runs must stop before it (as they do before `REVIEW`).
- Each apply slice cut by `DECOMP2` needs **RESPECT THE DESIGN** in both its `plan.md` and its dispatch
  prompt.
