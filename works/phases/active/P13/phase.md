# Phase P13: Feedback email alerts over SMTP

_Intent: see [intent.md](intent.md)._

## Objective

When the worker persists a captured feedback event, send one plain-text email alert via SMTP to the account email of the owning org's owner (feedback -> project -> tenant -> owner member). SMTP transport is configured entirely from env (VOCKY_SMTP_*), reusing the SMTP account changple5 already uses in production; unconfigured SMTP means alerts are cleanly disabled, and a send failure is never allowed to duplicate or requeue an already-persisted feedback event. Recipient/preferences configurability is deliberately out of scope — this phase lands the default-on, owner-addressed alert only.

## Context

## Decomposition

_Slice breakdown and rationale — filled by the `P13.DECOMP` slice._

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

## Constraints

## Open Questions

-
