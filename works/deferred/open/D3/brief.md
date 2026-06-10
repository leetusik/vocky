# Deferred: D3 Garbage-collect never-linked attachment uploads

## Context

## Why Deferred

The upload-first async-link protocol lets an attachment be uploaded and stored before (or without) the capture that references it. Attachments whose capture never arrives, or that reference only a subset of uploaded ids, stay `feedback_id IS NULL` with their files on disk indefinitely — unbounded storage growth and stale PII. A periodic sweeper that deletes orphan rows + files (`feedback_id IS NULL AND created_at < now() - INTERVAL`) is the fix, but no scheduler exists in the repo yet and MVP volume is low.

## Trigger to Promote

user promotes, or the first cleanup / scale / PII-retention need

## Notes

- P2 keeps the schema sweep-ready: `feedback_attachments.created_at` plus a `created_at` index (added in `P2.S2`).
- Deleting feedback already deletes its attachment files (`P2.S5`), so the only residue this job targets is never-linked uploads.
- A scheduling mechanism (cron, periodic worker task, or admin-triggered endpoint) must be chosen when this is promoted.
