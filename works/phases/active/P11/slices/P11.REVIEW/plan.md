# P11.REVIEW — phase review

## What you are reviewing

**P11: Frictionless onboarding — working install, env-var quickstart, agent skill on the landing.**

Eleven slices ran: `DECOMP`, `S1`–`S5`, `DECOMP2`, `S6`–`S10`. `S5` was a `co-work` design gate (round 02),
and `DECOMP2` cut the build from the landed design — a two-pass decomposition, per `design-cowork`.

Read, in this order: `works/phases/active/P11/intent.md` (the operator's confirmed intent — the source of
truth for what was asked), `phase.md` (the notebook: operator decisions, grounded facts, DECOMP2's nine
corrections, every slice's landed notes, and the `## Doc impact` list), then each slice's `plan.md` and
`result.md`, then `AGENTS.md`.

## The objective, as stated

> Make vocky's onboarding real end to end for a coding agent: ship an install path for the `vocky` CLI that
> actually runs from the landing page, add the missing `VOCKY_API_TOKEN` so two environment variables are
> the whole agent contract alongside today's `VOCKY_BASE_URL`, publish a copyable and downloadable end-user
> `SKILL.md` on the landing behind a byte-parity CI gate, and correct the landing's untrue hero payload.
> Any net-new landing section goes through a design-cowork gate; no new backend capture contract.

Judge the phase against **that**, and against `intent.md` — not against what you would have built.

## Validate all slices together

Run these and record verbatim output. This is the phase's consolidated behavioural validation — the
orchestrator deliberately did **not** re-run each slice's tests at its boundary.

From the repo root:

1. `python3 scripts/workflow.py validate` → passes.
2. `uv run pytest -q` → compare against the phase baseline. This environment has a live Postgres, so expect
   ~**209** passed / 0 errors (S2 established it; the ~108-error figure in older citations describes a
   no-DB environment). Report the number.
3. `python3 scripts/skill_parity.py` → `PASS`, and `cmp skills/vocky-feedback/SKILL.md web/public/SKILL.md`
   → identical.
4. `bash -n web/public/install.sh` → exit 0; `tail -n 1 web/public/install.sh` is exactly `main "$@"`.
5. `uv run vocky capture --help` and `uv run vocky --help` → render, `capture` listed.

From `web/`:

6. `pnpm lint`, `pnpm typecheck` → exit 0.
7. `pnpm test` → **78** passed across 10 files.
8. `pnpm build` → succeeds, **zero warnings**, `/` stays `ƒ` (dynamic since P9.S6 — not a regression).

Then sanity-check the CI workflow will actually be green when it first runs: `.github/workflows/ci.yml`
runs the parity script, the installer syntax check, and web lint/typecheck/test — all four are covered
above. Confirm it does **not** run `prettier --check` (12 pre-existing failures) or `pytest` (needs
Postgres); both exclusions are deliberate and belong to P12.

## Review against the objective

Work through each pillar and say plainly whether it landed:

1. **A working install path.** Operator decision: `curl | bash`, **not** PyPI. `web/public/install.sh`
   exists, all logic inside `main()` with `main "$@"` last so a truncated download cannot half-execute
   (proven at two cut points), `uv` bootstrapped only when absent, `--reinstall` for idempotent upgrades,
   no sudo. Docs corrected to drop the stale "PyPI publishing is P6" promise.
   **Check the honesty claim holds**: the hosted line is presented as live *once the site deploys*, and the
   site is not deployed until P12 — so no live page ever serves a dead command.
2. **`VOCKY_API_TOKEN` + a consumer.** `resolve_api_token()` beside `resolve_base_url`; a real
   `vocky capture` command; env-var only, no `--token` flag (argv is world-readable via `ps`); no
   config-store slot (`clear_token()` pops only `"token"`, so a persisted `vk_` key would survive
   `vocky logout`). Verify the session token and the `vk_` key genuinely cannot cross —
   `make_client(token=…, use_stored_token=False)` is the structural guarantee.
3. **The skill, published behind a byte-parity CI gate.** `skills/vocky-feedback/SKILL.md` → byte-identical
   `web/public/SKILL.md`, held by `scripts/skill_parity.py` in `.github/workflows/ci.yml` — the repo's
   first push/PR gate. Check the skill is written against the surface that actually shipped (its commands
   must match `src/vocky/cli/capture.py`'s real options and output strings).
4. **The hero honesty fixes.** No `vk_live_` tier; nested `source.product`. Confirm both, **scoped to
   `web/` and `src/`** — three read-only S5 design-record files under `docs/reference/design/` contain
   `vk_live_` in negation form documenting the correction, permanently and expectedly.
5. **The design-cowork gate.** Every net-new landing section went through round 02: handoff → `pending` →
   read-back → landed as-is → SIGNOFF, with the design slice run inline and never dispatched. Check the
   record is complete and **read-only**, the SIGNOFF records the operator's authorization and a token delta
   of `None.`, and no build slice edited `output/`.
6. **No new backend capture contract.** `POST /api/feedback` untouched. Verify.

## Scrutinize these specifically

Things a careless review would wave through:

- **Deliberate departures that must be judged, not just noted.** (a) Both new sections keep `Section`'s
  shipped padding (72/104px) rather than the contract's explicit `84px 28px` — argued in S9's and S10's
  `result.md` on the grounds that `28px` is not the landing's gutter. (b) `ci.yml` omits `format:check` and
  `pytest`. Decide whether each is sound, and say so.
- **`RESPECT THE DESIGN`.** Spot-check the built sections against `build-prompt.md` §4–§7. Was anything
  dropped, simplified, or restyled to save effort? The states table (2s revert on success, **persisting**
  failure with programmatic selection), the no-JS floor (buttons **absent**, not inert), and the preview's
  computed — never hardcoded — line/byte counts are the highest-risk places.
- **The no-JS floor is a locked floor, not a nicety.** The full 119-line file must be in the server HTML;
  a 22-line truncation would pass every CI check and still break it.
- **Test quality over quantity.** `AGENTS.md` wants terse, high-value tests. 61 → 78 across the phase.
  Judge whether the 17 additions are high-value or scaffolding.
- **What was NOT proven.** The site is not deployed, so nothing was verified against a live origin, and
  `ci.yml` has never executed on a GitHub runner. Every `result.md` should say so. Confirm the P12 hand-off
  in `phase.md` is accurate and complete — especially the armed flip probes (`/install.sh` and `/SKILL.md`
  are 404 today) and the **`git push` prerequisite**: GitHub `main` is 45 commits behind, so the installer's
  `git+https://` target would deliver a pre-P10 CLI until it is pushed.

## Doc consolidation — ONLY on a passing verdict

`phase.md`'s `## Doc impact` list has bullets from S2, S3, S4, S6, S7 (a retroactive addendum S10 added),
S8, S9 and DECOMP2. **If and only if your verdict is `pass`**, consolidate them into new doc versions with
`python3 scripts/workflow.py doc-new-version --doc <name> --summary "..." --source P11.REVIEW`.

Expected, but verify against the actual list rather than trusting this plan:

- **`frontend`** — the landing gains two sections (`AgentQuickstart` at `#quickstart`, `SkillSection` at
  `#skill`), new primitives (`Snippet`, `Trap`) and helpers (`lib/clipboard.ts`, `lib/use-is-hydrated.ts`),
  `section-ids.ts` grows, and the landing now reads a served static file at request time. **One
  consolidated version**, not one per slice.
- **`experience`** — the onboarding story: a real install line, the two-variable agent contract, the
  published skill.
- **`product`** — the agent-skill surface and its three capture paths; the install decision.
- **`operations`** — `web/public/install.sh`, `.github/workflows/ci.yml` as the first push/PR gate with its
  two deliberate exclusions, and the CLI's new `capture.py` module.
- **`qa`** — only if the CI gate genuinely belongs there. `docs/current/qa.md` is still the bootstrap
  placeholder and **P12 owns writing it** — do not pre-empt that here.

**Never hand-edit `docs/current/*.md`** — they are generated. Never patch old files under `docs/versions/`.
Write **only docs**, never source.

**On `changes_requested` or `blocked`: STOP before any consolidation.** Complete the validation and the
judgment first — so the orchestrator gets the whole picture in one cycle rather than one finding per cycle
— then return the verdict with **numbered findings and proposed fix slices**, and do no pass-only work.

## Return

- `review_verdict`: `pass` | `changes_requested` | `blocked`
- `doc_versions`: the versions created (pass only), or `none`
- `explain`: the fixed pointer `not written — run /explain for this phase`. **Do not write a phase
  explainer** — explaining is a separate operation the operator runs.

Write `works/phases/active/P11/slices/P11.REVIEW/result.md` from scratch (free-form): the validation
evidence, the pillar-by-pillar judgment, the departures you accepted or rejected and why, what was not
proven, and the doc versions created. Append any durable notes to `phase.md`. Do not commit and do not
change any slice or phase status — the orchestrator records the verdict with `review-phase`.
