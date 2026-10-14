---
name: parallel-phase
description: "Run a phase in its own git worktree when the operator asks for one, and integrate it back: quiet-point gate, local merge, the review's two gate sections, teardown; push → PR is the remote variant."
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit, Write, Glob, Grep, Bash
disable-model-invocation: true
---

# parallel-phase

A phase can run on its own git branch in its own git worktree, driven from the same session that
started it, while the default stream keeps `main` free for another phase. **Since v43 this is opt-in:
a phase runs on the current checkout unless the operator asks for a worktree.** Nothing else moves it
— not the engine, not `create-phase`, not the do-* skills on their own initiative. Asking looks like
one of three things:

- the **`worktree` mode word** on `/do-next-slice` or `/do-whole-phase` (or the same thing in their
  own words: "in a worktree", "in parallel", "on its own branch"), on a phase that is still `planned`;
- **`parallel-start <P>` run by the operator's own hand**, after which execution enters the stamped
  worktree without asking again;
- an explicit instruction to run two phases at once, which is the case the whole mechanism exists for.

v42 briefly made the worktree the default and v43 put it back, because one phase at a time is the
normal shape of this workspace and a branch per phase made every ordinary run pay for parallelism it
never used. What v42 built stays — the dirty-tree stamp commit, the in-repo worktree home (`.claude/worktrees/`), the local
merge, the gate-section notes — it is simply reached on request now.

The unit of parallelism is the **phase**. Slices inside a phase stay strictly sequential — they build
on each other through `phase.md` and a commit at every boundary — so never fan out slices.

Everything below is the whole lifecycle, in order: the operator asks → enter → work → review on the
branch → integrate back (a local merge by default). The contract (`CLAUDE.md`) carries only the rules;
the detail lives here.

## 1. The opt-in — only when the operator asks

**Worktree rules:**

1. **When — only when asked** — a `planned` phase moves into its own worktree on the operator's
   word and nothing else (the three forms above). `do-next-slice` / `do-whole-phase` run
   `parallel-start <P>` when they are told to and never on their own initiative; `create-phase`
   never does. A phase already carrying the stamp is entered without asking again.
2. **Where** — `<repo>/.claude/worktrees/P<N>-<slug>` on branch `phase/P<N>-<slug>` (`--worktree`
   overrides); the engine puts `.claude/worktrees/` in `.git/info/exclude` (common dir), never in
   `.gitignore`. **Nested install:** a pair — the host worktree `<host>/.claude/worktrees/P<N>-<slug>`
   on the operator-confirmed host branch, with the nested worktree at its `workflow/` on
   `phase/P<N>-<slug>`; the engine adds `/.claude/worktrees/` to the host's `info/exclude`.
3. **The stamp commit** — the engine's one fixed-message commit (the stamp must exist on both branches)
   contains exactly the phase folder plus the five regenerated `works/` files
   (`git add -- <paths>` + `git commit --only -- <paths>`); a phase not yet committed goes in whole.
4. **What stays behind** — a dirty or staged default checkout does not block it: everything else stays
   there, uncommitted, and the worktree starts from that commit ("start from the latest commit").
5. **What still refuses** — the phase is not `planned`; it already carries an `execution` block
   (parallel or pinned); no git repo; the checkout is on a parallel stream; a merge or rebase is in
   progress; the branch exists or is stamped on another phase; the worktree path exists; an overridden
   path's parent is missing. **Nested install**, also: no `--host-branch` (nothing is written); the
   host branch is checked out elsewhere; the host base cannot be resolved (pass `--host-base`).
