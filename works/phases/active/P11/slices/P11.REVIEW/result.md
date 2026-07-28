# P11.REVIEW — result: **pass**

Phase **P11: Frictionless onboarding** — eleven slices (`DECOMP`, `S1`–`S5`, `DECOMP2`, `S6`–`S10`),
two decomposition passes around a `co-work` design gate. All six objective pillars landed. Two deliberate
departures were examined and **accepted**. Four consolidated doc versions were written.

**Verdict: `pass`.** Nothing was found that a fix slice should close.

---

## 1. Consolidated validation — every command, verbatim

Run at review time, from a clean tree (only `works/` state modified by the in-flight slice). The
orchestrator deliberately skipped per-slice re-validation, so this is the phase's behavioural gate.

| # | Command | Result |
|---|---|---|
| 1 | `python3 scripts/workflow.py validate` | `Workflow validation passed.` |
| 2 | `uv run pytest -q` | **`209 passed in 9.72s`** — 0 errors (live Postgres present, as S2 established) |
| 3 | `python3 scripts/skill_parity.py` | `PASS — web/public/SKILL.md matches the canonical skill byte-for-byte.` (exit 0) |
| 3b | `cmp skills/vocky-feedback/SKILL.md web/public/SKILL.md` | identical; `wc -l -c` = **119 / 7975** on both |
| 4 | `bash -n web/public/install.sh` | exit 0 |
| 4b | `tail -n 1 web/public/install.sh` | exactly `main "$@"` |
| 5 | `uv run vocky --help` / `uv run vocky capture --help` | both render; `capture` listed between `whoami` and `usage`; every option matches the skill's documented surface |
| 6 | `pnpm lint` | exit 0, no output |
| 6b | `pnpm typecheck` | exit 0, no output |
| 7 | `pnpm test` | **`Test Files 10 passed (10)` / `Tests 78 passed (78)`** |
| 8 | `pnpm build` | `✓ Compiled successfully in 1549ms`, **zero warnings**, `┌ ƒ /` (dynamic since P9.S6 — not a regression) |

### 8b. Live-server probe (beyond the plan's list)

I did not take S9's and S10's `next start` evidence on trust — I re-ran it. `pnpm exec next start` on a
spare port, `GET /` → **HTTP 200, 124 018 bytes**, then analysed the pre-hydration HTML:

```
buttons in whole page:                 1      (P9's disabled Pricing CTA, `disabled=""` — nothing else)
buttons in #skill section:             0
all 84 non-blank SKILL.md lines inside #skill:  0 missing
header meta "119 lines"/"7975" present: True
href="/SKILL.md": 3    download attr: 2
id="quickstart": True   href="#skill": True
nav anchors, in order: How it works · Get started · Features · Pricing · Docs
vk_live_ in served HTML: False
install command present verbatim: True
```

**The no-JS floor is genuinely intact**, not merely asserted: the whole skill file is in the server HTML,
and there is not one copy button anywhere in the document before hydration.

### 8c. CI green-on-first-run sanity check

`.github/workflows/ci.yml`'s three jobs run exactly commands 3, 4 and 6/6b/7 above — **all four are
covered and all four pass locally**, so the workflow will be green when it first executes. Confirmed by
reading the file that it runs **neither** `prettier --check` **nor** `pytest`; both exclusions are
commented in the file itself with a pointer to P12.

### 8d. What I could not verify

`curl https://vocky.hi2vi.com/install.sh` and `/SKILL.md` returned **`Could not resolve host`** from this
environment (no outbound DNS), so I could not independently re-confirm the armed `404` probes. This costs
nothing: the site is not deployed, the probes are P12's to run, and no P11 claim depends on them.

---

## 2. The objective, pillar by pillar

### 1. A working install path — **landed**

`web/public/install.sh` (61 lines) exists and is exactly the shape the operator decision called for:
`curl | bash`, **not** PyPI; `set -euo pipefail`; every executable statement inside `main()` with
`main "$@"` as the literal last line; `uv` bootstrapped via the Astral installer **only when absent** (a
branch S3 genuinely exercised under `env -i`); `uv tool install --reinstall` for idempotent upgrades; no
sudo, nothing outside `$HOME/.local`; PATH-tolerant verification that warns rather than dies; closing
lines that print both the next command and the two-export agent line. The truncation safety was proven at
**two** cut points, which is stronger than "argued".

