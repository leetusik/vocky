---
name: parallel-phase
description: Run a phase in parallel on its own branch and worktree, and integrate it back: PR, quiet-point gate, merge, deferred doc consolidation, teardown.
allowed-tools: Bash(python3 scripts/workflow.py:*), Read, Edit, Write, Glob, Grep, Bash
disable-model-invocation: true
---

# parallel-phase

Parallel mode runs **one phase** on its own git branch in its own git worktree, driven by its own
session, while the default stream keeps working on `main`. It is **opt-in per phase and never a
default**: a workspace that never opts in behaves exactly as before.

The unit of parallelism is the **phase**. Slices inside a phase stay strictly sequential — they build
on each other through `phase.md` and a commit at every boundary — so never fan out slices.

Everything below is the whole lifecycle, in order: suggest → opt in → work → review on the branch →
integrate back. The contract (`CLAUDE.md` / `AGENTS.md`) carries only the rules; the detail lives here.

## 1. When — suggestion only

The engine hints; it never acts. Relay a hint to the operator, and stop there unless they opt in:

- `python3 scripts/workflow.py new-phase ...` prints a hint when another phase is already
  `in_progress` — the new phase can run on its own branch instead of queueing behind it.
- `python3 scripts/workflow.py next` prints a hint when a `planned` phase is waiting behind the
  `in_progress` one.

Both hints name `python3 scripts/workflow.py parallel-start <P>`. They are advisory: queueing the
phase normally is always a valid answer, and parallel mode is worth its overhead only when the two
phases genuinely touch different ground.

## 2. Opt in — `parallel-start`

```sh
python3 scripts/workflow.py parallel-start <P> [--worktree <path>] [--slug <slug>]
```

Run it **between `new-phase` and any `start-slice`** — from the default stream, with a clean tree.
It refuses unless the phase is `planned`, has no `execution` block yet, the checkout is on the
default stream inside a git work tree, the tree is clean, the branch name is free, and the worktree
path is free with an existing parent. Every guard runs before any mutation, so a refusal leaves no
partial state.

What it does:

- stamps `phase.json` with `execution: {mode: "parallel", branch, worktree, consolidation: "pending"}`;
- makes **one** fixed-message engine commit — `chore(works): opt <P> into parallel execution`, no
  trailers — containing nothing but that stamp plus the regenerated `works/` files. This is the single
  deliberate exception to "the engine never commits": the stamp must exist on **both** branches, so
  the phase branch has to be cut from a commit that already contains it;
- cuts `phase/P<N>-<slug>` (slug = the slugified phase name unless `--slug` overrides) and adds a
  sibling worktree at `../<repo>-<P>` unless `--worktree` overrides.

Then **open a second session in that worktree** and drive the phase from there (`/do-whole-phase`,
`/do-next-slice`). A teammate can instead clone the repo and check the branch out — from that point
on the two are identical, because stream membership is read from the current git branch versus the
stamped `execution.branch`, never from a marker file.

## 3. Work — in the worktree, as normal

Nothing about slice work changes. Inside the worktree, run the usual skills; from anywhere, use
`python3 scripts/workflow.py parallel-status` to see every stream at once (it is the one command that
writes nothing — safe to run from a parallel worktree).

What *is* stream-scoped:

- **Selection.** `next` and `works/state.json` cover only the current checkout's stream: the default
  stream skips phases opted out to a branch; a phase-branch checkout sees only its own phase. On a
  parallel stream `next` prints a `stream=` line; on the default stream it prints
  `parallel_phases_elsewhere=<P>:<branch>` when opted-in phases exist elsewhere.
- **`pending`.** A `pending` slice or phase halts only its own stream — `WAITING ON OPERATOR` on one
  branch no longer freezes the other.
- **Dashboards** still list *every* active phase (`works/backlog.md` marks the row
  `· parallel: <branch>`), but main's backlog cannot show the branch's slice progress until the
  merge — that is what `parallel-status` is for.

Commits land on the phase branch; do not merge or rebase against `main` mid-phase unless the operator
asks. Generated files (`works/state.json`, `works/index.json`, `works/backlog.md`,
`works/deferred.md`, `docs/current/*.md`) are **regenerated, not merged** — never hand-fix them.

## 4. Review on the branch — with consolidation deferred

Run the phase review exactly as `review-phase` describes, with **one** difference: a parallel phase's
passing review **stops before doc consolidation**. Doc versions are allocated from a single
`docs/index.json` counter, so two branches consolidating at once collide; consolidation is therefore
deferred to the serialized post-merge step on the default stream.

So on a parallel branch the review executor:

