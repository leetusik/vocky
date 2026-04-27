# Backlog

## Status Model

- Phase: `planned`, `in_progress`, `in_review`, `blocked`, `done`
- Slice: `todo`, `in_progress`, `in_review`, `changes_requested`, `done`

## Usage Rules

- Every newly created phase starts with only `decompose phase` and `phase review`.
- Phase-level notes are allowed and encouraged; they do not count as slices.
- Do not pre-seed phase-specific middle slices in a newly created backlog.
- Add phase-specific middle slices only from the dedicated `decompose phase` slice.
- Keep `phase review` open until the phase passes review.
- If review fails, add dedicated fix slices and rerun review.
- Keep this file limited to actively scheduled phases and slices.
- This file schedules backlog-driven phases and slices only; unrelated standalone requests do not need phase, slice, or work-item entries.
- Move intentionally deferred work into `works/deferred.md` instead of leaving it in the active backlog.
- Link active work items from `works/current/`.
- If every documented phase is `done` and every documented slice is `done`, run `scripts/rotate_backlog.sh` before starting new backlog-scheduled work.
- `scripts/rotate_backlog.sh` archives the active `works/backlog.md` file to `works/archives/backlogs/<timestamp>_backlog.md` and replaces it from `works/templates/backlog.md`.
- If the next request is standalone, completed-backlog rotation is housekeeping only and does not create a phase or slice for that request.
- Use stable phase IDs such as `P1`.
- Use stable slice IDs such as `P1.DECOMP`, `P1.S1`, `P1.F1`, and `P1.REVIEW`.
- Prefix each slice with `[ ]` until it is done, then switch it to `[x]`.
- Treat the checkbox as a visual summary only. The `Status` field remains authoritative.

## Active Phases

### Phase P1: Self-hosted Web UI foundation

- Phase ID: `P1`
- Objective: Establish the integrated browser UI surface, routing, auth model, navigation shell, and reference-doc direction for self-hosted operators.
- Status: done
- Review outcome: passed
- Notes: Serve the first Web UI from the existing Starlette app under an admin-oriented path such as `/admin`, while preserving `/mcp`, `/api/*`, and `/admin/api/*`. This phase should update product and architecture docs to move dashboard UI out of current non-goals and clarify that the UI is for self-hosted operators, not SaaS tenants.
- Work items:
  - `works/archives/work_items/20260427_1114_decompose_web_ui_foundation` (`P1.DECOMP`)
  - `works/archives/work_items/20260427_1120_lock_web_ui_scope_and_docs_direction` (`P1.S1`)
  - `works/archives/work_items/20260427_1123_add_admin_web_ui_route_and_static_assets` (`P1.S2`)
  - `works/archives/work_items/20260427_1125_build_operator_navigation_shell_and_token_client` (`P1.S3`)
  - `works/archives/work_items/20260427_1130_phase_review_web_ui_foundation` (`P1.REVIEW`)
- Slices:
  - [x] Slice ID: `P1.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260427_1114_decompose_web_ui_foundation` | Notes: Added implementation slices for Web UI scope/docs direction, Admin UI route/static serving, and the operator navigation/token client.
  - [x] Slice ID: `P1.S1` | Name: `lock Web UI scope and docs direction` | Status: done | Work item: `works/archives/work_items/20260427_1120_lock_web_ui_scope_and_docs_direction` | Notes: Updated product, architecture, and README wording for the self-hosted operator Admin Web UI foundation and Admin REST data boundary.
  - [x] Slice ID: `P1.S2` | Name: `add Admin Web UI route and static assets` | Status: done | Work item: `works/archives/work_items/20260427_1123_add_admin_web_ui_route_and_static_assets` | Notes: Added packaged `/admin` HTML and `/admin/assets/*` routes before the MCP mount while preserving Admin REST, public REST, and MCP route behavior.
  - [x] Slice ID: `P1.S3` | Name: `build operator navigation shell and token client` | Status: done | Work item: `works/archives/work_items/20260427_1125_build_operator_navigation_shell_and_token_client` | Notes: Built the first Admin Web UI operator shell with Dashboard, Feedback, and Docs views plus a session-stored Admin bearer token client for `/admin/api/*`.
  - [x] Slice ID: `P1.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260427_1130_phase_review_web_ui_foundation` | Notes: Review passed for route safety, auth behavior, docs consistency, package resource serving, and UI baseline. No fix slices were needed.

### Phase P2: In-app operator documentation

