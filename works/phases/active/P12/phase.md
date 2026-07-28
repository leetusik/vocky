# Phase P12: Production launch & hardening: bring-up, rate limits, CI tests, QA doc

_Intent: see [intent.md](intent.md)._

## Objective

Take vocky live, then close the operational gaps its own phases left open: run the operator-gated production bring-up at `vocky.hi2vi.com` using the artifacts P6 authored but deliberately never executed (compose topology, edge vhost, deploy/rollback scripts, CI chain — none has ever touched real infrastructure), then rate-limit the public `/auth/*` surface (deferred D5 — a Cloudflare rule or an in-process per-IP limiter, since the shared edge forbids `limit_req_zone`), add the CI test workflow the repo has never had (`.github/workflows/` holds only `deploy-production.yml`), write `docs/current/qa.md` (still the bootstrap v0001 placeholder after nine phases), decide the fate of the now-unreachable `/admin/api/*` surface and its `VOCKY_ADMIN_AUTH_TOKEN` box secret, and add Postgres backups plus basic log/metrics. Deploying only after P10 and P11 is deliberate: the accounts-v2 migration then lands on an empty schema instead of as a live cutover on prod data. Feature work and the deferred attachment GC (D3, which needs a scheduler that does not exist) stay out of scope.

## Context

## Decomposition

_Slice breakdown and rationale — filled by the `P12.DECOMP` slice._

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

## Constraints

## Open Questions

-