`docs/cli.md` and `README.md` both carry the exact hosted line, explicitly marked "once the site is live",
with the checkout path kept as what works today. The stale PyPI promise is gone from both
(`grep -rn "PyPI\|pip install vocky\|uv publish" README.md docs/cli.md` → zero).

**The honesty claim holds.** The hosted line 404s today, but the site is not deployed and the landing page
that shows it ships in the *same* P12 bring-up — so no live page ever serves a dead command. That is the
right resolution of the tension `intent.md` flagged, and it is stated in the copy rather than left implicit.

### 2. `VOCKY_API_TOKEN` + a real consumer — **landed**

`resolve_api_token()` sits beside `resolve_base_url()` in `cli/context.py`; `vocky capture` is a real
top-level command in the new `cli/capture.py`. Every guard the plan asked me to verify is real, and each
is enforced structurally rather than by convention:

- **No `--token` flag** — `--help` confirms it; the docstring records the `ps`/shell-history reasoning.
- **No config-store slot** — `clear_token()` pops only `"token"`, so a persisted `vk_` key would have
  survived `vocky logout`. That bug was avoided by not persisting at all.
- **The two credentials cannot cross**: `context.make_client(token=api_token, use_stored_token=False)`.
  I read it at the call site — it is the structural guarantee the plan describes, not a comment.
- `client.py` gained an `unauthorized_message` override *only* so a `vk_`-keyed 401 stops saying
  "run `vocky login`". The change is additive and defaulted; no other outcome moves.
- `capture.py` hand-builds the body as a plain `dict` rather than importing `vocky.capture`'s pydantic
  models — import isolation held, and S2 re-proved it with a fresh wheel resolve (15 packages).

### 3. The skill, behind a byte-parity CI gate — **landed**

`skills/vocky-feedback/SKILL.md` (119 lines, 7 975 bytes) ↔ `web/public/SKILL.md`, byte-identical,
gated by `scripts/skill_parity.py` in `.github/workflows/ci.yml` — the repo's first push/PR gate. The
canonical is correctly **not** under `.claude/skills/` or `.agents/skills/`.

**I checked the skill against the surface that actually shipped, line by line**, and it matches:

| Skill claims | `src/vocky/cli/capture.py` / `context.py` / `client.py` |
|---|---|
| `--product` the only required option; `--tag` repeatable, omitted when empty; `-` reads stdin | matches exactly (`if tags:` — never sends `[]`) |
| `Captured — request_id <full uuid>` | `f"Captured — request_id {result['request_id']}"` |
| `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).` | `_UNAUTHORIZED_MESSAGE`, verbatim |
| ``VOCKY_API_TOKEN is not set — mint a key with `vocky keys mint` and export it.`` | `resolve_api_token()`'s `fail(...)`, verbatim |
| `Could not reach vocky at <base_url> (<exc>).` | `client.py`'s transport branch, verbatim |
| exit code always `1`, never the HTTP status | `fail`/`cli_errors` → `typer.Exit(1)` |
| `--project` honoured only for an org-level key | matches the help text and the REST contract |

**S4's flagged ambiguity is resolved in favour of what shipped.** Its plan said "REST primary" in one
sentence and labelled the CLI "Path A … (primary)" in another; the skill was written CLI-first. That is
the correct reading and the phase is internally consistent with it: S2 framed `vocky capture` as
`VOCKY_API_TOKEN`'s first-class consumer, and the landing's quickstart is install-CLI-first with REST as
the peer path behind "No install, or not zsh?". No change needed.

### 4. The hero honesty fixes — **landed**

`grep -rn "vk_live_" web/ src/` → **exit 1, zero matches** (scoped as the plan directs; the three
`docs/reference/design/` hits are read-only S5 record files documenting the correction in negation form).
`grep -n "source_product" web/src/content/landing.ts` → exactly one hit, and it is the *explanatory
comment* distinguishing the read path from the capture request. The hero body is
`"source": { "product": "checkout-web" }` and the auth line is `Bearer vk_9f3c…`. The read-path
`source_product` (feedback pages, `lib/vocky/types.ts`, `smoke.py`) was correctly left alone.

