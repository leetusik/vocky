# P1.REVIEW result — Phase review (validate + judge; docs NOT consolidated)

**Verdict: `changes_requested`.** The relicense and MCP/agent-capture retirement are functionally
complete and the REST-only surface is intact and tested, but the phase's own behavioral gate
(`make verify`) is **not green**: S2's MCP scrub of the runtime admin asset `docs.json` also removed a
required *REST* (non-MCP) help string, so `make verify`'s `package-check` step fails. Fixing it needs a
source edit, which a review slice may not make — so this is `changes_requested` with one fix slice
(`P1.F1`), not a pass. **No durable docs were consolidated** (consolidation happens only on a pass) and
**no source was edited**.

## Step 1 — Validation results

Stack: rebuilt from current source via `make bootstrap` (the 2-day-old containers predated S2) so the
smoke ran against the shipped MCP-free app; Postgres `55432` + Redis `56379` + Docker all reachable.

| Check | Command | Result |
| --- | --- | --- |
| State integrity | `python3 scripts/workflow.py validate` | **PASS** — `Workflow validation passed.` |
| Relicense (S1) | `grep -riE "AGPL\|Affero\|GNU\|Public License" LICENSE pyproject.toml README.md` | **PASS** — no matches (exit 1); `pyproject.toml:11 license = { text = "MIT" }`; `LICENSE` line 1 `MIT License` |
| MCP-free src/tests (S2) | `grep -rinE "import mcp\|from mcp\|mcp\.\|streamable_http\|FastMCP" src/ tests/` | **PASS** — empty |
| MCP env/deps (S2) | `grep -rniE "VOCKY_MCP\|mcp-tools" src/ .env.example docker-compose.yml Makefile` | **PASS** — empty |
| No root catch-all (S2) | `grep -nE 'Mount\("/"' src/vocky/app.py` | **PASS** — empty (no `Mount("/", …)`) |
| No mcp under src/ (S2) | `grep -rin "mcp" src/` | **PASS** — empty |
| README REST-only (S3) | `grep -inE "\bmcp\b\|/mcp\|VOCKY_MCP\|capture_feedback\|list_feedback\|summarize_feedback\|list_liked_conversations" README.md` | **PASS** — empty |
| Behavioral: package-check | `make verify` → `package-check` | **FAIL** — `docs.json missing REST try content: target_type message, conversation, or surface` |
| Behavioral: REST smoke | `make smoke` (`vocky-smoke`) | **PASS** — health ok → `POST /api/feedback` accepted (`d3bd0d28-…`) → `GET /api/feedback ok: 1 record` |
| Behavioral: full suite | `make test` (`uv run pytest`) | **PASS — 132 passed in 3.30s** (all 14 test files) |

`make verify` = `package-check smoke test`; it stops at the first failing target (`package-check`), so
`smoke` and `test` were run separately (both green). The full suite is genuinely green here (not
deferred) — 132 passed against a fresh `vocky_test` DB.

## The one gap (why `changes_requested`)

`scripts/check_admin_ui_package.py` (line 115) asserts the exact substring
`target_type message, conversation, or surface` exists in the packaged `src/vocky/admin_assets/docs.json`.
S2's MCP scrub deleted the bullet that carried it. Pre-S2 (`git show 7f32a34:…/docs.json`) that bullet read:

> "Use target_type message, conversation, or surface to review exact message feedback,
> whole-conversation feedback, or product-surface feedback separately."

It sat directly beside an MCP `list_feedback`/`summarize_feedback` bullet that was *correctly* removed;
the adjacent REST/transport-neutral bullet was removed along with it. This string is **REST content, not
MCP** — it should have been kept.

Why the suite stayed green while `make verify` fails: `tests/test_admin_ui.py`'s `required_text` list
asserts the sibling string `"Any leaves older records with unset target_type visible"` (still present,
docs.json line 160) but does **not** assert `"target_type message, conversation, or surface"`. That
requirement lives only in the standalone packaging validator, which `make test` does not invoke — so the
132-test suite is green while `package-check` is red.

This is a real regression attributable to the phase (S2), and a green `make verify` is the phase's stated
exit bar (DECOMP: "must end with a green suite"; this plan's Step 1: run `make verify`). It cannot pass.

## Step 2 — Objective & intent assessment

Judged against `phase.md` objective (line 7) and `intent.md`'s confirmed P1 scope:

- **Relicense AGPL-3.0 → MIT (everywhere declared):** MET. `LICENSE` is MIT, `pyproject.toml` `license
  = { text = "MIT" }`, README `## License` reworded to MIT; nothing claims AGPL/Affero/GNU anywhere.
- **Retire MCP / AI-agent-decided capture entirely:** MET. MCP server, the four agent tools, MCP
  config/env/deps, `MCPBearerAuthMiddleware`, and the `/mcp` root mount are gone; app imports with
  `mcp` uninstalled; `src/` is 100% MCP-free; git history keeps it recoverable per intent.
- **REST feedback surface intact & tested:** MET. `POST`/`GET /api/feedback`, attachment upload/
  download, Admin REST, Admin Web UI, worker/queue/Postgres all present; end-to-end REST smoke passes;
  132 tests pass.
- **README + runtime `docs.json` reflect REST-only reality:** README MET; `docs.json` is MCP-free but
  lost a required REST string (the gap above).
- **No regressions beyond the intended removal:** ONE regression — the `docs.json` REST help string —
  breaking `make verify` package-check.

Everything the operator asked for is delivered except this single mechanical packaging gap.

## Step 3 — Docs consolidation

**Not performed.** Durable docs are consolidated only on a passing review. The four Doc-impact areas
(`api`, `architecture`, `product`, `experience`) still describe MCP and remain queued for consolidation
at the *next* (re-)review after `P1.F1` lands and `make verify` is green.

## Proposed fix slice

**`P1.F1` — Restore the REST `target_type` help string in `docs.json`** · `kind: fix` · risk **low** ·
order ~3.5 (between S3 and REVIEW).

- *Problem:* S2's MCP scrub removed the REST/transport-neutral bullet containing
  `target_type message, conversation, or surface` from `src/vocky/admin_assets/docs.json`; the packaging
  validator `scripts/check_admin_ui_package.py:115` still requires it, so `make verify` (`package-check`)
  fails while `make test` (132) and `make smoke` pass.
- *Fix:* re-add a REST-appropriate sentence containing the exact substring
  `target_type message, conversation, or surface` to `docs.json` — natural home is the `rest-capture`
  topic near the existing `target_type surface` guidance, or the `admin-rest` read-filters block beside
  the existing "Any leaves older records with unset target_type visible" line. **Keep it MCP-free** — do
  not reintroduce `list_feedback`/`summarize_feedback` or any MCP wording.
- *Do NOT change* `topic_ids` (must stay `[operator-overview, rest-capture, admin-rest,
  local-self-hosting, public-custom-domain]`) or the `rest_capture_try` block; adding a bullet inside an
  existing topic keeps `test_admin_ui.py` green, so no pytest change is expected.
- *Verify:* `make verify` fully green (package-check + smoke + test 132); and
  `grep -c "target_type message, conversation, or surface" src/vocky/admin_assets/docs.json` == 1.

After `P1.F1` lands, re-review P1 (the greps + full `make verify` + `validate`), then consolidate the
four durable docs on the pass.

## Deviations from plan.md

The plan anticipated a likely `pass` → doc consolidation. Instead the behavioral suite surfaced a real
`package-check` failure the earlier slices did not run (`make test` excludes `package-check`), so per the
review-slice rules I stopped at `changes_requested`, consolidated no docs, and edited no source.
