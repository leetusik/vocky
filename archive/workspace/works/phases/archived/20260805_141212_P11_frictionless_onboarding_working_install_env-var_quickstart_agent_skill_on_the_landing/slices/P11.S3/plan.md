# P11.S3 — `curl | bash` installer: `web/public/install.sh`

## Why

Operator decision 1 for this phase: the install path is a **`curl | bash` installer, not PyPI**. Today the
only documented way to get the `vocky` command is from a checkout (`docs/cli.md:11-19`, `README.md:48-63`),
and both places still say "PyPI publishing is planned (P6)" — stale twice over, since the intent moved
publishing to P11 and the operator then took PyPI off P11 entirely.

Serving the script costs **zero infra**, already verified: `web/next.config.ts:55` `output: "standalone"`,
`web/Dockerfile:40` `COPY --from=build /app/public ./public`, and `deploy/vocky.conf:282-288` is a bare
`location / { proxy_pass … :3000; }` with no more-specific location shadowing a root path. **Do not touch
the Dockerfile, `next.config.ts`, or `deploy/vocky.conf`** — they already work.

## Two verified findings that shape this slice

1. **The GitHub repo is public** — `https://api.github.com/repos/leetusik/vocky` returns `200`,
   `"visibility": "public"`. So `git+https://github.com/leetusik/vocky` resolves for an anonymous user and
   the installer mechanism is viable with no auth.