In the served HTML, the only `source_product` anywhere on the page is inside the skill preview — in the
skill's own sentence "a top-level `source_product` field is rejected outright". That is the correction
being taught, not repeated.

### 5. The design-cowork gate — **landed, and clean**

`docs/reference/design/rounds/02-onboarding/handoff.md` (OUT) + `output/{result.md, build-prompt.md}` (IN),
plus a SIGNOFF entry that records the operator's literal authorization (`"done"`), the delegation of all
thirteen §6 questions ("Decide for me"), the project id, the 43-card set staying in the design project,
and a **token delta of `None.`** — all as the plan requires.

**The record is verifiably read-only.** `git log 880bc93..HEAD -- docs/reference/design/` returns exactly
two commits, both `P11.S5`'s (`73e449d` handoff, `5f06ed2` read-back). **No build slice touched `output/`**
— DECOMP2 catalogued its nine corrections in `phase.md` instead of editing the contract, which is exactly
right. `git diff --stat` confirms `web/src/app/globals.css` was never touched by any P11 commit, matching
the `None` delta.

The design slice was run inline on the main thread and never dispatched, per `design-cowork`.

### 6. No new backend capture contract — **confirmed**

`git diff --stat 880bc93..HEAD` over `src/` shows changes in **`src/vocky/cli/` only** (`app.py`,
`capture.py`, `client.py`, `context.py`, `projects.py`). `src/vocky/capture.py`, `api.py`, `auth.py`,
`app_api.py`, `mcp_server.py` and the tools are **untouched**. `POST /api/feedback` is byte-for-byte the
P10 shape.

---

## 3. The two deliberate departures — judged

### (a) Both new sections keep `Section`'s shipped padding, not `84px 28px` — **accepted**

The contract states `Padding: 84px 28px; container 1180px` for §5 and §6; both sections ship
`py-section md:py-section-lg` (72/104px) with the standard `px-5 md:px-14` gutter, and honour
`container: 1180px` exactly via `max-w-page`.

I accept it, on the argument S9 and S10 made rather than on the one S8 opened with:

1. **The horizontal half is decisive.** `28px` is not this landing's gutter — every other `Section` uses
   20/56px. Honouring `28px` would put these two bands' content edge visibly out of line with the hero,
   `HowItWorks` and `Showcase` immediately above and below. That is a *visible* fidelity failure; the
   vertical delta is invisible in isolation. Trading a visible break for an invisible one is the wrong way
   round.
2. **The string reads as tool boilerplate.** `Padding: 84px 28px` appears *word for word* on two
   structurally different sections, always paired with the same `container 1180px` line — the same
   artifact class DECOMP2's correction 3 already identified for `.eyebrow`/`.note`/`.tag`/`.card`, which
   turned out to be card-kit specimen classes with zero repo counterparts. `container: 1180px` survives
   because it coincides with a real token, not because the whole line is normative.
3. **`Section` is a shared primitive whose entire job is one padding rhythm.** A one-off override here
   would make these the only two exceptions on the page — itself a fidelity break.

Two things make this an acceptable departure rather than a shortcut: it was **not taken to save effort**
(an override is one class — strictly less work than the argument they wrote), and it was **applied to both
sections identically**, which S9 correctly identified as the only two coherent options. S10 also
re-derived it independently and **dropped S8's weakest supporting point** (that "no token lands on 84px"
forbids it — `py-[84px]` adds no token, and this round uses arbitrary values a dozen times), keeping the
conclusion on the stronger grounds. That is a review-grade self-correction, and it is why I trust the call.

### (b) `ci.yml` omits `format:check` and `pytest` — **accepted**

Both are sound, and both are documented **in the workflow file itself** with a pointer to P12 — not
buried in a `result.md`.

- **`prettier --check`**: 14 files fail today (12 P4-era, plus `agent-quickstart.tsx` and `hero.tsx`,
  which differ only by `prettier-plugin-tailwindcss` class ordering). Gating on it would make the repo's
  first CI run red for reasons unrelated to any change under review, which teaches everyone to ignore CI.
  Fixing 14 unrelated files inside a feature phase is exactly the scope creep `AGENTS.md` warns against.
