# Plan — P15.S3: Knowledge — security, operations, and QA

Third of the four-explainer series (see `../../phase.md`). Executed **inline by the orchestrator** — `/explain` is main-thread-only; no executor dispatched.

## What this slice produces

One `/explain` run in topic mode → personal KB (project `vocky`), no `here` flag. Repo writes limited to `result.md` + a `phase.md` note.

## Topic

*How vocky is kept safe and kept running* — identity/tenancy/credential trust boundaries (404-never-403, scope resolution, fail-closed admin guard vs best-effort last-used stamp), the config surface (local vs production), the production topology and deploy/rollback lifecycle (5 containers, image-tag rollback, migrations outside images, edge vhost in `leetusik/edge`), the rate limiter and its single-worker invariant, `/mcp` host allowlisting, the test suites (two-database contract, 32 backend files + web vitest) and CI gates (`skill_parity`, workflows).

Topic string:

> vocky security, operations, and QA for a maintainer: the identity and credential trust boundaries (404-never-403, fail-closed admin bearer, the in-memory rate limiter's single-worker invariant, /mcp host allowlisting), the local and production configuration surfaces, the five-container deploy topology with image-tag rollback and migrations-before-code, and the test suites and CI gates

## Reading set (from `phase.md` §Sources — S3)

Docs: `docs/current/security.md` (all), `operations.md` (all), `qa.md` (all); `architecture.md` §Identity/§Credential Scope/§Config/§Production Topology already read in S2 — reuse, do not re-read.
Files (grounding): `Makefile`, `.github/workflows/` listing, `deploy/` listing, `tests/` listing, `scripts/skill_parity.py` (skim). `rate_limit.py`/`auth.py`/`config.py` shapes already known from docs.

## Steps

1. Read the three docs; skim the grounding files.
2. Web-research judgment at research time: security posture (fail-closed defaults, rate limiting, secret handling) has an external comparison surface — likely include a light cited section; degrade gracefully if offline.
3. Check KB for a prior doc on this subject (expected none). Author the HTML explainer per the explain skill contract.
4. POST to the KB API; record url/version.
5. Write `result.md`; append the `phase.md` note.

## Done means

Explainer #3 in the KB; `result.md` records where; coverage sufficiency stated (this is the other heavy grouping).
