# Deferred Jobs

> Generated dashboard. Do not put detailed deferred context here; edit each `works/deferred/<state>/<DID>/` folder instead.

## Summary

- Open: `5`
- Promoted: `0`
- Dropped: `1`
- Rebuilt at: `2026-08-04T10:38:56+09:00`

## Open

| ID | Status | Title | Source | Trigger | Path |
|---|---|---|---|---|---|
| `D1` | `deferred` | Refine trajectory-aware feedback export model | user request | user promotes or schedules this job | `works/deferred/open/D1` |
| `D2` | `deferred` | Scope end-user feedback read to a public-safe field subset | P1.REVIEW | user promotes, or revisit alongside P2 attachment exposure | `works/deferred/open/D2` |
| `D3` | `deferred` | Garbage-collect never-linked attachment uploads | P2.DECOMP | user promotes, or the first cleanup / scale / PII-retention need | `works/deferred/open/D3` |
| `D4` | `deferred` | Project-scope the end-user attachment download endpoint | P3.REVIEW | operator promotes, or the next time the /api/* attachment surface is touched | `works/deferred/open/D4` |
| `D6` | `deferred` | Org management: additional orgs, member invites, roles | P10.DECOMP | When a user needs more than one org, or when a second person must share an org (team/collaboration demand), or before any pricing tier is sold per-seat. | `works/deferred/open/D6` |

## Promoted

| ID | Status | Title | Promoted To | Path |
|---|---|---|---|---|
| - | - | - | - | - |

## Dropped

| ID | Status | Title | Reason | Path |
|---|---|---|---|---|
| `D5` | `dropped` | Rate-limit the public /auth/* (open signup + password login) | Resolved by P12.S3, not abandoned: in-process per-(IP,route) fixed-window limiter on /auth/signup + /auth/login (src/vocky/rate_limit.py), default 20 per 900s, <=0 disables. promote-deferred was unavailable because the slice folder already existed. | `works/deferred/dropped/D5` |