6. **Enter and exit** — the orchestrator calls `EnterWorktree` with the printed path in the same
   session, re-runs `next` (`stream=phase/…`), and works there; background Agents dispatched from there
   run in the worktree. `ExitWorktree` `keep` returns to the default checkout for integration and never
   removes the worktree. Stream membership is the current git branch vs. the stamped
   `execution.branch`, never a marker file, so a plain clone of the branch works too. (Fallback if the
   session cannot switch: drive the default checkout's engine by absolute path,
   `python3 <repo>/scripts/workflow.py …`, since `ROOT` derives from the script's own location.)
   **In a nested install** `EnterWorktree` takes the printed **host** worktree path, and the engine
   runs from there as `python3 workflow/scripts/workflow.py …`. `CLAUDE.local.md` is copied into the
   host worktree; skills, agents and settings read through from the main checkout, so never create
   `<host-wt>/.claude/`.
7. **The merge** — after `parallel-gate <P>` is OPEN (branch phase `done` + review `pass`, default
   stream not busy; never past a closed gate): `ExitWorktree keep` → `git pull --ff-only` only if
   `main` tracks a remote → if anything is staged, or a file the merge touches is uncommitted (typically
   the generated `works/` files after a phase was created here since the stamp — commit that
   workflow state first), STOP and ask (git refuses both; never unstage or discard the operator's work)
   → `git merge --no-ff phase/P<N>-<slug> -m "merge(P<N>): <name>"`
   (an orchestrator commit; a conflict in a generated file = take either side + regenerate) →
   `parallel-merge-finish` → the review's tagged gate-section notes via `doc-new-version` +
   `rebuild-docs` → commit → `parallel-teardown <P>` (worktree must be clean) → commit. Push → PR →
   CI → `gh pr merge` is the **remote variant**, only when the operator asks or repo policy requires.
8. **Staying on `main` needs nothing** — it *is* the default: no flag, no stamp, no `execution`
   block. `parallel-skip <P>` and `new-phase --on-main` are **retired no-ops** (v43), kept callable
   only so v42 habits and scripts survive the upgrade: they write nothing and report where the phase
   already runs. A docs phase needs no pin either — it runs here like everything else, and since
   `doc-new-version` / `docs-consolidated` only work on the default stream, never ask for a worktree
   for one. A phase still carrying v42's `execution: {"mode": "default"}` pin keeps it, and
   `parallel-start` refuses that phase rather than override a deliberate pin: to un-pin it, delete the
   block from its `phase.json` by hand.

**The two hints — suggestions, not instructions.** The engine suggests a worktree at the two moments
one actually pays, and at no other time. Both are silent in the ordinary one-phase-at-a-time run.
**Relay a hint to the operator; never act on it.** Only their word starts a worktree:

- `python3 scripts/workflow.py new-phase ...`, when another phase is already `in_progress` on this
  stream:
  `hint: <busy> is in progress -- this phase can run in parallel on its own branch: python3 scripts/workflow.py parallel-start <P>`
- `python3 scripts/workflow.py next` on the default stream, when the current phase is `in_progress`
  and a later phase is still `planned`:
  `hint: <P> is waiting behind <current> -- it can run in parallel on its own branch: python3 scripts/workflow.py parallel-start <P>`

A phase already stamped gets no hint, and neither does a worktree checkout.

## 2. `parallel-start` — what the stamp commit contains and what still refuses

```sh
python3 scripts/workflow.py parallel-start <P> [--worktree <path>] [--slug <slug>]
```

Run it from the default stream, before the phase's first `start-slice`, and only on the operator's
word (rule 1): when `next` prints the hint, the do-* skills relay it and run nothing. It refuses when:
the phase is not `planned`; it already carries an `execution` block (parallel or pinned); the
checkout is not inside a git work tree; the checkout is on a parallel stream; a merge or rebase is in
progress; the branch name exists or is stamped on another phase; the worktree path exists; an
overridden path's parent is missing. Every guard runs before any mutation, so a refusal leaves no
partial state.

**A dirty tree does not block it.** The commit is made with `git add -- <paths>` and
`git commit --only -- <paths>`, so it contains exactly the phase folder plus `works/state.json`,
`works/index.json`, `works/backlog.md`, `works/deferred.md`, `works/events.jsonl` — whatever else is
dirty or staged stays behind in the default checkout, uncommitted, and the worktree starts from that
commit. A phase `create-phase` just made is usually not yet committed: the stamp carries the whole new
folder, on purpose.

What it does:

- stamps `phase.json` with `execution: {mode: "parallel", branch, worktree, consolidation: "pending"}`;
- makes **one** fixed-message engine commit — `chore(works): opt <P> into parallel execution`, no
  trailers — containing nothing but that stamp plus the regenerated `works/` files (rule 3). This is
  the single deliberate exception to "the engine never commits": the stamp must exist on **both**
  branches, so the phase branch has to be cut from a commit that already contains it;
- cuts `phase/P<N>-<slug>` (slug = the slugified phase name unless `--slug` overrides) and adds the
  worktree at `<repo>/.claude/worktrees/P<N>-<slug>` unless `--worktree` overrides (the engine adds
  `.claude/worktrees/` to `.git/info/exclude`, never `.gitignore`).

Then **enter it in this session**: call `EnterWorktree` with the printed `worktree=` path (it must be
under `.claude/worktrees/` — an overridden path elsewhere means a second session there instead), run
`python3 scripts/workflow.py next` (it prints `stream=phase/P<N>-<slug>`), and continue; background
Agents dispatched from there run in the worktree. A teammate can instead clone the repo and check the
branch out — from that point on the two are identical, because stream membership is read from the
current git branch versus the stamped `execution.branch`, never from a marker file.

### Starting in a nested install

The host side follows the host's own custom, so the orchestrator prepares the start, and the engine
stays policy-neutral:

1. Read the recorded custom: `python3 scripts/workflow.py nested-convention` (its scope is commits,
   branches and pull requests).
2. Propose a host branch name in that custom — never with workspace phase or slice IDs.
3. The operator confirms or changes it. The engine never invents a name.
4. The base defaults to the host's default branch (`origin/HEAD`, else the local `init.defaultBranch`,
   else `main`, then `master`, else it refuses and asks for `--host-base`). Pass `--host-base <ref>`
   to stack on another phase's branch or on `HEAD`.
5. When the custom says to branch from fresh main, run `git fetch` in the host first; the engine
   itself never fetches.
6. Run `python3 scripts/workflow.py parallel-start <P> --host-branch <name> [--host-base <ref>]`, then
   `EnterWorktree` with the printed host worktree path.

## 3. Work — in the worktree, as normal

Nothing about slice work changes. Inside the worktree, run the usual skills; from anywhere, use
`python3 scripts/workflow.py parallel-status` to see every stream at once (it is the one command that
writes nothing — safe to run from a phase worktree).

What *is* stream-scoped:

- **Selection.** `next` and `works/state.json` cover only the current checkout's stream: the default
  stream skips phases in their own worktrees; a phase-branch checkout sees only its own phase. On a
  parallel stream `next` prints a `stream=` line; on the default stream it prints
  `parallel_phases_elsewhere=<P>:<branch>` when phases are running elsewhere.
- **`pending`.** A `pending` slice or phase halts only its own stream — `WAITING ON OPERATOR` on one
  branch no longer freezes the other.
- **Dashboards** still list *every* active phase (`works/backlog.md` marks the row
  `· parallel: <branch>`), but main's backlog cannot show the branch's slice progress until the
  merge — that is what `parallel-status` is for.

`works/backlog.md`'s `## Streams` table lists the default stream and every in-flight worktree phase,
read live from its branch (with the host branch in a nested install); `parallel-status` gives the
detail.

**A worktree isolates files only.** Docker containers, ports, local databases and caches stay shared,
so coordinate them across streams.

Commits land on the phase branch; do not merge or rebase against `main` mid-phase unless the operator
asks. **Nested install:** product commits go to the host branch in the host worktree, in the host's
convention and with no workspace IDs; workflow commits run `git -C workflow …` there. Generated files (`works/state.json`, `works/index.json`, `works/backlog.md`,
`works/deferred.md`, `docs/current/*.md`) are **regenerated, not merged** — never hand-fix them.

**`phase.md` is not one of them.** The notebook is hand-written prose with one generated region
inside it, so "take either side and regenerate" does not apply to the file: a conflict *inside* its
`<!-- slices:begin -->` … `<!-- slices:end -->` block is resolved by taking either side and re-running
`python3 scripts/workflow.py rebuild`, while the rest of the notebook — Decisions, Doc impact,
Operator Questions, Notes, Now — is merged by hand like any other prose.

## 4. Review on the branch — with even the gate sections deferred

Run the phase review exactly as `review-phase` describes, with **one** difference. Every phase now
defers consolidation to a docs phase, but a default-stream review still writes two named sections
itself (`## Regression Checklist`, `## Operator Runtime`); on a branch it writes **nothing**. Doc
versions are allocated from a single `docs/index.json` counter, so two branches writing at once
collide — everything waits for the serialized post-merge step on the default stream.

So on a parallel branch the review executor:

- validates every slice together and judges the phase as usual;
- **verifies** that the running "Doc impact" list in `phase.md` covers every durable-truth change the
  phase made (that list is the input the post-merge step consolidates from — an incomplete list is a
  review finding, not a detail);
- runs **no** `doc-new-version` and no `rebuild-docs` — including the two named gate sections a
  default-stream review may write (`## Regression Checklist`, `## Operator Runtime`) — and reports
  `doc_versions: none — deferred to post-merge consolidation (parallel mode)`;
- the "does `docs/current` match `docs/index.json`" check applies at consolidation time on the
  default stream, not here.

**The two gate sections are recorded, not lost.** Where a default-stream review writes
`## Regression Checklist` (its stage-4 append) and `## Operator Runtime`, the branch review appends
them to `phase.md`'s `## Doc impact` as notes tagged `(gate section — written at merge)` — the
checklist lines verbatim in the shipped `- [ ] <surface>: <behaviour> (P<N>)` shape, the runtime
change as the exact text — and the post-merge step writes exactly those, nothing more. Every other
note waits for the operator's docs phase, as on the default stream, which records
`parallel-consolidated <P>`.

Record the verdict normally, from the worktree:

```sh
python3 scripts/workflow.py review-phase <P> --verdict pass --reviewer slice-executor-high --note "..."
```

A `changes_requested` or `blocked` verdict behaves as always — fix slices on the branch, then
re-review. Only a `pass` opens the integration below.

**The operator acceptance gate needs no parallel-mode special case:** on a phase whose gate is
`required: true`, it opens (`accept-gate <P> --open --walkthrough "..."`) and is cleared
(`accept-gate <P> --clear`) here on the branch, against the branch's running product, before the
`pass` above can be recorded — so `parallel-gate`'s "branch phase `done` + review `pass`" already
implies the operator accepted what is about to be merged.

## 5. Integrate — local merge by default, after the review passes

The orchestrator runs this sequence itself; it is not a set of manual operator clicks. **If anything
closes the gate or turns a check red mid-sequence, STOP and report — never merge past a closed gate.**

1. **Gate.** From the worktree:
   ```sh
   python3 scripts/workflow.py parallel-gate <P>
   ```
   `GATE OPEN` (exit 0) → continue. `GATE CLOSED` (exit 1) prints numbered reasons: the branch's phase
   is not `done` with a `pass` review, or the default stream is busy (any default-stream phase
   `in_progress` / `in_review` / `pending` / `blocked`). A busy main means wait, not merge. Run from
   the worktree it reads the default stream from the local default branch; `--branch-ref` /
   `--main-ref` override where each side is read from (CI uses
   `--branch-ref HEAD --main-ref origin/<base>`).
2. **Exit the worktree.** `ExitWorktree` with `action: "keep"` — the session returns to the default
   checkout and the worktree stays on disk for the teardown below.
3. **Pull, only if there is something to pull from.** `git pull --ff-only` only when
   `git rev-parse --abbrev-ref @{u}` names an upstream; a repo with no remote skips this.
4. **Merge locally.** If `git diff --cached --quiet` fails, STOP and ask the operator to commit or
   unstage — git refuses a merge on a non-clean index, and you never unstage their work. The same
   refusal fires for uncommitted changes to a file the merge touches — typically the generated
   `works/` files after a phase was created on this checkout since the stamp: that is
   workflow state, yours to commit first (`git add works && git commit`), never the operator's edit
   to discard. Then:
   ```sh
   git merge --no-ff phase/P<N>-<slug> -m "merge(P<N>): <phase name>"
   ```
   An orchestrator commit. A conflict in a generated file is resolved by taking either side, `git add`,
   and concluding the merge (step 5 regenerates it); `phase.md` prose is merged by hand.
5. **Finish the merge on the default stream.**
   ```sh
   python3 scripts/workflow.py parallel-merge-finish
   ```
   It refuses mid-merge (`MERGE_HEAD` present), regenerates every generated file from the merged
   folders, and lists the phases still owing doc consolidation with the exact commands. It makes no
   commit. `phase.md` is **not** a generated file: only its `## Slices` marker block is, so a conflict
   inside that block is fixed by re-running `rebuild`, and the rest of the notebook is merged by hand.
6. **Write the review's two gate sections — and nothing else.** For each `## Doc impact` note tagged
   `(gate section — written at merge)`:
   ```sh
   python3 scripts/workflow.py doc-new-version --doc <qa|operations> --summary "..." --source <P>.REVIEW
   # edit only that section in the returned edit_path
   python3 scripts/workflow.py rebuild-docs
   ```
   None tagged = skip this step. The rest of the `## Doc impact` list is not consolidated here.
7. **Commit** the merge follow-up: the regenerated files and any doc versions from step 6, following
   the Commit Convention.
8. **Tear down.** `python3 scripts/workflow.py parallel-teardown <P>` — removes the worktree and the
   merged branch (it refuses if the branch is unmerged, if run from the branch itself, or if the
   worktree is not clean) and nulls `execution.worktree`. It makes no commit.
9. **Commit** the `phase.json` change on the default stream.

The rest of the debt is the docs phase's (`docs-debt` → `create-phase` docs-phase route), which records
`parallel-consolidated <P>` — that flips the phase's `consolidation` to `"done"` (in both the general
field and the `execution` block), which is also what unblocks archiving. `docs-consolidated <P>` is
the twin for a phase that never left the default stream.

