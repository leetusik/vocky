# Deferred: D5 Rate-limit the public /auth/* (open signup + password login)

## Context

## Why Deferred

vocky exposes /auth/signup + /auth/login publicly at vocky.hi2vi.com with no server-side limiter (knowledge ships an in-process per-IP limiter; vocky does not), and a limit_req_zone is forbidden at the shared edge (global-name footgun).

## Trigger to Promote

At/soon after go-live: add a Cloudflare rate-limiting rule for /auth/*, or an in-process per-IP limiter in src/vocky/auth_api.py.

## Notes