- **`pytest`**: needs a live Postgres; a bare runner has none. Adding a service container is real work,
  and P12 already owns it. Crucially the file was **shaped so P12 appends a job**, not so P12 starts over.

One residual worth recording, not a finding: 2 of the 14 format failures are new to this round. They are
cosmetic, ungated, and precisely documented by S10 — I have folded the corrected count into the `frontend`
doc so a later sweep does not undercount.

---

## 4. Scrutiny items the plan named

**RESPECT THE DESIGN — held.** I spot-checked the built sections against `build-prompt.md` §4–§7 and
found nothing dropped, simplified or restyled:

- **§7's asymmetric states are real in code.** `snippet.tsx`: success reverts after exactly
  `COPIED_REVERT_MS = 2000` with the timer cleared on unmount; failure sets `"failed"` and **persists**,
  and `selectCommandText()` builds a real `document.createRange()` + `selection.addRange()` over the
  command node. The failure hint renders only in that state. One **polite** live region per snippet,
  success only. `grep` confirms **no `role="alert"` and no `aria-live="assertive"`** anywhere in the new
  components, and `Trap` is an `<aside>` — §9's explicit requirement.
- **The clipboard rule is real.** `command` renders into a ref'd `<code>`/`<pre>` and the click reads
  `node.textContent`; `attemptCopy` takes the read as a *callback* so a failing read is also a failure.
  The block's recolouring `<span>` does not alter `textContent`, so comment lines are copied verbatim.
- **The counts are computed.** `readServedSkill()` does `fs.readFile(…"public","SKILL.md")` and derives
  `content.split("\n").length - 1` / `Buffer.byteLength(content)`. `grep -n "119\|7975"` over the five
  new skill modules → no matches. S10 re-proved it dynamically (append a byte → served meta reads
  `120 lines · 7976 bytes`; restore → `119 lines · 7975 bytes`, `git status` clean, parity `PASS`).
- **The no-JS floor** — see §1 8b. Verified by me against a running server, not inherited.

**Test quality — high-value, not scaffolding.** 61 → 78, +17 across 5 files (32–63 lines each). Every one
targets a failure mode that would otherwise ship green:

- `clipboard.test.ts` (3) — the three `attemptCopy` outcomes, including a *read* that throws. Mistaking
  failure for success would flash "✓ Copied" and clear itself while the clipboard held something else.
- `landing-copy.test.ts` (3) — the three commands a visitor is invited to **paste**, re-spelled as
  literals, plus a cross-check that the install line appears verbatim in `web/public/install.sh`. A
  prettier reflow or a smart quote would render, typecheck and ship a broken command.
- The three `*-ssr.test.ts` (11) — the no-JS floor asserted in the server HTML, including an assertion on
  `SKILL.md`'s **last** section so a reintroduced truncation fails CI.

No fixture sprawl, no scaffolding, no test that merely restates an implementation. This is what
`AGENTS.md` asks for. What they cannot reach (the 2 s timer, the real `Range`/`Selection`, the
announcement, `< 900px`) is stated as unverified in every `result.md` rather than papered over — the Node
env has no jsdom, and adding a browser runner was correctly not smuggled into a feature slice.

**What was NOT proven — every `result.md` says so.** S2 (no live round trip), S3 (no live fetch, real
`git+https://` target never installed from), S4 (workflow never ran on a runner, `/SKILL.md` never
fetched live), S7/S8/S9/S10 (nothing checked against a live origin). Consistent and honest throughout.

**The P12 hand-off is accurate and complete, with one stale number.** The armed flip probes are recorded
with their exact commands and expected `404 → 200`; the `git push` prerequisite is stated as a hard
prerequisite, not a nicety, with the concrete post-push assertions (`vocky --version` ≥ `0.2.0`,
`vocky capture --help` renders). **The "45 commits behind" figure is now 56** — `origin/main` is still
`3e1e85a` (last pushed 2026-07-17), and P11's own eleven commits landed after S3 wrote that line. The
substantive claim is unchanged and correct. I appended a correction to `phase.md` rather than treating it
as a finding.

