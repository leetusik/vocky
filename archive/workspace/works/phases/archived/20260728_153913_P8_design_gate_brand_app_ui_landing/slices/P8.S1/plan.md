# P8.S1 — Retire the `web/design/canvas/` mirror

`implementation` / `risk: low` / order 1. Every edit below is given as **exact text** — apply it
literally.

## Context

P8 is the Claude Design gate. Under workspace **v13**, Claude Design reads the **real repo** itself via
Connect GitHub — so Claude Code authors no cards, no canvas, and no token mirror. That retires
`web/design/canvas/`, the 13-file mirror P4.S1 left behind (**constraint 8** in `phase.md`).

**Why it goes now, before the gate.** P8.S2 pushes the branch so Claude Design can read current code. The
mirror carries its own copy of the **placeholder** palette in `tokens.css` — it would read to the design
session as authoritative while contradicting the real `web/src/app/globals.css` tokens. Deleting it first
is the whole point of the S1→S2 ordering: **delete, then publish.**

It is verified inert — nothing in `web/src/`, `next.config.*`, `tsconfig.json`, or `postcss.config.*`
imports or globs it — and git history keeps it. All 13 files are tracked; no untracked strays.

## New finding — the notebook recorded one dangling reference; there are two

`phase.md`'s *Decomposition* says S1's "one dangling code reference is `web/src/app/page.tsx:11`". That is
**incomplete**. A second exists: **`web/.prettierignore:8-9`**, a comment + rule block whose only purpose
is this tree. Both earlier sweeps missed it — it says `design/`, not `design/canvas`, and
`.prettierignore` is not matched by a `--include="*.ts,*.tsx,*.css,*.json"` grep. Delete the tree without
it and a dead ignore rule points at nothing.

## The three edits

### 1. Delete the tree

```bash
git rm -r web/design
```

`canvas/` is the **only** thing under `web/design/`, so the parent goes too — no empty directory is left
behind. This stages the deletion; **the orchestrator commits, not you.**

### 2. `web/src/app/page.tsx` — the header comment

Replace exactly:

```
// P4.S2 — root redirect. `/` is a pure router for now: a signed-in visitor goes to
// the dashboard, everyone else to login. (P6 replaces this with the public landing
// page, at which point this bounce moves behind the landing's CTA.)
//
// This replaces S1's design-system preview, which was that slice's smoke test and
// has served its purpose — the primitives are now exercised by the real auth and
// shell surfaces. The `design/canvas/` mirror remains the design-gate artifact.
```

with exactly:

```
// P4.S2 — root redirect. `/` is a pure router for now: a signed-in visitor goes to
// the dashboard, everyone else to login. (P9 replaces this with the public landing
// page, at which point this bounce moves behind the landing's CTA.)
//
// This replaces S1's design-system preview, which was that slice's smoke test and
// has served its purpose — the primitives are now exercised by the real auth and
// shell surfaces.
```

Two changes: the canvas sentence goes (mandatory — it names a tree that no longer exists), and **P6 → P9**
because P8+P9 absorb the landing build, leaving P6 deploy-only (`intent.md`). This touches only the code
comment — P6's own phase folder stays untouched per constraint 7.

**Leave the rest of the comment alone.** In particular *"this bounce moves behind the landing's CTA"* is a
pre-existing P4.S2 claim, and whether a signed-in visitor at `/` sees the landing or gets bounced is an
**open gate question** in `phase.md`. Rewriting it would be answering a design question — forbidden.
P9 owns that comment when it builds the landing.

### 3. `web/.prettierignore` — drop the dead ignore block

Replace exactly:

```
node_modules/

# Design canvas artifacts — standalone HTML specimens, not in Prettier's domain
design/
```

with exactly:

```
node_modules/
```

(Removes the trailing blank line, the comment, and the rule — the file then ends at `node_modules/`.)

## Verification

From `/Users/sugang/projects/personal/vocky/web` (`pnpm` 10.28.2, `node_modules` present):

```bash
pnpm typecheck      # page.tsx still compiles
pnpm lint
pnpm format:check   # the .prettierignore edit is coherent with the tree gone
```

From the repo root:

```bash
python3 scripts/workflow.py validate
test ! -e web/design && echo "tree gone"
grep -rn "design/canvas" web/ ; echo "^ expect: no matches"
```

## Record in `phase.md`

Append to ***Findings & Notes*** the two-dangling-references correction (`web/.prettierignore:8-9`
alongside `page.tsx:11`), and **why both sweeps missed it** — it reads `design/`, not `design/canvas`, and
lives in a file no source-extension grep matches. That is the durable, transferable part.

Then write `result.md` (free-form, from scratch — no template).

## Out of scope

- **Docs.** `frontend.md` and `decisions.md` describe the canvas; they are already pre-recorded in
  *Doc impact* for `P8.REVIEW` to consolidate (constraint 10). **No `doc-new-version` here.**
- **`CLAUDE.md` / `AGENTS.md`** mention "canvas mirror" in the design-cowork *rule text*. That is the
  workspace contract, not a reference to this tree. **Do not touch.**
- No design decisions, no handoff, no landing work.
- **No commits and no status transitions** — the orchestrator owns both.
