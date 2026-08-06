# Result — P15.S5: Audit and refresh README.md

## What changed

Audited the (then-)476-line `README.md` against current reality (`docs/current/operations.md`, the
`Makefile`, `src/vocky/cli/`, `skills/vocky-feedback/SKILL.md`) and fixed exactly the six known-staleness
items from `phase.md` §"Already-spotted README staleness", verified in place before each fix. No
restructuring — same section order, same headings, same code examples. File is now 481 lines (net +5,
11 insertions / 7 deletions).

1. **Line 28 (Surfaces → Web app)** — "It runs locally today; the public deployment is P6." was wrong
   (verified: P12 deployed `https://vocky.hi2vi.com` on 2026-08-04, live per `operations.md`'s
   `✅ vocky is LIVE` banner). Replaced with a statement that it's live in production since 2026-08-04,
   plus still runs locally for dev.

2. **Install section (was lines ~50–71)** — verified the backwards framing ("**Once** … is live" /
   "**Today, before the site is deployed**, install from a checkout instead"). Flipped it: the hosted
   `curl | bash` line is now presented as live and primary; the checkout-install options are now framed as
   the dev/no-curl-pipe alternative.

3. **`make verify` description (was line 215) + granular target list (was line 231)** — verified against
   the `Makefile`: `verify: smoke test` (no wheel build, no `package-check` target — `.PHONY` list confirms
   it does not exist; likely removed in P6 with the Admin UI per `phase.md`'s note). Rewrote the sentence to
   say what `verify` actually runs, and swapped the dead `make package-check` bullet for the real
   `make check-skill-parity` (verified target exists and matches `operations.md`'s CI-gate description).

4. **`VOCKY_SMTP_*` (P13 email alerts)** — was entirely absent. Verified against `operations.md` §"SMTP
   feedback alerts (P13)" (five vars: `VOCKY_SMTP_HOST`/`USER`/`PASSWORD` required in prod, `PORT`/`FROM`
   optional; worker-only; silently off when unconfigured). Added one bullet to §What The Current Pre-MVP
   Does (feature-list framing, `VOCKY_SMTP_*` shorthand) and one to §Current Status (status framing, the
   three required var names spelled out plus the two optional ones) — no third location, kept surgical.

5. **§What The Current Pre-MVP Does / §Current Status** — verified both were silent on the live deployment,
   the published installer, the `vocky-feedback` agent skill, and email alerts (`recorded_by` was already
   covered later in the file, at what is now line 271, so I only added a cross-reference to it from the
   feature list — no duplication of its documentation). Added:
   - Current Status: a new lead bullet stating live-since-2026-08-04 + the hosted install line + "not on
     PyPI" (matches `operations.md`'s "still not on PyPI, and will not be").
   - What It Does: a `recorded_by` mention folded into the existing "Store like/dislike…" bullet (linking to
     §Agent Capture Over MCP), a bullet for the published `vocky-feedback` skill (linked to
     `skills/vocky-feedback/SKILL.md`, confirmed present on disk), and the SMTP-alerts bullet from item 4.

6. **Whole-file cross-check** — grepped for every other `P6`/`P11`/`P12`/`P13`/`PyPI`/`live`/"not yet"
   occurrence in the file (see Verification below). The three remaining "removed in P6" mentions (lines 34,
   211) are correct historical facts about the Admin UI removal, not staleness — left untouched. No other
   drift found; everything else in the file (CLI commands, REST examples, Makefile targets, env var names,
   endpoint lists) checked out against `Makefile`, `src/vocky/cli/`, and `operations.md`/`security.md`.

## Doc-impact decision

**No new "Doc impact" note.** Per the plan's rule of thumb (README isn't under `docs/`, so a correction to
it alone doesn't rise to durable-doc versioning), and confirmed by content: every fact I added to the README
is one that's already correctly stated in `docs/current/operations.md` (live-since-2026-08-04, the five
`VOCKY_SMTP_*` vars, `check-skill-parity`, the published skill) — I was bringing the README into line with
already-accurate `docs/current/*.md`, not surfacing a new contradiction that needs a doc version. The one
genuine `docs/current/*.md` staleness the audit touches (`product.md`/`experience.md` still carrying
pre-P12 "not live" wording) was already found and recorded by **S1**, not this slice — see `phase.md`
§"Cross-slice notes from the knowledge slices" → "S1 finding". S5 did not duplicate that finding; it's the
review's/operator's decision to act on, per that note and per the plan (explicitly out of S5's scope).

## Verification

- Re-read the entire edited `README.md` (481 lines) top to bottom for coherence — flows correctly, no
  orphaned framing, anchors (`#install`, `#agent-capture-over-mcp-write-only`) resolve to real headings.
- `grep -n "package-check" README.md` → no match (was present once, at the dead bullet; now removed).
- `grep -niE "not live|once.*is live|before the site is deployed" README.md` → no match.
- `grep -n "VOCKY_SMTP" README.md` → 2 matches (the two new bullets).
- `grep -n "check-skill-parity" README.md` → 1 match (the new bullet).
- Cross-checked every `make <target>` mentioned in the README (`bootstrap`, `check-skill-parity`,
  `compose-down`, `compose-logs`, `compose-up`, `external-smoke`, `external-verify`, `migrate`, `smoke`,
  `sync`, `test`, `verify`) against `Makefile`'s `.PHONY` list — all exist.
- Cross-checked `vocky` CLI subcommands mentioned (`feedback list`, `feedback search`, `keys mint`,
  `logout`, etc.) against `src/vocky/cli/*.py` — `feedback.py` registers a `feedback` sub-app with
  `list`/`search`/`show`, `auth.py` registers `logout`, `client.py`/`projects.py` back the rest; all real.
- Confirmed `skills/vocky-feedback/SKILL.md` exists on disk.

## Deviations from plan.md

None. Followed all six known-staleness items and the whole-file cross-check; decided the doc-impact
question as instructed.
