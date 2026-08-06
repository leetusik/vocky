# Plan — P15.S5: Audit and refresh README.md

Docs-only slice, dispatched normally (`slice-executor-mid`; escalate if it turns out to be more). Scope: **audit the 476-line `README.md` against current reality and fix only what is stale, wrong, or missing — not a rewrite.** The README's structure should survive intact.

## Known staleness to fix (from `phase.md` §"Already-spotted README staleness" — verify each in place, then fix)

1. **Line ~28** — "It runs locally today; the public deployment is P6." Wrong: P12 deployed `https://vocky.hi2vi.com` on 2026-08-04 and it is live.
2. **Lines ~50–71 (Install)** — framed as "**Once** `https://vocky.hi2vi.com` is live … **Today, before the site is deployed**, install from a checkout instead". Backwards now: the hosted `curl -fsSL https://vocky.hi2vi.com/install.sh | bash` is the real primary path; from-checkout is the fallback/dev path.
3. **Line ~215 + ~231** — "`make verify` builds a fresh wheel and checks the packaged assets" and the `make package-check` bullet. `package-check` no longer exists (removed in P6); `verify` is `smoke test` today. The granular target list also omits the real `make check-skill-parity`.
4. **P13 SMTP email alerts absent** — no `VOCKY_SMTP_*` mention anywhere. Add a brief mention where config/production features are described (worker-side feedback alert emails, five `VOCKY_SMTP_*` vars, off when unconfigured).
5. **§What The Current Pre-MVP Does (~line 156) / §Current Status (~line 184)** — neither mentions the live deployment, the published installer, the `vocky-feedback` agent skill, `recorded_by` capture provenance, or email alerts. Bring both up to date concisely. (`recorded_by` is already documented at ~line 267 — do not duplicate, just reference.)
6. **Cross-check the whole file** against `docs/current/product.md` §Status (note: that doc itself carries stale pre-P12 lines — trust `operations.md`'s live-status account, which is internally consistent) and `docs/current/operations.md`. Fix anything else stale/wrong/missing you find; keep edits surgical.

## Doc-impact question (from `phase.md` §Open Questions — decide explicitly)

Decide and record in `result.md`: does this README correction rise to a "Doc impact" note for the review? Rule of thumb: README is not under `docs/`, so on its own — no. Only if you find the audit forces a factual claim that *also* contradicts `docs/current/*.md` does it become a Doc impact note. (The already-known `product.md`/`experience.md` staleness is recorded in `phase.md` separately; it is NOT this slice's scope to fix those docs.)

## Verification

- Re-read the edited README in full for coherence.
- `grep` sanity checks: no remaining "package-check", no remaining "not live"/"once the site is live"-style framing about vocky.hi2vi.com, `VOCKY_SMTP` now present, `check-skill-parity` present.
- Confirm every claimed command/target exists (`Makefile` targets, script names).

## Deliverables

- The edited `README.md` (only file changed besides this slice's bookkeeping).
- `result.md`: what was changed and why, the doc-impact decision, anything the review should know.
- A one-line cross-slice note appended to `phase.md`.

Never commit; never transition status.
