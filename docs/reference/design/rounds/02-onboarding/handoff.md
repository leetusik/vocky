# Design handoff — Round 02: onboarding on the landing page

**To:** Claude Design, with the operator (sugang)
**From:** Claude Code (vocky repo)
**Round:** 02 · **Phase:** P11 · **Slice:** P11.S5
**Repo:** `github.com/leetusik/vocky` (public) — connect via **Connect GitHub**, branch `main`
**Design project:** `1eaa0803-46e3-426a-ab04-17a802170234` (`vocky design system`) — the round-01 project;
target it **by id**, not by name.

> **Repo currency — read this before connecting.** GitHub `main` is currently **45 commits behind** the
> local tree (remote head `3e1e85a`, pushed 2026-07-17). Everything this round is about — the corrected
> hero, `vocky capture`, `web/public/install.sh`, `skills/vocky-feedback/SKILL.md` — is **unpushed**. A
> GitHub connection would read a repo where none of it exists. The operator resolves this at the gate:
> either push `main`, or use a **local-directory connection** instead. Do not design against the stale
> remote.

---

## 0. What this is, and who decides

This document says **what to design**. It decides **nothing**.

Every visual decision in this round — layout, hierarchy, density, where these sections sit in the page,
what a "known trap" looks like, how much of a file a preview pane shows — is yours to make with the
operator. Claude Code has proposed no layout and no copy, and has answered none of the questions in §6.
**They are posed, not answered.** Where this document describes something, it is describing **what exists
in the repo today**.

**Round 01 already gave vocky its brand**, and it is applied in code (P9). This round is not a rebrand. It
adds **onboarding** to a landing page that currently explains what vocky is but never tells anyone how to
start using it.

**What changed in the repo this phase, before this round** — all four are shipped and readable:

1. The hero's request payload was **factually wrong** and is now correct (it showed a `vk_live_` key tier
   that does not exist, and a flat `source_product` where the API requires a nested `source.product`).
2. `vocky capture` now exists as a CLI command, authenticating with a `vk_` key from `VOCKY_API_TOKEN`.
3. `web/public/install.sh` exists — a `curl | bash` installer, served at `/install.sh`.
4. `skills/vocky-feedback/SKILL.md` exists — an end-user agent skill, published byte-identically at
   `/SKILL.md` and held there by a CI parity gate.

**None of them is visible on the landing page.** That is the gap this round designs.

---

## 1. Product context

vocky is a feedback layer for products. A backend — or a coding agent — sends explicit user reactions
(likes, dislikes, comments) over a single REST call, and vocky turns them into structured, searchable
signal across projects.

**Who this round is for:** a developer or a coding agent who has just landed on `vocky.hi2vi.com` and has
to get from "reading a page" to "capturing feedback". Today the page gives them a `Start free` button and
nothing else — no install, no credential setup, no agent path.

**The thing that makes vocky's onboarding unusual, and worth designing well:** the whole agent contract is
**two environment variables**. Not a plugin, not an SDK, not a config file — two exports give every coding
agent on the machine equal access:

```
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."
```

---

## 2. Scope checklist — every item this round must cover

Three surfaces plus their consequences. **The design is free to add to this list and to cut from it** —
that is why the build slices have not been cut yet.

### 2.1 A hero install row

The landing page does not mention the CLI at all. The install command is:

```
curl -fsSL https://vocky.hi2vi.com/install.sh | bash
```

It needs to be **copyable**. Where it sits, whether it displaces or joins the existing CTAs, and what it
does to the hero's balance are design questions (§6.1).

### 2.2 An agent quickstart — the two-variable contract

The recommended path for a coding agent. It has to carry four things, all of them real and all of them
load-bearing:

- **The two exports** (above).
- **Where they go: `~/.zshenv`, never a repo `.env`.** Two reasons, both real: a repo `.env` is **never
  auto-loaded** by Claude Code or Codex, so a resolver would never see it; and a secret in a repo file
  risks an accidental commit. `~/.zshenv` is sourced by every zsh invocation, so every Bash call, every
  Codex `exec`, and every repo inherits it, and the key stays out of all repos.
- **A Codex-only trap:** the `workspace-write` sandbox **denies outbound network by default**, so the
  capture POST fails silently. The fix is `[sandbox_workspace_write] network_access = true` in
  `~/.codex/config.toml`. Claude Code needs nothing.
