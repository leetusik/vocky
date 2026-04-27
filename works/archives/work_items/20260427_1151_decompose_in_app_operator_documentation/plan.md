# Plan

- Work item: works/current/20260427_1151_decompose_in_app_operator_documentation
- Created at: 20260427_1151
- Phase ID: P2
- Phase: In-app operator documentation
- Slice ID: P2.DECOMP
- Slice: decompose phase

## Goal

Decompose P2 into concrete middle slices for the in-app operator documentation phase before implementation starts.

## Scope

- In scope: Update `works/backlog.md` with P2 implementation slices, mark `P2.DECOMP` complete, and record this work item.
- Out of scope: Implementing Docs UI rendering, docs content modules, source changes, tests, or reference-doc edits in this slice.

## Context

- P2 should add Web UI documentation pages for MCP tools, REST capture, Admin REST, auth tokens, local self-hosting, and public custom-domain setup.
- The existing Admin Web UI already has a Docs navigation view and placeholder surfaces panel under `/admin`.
- Durable source material already exists in `docs/product.md`, `docs/architecture.md`, `docs/api.md`, `README.md`, and `docs/action-feedback-integration.md`.
- The phase note asks for operator-focused and maintainable content, preferably sourced from durable docs or small structured documentation modules rather than duplicated long-form strings spread through UI code.

## Milestones

1. Add middle slices for the Docs content framework, API/auth reference pages, and self-hosting/public-domain guides.
2. Mark P2 as `in_progress` and `P2.DECOMP` as `done`.
3. Link this work item in the P2 work-item list and `P2.DECOMP` slice row.

## Validation

- Manual review of `works/backlog.md` confirming the final P2 slice order is `P2.DECOMP`, `P2.S1`, `P2.S2`, `P2.S3`, and `P2.REVIEW`.
- Confirm this slice changes only backlog/work-item files.

## Risks / open questions

- Future content work should avoid managed-SaaS account, tenant, organization, billing, or tenant-selection concepts.
- Future UI work should preserve existing `/mcp`, `/api/*`, `/admin/api/*`, and `/admin` route behavior.

## Docs to update

- None in this slice. Later P2 implementation slices will update reference docs or README only if the in-app docs change durable product, architecture, or public contract truth.
