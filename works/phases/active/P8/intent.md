# Intent — P8

- Captured at: 2026-07-17T10:03:12+09:00
- Origin: operator

> **This phase was re-created on 2026-07-17 after a full revert.** An earlier P8 ran under rules that
> did not yet exist and was reverted at commit `c9102e3`. The operator's verbatim words below are
> carried forward unchanged from that phase (`git show 0007184:works/phases/active/P8/intent.md`);
> everything refined has been re-derived under workspace **v12**'s `design-cowork` skill. See
> *The correction* below — it is the reason this phase exists twice.

## Original Input (verbatim)

> make a design system for the vocky app, and make a design co-work slice for that task. I'll finish the design system and acutall user interface with claude design.

Context — the operator's preceding message in the same exchange, which framed the request:

> let me ask you a question. p4.s1 said design system foundation did but I can't find one. where is it? I meant design system for actual claude designs design system we didn't do that right?

### Additional Operator Input (verbatim — 2026-07-17, at the first `P8.DECOMP` planning)

> for the design system, make a design system only for vocky but inherit hi2vi vibe.

### The process correction (verbatim — 2026-07-17, after the first `P8.S1`)

The single most load-bearing statement in this phase. It predates v12 by ~8 hours and v12 codifies it
almost word for word:

> you don't understand the process. claude code will be nothing to do with the design. only claude design will do the design and after the design work, claude code(you) just use designsync skill to implement on this code base. you just make vocky's design system in claude design using dedicated skill, and wait till the design is done for the vocky app. and give me list of what to design.

### On implementation scope (verbatim)

> not just re-skinning. there maybe feature change while re-design process.

### The re-scope request (verbatim — 2026-07-17, this phase's re-creation)

> p8 is working phase but not match with new arrived v12 rule. revertwhat we've done for p8, and fresh start the design part again. with changed rule

## Confirmed Intent (refined + clarified)

Run vocky's **real Claude design gate** — the one P4 deliberately deferred (**D-P4-3**) — under
workspace v12's `design-cowork` rules. **This phase is the design only; the implementation is P9.**

**Why this phase exists.** P4.S1 shipped the design-system *mechanism* only: the Tailwind v4 `@theme`
token block in `web/src/app/globals.css`, the CVA primitives in `web/src/components/ui/`, and the
`web/design/canvas/` browser-openable mirror. Its **values** are a deliberately neutral placeholder
set — a slate surface ramp plus one indigo accent — reusing hi2vi_web's token *names* verbatim so a
later gate could swap values only (hence `--color-green` is currently indigo `#6366f1`). **No vocky
brand exists yet.** This phase supersedes **D-P4-3**, which deferred the intensive operator design
session to P6.

**Mechanism — v12's default: Seeded canvas + Connect GitHub.** Claude Code **seeds** the canvas by
mirroring live code, says **what** to design, **STOPS**, reads the result back via the `DesignSync`
**tool**, and P9 implements it. Claude Design gets **the real repo** (the operator runs **Connect
GitHub**) **+ the hand-mirrored palette**. The gate closes with a `SIGNOFF` written by Claude Code.

- Live target: claude.ai design-system project **`1eaa0803-46e3-426a-ab04-17a802170234`**
  (`vocky design system`, `PROJECT_TYPE_DESIGN_SYSTEM`, verified).
- **The `/design-sync` skill is forbidden here** — see *The correction*.

**Division of labor — the load-bearing constraint.** The agent's scope is **canvas prep only, with
zero brand decisions.** Build a faithful seed mirroring the *real shipped surfaces* at the current
placeholder palette, push it, and hand off. Every brand decision is concluded **in the operator's
Claude Design session, with Claude Design asking the operator those questions.** The agent does not
propose a palette, a type direction, or a brand — and never answers a design question; it poses it
back.