- **A verify step** the reader runs before capturing anything, with a **success** and a **failure**
  reading (a valid key vs. a wrong or revoked one).

How a trap or a caveat is expressed visually is net-new vocabulary for this design system (§6.4).

### 2.3 The skill, on the page

`skills/vocky-feedback/SKILL.md` is served verbatim at `/SKILL.md`. The section needs to let a visitor:

- **read** enough of it to judge it without leaving the page,
- **copy** it, and
- **download** it.

The real file, as it exists today — ground the preview in this, never in lorem:

- **119 lines, 7,975 bytes.**
- YAML frontmatter: `name`, `description` (one long line carrying a hard negative trigger),
  `allowed-tools`.
- Then `# vocky-feedback`, a one-paragraph lede, and eight `##` sections:
  1. `Set up the two-variable contract`
  2. `Verify before you capture anything`
  3. `Path A — capture with the CLI (primary, one command)`
  4. `Path B — raw REST (no vocky install required)`
  5. `Path C — /mcp (alternative transport, not detailed here)`
  6. `Error handling — branch by branch`
  7. `Report back`
- The body is dense: fenced `bash` and `json` blocks, and one table.

**A hard constraint on the preview, from the CI gate:** whatever renders on the page must derive from the
**served** `/SKILL.md`, never a pasted copy. A byte-parity gate holds `web/public/SKILL.md` to a
byte-for-byte match with the canonical, and a hand-copied excerpt in a component would fork from it
silently. This constrains **implementation**, not your design — but it means "show the first N lines" must
mean "read the served file and show the first N lines".

### 2.4 Consequences

New sections need anchor ids and possibly nav entries (§3.3). Whether the nav grows is a design question.

---

## 3. Where to look — real paths, real content

### 3.1 The landing page as it stands

`web/src/app/page.tsx:32-46` composes it in this order:

| # | Component | File (`web/src/components/landing/`) | Section tone |
|---|---|---|---|
| — | `LandingNav` | `landing-nav.tsx` | sticky, not a `Section` |
| 1 | `Hero` | `hero.tsx` | `default`, above the fold, no reveal |
| 2 | `TrustStrip` | `trust-strip.tsx` | `surfaceSoft` |
| 3 | `HowItWorks` | `how-it-works.tsx` | `surface`, `id="how"` |
| 4 | `Showcase` | `showcase.tsx` | `default` |
| 5 | `Features` | `features.tsx` | `surface`, `id="features"` |
| 6 | `Pricing` | `pricing.tsx` | `default`, `id="pricing"` |
| 7 | `ClosingCTA` | `closing-cta.tsx` | `forest` |
| — | `LandingFooter` | `landing-footer.tsx` | `forest` |

**The hero today** (`hero.tsx`): a two-column layout. Left is eyebrow pill → `h1` → sub-paragraph → two
CTAs (`Start free`, `Read the docs`). Right is an `EndpointCard` showing a real `POST /api/feedback`
request, with a "captured record" `Card` layered under it.

### 3.2 Copy is data — a house rule

Components hold **no literal copy**. Every string lives in `web/src/content/`, and the landing's is
`web/src/content/landing.ts` (267 lines, one `LANDING` const). Round 01 established this; it still holds.

### 3.3 Anchors are typed

`web/src/content/section-ids.ts` is the single source of truth — currently exactly three ids: `features`,
`how`, `pricing`. `Section`'s `id` prop is typed `SectionId`, so **an anchor that is not in that map
cannot be written**. New sections mean new entries.

### 3.4 Primitives that already exist

Reuse rather than rebuild, where the design allows:

- `web/src/components/ui/endpoint-card.tsx` — a `<pre>` inside a forest panel. Real selectable text, no
  copy button, no syntax highlighting, no client JS. This is the closest thing to a snippet block today.
- `web/src/components/show-once-key.tsx` — the app's **only** clipboard implementation
  (`navigator.clipboard.writeText` with an explicit copy-failed fallback). Not reusable as-is (it renders
  an alert box with a Dismiss button), but the copy mechanics are proven and live here.
- `web/src/components/ui/section.tsx` — `tone` is an enumerated CVA set; `reveal` is opt-in.
- `web/src/components/ui/reveal.tsx` — the one existing client island on the landing.

**There is no copy button, no snippet component, and nothing that fetches a static file, anywhere on the
landing today.**

