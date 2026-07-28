# Deferred Jobs

> Generated dashboard. Do not put detailed deferred context here; edit each `works/deferred/<state>/<DID>/` folder instead.

## Summary

- Open: `6`
- Promoted: `0`
- Dropped: `0`
- Rebuilt at: `2026-07-28T23:22:11+09:00`

## Open

| ID | Status | Title | Source | Trigger | Path |
|---|---|---|---|---|---|
| `D1` | `deferred` | Refine trajectory-aware feedback export model | user request | user promotes or schedules this job | `works/deferred/open/D1` |
| `D2` | `deferred` | Scope end-user feedback read to a public-safe field subset | P1.REVIEW | user promotes, or revisit alongside P2 attachment exposure | `works/deferred/open/D2` |
| `D3` | `deferred` | Garbage-collect never-linked attachment uploads | P2.DECOMP | user promotes, or the first cleanup / scale / PII-retention need | `works/deferred/open/D3` |
| `D4` | `deferred` | Project-scope the end-user attachment download endpoint | P3.REVIEW | operator promotes, or the next time the /api/* attachment surface is touched | `works/deferred/open/D4` |
| `D5` | `deferred` | Rate-limit the public /auth/* (open signup + password login) | P6.S6 | At/soon after go-live: add a Cloudflare rate-limiting rule for /auth/*, or an in-process per-IP limiter in src/vocky/auth_api.py. | `works/deferred/open/D5` |
| `D6` | `deferred` | Org management: additional orgs, member invites, roles | P10.DECOMP | When a user needs more than one org, or when a second person must share an org (team/collaboration demand), or before any pricing tier is sold per-seat. | `works/deferred/open/D6` |

## Promoted

| ID | Status | Title | Promoted To | Path |
|---|---|---|---|---|
| - | - | - | - | - |

## Dropped

| ID | Status | Title | Reason | Path |
|---|---|---|---|---|
| - | - | - | - | - |
