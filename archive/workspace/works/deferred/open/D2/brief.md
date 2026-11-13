# Deferred: D2 Scope end-user feedback read to a public-safe field subset

## Context

## Why Deferred

End-user `GET /api/feedback` echoes the full internal record (including operator-set `attributes`, `source_metadata`, and other admin-shaped fields). This is intentional and in scope for the P1 MVP, but a product owner may later want a narrower public projection that hides operator-only fields from end users.

## Trigger to Promote

user promotes, or revisit alongside P2 attachment exposure

## Notes

- Flagged as a non-blocking note by the P1.REVIEW phase-reviewer audit.
- Touch points: `serialize_user_feedback_record` and `list_user_feedback` in `src/vocky/api.py`; contract docs in `docs/current/api.md` ("End-User Feedback Read REST API").