### 3.5 The artifacts being published

- `web/public/install.sh` — 61 lines, served at `/install.sh`.
- `skills/vocky-feedback/SKILL.md` → `web/public/SKILL.md`, served at `/SKILL.md`.
- `scripts/skill_parity.py` — the CI gate holding the two byte-identical.

### 3.6 Tokens and the applied system

`web/src/app/globals.css` (`@theme` block). The applied system is documented at
`docs/current/frontend.md:84-87` and the landing specifically at `:229-231`. Round 01's record is in
`docs/reference/design/rounds/01-brand-app-landing/output/build-prompt.md`.

---

## 4. Locked vs. in play

### In play — move these freely

- **Layout, hierarchy, density, spacing, motion, and expression** of all three new surfaces.
- **Where the new sections sit** in the page order, and whether they are two sections or one.
- **New component vocabulary** — a snippet block, a copy affordance, a preview pane, a caveat/trap
  treatment. None of these exists yet; inventing them is this round's job.
- **The hero's internal balance**, to the extent the install row demands it.
- **Copy for the three new surfaces only** — they have none, and Claude Code may not invent it. Same
  exception round 01 made, scoped to what is net-new here. **Existing landing copy is locked** (§below).

### Locked

- **The brand.** Round 01's palette, type, radius, and token *names* are applied and shipped. This round
  is not a rebrand. If it needs a token, say so explicitly as a delta.
- **Existing landing copy** in `web/src/content/landing.ts` — the hero headline, sub, CTAs, and every
  shipped section's strings stay. The hero's request payload in particular was just corrected for factual
  accuracy and **must not be edited back** into a friendlier-looking but wrong shape.
- **System structure** — routes, the BFF boundary, `output: "standalone"`, the copy-as-data rule, the
  typed `SectionId` map.
- **Backend and data contracts.** This round needs **no** backend change; `POST /api/feedback` is not
  being redesigned.

### Locked floors — non-negotiable

- **The two variable names are `VOCKY_BASE_URL` and `VOCKY_API_TOKEN`.** They are real, shipped, and
  quoted in a published skill. A prettier name is a broken instruction.
- **The install command is exactly** `curl -fsSL https://vocky.hi2vi.com/install.sh | bash`. It must be
  copyable **verbatim** — a display form that reflows or truncates must not be what the clipboard gets.
- **`vk_` keys have no `live`/`test` tier.** Any depicted key is `vk_` + an opaque token. This exact
  falsehood was on the page until this phase and must not return.
- **The nested `source.product`** shape in any depicted capture payload. A flat `source_product` is a
  `400`.
- **The preview must derive from the served `/SKILL.md`**, not a pasted excerpt (§2.3).
- **The a11y and reduced-motion floor** from round 01, including `h1–h6 { word-break: keep-all }` for
  Korean, and Korean-capable `--font-sans`.
- **No-JS behaviour must be stated.** If a preview pane collapses or a copy button is a client island,
  say what a visitor without JS sees — the Download link is a plain anchor and must keep working.

---

## 5. Required outputs — strict

A round is incomplete without all three.

### 5.1 The card set — this is what makes the design reviewable

The Design System pane builds its index from a **first-line marker in each preview HTML**, compiled into
`_ds_manifest.json`. **No marker → no card → an empty pane**, however good the design is.

- **One card per reviewable unit** — per component, per surface, per state. **Never one monolithic
  "onboarding" page**: the operator fixes one card at a time, and a monolith cannot be reviewed or
  superseded piecemeal.
- **Line 1 of every card file, exactly this shape:**
  ```html
  <!-- @dsCard group="Landing" name="Agent quickstart" subtitle="Two-var contract · zshenv · Codex trap" viewport="1280x900" -->
  ```
- **Groups** to organize the pane: `Landing` for the surfaces, `Components` for the new primitives,
  `States` for the interaction and failure states. Add groups if the design needs them — grouping is
  organization, not a design decision.
- **Ask the pane to compile foundations from a `tokens.css`** the cards link, carrying round 01's real
  values. If this round changes no token, say **"None."** rather than omitting the statement.
- **The definition of done is "the cards appear in the pane,"** not "the files exist."

Cards this round plausibly needs — **a starting list, not a specification**; add, split, and drop as the
design requires:

