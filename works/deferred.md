# Deferred Jobs

> Generated dashboard. Do not put detailed deferred context here; edit each `works/deferred/<state>/<DID>/` folder instead.

## Summary

- Open: `9`
- Promoted: `0`
- Dropped: `1`
- Rebuilt at: `2026-08-06T23:04:20+09:00`

## Open

| ID | Status | Title | Source | Trigger | Path |
|---|---|---|---|---|---|
| `D1` | `deferred` | Refine trajectory-aware feedback export model | user request | user promotes or schedules this job | `works/deferred/open/D1` |
| `D10` | `deferred` | Per-credential permission scopes (capture-only keys) — revisit D-P3-2 now that vk_ keys live in third-party agent processes | P14.DECOMP | before recommending vocky keys be embedded in any third-party runtime the operator does not control | `works/deferred/open/D10` |
| `D2` | `deferred` | Scope end-user feedback read to a public-safe field subset | P1.REVIEW | user promotes, or revisit alongside P2 attachment exposure | `works/deferred/open/D2` |
| `D3` | `deferred` | Garbage-collect never-linked attachment uploads | P2.DECOMP | user promotes, or the first cleanup / scale / PII-retention need | `works/deferred/open/D3` |
| `D4` | `deferred` | Project-scope the end-user attachment download endpoint | P3.REVIEW | operator promotes, or the next time the /api/* attachment surface is touched | `works/deferred/open/D4` |
| `D6` | `deferred` | Org management: additional orgs, member invites, roles | P10.DECOMP | When a user needs more than one org, or when a second person must share an org (team/collaboration demand), or before any pricing tier is sold per-seat. | `works/deferred/open/D6` |
| `D7` | `deferred` | Define the project QA driver /qa-check requires | P12.S7 | When the operator wants exploratory browser QA runs against the live site, or the next phase that builds UI features wants automated QA evidence. | `works/deferred/open/D7` |
| `D8` | `deferred` | Retry or outbox for failed feedback alert emails | P13.REVIEW | A real alert observed missing/failed on the box, volume growth past single-owner scale, or any work adding a second notification channel or preferences surface. | `works/deferred/open/D8` |
| `D9` | `deferred` | Rate-limit the public capture surfaces (POST /api/feedback, /mcp) per credential, not per IP | P14.DECOMP | before a second third-party agent product goes live, or on the first abuse/cost incident | `works/deferred/open/D9` |

## Promoted

| ID | Status | Title | Promoted To | Path |
|---|---|---|---|---|
| - | - | - | - | - |

## Dropped

| ID | Status | Title | Reason | Path |
|---|---|---|---|---|
| `D5` | `dropped` | Rate-limit the public /auth/* (open signup + password login) | Resolved by P12.S3, not abandoned: in-process per-(IP,route) fixed-window limiter on /auth/signup + /auth/login (src/vocky/rate_limit.py), default 20 per 900s, <=0 disables. promote-deferred was unavailable because the slice folder already existed. | `works/deferred/dropped/D5` |