---

## 5. Doc consolidation — four versions, one per doc

Written **only** on this passing verdict, from `phase.md`'s `## Doc impact` bullets (S2, S3, S4, S6, S7
addendum, S8, S9, DECOMP2), folded per doc rather than per slice. No `docs/current/*.md` was hand-edited;
`rebuild-docs` regenerated them.

| Doc | Version | Covers |
|---|---|---|
| `frontend` | **v0007** | S6 + S7 + S8 + S9 + S10 + DECOMP2, in one pass: the two new sections and the five-link nav reorder, `Snippet`/`Trap` in the primitive inventory, `section-ids` + the four `landing.ts` copy blocks, `lib/clipboard.ts` + `lib/use-is-hydrated.ts`, the three net-new mechanics (mount gate, `textContent` clipboard rule, request-time `fs` read), the locked no-JS floor and how it is regression-tested, the hero honesty correction, the padding departure with its argument, tests 61 → 78, and format:check 12 → 14. Four new constraints. |
| `experience` | **v0011** | S2 + S3 + S4: the hosted `curl \| bash` install line and its `main()` safety argument, the two-variable agent contract (`~/.zshenv`, the Codex `network_access` trap, no `--token`, no persistence, the 401 remap), `vocky capture` in the onboarding journey, and the published `vocky-feedback` skill with its three capture paths. |
| `product` | **v0010** | S3 + S4: distribution decided as `curl \| bash` (PyPI off the table, `uv publish` unexercised), the agent-skill surface as a product surface, and the correction that the CLI now straddles both auth planes in exactly one place. |
| `operations` | **v0005** | S2 + S3 + S4: `web/public/install.sh` in full, `.github/workflows/ci.yml` as the first push/PR gate with its three jobs and two documented exclusions, `capture.py` in the CLI module list with its import-isolation consequence, `VOCKY_API_TOKEN` resolution beside base-URL resolution, the armed flip probes, and three P12 gaps. |

**`qa` was deliberately not versioned.** `docs/current/qa.md` is still the 14-line bootstrap placeholder
and **P12 owns writing it**; the CI gate is documented where it operationally belongs (`operations.md`).
Writing a partial `qa.md` here would pre-empt that and leave P12 patching a stub.

`docs/cli.md` and `README.md` were edited directly by S3/S2 — correct, since they are hand-written
reference files, not generated `docs/current/*` snapshots.

---

## 6. Deviations from `plan.md`

1. **One doc version was created, deleted, and recreated.** My first `doc-new-version --doc frontend`
   summary ended in "…the served SKILL.md", whose slug produced a `…skill.md.md` filename. I removed the
   stray version file and `git checkout`-ed `docs/index.json` + `docs/current/frontend.md` (both were
   clean beforehand and their only modification was that command), then re-ran with a summary ending
   "…the served skill file". The only trace is one superseded entry in the append-only
   `works/events.jsonl`; `validate` passes. **Cosmetic housekeeping, no content impact.**
2. **I ran one probe beyond the plan's list** — `next start` + a fetch of `/` — rather than accepting S9's
   and S10's page-level evidence on trust. The no-JS floor is the phase's highest-risk invariant and the
   plan calls it a locked floor, so re-proving it independently was worth the two minutes.
3. **The live 404 probes could not run** (no outbound DNS from this environment). Recorded in §1 8d;
   they are P12's to run and no P11 claim rests on them.

Nothing else departed. No source file was edited — a review slice writes only docs, `result.md` and
`phase.md`. No status was transitioned and nothing was committed; the orchestrator records the verdict
with `review-phase`.

---

## 7. Verdict

**`pass`.** The phase did what its objective said, against the model `intent.md` describes: the install
path is real and safe, `VOCKY_API_TOKEN` has a first-class consumer with the credential split enforced
structurally, the skill is published behind a gate that cannot be bypassed silently, the two hero
falsehoods are gone, the design gate was run properly and its output respected, and no backend contract
moved. The two departures are argued, consistent and correct. The unproven work is precisely the work the
phase could not do without a deploy, and it is handed to P12 as falsifiable probes rather than assertions.

`explain: not written — run /explain for this phase.`
