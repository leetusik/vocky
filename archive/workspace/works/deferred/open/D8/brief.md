# Deferred: D8 Retry or outbox for failed feedback alert emails

## Context

## Why Deferred

A failed alert is logged and lost — no retry, no queue, no operator-facing signal. Deliberate per P13 Decision 2 (containment had to be total) and fine while feedback is durably stored, but not once someone relies on the email as their notification channel.

## Trigger to Promote

A real alert observed missing/failed on the box, volume growth past single-owner scale, or any work adding a second notification channel or preferences surface.

## Notes

