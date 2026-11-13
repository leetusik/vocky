# Deferred: D6 Org management: additional orgs, member invites, roles

## Context

## Why Deferred

P10 makes the tenant row the org in product-facing naming and adds org-level keys, but keeps exactly one org per user. The schema already supports more: tenant_members exists with a role column, and only "owner" is ever written (src/vocky/accounts/service.py:117). What is missing is the UI/API — creating a second org, inviting a member, assigning a role, and an active-org selector (require_user silently picks tenants[0], src/vocky/accounts/auth.py:89-93, so a second org would be unreachable today). That is a distinct product surface with its own authorization design, deliberately out of P10's scope.

## Trigger to Promote

When a user needs more than one org, or when a second person must share an org (team/collaboration demand), or before any pricing tier is sold per-seat.

## Notes