- the hero **with** the install row, at desktop and at narrow width;
- the install row / snippet primitive on its own;
- the agent quickstart surface;
- the trap/caveat treatment;
- the verify snippet with its success and failure readings;
- the skill section;
- the skill preview pane, collapsed **and** expanded;
- the copy affordance in its idle / copied / failed states;
- the nav, if it changes.

### 5.2 `output/result.md`

What was designed, and **every departure from this handoff logged**.

### 5.3 `output/build-prompt.md`

The implementation contract. **The implement slices size their work from it, and the executors that build
it have no access to the design project** — the cards stay in the pane and are not copied down. So
`build-prompt.md` must be complete enough to build from on its own: exact values, exact copy strings,
states, breakpoints, and the no-JS behaviour.

---

## 6. Open questions — posed, never answered

Claude Code has not answered any of these and will not. **Ask the operator.**

**6.1 The hero.** The left column already carries eyebrow → headline → sub → two CTAs, and the right
carries two layered panels. Where does an install command go without making the hero a wall? Does it join
the CTAs, replace one, sit below them, or span both columns? Is the `curl | bash` line the hero's primary
call to action now, or does `Start free` stay primary?

**6.2 Page order and section count.** Are the agent quickstart and the skill **two sections or one**? Where
do they sit relative to `How it works`, `Showcase`, `Features`, `Pricing`? Does an onboarding block belong
high (right after the hero, as the natural next step) or low (after the value case is made)?

**6.3 The nav.** Three anchors today. Do the new sections get nav entries, and if so at what cost to a nav
that is currently short?

**6.4 Caveats and traps.** The `~/.zshenv` reasoning and the Codex `network_access` trap are *warnings* —
a category the design system has no vocabulary for. What weight does a trap get? Is it an inline note, a
distinct block, an aside? How does it avoid reading as an error state?

**6.5 The preview pane.** How much of a 119-line file does a visitor see before expanding? Is it
collapsed-by-default with a fade, a fixed-height scroller, or something else? Does the frontmatter get
distinct treatment from the body? Is there any syntax colouring at all, given the repo ships no
highlighting library and the file is markdown containing bash and json fences?

**6.6 Copy affordances.** There are up to four copyable things: the install line, the two exports, the
verify command, and the whole skill. Are they one repeated primitive or several? What does "copied"
feedback look like, and what does a **copy failure** look like (it happens — non-secure contexts and
permission denials are real)?

**6.7 Download.** The skill is downloadable as a plain anchor. Is Download equal to Copy in weight, or
secondary?

**6.8 Two audiences, one page.** The existing landing speaks to a **backend** integrator ("your backend
sends a REST call"). This round adds a path for a **coding agent**. Are those the same visitor? Does the
page need to signal which path is which, or does that fragment the story?

**6.9 Prerequisites.** The installer bootstraps `uv` if it is missing and needs no sudo. Is any of that
worth surfacing, or is a bare command line the honest, confident presentation?

---

## 7. Operator attachments — asked, not answered

- Is there any **reference** — a product whose install/quickstart presentation the operator likes — that
  should inform this round? If so, upload it, clearly as reference.
- The operator may want to **read `skills/vocky-feedback/SKILL.md` in full** before deciding how much of
  it the page should show. It is 119 lines.
- **Repo currency** (see the note at the top): push `main`, or connect a local directory.

---

## 8. Definition of done

- The **cards appear in the Design System pane**, grouped, one per reviewable unit — not a monolith.
- `output/result.md` and `output/build-prompt.md` are both present, and `build-prompt.md` is complete
  enough to build from without access to the pane.
- Every question in §6 that the design depended on has been **answered by the operator**, not by an agent,
  and the answer is recorded in `result.md`.
- The token delta is stated explicitly — **"None."** if nothing changed.
- Every locked floor in §4 survives.

---

## 9. Notes on process

- **Claude Code writes no mockups, no palettes, no cards, and no copy for these sections.** Requiring the
  card set is not drawing one.
- The returned record lands in `docs/reference/design/rounds/02-onboarding/output/` **read-only and
  verbatim**. Nits found later are catalogued as apply-time to-dos, never edits to the record.
- **Implementation is a separate slice**, cut after this gate closes — deliberately not planned yet,
  because the design decides what gets built.
- The site is **not deployed yet** (production bring-up is the next phase), so nothing here can be reviewed
  against a live URL. `/install.sh` and `/SKILL.md` return 404 today and go live with the page itself.