- validates every slice together and judges the phase as usual;
- **verifies** that the running "Doc impact" list in `phase.md` covers every durable-truth change the
  phase made (that list is the input the post-merge step consolidates from — an incomplete list is a
  review finding, not a detail);
- runs **no** `doc-new-version` and no `rebuild-docs`, and reports
  `doc_versions: none — deferred to post-merge consolidation (parallel mode)`;
- the "does `docs/current` match `docs/index.json`" check applies at consolidation time on the
  default stream, not here.

Record the verdict normally, from the worktree:

```sh
python3 scripts/workflow.py review-phase <P> --verdict pass --reviewer slice-executor-high --note "..."
```

A `changes_requested` or `blocked` verdict behaves as always — fix slices on the branch, then
re-review. Only a `pass` opens the integration below.

## 5. Integrate — agent-run, after the review passes

The orchestrator runs this sequence itself; it is not a set of manual operator clicks. **If anything
closes the gate or turns a check red mid-sequence, STOP and report — never merge past a closed gate.**

1. **Gate.** From the worktree (or anywhere):
   ```sh
   python3 scripts/workflow.py parallel-gate <P>
   ```
   `GATE OPEN` (exit 0) → continue. `GATE CLOSED` (exit 1) prints numbered reasons: the branch's phase
   is not `done` with a `pass` review, or the default stream is busy (any default-stream phase
   `in_progress` / `in_review` / `pending` / `blocked`). A busy main means wait, not merge.
   `--branch-ref` / `--main-ref` override where each side is read from (CI uses
   `--branch-ref HEAD --main-ref origin/<base>`).
2. **Push the branch.** `git push -u origin phase/P<N>-<slug>`. The interactive permission prompt
   **is** the operator's approval — nothing is pre-allowed. Existing adopters must first delete the
   old blanket `Bash(git push:*)` deny from `.claude/settings.json` by hand (settings merges are
   additive, so an update cannot remove it); keep `Bash(git push --force:*)`.
3. **Open the PR.** `gh pr create --base main --head phase/P<N>-<slug> --title "..." --body "..."`.
   The **phase is the reviewable unit** — one PR per phase, body drawn from `phase.md` (objective,
   slice breakdown, notable decisions). PR approval maps to the passing review verdict that already
   exists; do not re-litigate the review in the PR.
4. **Wait for CI.** `gh pr checks --watch`. The `validate` job runs everywhere; the `parallel-gate`
   job re-runs the quiet point server-side on `phase/*` PRs. Red → stop and report.
5. **Merge with a merge commit.** `gh pr merge --merge` — the slice-by-slice history is worth keeping,
   so no squash and no rebase.
6. **Finish the merge on the default stream.** Switch to the default checkout, `git pull`, then:
   ```sh
   python3 scripts/workflow.py parallel-merge-finish
   ```
   It refuses mid-merge (`MERGE_HEAD` present), regenerates every generated file from the merged
   folders, and lists the phases still owing doc consolidation with the exact commands. A merge
   conflict in a generated file is resolved by taking **either** side and re-running it. It makes no
   commit.
7. **Consolidate the docs — serialized, on the default stream, one phase at a time.** Read the merged
   `works/phases/active/<P>/phase.md` `## Doc Impact` section and, per named doc:
   ```sh
   python3 scripts/workflow.py doc-new-version --doc <doc> --summary "..." --source <P>.REVIEW
   # edit only the returned edit_path
   python3 scripts/workflow.py rebuild-docs
   ```
   One version per doc, capturing the whole phase. Never two phases in parallel here.
8. **Mark it consolidated.** `python3 scripts/workflow.py parallel-consolidated <P>` — flips
   `execution.consolidation` to `"done"`, which is also what unblocks archiving.
9. **Tear down.** `python3 scripts/workflow.py parallel-teardown <P>` — removes the worktree and the
   merged branch (it refuses if the branch is unmerged, or if run from the branch itself) and nulls
   `execution.worktree`. It makes no commit.
10. **Commit** the regenerated files, the new doc versions, and the `phase.json` changes on the
    default stream, following the Commit Convention.

Afterwards the phase is `done` and archivable the normal way (`archive-phase <P>`, `rotate-backlog`,
`archive-all`) — archiving is still manual and still blocked while `execution.consolidation` is
`"pending"`.

## Guardrails

- Never merge a parallel phase whose `parallel-gate` is closed, and never merge two phases into the
  same quiet point at once.
- Never run `parallel-consolidated` or `parallel-merge-finish` from a parallel worktree — they belong
  on the default stream, after the merge.
- Never hand-resolve a generated file's merge conflict by editing it; take either side and regenerate.
- Slice-level parallelism inside a phase stays out of scope.
- Outside this documented flow the ordinary rules stand: no branching unasked, no pushing unasked.
