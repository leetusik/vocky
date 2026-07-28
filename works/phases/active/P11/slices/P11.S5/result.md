# P11.S5 — Design round 02: onboarding on the landing · result

**Status: `done`.** Gate opened and closed 2026-07-29. Run **inline on the main thread** — a `co-work`
slice is never dispatched, because `DesignSync` is main-thread only and no executor has it.

## What happened

1. **Handoff written** — `docs/reference/design/rounds/02-onboarding/handoff.md`. It named three surfaces,
   grounded every claim in real files (the skill quoted by its actual 8 section headings and 119-line
   length; the install line quoted verbatim from `web/public/install.sh`), stated what was locked, required
   the card set with its line-1 `@dsCard` marker plus `result.md` and `build-prompt.md`, and posed **nine
   numbered open questions** (thirteen counting the sub-parts) — answering none.
2. **`pending`** — the operator ran the round in Claude Design.
3. **Read back** with `DesignSync`, main-thread and read-only: `get_project` (verified **by id**),
   `list_files`, then `_ds_manifest.json`, `output/result.md`, `output/build-prompt.md`.
4. **Concreteness check: passed** — see below.
5. **Landed as-is**, then SIGNOFF written.

## Read-back verification

- **Project verified by id**, not by name: `1eaa0803-46e3-426a-ab04-17a802170234`,
  `type: PROJECT_TYPE_DESIGN_SYSTEM`, `canEdit: true`.
- **`_ds_manifest.json` compiled with counts in sync** — **43 cards** total (round 01's 30 + **13 new**),
  every one carrying a group and a subtitle. Not an empty `cards[]`, and **not one monolithic HTML**. The
  round genuinely became visible in the Design System pane, which is the only thing that makes it
  co-workable.
- New cards this round, by group: **Landing** (5) — hero+install desktop and narrow, agent quickstart,
  skill section, page order; **Components** (4) — snippet, note-vs-trap-vs-error, nav, preview collapsed;
  **States** (4) — preview expanded, copy idle/copied/failed, verify readings, no-JS.
- **Both required outputs present**: `output/result.md` and `output/build-prompt.md`.

**Concreteness check — the bar is "there are no design decisions left to invent."** Passed. Every one of
the handoff's thirteen questions is answered with a decision *and* its reasoning; `build-prompt.md` carries
exact pixel values, final copy strings, a normative state table, breakpoint behaviour, an a11y floor with
measured contrast ratios, a per-file change manifest, and seven acceptance checks. Nothing was returned as
"the implementer decides."

## What was landed

| Path | Content |
|---|---|
| `docs/reference/design/rounds/02-onboarding/handoff.md` | OUT — what we asked for |
| `docs/reference/design/rounds/02-onboarding/output/result.md` | IN — decisions + departures, **verbatim, read-only** |
| `docs/reference/design/rounds/02-onboarding/output/build-prompt.md` | IN — the implementation contract, **verbatim, read-only** |
| `docs/reference/design/SIGNOFF.md` | Round 02 entry prepended (newest first) |
| `works/phases/active/P11/phase.md` | The spec summary downstream slices build from |

**The 13-card set stays in the design project and was not copied down** — the pane is its home, and a local
copy would be a mirror that goes stale the moment the next round moves. That is precisely why
`build-prompt.md` had to be self-sufficient, and it is: the build executors have no `DesignSync`, so that
file is the whole source of truth they get. It is complete enough to build from.

## The design in one line

Two new sections (`AgentQuickstart` at `#quickstart`, `SkillSection` at `#skill`) inserted at positions 4–5
between `HowItWorks` and `Showcase`, an install row appended below the hero's existing grid, one new nav
link, three new components (`Snippet`, `Trap`, `SkillPreview`), **no token delta**, **no backend change**.
Full spec in `phase.md`'s "S5 done" section and `output/build-prompt.md`.

## Notable, for the phase review

- **Token delta is `None.`** — `web/src/app/globals.css` requires no change. Round 01's caution family was
  shipped but unused; it now carries the trap treatment. The new vocabulary is composition, not tokens.
- **The operator delegated all thirteen questions** ("Decide for me"), so the decisions are Claude Design's
  under explicit delegation. Each is recorded with its reasoning in `output/result.md` §2 — none was left
  for an implementer to invent, which is what the concreteness bar requires.
- **No push happened.** The handoff flagged GitHub `main` as 45 commits behind with everything unpushed;
  the operator resolved it with a **local-directory connection** instead. `ci.yml` did not fire, and the
  round read the actual current tree.
- **Round 01's record is untouched in this repo.** The session copied round 01's outputs to
  `output/round-01/` **inside the design project** to free the canonical `output/` path — a project-side
  move, not a repo one. `rounds/01-brand-app-landing/output/` here is unchanged.
- **Apply-time nit, catalogued not corrected** (the returned record is read-only): `result.md` §6.4 notes
  the handoff's *119 lines* vs. `wc -l`'s 120 (trailing newline). `build-prompt.md` §3.4 requires both the
  line and byte figures be **computed from the served file, never hardcoded**, so the discrepancy cannot
  reach production — and that requirement is itself the fix.

## Not proven

Nothing behavioural — a design slice writes no implementation code, and none was written here. `web/` is
byte-for-byte unchanged by this slice. The design is proven only in the pane; whether it is built
faithfully is the build slices' burden, and `build-prompt.md` §11's seven acceptance checks are how that
gets tested.

## Doc impact

**None from this slice directly** — the design record lives outside `docs/current/` on purpose, and no
durable truth changed until the design is built. The build slices `P11.DECOMP2` cuts will carry the
`experience` / `frontend` doc impact once the sections exist.