Afterwards the phase is `done` and archivable the normal way (`archive-phase <P>`, `rotate-backlog`,
`archive-all`) — archiving is still manual and still blocked while `consolidation` is `"pending"`.

### Integrating in a nested install

The nested repo (`workflow/`) is the workspace's own, so its integration is the local merge above,
run with `git -C workflow` from the main host checkout. The host side is the host's: the engine
never pushes, opens a PR or merges into the host's default branch.

1. `python3 scripts/workflow.py parallel-gate <P>` from the host worktree; `GATE OPEN` continues.
2. `ExitWorktree` with `action: "keep"`.
3. In the main host checkout: `git -C workflow pull --ff-only` only if it tracks a remote; the same
   staged/uncommitted STOP rule as step 4 above (in the nested repo); then
   `git -C workflow merge --no-ff phase/P<N>-<slug> -m "merge(P<N>): <phase name>"`.
4. `python3 scripts/workflow.py parallel-merge-finish`.
5. The tagged gate-section notes (`doc-new-version` + `rebuild-docs`), as in step 6.
6. `git -C workflow commit` the follow-up.
7. **The host side, by the recorded custom.** Never merge into the host's default branch, and never
   push, open or merge without the operator's word; where the custom is silent, ask.
   - **One PR per phase:** on the operator's word, push the host branch and open its PR.
   - **A ticket's phases folded into one PR:** rebase or cherry-pick each phase's host commits onto
     the ticket branch (no merge commits: a squash-merging host publishes every branch subject);
     re-run the host's pre-merge checks on the combined commit; keep each phase's host branch until
     the PR merges (its review recorded host commit ranges by sha).