2. **GitHub `main` is 45 commits behind local** — remote head is `3e1e85a` ("feat(design): P8.S2
   handoff-02"), last pushed `2026-07-17`. Every commit of P9 (design apply), P10 (accounts v2) and P11 is
   **unpushed**. So `uv tool install git+https://github.com/leetusik/vocky` **today installs a CLI that
   predates org keys, `--project` resolution, and `vocky capture`.** The installer would appear to work and
   silently deliver a stale CLI.

   This is the knowledge repo's documented "`git+` installs whatever is on GitHub `main`" caveat, in a much
   larger size. **P11 does not push** — the workspace never pushes unasked, and the site is not live
   either. Both facts go in `result.md` and in the `phase.md` P12 hand-off as hard prerequisites.

## Deliverable — `web/public/install.sh`

Mirror the shape knowledge verified in production. Target ~50 lines. Every property below is deliberate;
none is decoration.

### Structure, in order

1. **A header comment block** stating: the URL it is served from, the exact `curl -fsSL … | bash`
   invocation, and **why the `main()` shape exists** (the next point). A reader who lands on this file via
   `curl` should be able to audit it in one screen.
2. `set -euo pipefail` immediately after the shebang (`#!/usr/bin/env bash`).
3. Two constants:
   - `UV_BIN_DIR="$HOME/.local/bin"`
   - `INSTALL_TARGET="${VOCKY_INSTALL_TARGET:-git+https://github.com/leetusik/vocky}"` — the env override
     exists so this slice can verify the script against a **local** checkout, and so a fork can retarget
     it. Comment it as such. (It is not a new attack surface: anyone who can set your environment can
     already run arbitrary commands.)
4. Two one-line helpers: `say() { printf '==> %s\n' "$1"; }` and
   `die() { printf 'error: %s\n' "$1" >&2; exit 1; }`.
5. **`main()` containing every executable statement.**
6. **`main "$@"` as the last line of the file.**

### The properties that matter

- **The `main()` wrapper is the whole safety argument.** `curl | bash` streams: bash executes what it has
  received while the rest is still downloading. If the connection drops mid-file, a flat script runs a
  *prefix* of itself. With every statement inside `main()` and `main "$@"` last, a truncated download
  defines a function and then reaches EOF — **it can never half-execute**. Say this in the header comment.
- **Precondition check**: `command -v curl >/dev/null 2>&1 || die "curl is required but was not found on PATH."`
- **Bootstrap `uv` only if absent, and echo before doing it** — never silently install something:
  ```bash
  if ! command -v uv >/dev/null 2>&1; then
    say "uv not found — installing it via the official Astral installer."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$UV_BIN_DIR:$PATH"
    command -v uv >/dev/null 2>&1 \
      || die "uv still not on PATH after install — open a new shell (or add $UV_BIN_DIR to PATH) and re-run."
  fi
  say "uv: $(command -v uv)"
  ```
- **`--reinstall` makes re-runs idempotent and upgrade-safe**:
  `uv tool install --reinstall "$INSTALL_TARGET"`, preceded by a `say` that tells the user re-running is
  how they upgrade.
- **No sudo, nothing system-wide.** Everything lands under `$HOME/.local`.
- **PATH-tolerant verification that warns rather than dies**: re-export `$UV_BIN_DIR` onto `PATH` so the
  check works in the same shell; on success `say "installed: $(vocky --version)"`; on failure print a
  `note:` to **stderr** with the remedy (add `$UV_BIN_DIR` to PATH, or `uv tool update-shell`) and **do
  not** `die` — the tool is installed, only the current shell's PATH is stale.
- **Close by printing the next command.** Verified against the real CLI:
  ```
  Next: vocky signup --email you@example.com
  ```
  (`src/vocky/cli/auth.py:62-66` — `signup` takes `--email` and `--password-stdin`.) Follow it with one
  line pointing at the agent path, using the surface `P11.S2` actually shipped:
  `Agents: export VOCKY_BASE_URL and VOCKY_API_TOKEN, then run \`vocky capture\`.`

- **No `#subdirectory=` fragment.** vocky's CLI lives at the repo root with a single `pyproject.toml`
  (unlike knowledge's `cli/` subdirectory). A plain git install builds the wheel from
  `packages = ["src/vocky"]` and, because of the lean/`server`-extra split, resolves only httpx + typer
  and their transitives.

## Docs — tell the truth about *when* it works

The install line must not claim to work before P12 deploys the site. Update both places to say plainly
that the hosted installer is the path **once vocky.hi2vi.com is live**, and keep the checkout path as
what works today.

- **`docs/cli.md:9-19`** — replace the stale "PyPI publishing is planned (P6); until then install from a
  checkout" framing. New shape: the `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` one-liner,
  explicitly marked as available once the site is live, then the existing checkout options as today's
  path. Do **not** claim PyPI is coming — it is off this phase.
- **`README.md:48-63`** — the same correction. Its line about `pip install vocky` / `uvx vocky` "once
  published to PyPI" is now misleading about the plan; reword so it describes the lean-CLI vs `[server]`
  extra split as a packaging fact without promising a publish.

Do **not** edit `docs/current/*.md` — those are generated snapshots. Append **one line** to the
`## Doc impact` section of `works/phases/active/P11/phase.md` naming `operations` and `experience` (both
currently describe the install story) for the phase review to consolidate. Do **not** run
`doc-new-version`.

## Validation

Run every step and record verbatim output.

1. **Syntax**: `bash -n web/public/install.sh` → exit 0.
2. **Shellcheck if available**: `command -v shellcheck && shellcheck web/public/install.sh` — if it is not
   installed, say so and move on; do not install it.
3. **Truncation safety — a real falsifiable check, not an assertion.** Pipe a prefix of the file to bash
   and prove nothing happens:
   ```sh
   head -n 40 web/public/install.sh | bash; echo "exit=$?"
   ```
   Expect **no output and no installation attempt** (`main` is never called). Also confirm
   `tail -n 1 web/public/install.sh` is exactly `main "$@"`.
4. **Real isolated install against the local checkout** — this is the slice's central proof:
   ```sh
   TMPHOME="$(mktemp -d)"
   env -i HOME="$TMPHOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" \
       VOCKY_INSTALL_TARGET="$PWD" bash web/public/install.sh
   ```
   Then assert, using that temp HOME's install:
   - `"$TMPHOME/.local/bin/vocky" --version` → **`0.2.0`** (proves it installed the current tree, and that
     `--version` reflects installed metadata).
   - `"$TMPHOME/.local/bin/vocky" capture --help` → renders (proves `P11.S2`'s command is present in what
     the installer delivers).
   Remove the temp HOME afterwards. If `uv` is already on PATH in this environment the bootstrap branch
   will be skipped — say so explicitly rather than claiming that branch was exercised.
5. **Idempotency**: run the same command a second time against the same temp HOME → exit 0, and the
   version check still passes.
6. **Serving path sanity** (static, no deploy): confirm `web/public/install.sh` is not excluded by
   `web/.dockerignore` or `web/.gitignore`, and that `web/Dockerfile:40` still copies `public/`. No edits.
7. `pnpm typecheck && pnpm test` from `web/` → unchanged from S1's baseline (61 tests). Adding a file to
   `public/` must not affect the app build.
8. `python3 scripts/workflow.py validate` → passes.

**State plainly in `result.md` what was NOT proven**: no live `https://vocky.hi2vi.com/install.sh` fetch
(the site is not deployed), the `404 → 200` flip is P12's, the `uv` bootstrap branch was probably not
exercised, and the `git+https://…` target was **not** installed from — because GitHub `main` is 45 commits
stale and would have delivered a pre-P10 CLI, which is itself the finding.

## Hand-off to P12 — append to `phase.md`

Add to the existing hand-off section:

- **Armed flip probe**: `curl -sS -o /dev/null -w '%{http_code}' https://vocky.hi2vi.com/install.sh` → `404`
  today, must be `200` after the first deploy.
- **`git push` is a hard prerequisite**, not a nicety: until local `main` reaches GitHub, the hosted
  installer delivers a pre-P10 CLI with no org keys and no `vocky capture`. Verify after pushing by
  installing into a clean environment from the real `git+https://` target and asserting
  `vocky --version` ≥ `0.2.0` and that `vocky capture --help` exists — **install and check, do not assert**.

## Out of scope

- No PyPI, no `uv publish`, no `dist/` work.
- No Dockerfile, `next.config.ts`, or nginx change — all three already serve `public/` correctly.
- No Windows `install.ps1`.
- No landing-page change: the hero's install row is designed in `P11.S5` and built after `P11.DECOMP2`.
- No `git push`, no deploy.
- No `doc-new-version`.

## When done

Write `works/phases/active/P11/slices/P11.S3/result.md` from scratch (free-form): the script as it landed
with its line count, the verbatim output of every validation step, an explicit list of what was not
proven, and the P12 prerequisites. Append durable cross-slice notes to
`works/phases/active/P11/phase.md` — `P11.S4`'s skill and the `P11.S5` design handoff both quote the
install line, so record its **exact** final text. Do not commit and do not change any slice or phase
status.
