#!/usr/bin/env python3
"""Verify the served ``SKILL.md`` is a byte-for-byte copy of the canonical one.

vocky ships exactly one end-user agent skill. Its canonical home is
``skills/vocky-feedback/SKILL.md``; the landing page serves a **committed**
copy at ``web/public/SKILL.md`` (a straight publish, not a build-time
generation — see ``web/next.config.ts``'s ``output: "standalone"`` and
``web/Dockerfile``'s ``COPY --from=build /app/public ./public``). Nothing is
allowed to differ between the two, full-file bytes including frontmatter, so
this compares them exactly and fails loudly the moment a hand-edit, a
prettier reflow, or a stale copy lets them drift.

Exit code is the contract: ``0`` when the files match, ``1`` when either file
is missing or the bytes differ.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_PATH = REPO_ROOT / "skills" / "vocky-feedback" / "SKILL.md"
SERVED_PATH = REPO_ROOT / "web" / "public" / "SKILL.md"


def main() -> None:
    """Compare the canonical and served ``SKILL.md`` copies and exit accordingly."""

    for path in (CANONICAL_PATH, SERVED_PATH):
        if not path.is_file():
            raise SystemExit(f"FAIL — missing file: {path.relative_to(REPO_ROOT)}")

    canonical_bytes = CANONICAL_PATH.read_bytes()
    served_bytes = SERVED_PATH.read_bytes()

    if canonical_bytes != served_bytes:
        raise SystemExit(
            "FAIL — "
            f"{SERVED_PATH.relative_to(REPO_ROOT)} is not a byte-for-byte copy of "
            f"{CANONICAL_PATH.relative_to(REPO_ROOT)}. "
            f"Fix: cp {CANONICAL_PATH.relative_to(REPO_ROOT)} "
            f"{SERVED_PATH.relative_to(REPO_ROOT)}"
        )

    print(f"PASS — {SERVED_PATH.relative_to(REPO_ROOT)} matches the canonical skill byte-for-byte.")


if __name__ == "__main__":
    main()