8. `python3 scripts/workflow.py parallel-teardown <P>` (add `--discard-ignored` only to delete ignored
   worktree-only files the refusal listed). It checks first and refuses in one report — uncommitted
   work in either worktree, ignored worktree-only files, orphaned detached host commits — then removes
   the nested worktree, then the host worktree. The host branch is kept unless the engine created it
   and it holds no commits; a failed step prints the remaining commands, and a re-run resumes.
9. `git -C workflow commit` the `phase.json` change.

### The remote variant — push → PR → CI → `gh pr merge`

(At-root installs; a nested install's host side is step 7 above.)

Only when the operator asks or the repo's policy requires it. It replaces steps 2-4 above:

1. **Push the branch.** `git push -u origin phase/P<N>-<slug>`. The interactive permission prompt
   **is** the operator's approval — nothing is pre-allowed. Existing adopters must first delete the
   old blanket `Bash(git push:*)` deny from `.claude/settings.json` by hand (settings merges are
   additive, so an update cannot remove it); keep `Bash(git push --force:*)`. That note matters only
   here.
2. **Open the PR.** `gh pr create --base main --head phase/P<N>-<slug> --title "..." --body "..."`.
   The **phase is the reviewable unit** — one PR per phase, body drawn from `phase.md` (objective,
   slice breakdown, notable decisions). PR approval maps to the passing review verdict that already
   exists; do not re-litigate the review in the PR.
3. **Wait for CI.** `gh pr checks --watch`. The `validate` job runs everywhere; the `parallel-gate`
   job re-runs the quiet point server-side on `phase/*` PRs. Red → stop and report.
4. **Merge with a merge commit.** `gh pr merge --merge` — the slice-by-slice history is worth keeping,
   so no squash and no rebase.
5. **Back on the default checkout** (`ExitWorktree` `keep` if you are still in the worktree), `git pull`,
   then continue at step 5 above.

## Guardrails

- Never merge a parallel phase whose `parallel-gate` is closed, and never merge two phases into the
  same quiet point at once.
- Never run `parallel-consolidated` or `parallel-merge-finish` from a phase worktree — they belong
  on the default stream, after the merge.
- Never hand-resolve a generated file's merge conflict by editing it; take either side and regenerate.
- Never merge from inside the worktree — exit first.
- Never `parallel-start` a phase the operator did not ask about, nor a pinned or in-flight one.
- Never enter a path the engine did not print / `git worktree list` does not show.
- Slice-level parallelism inside a phase stays out of scope.
- The phase branch and the stamp commit are part of executing a phase; pushing is not — push only
  when asked.
- Nested install: never merge a host branch into the host's default branch, and never push, open a
  PR or merge on the host without the operator's word; the host's custom decides the shape.
