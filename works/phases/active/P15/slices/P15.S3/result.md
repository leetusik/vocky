# Result — P15.S3: Knowledge — security, operations, and QA

**Status: done.** The third explainer of the new-maintainer series is published to the personal KB.

## What was produced

One `/explain` run (topic mode, no `here`, executed inline by the orchestrator):

- **Title:** "Vocky Security, Operations, and QA: Keeping It Safe and Keeping It Running"
- **KB location:** document id 27, **v1** (project `vocky`)
- **URL:** https://knowledge.hi2vi.com/documents/27
- **Save state:** `201`, committed, `push_pending: true` (normal)
- **Research section:** **included** — cited OWASP Password Storage Cheat Sheet (argon2id alignment) and OWASP Session Management Cheat Sheet (token entropy/cookie-attribute alignment, and the honest 30-day-session divergence from OWASP's idle/absolute-timeout guidance). Next steps: rehearse the restore drill + apply the P12.S5 box artifacts, per-credential capture rate limiting, off-box backup replication, ruff sweep-then-gate.

## Coverage

Grounded in `security.md` v0011 (full), `operations.md` v0008 (full), `qa.md` v0004 (full), plus the architecture/backend sections already read in S2. Covers: the six-secret credential inventory with blast radii; the P14 third-party-agent-runtime escalation; 404-never-403 and no-enumeration; the fail-closed vs best-effort asymmetry (scope resolution vs last_used_at; `${VAR:?}` secrets; the 503 tokenless admin guard); the rate limiter's four properties and the single-uvicorn-worker invariant; the deploy lifecycle SVG (tag → build → migrate-first → recreate → gate; tag-flip rollback; never `down -v`); the smoke ladder (suites → vocky-smoke → CI → manual-only territory incl. the unrehearsed restore drill); the production file map (compose, deploy/rollback/backup scripts, edge vhost + house rules + proxy_set_header footgun, CI workflows); the app/edge header split and no-nonce CSP; QA run commands with the new-maintainer trap list (two-database contract, pnpm dev vs start, BFF origin gate, stale worker image, env -u false-pass); the two mirror-assertions. 5-question quiz.

## Coverage sufficiency

One run sufficed. The grouping is broad but coheres as one "operator's view" read; the explainer teaches the invariants and points at the runbooks rather than reproducing them.

## Notes for later slices

- None new. (operations.md/qa.md are internally consistent about the live status — the staleness S1 found is confined to product.md/experience.md.)