**The line** (v12, and the operator's own ruling that let the first `P8.S1` survive its re-scope):
*documenting what exists is Claude Code's job; deciding what it should look like is Claude Design's.*
Mirroring the live palette into a card is documentation. Proposing a palette is design — not ours.

**One session covers app + landing together:**

- Foundations — colors, type, spacing/radius.
- Components — `button`, `card`, `badge`, `field`, `grid`, `section`, `data-table`.
- App sections — login/signup, app shell, dashboard, project detail, feedback list, feedback detail
  (every surface P4.S2–S5 shipped).
- Landing sections — hero, features, pricing, footer.

**Landing copy is not drafted by the agent.** Claude Design surfaces the value-prop and messaging
questions during the session, and the `SIGNOFF` carries the real copy back.

**Implementation is a floor, not a ceiling — and it is P9.** Per the operator: *"not just re-skinning.
there maybe feature change while re-design process."* P9's slices follow the signoff wherever it lands
— token/palette swap, primitive changes, app surface rework, the landing build, **and any feature or
UX changes the session concludes on**, including backend if required. **The phase's true size stays
unknown until the signoff; that is accepted**, and is why P9 is a separate phase whose `DECOMP` runs
only after this gate closes.

## The correction — why P8 exists twice

The first P8 named its mechanism as *"synced via the `DesignSync` tool **+ the `/design-sync`
skill**"*. That conflated two different things:

| | What it is | Verdict |
| --- | --- | --- |
| **`DesignSync` tool** | read/write the design project — push the seed, read the design back | **Correct.** What v12 prescribes, and what the operator meant. |
| **`/design-sync` skill** | a repo→component-bundle compiler that runs *before* design work | **Forbidden here.** v12: never run it on a repo with no design system in code. |

**The operator never asked for the bundle path.** Their words were *"after the design work, claude
code(you) just use designsync skill to **implement on this code base**"* — that clause describes the
**read-back**, which is the `DesignSync` tool. The bundle compiler runs before design work and does
the opposite thing.

An agent wrote the conflation into the confirmed intent; a later agent read it and dutifully ran
`/design-sync` **off-book** (`P8.S6` still read `todo`, with no plan, no result, and no entry in
`works/events.jsonl`). It walked into what v12 calls **the app-first trap** and reached 3 of 13
components. The measured evidence is in `phase.md` → *Harvested from the reverted `/design-sync` run*
and *The anti-finding*.

**v12 exists partly because of this.** The plan that built the `design-cowork` skill names vocky P8
as one of its two motivating failures, and lists *"apply the ruling to vocky"* as a deliberate
follow-up. This phase is that follow-up.

## Clarifications Resolved

Carried forward from the first P8 (still binding):

- Q: Where should the design co-work slice live — inserted into P4, a new phase, or P6? — A: A new
  phase before P5, and it includes the real implementation. (→ order `4.5`, following P7's
  fractional-insert precedent at 3.5.)
- Q: How far should the agent take the design system before handing off — canvas prep with no brand
  decisions, or a first-cut brand proposal to refine? — A: **Canvas prep only**; "the brand decisions
  will be concluded with the claude design. by it asking me those."
- Q: Which surfaces go on the canvas — app only, or app + landing? — A: **App + landing together**, in
  one session. This absorbs P6's design work.
- Q: Does "include real implementation" cover building the landing page too, or just re-skinning the
  app? — A: **Everything**, "and not just re-skinning. there maybe feature change while re-design
  process."
- Q: The landing page has no copy or value prop written yet — where does that come from? — A: Claude
  Design asks the operator during the session; cards ship with placeholder copy.
- Q: P8 absorbs P6's landing design and landing build — should P6 be re-scoped now? — A: **No.** Note
  the consequence here; leave P6 untouched and reconcile at `P6.DECOMP`.
- Q: The app-section list says "login, tenant dashboard, project detail, usage" but never names the
  feedback list/detail that P4.S5 shipped — how much canvas coverage? — A: **Every shipped surface**
  (login/signup, app shell, dashboard, project detail, feedback list, feedback detail).
- Q: If the design session concludes on feature/UX changes, does that reopen the P2/P3 API contracts
  or stay frontend-only? — A: **Backend in scope if needed.** The phase may reopen `src/vocky/**` and
  the P2/P3 contracts to serve what the design concludes.
- Q: "Inherit hi2vi vibe" collides with "canvas prep only, zero brand decisions" — how does the vibe
  reach the session without the agent deciding vocky's brand? — A: **A reference card on the canvas**,
  clearly labeled `Reference — hi2vi vibe`, showing hi2vi's real palette/type beside vocky's current
  values, so Claude Design can ask the operator how far to carry it. The claude.ai project stays
  **vocky-only** otherwise. (v12 independently prescribes exactly this: any operator-named reference
  goes in *"clearly labeled REFERENCE — data, not a proposal."*)
- Q: Must P4.REVIEW close before this phase starts? — A: Yes, and it has — `P4.REVIEW` passed at
  commit `8cea96f`.

### Resolved at the v12 re-creation (2026-07-17)

- Q: How deep should the revert go? — A: **Full revert of P8**; re-create the phase fresh under v12.
  (Done at `c9102e3`. The canvas is byte-identical to `8cea96f` again, so the first `P8.S1`'s
  foundations work is redone as part of this phase's seed — under v12, and now also carrying the
  frozen baseline render.)
- Q: The claude.ai project holds a half-pushed bundle — reuse it or start fresh? — A: **Fresh
  project; abandon the current one.** The operator's Design systems UI does **not** show
  `2d64ae63-…` even though `list_projects` returns it — and an invisible project cannot host a design
  gate. *(Claude Code initially argued to reuse it, on the strength of `list_projects`. The operator's
  screen was right; the API and the UI disagreed.)* DesignSync has **no `delete_project`**, so the old
  shell persists forever — it was emptied of all 23 files instead. **Both projects are named
  `vocky design system`; target by id, never by name.**
- Q: v12 says a big design change → two phases. One phase or two? — A: **Two.** P8 = design (order
  4.5), **P9 = apply (order 4.6)**. Both still land before P5@5, so the operator's original "a new
  phase before P5, and it includes the real implementation" ruling holds on both clauses: the
  implementation happens in this stream, ordered before P5, rather than being deferred a third time.
- Q: v12's default mechanism needs the operator to run Connect GitHub, which needs `main` on origin —
  but `main` is 36 commits ahead and the repo is public. — A: **Push, then Connect GitHub.** v12
  authorizes exactly this one push, **at the gate slice only** — *"it is not a standing permission."*
  See the Notes for what that publishes.

## Notes

- **The gate slice must be `--kind co-work --risk high`, and is NEVER dispatched.** v12's deliberate
  exception to the contract's "every slice is delegated": executors have no `DesignSync` tool, so
  every push and read-back is **orchestrator-inline**. Never rate a design gate `low`.
- **Do not over-plan before the gate.** v12: *"you do not know what the operator will design."*
  `DECOMP` creates round 1 only — seed, brief, gate, synthesis. If the session needs a round 2, cut it
  at a fractional order afterward; *"expect the gate to re-shape the phase."*
- **The one authorized `git push`** publishes ~340 files / +38k lines to the **public**
  `github.com/leetusik/vocky`, including all of `works/` — every phase notebook and every verbatim
  operator message in this file. **No secrets travel** (verified: `.env` is gitignored, `web/.env.local`
  matches `web/.gitignore:4 .env*.local`, only `*.env.example` are tracked). Worth one deliberate look
  before the gate slice runs.
- **P6 consequence (deliberately not yet applied).** P8+P9 absorb both the landing *design* and the
  landing *build*, which leaves **P6 as production-deploy-only** (vocky.hi2vi.com, the oracle-cloud
  box, nginx via edge). P6's name, objective, and `intent.md` are **intentionally untouched** — the
  operator chose to reconcile them at **P6.DECOMP**. P6's intent still reads "landing page + deploy"
  and still claims the design-gate workflow; that is known and stale, not an oversight.
- **The canvas is a scaffold, not a baseline.** `web/design/canvas/` holds `tokens.css` (a 1:1 `:root`
  mirror of the app's `@theme`), `_ds_manifest.json` (125 tokens, 10 cards), foundations + component
  cards, and `sections/dashboard-placeholder.html`. **No card mirrors a real shipped surface**, and
  the one section card is **fictional** — its table is `Project | Status | Last used` with badges; the
  real dashboard is `Name | Created`, no badges. **Delete it, don't push it** — a card with nothing
  real to mirror is invention, and a *fictional* card is worse than none.
- **Canvas ↔ app sync is manual and bidirectional-by-hand.** `globals.css`'s `@theme` is the source of
  truth for the running app; `canvas/tokens.css` mirrors it. A read-back must edit both in lockstep.
  Standing v12 obligation: any slice that changes `@theme`, a component variant, or a designed surface
  must **re-push**, or the next design pass runs against a lie.
- **The `/` design-system preview page is gone.** P4.S2 replaced P4.S1's preview at
  `web/src/app/page.tsx` with a session redirect, so today the canvas HTML files are the only way to
  view the system.
- All measured findings, the harvested `/design-sync` evidence, the anti-finding, and the open gate
  questions live in [phase.md](phase.md) → *Findings & Notes*. **Do not re-derive them.**
