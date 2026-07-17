# P8.S1 — Result

Executed the plan literally: three exact edits, no improvisation, no design decisions.

## What was done

1. **`git rm -r web/design`** — staged deletion of all 13 tracked files under
   `web/design/canvas/` (`README.md`, `_ds_manifest.json`, `tokens.css`, 6 component/
   foundation cards, 1 section card). Confirmed via `git ls-files web/design` before
   deleting that exactly these 13 files were tracked, matching the plan's count. No
   untracked strays. **Staged, not committed** — the orchestrator commits.

2. **`web/src/app/page.tsx`** — replaced the header comment block exactly as specified:
   removed the sentence naming `design/canvas/` as the design-gate artifact (it no
   longer exists), and corrected `P6` → `P9` in "P9 replaces this with the public
   landing page" (P8+P9 absorb the landing per `intent.md`; P6 goes deploy-only). Left
   the rest of the comment untouched, including the "this bounce moves behind the
   landing's CTA" clause — that is an open gate question (`phase.md` → *Open Questions*),
   not this slice's to answer.

3. **`web/.prettierignore`** — removed the dead `design/` ignore block (the trailing
   blank line, the comment, and the rule). The file now ends at `node_modules/` (9 lines
   → 6 lines, confirmed via `wc -l` and `od -c` before/after).

All three edits matched the plan's exact old/new text byte-for-byte; no deviation was
needed.

## Verification

From `web/` (pnpm 10.28.2, `node_modules` present):

- `pnpm typecheck` — **pass** (silent, exit 0; `page.tsx` still compiles).
- `pnpm lint` — **pass** (silent, exit 0).
- `pnpm format:check` — **fails** (exit 1), but on 20 **pre-existing** files unrelated
  to this slice (`web/README.md`, `web/src/lib/env.ts`, `web/src/lib/session.ts`,
  several `web/tests/*.test.ts`, etc.). Confirmed via `git diff --stat HEAD` / `git
  status --short` on a sample of those files that none were touched by this slice.
  Neither `page.tsx` nor `.prettierignore` — the two files this slice edited — appear
  in the warning list, which confirms the plan's specific intent for this check ("the
  `.prettierignore` edit is coherent with the tree gone") holds: nothing under the now
  -deleted `design/` surfaced, and this slice's own edits are Prettier-clean. The
  pre-existing repo-wide formatting debt is out of this slice's scope and was left
  untouched.

From the repo root:

- `python3 scripts/workflow.py validate` — **pass** ("Workflow validation passed.").
- `test ! -e web/design && echo "tree gone"` — **pass** (printed `tree gone`).
- `grep -rn "design/canvas" web/` — **pass** (zero matches, as expected).
- Additional check (not in the plan, done for extra confidence): `grep -rln "web/design"
  web/` and a scan of `web/next.config.*` / `web/tsconfig.json` for `design/` — zero
  matches anywhere.

## Deviations from `plan.md`

None. All three edits applied verbatim; all verification commands run as specified.
(One incidental hiccup: a `git stash push` I ran mid-task to sanity-check the
`format:check` pre-existing-vs-caused-by-this-slice question hit a locale-related
pathspec error on the deleted `web/design` path but still created a stash entry
duplicating the working-tree changes without actually resetting the tree. Working tree
was verified intact via `git diff --cached --stat` / `git diff --stat web/` immediately
after, and the redundant stash entry was dropped with `git stash drop`. No slice files
were lost or altered by this; noted here only for transparency, not because it affected
the outcome.)

## Doc impact

None recorded by this slice — `frontend.md` and `decisions.md`'s canvas references were
already pre-recorded in `phase.md`'s *Doc impact* list at the phase's re-creation, for
`P8.REVIEW` to consolidate (constraint 10). This slice ran no `doc-new-version`.

## `phase.md` update

Appended a new subsection under *Findings & Notes* — "`P8.S1` — two dangling references
to `web/design/canvas/`, not one" — recording the `web/.prettierignore:8-9` finding
alongside `page.tsx:11`, why both earlier sweeps missed it (string mismatch +
extension-filtered grep), and the transferable lesson (also grep ignore/dotfiles by bare
directory name). Also noted the pre-existing, out-of-scope `format:check` failures there
for `P8.REVIEW`'s awareness.

## State left behind

- Staged: deletion of 13 files under `web/design/canvas/`.
- Unstaged (working tree): `web/src/app/page.tsx`, `web/.prettierignore`.
- `works/phases/active/P8/phase.md` — appended findings (unstaged in the working tree,
  same as the code edits).
- No commits made. No slice/phase status transitioned. No `doc-new-version` run.
