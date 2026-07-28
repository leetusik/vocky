#!/usr/bin/env bash
# vocky installer — served at https://vocky.hi2vi.com/install.sh (once the site
# is live; see docs/cli.md). Run it with:
#
#   curl -fsSL https://vocky.hi2vi.com/install.sh | bash
#
# Every executable statement lives inside main(), and `main "$@"` is the last
# line of this file. That shape is the whole safety argument for piping a
# remote script into bash: `curl | bash` streams, so bash starts executing
# what it has already received while the rest of the file is still
# downloading. If the connection drops mid-transfer, a flat (non-wrapped)
# script would run whatever prefix of itself it had received. Wrapped in
# main(), a truncated download instead defines a function body and then hits
# EOF before the final `main "$@"` line is ever reached — it can never
# half-execute. Read this file before you pipe it into a shell; that is
# exactly what this comment block is for.

set -euo pipefail

UV_BIN_DIR="$HOME/.local/bin"
# Override for local verification/forking — e.g.
# VOCKY_INSTALL_TARGET="$PWD" bash install.sh installs from a local checkout
# instead of GitHub. This is not a new attack surface: anyone who can set your
# environment before running this script can already run arbitrary commands.
INSTALL_TARGET="${VOCKY_INSTALL_TARGET:-git+https://github.com/leetusik/vocky}"

say() { printf '==> %s\n' "$1"; }
die() { printf 'error: %s\n' "$1" >&2; exit 1; }

main() {
  command -v curl >/dev/null 2>&1 || die "curl is required but was not found on PATH."

  if ! command -v uv >/dev/null 2>&1; then
    say "uv not found — installing it via the official Astral installer."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$UV_BIN_DIR:$PATH"
    command -v uv >/dev/null 2>&1 \
      || die "uv still not on PATH after install — open a new shell (or add $UV_BIN_DIR to PATH) and re-run."
  fi
  say "uv: $(command -v uv)"

  say "Installing vocky (re-run this script any time to upgrade)."
  uv tool install --reinstall "$INSTALL_TARGET"

  # PATH-tolerant verification: re-export the uv tool bin dir so the check
  # below works even in this same non-interactive shell, but never `die` on
  # failure here — the tool is installed either way, only the *current*
  # shell's PATH may be stale.
  export PATH="$UV_BIN_DIR:$PATH"
  if command -v vocky >/dev/null 2>&1; then
    say "installed: $(vocky --version)"
  else
    printf 'note: vocky was installed but is not on this shell'"'"'s PATH yet.\n' >&2
    printf 'note: add %s to PATH, or run `uv tool update-shell`, then open a new shell.\n' "$UV_BIN_DIR" >&2
  fi

  say "Next: vocky signup --email you@example.com"
  say "Agents: export VOCKY_BASE_URL and VOCKY_API_TOKEN, then run \`vocky capture\`."
}

main "$@"