- Phase ID: `P2`
- Objective: Add Web UI documentation pages for MCP tools, REST capture, Admin REST, auth tokens, local self-hosting, and public custom-domain setup.
- Status: done
- Review outcome: passed
- Notes: Keep the documentation operator-focused and maintainable. Prefer content sourced from durable docs or small structured documentation modules rather than duplicated long-form strings spread through UI code.
- Work items:
  - `works/archives/work_items/20260427_1151_decompose_in_app_operator_documentation` (`P2.DECOMP`)
  - `works/archives/work_items/20260427_1235_build_docs_content_framework` (`P2.S1`)
  - `works/archives/work_items/20260427_1239_add_api_and_auth_reference_pages` (`P2.S2`)
  - `works/archives/work_items/20260427_1241_add_self_hosting_and_public_domain_guides` (`P2.S3`)
  - `works/archives/work_items/20260427_1244_review_in_app_operator_documentation` (`P2.REVIEW`)
  - `works/archives/work_items/20260427_1246_remove_tenant_wording_from_ui_docs` (`P2.F1`)
  - `works/archives/work_items/20260427_1247_review_in_app_operator_documentation_rerun` (`P2.REVIEW`)
- Slices:
  - [x] Slice ID: `P2.DECOMP` | Name: `decompose phase` | Status: done | Work item: `works/archives/work_items/20260427_1151_decompose_in_app_operator_documentation` | Notes: Added implementation slices for the Docs content framework, API/auth reference pages, and self-hosting/public-domain guides.
  - [x] Slice ID: `P2.S1` | Name: `build Docs content framework` | Status: done | Work item: `works/archives/work_items/20260427_1235_build_docs_content_framework` | Notes: Added packaged Docs JSON content, `/admin/assets/docs.json`, DOM-based Docs rendering, responsive Docs layout styling, and static route/auth coverage.
  - [x] Slice ID: `P2.S2` | Name: `add API and auth reference pages` | Status: done | Work item: `works/archives/work_items/20260427_1239_add_api_and_auth_reference_pages` | Notes: Added in-app MCP tools, REST capture, Admin REST, status expectations, and bearer-token reference topics sourced from durable docs.
  - [x] Slice ID: `P2.S3` | Name: `add self-hosting and public-domain guides` | Status: done | Work item: `works/archives/work_items/20260427_1241_add_self_hosting_and_public_domain_guides` | Notes: Added local self-hosting and public custom-domain guide topics plus README, product, and architecture status updates for in-app operator docs.
  - [x] Slice ID: `P2.F1` | Name: `remove tenant wording from UI docs` | Status: done | Work item: `works/archives/work_items/20260427_1246_remove_tenant_wording_from_ui_docs` | Notes: Replaced `single-tenant` wording in the in-app Docs payload and confirmed Admin UI assets have no tenant/account/billing/organization matches.
  - [x] Slice ID: `P2.REVIEW` | Name: `phase review` | Status: done | Work item: `works/archives/work_items/20260427_1247_review_in_app_operator_documentation_rerun` | Notes: Review passed after `P2.F1`; route/auth boundaries, packaged docs asset behavior, content coverage, wheel packaging, and focused/full tests passed.

### Phase P3: Dashboard metrics

- Phase ID: `P3`
- Objective: Add dashboard metrics and trend views for feedback volume, likes, dislikes, unrated feedback, recent activity, and filterable time windows.
- Status: planned
- Review outcome: pending
- Notes: Reuse existing Admin REST data where practical. Add a minimal Admin REST metrics endpoint only if the UI cannot efficiently derive the needed dashboard state from existing list and summary contracts.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P3.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P3.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

### Phase P4: Feedback review and management

- Phase ID: `P4`
- Objective: Build the feedback review workflow with list, filtering, detail, tag/comment/channel editing, feedback value editing, and delete flows.
- Status: planned
- Review outcome: pending
- Notes: Use the existing Admin REST list, detail, patch, and delete contracts as the backing API. Keep the experience single-tenant and operator-focused, with no SaaS account, organization, billing, or tenant-selection concepts.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P4.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P4.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

### Phase P5: Self-hosted packaging and polish

- Phase ID: `P5`
- Objective: Make the Web UI reliable in Compose and local workflows, public custom-domain deployments, docs, tests, and release-facing README messaging.
- Status: planned
- Review outcome: pending
- Notes: Preserve the self-hosted default operational model. Verification should include UI route behavior, Admin auth behavior, Compose/local usability, public custom-domain guidance, and updated README messaging.
- Work items:
  - None yet
- Slices:
  - [ ] Slice ID: `P5.DECOMP` | Name: `decompose phase` | Status: todo | Work item: none | Notes: Break this phase into concrete middle slices before implementation starts.
  - [ ] Slice ID: `P5.REVIEW` | Name: `phase review` | Status: todo | Work item: none | Notes: Review the phase, add fix slices if needed, and rerun until it passes.

## Archive Notes

- Archive completed backlog snapshots under `works/archives/backlogs/`.
- Archive completed work-item folders under `works/archives/work_items/`.
- Fresh backlog contents come from `works/templates/backlog.md`.
