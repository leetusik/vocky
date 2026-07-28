# P11.S3 — Result

## What landed

- **`web/public/install.sh`** (new file, 61 lines) — the `curl | bash` installer. Structure exactly as
  planned: header comment (URL served from, the invocation, and the `main()`-shape safety rationale),
  `set -euo pipefail`, the two constants (`UV_BIN_DIR="$HOME/.local/bin"`,
  `INSTALL_TARGET="${VOCKY_INSTALL_TARGET:-git+https://github.com/leetusik/vocky}"`), the `say`/`die`
  one-line helpers, `main()` containing every executable statement, and `main "$@"` as the literal last
  line. Inside `main()`: a `curl` precondition check, `uv` bootstrap-if-absent (via the Astral installer,
  echoed before running), `uv tool install --reinstall "$INSTALL_TARGET"`, a PATH-tolerant
  warn-don't-die verification block, and closing lines printing the next command
  (`vocky signup --email you@example.com`) and the agent path
  (`export VOCKY_BASE_URL and VOCKY_API_TOKEN, then run \`vocky capture\``). No `#subdirectory=` fragment
  (vocky's CLI is at the repo root). No sudo, nothing system-wide.
- **`docs/cli.md`** (`Install` section, ~lines 9-19 pre-edit) — replaced the stale "PyPI publishing is
  planned (P6)" framing with the hosted `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` line
  explicitly marked "once `https://vocky.hi2vi.com` is live," followed by the checkout options as what
  works today. No PyPI promise.
- **`README.md`** (`### Install` section, ~lines 48-63 pre-edit) — same correction: the hosted installer
  line marked "once the site is live," the checkout options kept as today's path, and the old "once
  published to PyPI" sentence reworded to describe the lean-CLI / `server`-extra packaging split as fact,
  with no publish promise.
- **`works/phases/active/P11/phase.md`** — appended a "Doc impact" line for S3, an "S3 done" findings
  section, and refinements to the existing "Hand-off to P12" section (the exact armed flip-probe command
  and the concrete git-push / install-and-check prerequisite). See "Doc impact" and "Phase notes" below.

Files **not** touched, per the plan's explicit boundary: `web/Dockerfile`, `web/next.config.ts`,
`deploy/vocky.conf` (re-verified this slice that all three already serve `web/public/` correctly — see
validation step 6).

## Validation — every step run, verbatim output

**1. Syntax** — `bash -n web/public/install.sh`
```
exit=0
```

**2. Shellcheck if available**
```
shellcheck not installed — skipping
```
(Not installed in this environment; not installed by this slice, per plan.)

**3. Truncation safety — a real falsifiable check**

`tail -n 1 web/public/install.sh`:
```
main "$@"
```
Exactly `main "$@"`, confirmed.

`head -n 40 web/public/install.sh | bash` (line 40 falls inside the `if ! command -v uv...; then ... fi`
block, still inside `main()`'s body, before its closing `}`):
```
bash: line 41: syntax error: unexpected end of file
exit=2
```
No output, no installation attempt — `main` is never reached (bash cannot even finish parsing the
truncated function definition).

I additionally tested the cleaner cut point the plan's phrasing implies — through the full `main()`
definition (closing `}` at line 59) but before the final call:

`head -n 59 web/public/install.sh | bash`:
```
exit=0
```
No output, no installation attempt — the function is fully defined but `main "$@"` (line 61) is never
reached because it wasn't included in the piped prefix.

Both cut points independently prove the same property: a truncated `curl | bash` can never half-execute.
The mid-function cut fails to parse at all (a stronger safety property, not a weaker one); the
post-function cut parses clean and simply does nothing.

**4. Real isolated install against the local checkout**

```sh
TMPHOME="$(mktemp -d)"
env -i HOME="$TMPHOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
    VOCKY_INSTALL_TARGET="$PWD" bash web/public/install.sh
```

Verbatim output (uv-bootstrap branch included — see note below):
```
==> uv not found — installing it via the official Astral installer.
downloading uv 0.11.33 aarch64-apple-darwin
installing to <TMPHOME>/.local/bin
  uv
  uvx
everything's installed!
==> uv: <TMPHOME>/.local/bin/uv
==> Installing vocky (re-run this script any time to upgrade).
Resolved 14 packages in 168ms
   Building vocky @ file:///Users/sugang/projects/personal/vocky
      Built vocky @ file:///Users/sugang/projects/personal/vocky
Prepared 14 packages in 476ms
Installed 14 packages in 11ms
 + vocky==0.2.0 (from file:///Users/sugang/projects/personal/vocky)
Installed 4 executables: vocky, vocky-server, vocky-smoke, vocky-worker
==> installed: 0.2.0
==> Next: vocky signup --email you@example.com
==> Agents: export VOCKY_BASE_URL and VOCKY_API_TOKEN, then run `vocky capture`.
install exit=0
```

Assertions:
- `"$TMPHOME/.local/bin/vocky" --version` → `0.2.0` — **passed** (matches the plan's expected value; the
  current tree, and installed metadata, agree).
- `"$TMPHOME/.local/bin/vocky" capture --help` → rendered the full `capture` help (message argument,
  `--product` required option, `--integration`/`--value`/`--comment`/`--tag`/`--session-id`/`--user-id`/
  `--project`) — **passed**, `P11.S2`'s command is present in what the installer delivers.

**Deviation from the plan's stated expectation, not from the plan's instructions**: the plan said "If `uv`
is already on PATH in this environment the bootstrap branch will be skipped — say so explicitly." In fact
the bootstrap branch **was** exercised, on both the first run and the idempotent second run, because
validation used `env -i PATH="/usr/bin:/bin:/usr/sbin:/sbin"` — a minimal PATH with no `uv` on it,
regardless of whether the host machine has `uv` installed elsewhere (it does, at `/Users/sugang/.local/bin/uv`,
but that path was deliberately excluded from the isolated environment). This is stronger evidence than the
plan anticipated, not a gap.

**5. Idempotency** — ran the identical command a second time against the same temp `HOME`:
```
Resolved 14 packages in 86ms
   Building vocky @ file:///Users/sugang/projects/personal/vocky
      Built vocky @ file:///Users/sugang/projects/personal/vocky
Prepared 14 packages in 214ms
Uninstalled 14 packages in 55ms
Installed 14 packages in 13ms
 ~ vocky==0.2.0 (from file:///Users/sugang/projects/personal/vocky)
Installed 4 executables: vocky, vocky-server, vocky-smoke, vocky-worker
==> installed: 0.2.0
second-run install exit=0
0.2.0
version-check exit=0
```
Exit 0, version check still passes. The temp `HOME` was then removed — `rm -rf <TMPHOME>` was denied by
the sandbox permission system in this session (a destructive-command guard on `rm -rf` regardless of
target); the leftover directory is an OS `mktemp -d` temp path outside the repo and outside the session
scratchpad, harmless and subject to normal OS temp-directory cleanup. No repo file was affected —
`git status --short` immediately after showed only the expected new/modified files.

**6. Serving path sanity** (static, no deploy):
- `grep -n "install" web/.dockerignore` → no exclusion match.
- `grep -n "install\|public" web/.gitignore` → no exclusion match.
- `grep -n "web/public\|public/" .gitignore` (repo root) → no exclusion match.
- `grep -n "COPY.*public" web/Dockerfile` → `40:COPY --from=build /app/public ./public` — still present,
  unedited.

**7. Web build/tests** (from `web/`):
```
pnpm typecheck   →  tsc --noEmit, no errors (silent success)
pnpm test        →  Test Files  5 passed (5); Tests  61 passed (61)
```
Unchanged from S1's 61-test baseline; adding `install.sh` to `public/` did not affect the app build.

**8. `python3 scripts/workflow.py validate`** → `Workflow validation passed.` (run twice: once before the
`phase.md` notes were appended, once after — both passed).

## What was NOT proven (explicit, per plan)

- **No live `https://vocky.hi2vi.com/install.sh` fetch** — the site is not deployed (`P11`/`P12` boundary).
  The `404 → 200` flip is entirely P12's to prove.
- **The `git+https://github.com/leetusik/vocky` target was never installed from.** GitHub `main` is 45
  commits behind local (remote head `3e1e85a`, last pushed 2026-07-17); every P9/P10/P11 commit is
  unpushed. Installing from the real URL today would silently deliver a pre-P10 CLI with no org keys and
  no `vocky capture` — that risk is itself the finding this slice records, not something it works around.
  `VOCKY_INSTALL_TARGET=$PWD` stood in for the real target throughout validation.
- The **`uv`-bootstrap branch's *skip* path** (host already has `uv` on PATH) was not exercised in this
  slice's isolated test — only the *install* path was, because the test environment's PATH was stripped to
  exclude the host's own `uv`. Both code paths exist and are simple (`command -v uv` gate); only the
  install branch was behaviorally proven here.
- **Shellcheck** was not run — not installed in this environment, and the plan says not to install it.

## Doc impact (appended to `phase.md`, not versioned here)

- **S3**: install now has a real path — `docs/current/operations.md` (install/CLI narrative should mention
  `web/public/install.sh` and the exact `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` line, marked
  live only once the site deploys) and `docs/current/experience.md` (the onboarding "how do I get the CLI"
  gap is now closed) both describe the install story and may need updates at the phase review. Source docs
  (`docs/cli.md`, `README.md`) were edited directly in this slice, not doc-versioned — per the workspace
  rule, durable docs are versioned once per phase, at the review.
- No `doc-new-version` was run (out of scope for this slice, correctly).

## Deviations from plan.md

None substantive. One clarification worth flagging: the plan's validation step 3 example uses `head -n 40`
specifically; I ran that exact command (result: parse error, exit 2, no output — main never reached) and
additionally ran a second cut at the closing `}` of `main()` (line 59, before the final `main "$@"` call)
to show the "clean parse, function defined but uncalled" case the plan's prose also describes. Both are
consistent with "no output and no installation attempt (main is never called)" — I ran both rather than
picking one, to make the falsifiable claim as concrete as possible.

The script landed at 61 lines against the plan's "~50 lines" target — within the same order of magnitude;
no functionality was added beyond what the plan specifies.

## Boundaries respected

No `git push`, no deploy, no PyPI work, no landing-page change, no `doc-new-version`, no commit, no
`workflow.py` status-transition command was run in this slice.
