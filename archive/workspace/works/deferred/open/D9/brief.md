# Deferred: D9 Rate-limit the public capture surfaces (POST /api/feedback, /mcp) per credential, not per IP

## Context

## Why Deferred

Existing limiter is per-client-IP, which is wrong for server-to-server agent traffic: one deployment shares one IP and throttles as a single caller while a distributed abuser evades it; capture needs a per-credential bucket, and the module's single-worker invariant and trust model need re-reasoning first

## Trigger to Promote

before a second third-party agent product goes live, or on the first abuse/cost incident

## Notes

