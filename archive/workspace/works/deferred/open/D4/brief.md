# Deferred: D4 Project-scope the end-user attachment download endpoint

## Context

## Why Deferred

GET /api/feedback/{id}/attachments/{aid} stays user_id+source_product-scoped, not project-scoped like the S1-tightened GET /api/feedback self-read (D-P3-6). UUID-gated and non-blocking, but a small isolation asymmetry worth closing for consistency.

## Trigger to Promote

operator promotes, or the next time the /api/* attachment surface is touched

## Notes

