# Phase P10: Accounts v2: orgs, org-level keys & default project

_Intent: see [intent.md](intent.md)._

## Objective

Restructure vocky's accounts plane into an explicit user -> org -> project model: the existing `tenants` row becomes the org in product-facing naming (no table rename), signup auto-provisions a `default` org and a `default` project, `projects` gains UNIQUE(tenant_id, name) plus get-or-create-by-name, and credentials become mintable at org level (`project_credentials.tenant_id` NOT NULL, `project_id` nullable) so one `vk_` key works across every project in the org — while today's project-bound keys keep their exact current semantics. Org creation beyond the default, member invites, and roles stay out of scope (deferred).

## Context

## Decomposition

_Slice breakdown and rationale — filled by the `P10.DECOMP` slice._

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeds this, and each slice appends when it finishes._

## Constraints

## Open Questions

-
