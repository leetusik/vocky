# Product

## Status

Vocky is pre-MVP. The first runnable self-hosted capture plus review service is implemented with MCP capture/read tools, server-to-server REST capture, liked-conversation retrieval, Admin REST, a self-hosted operator Admin Web UI with dashboard metrics, feedback review management, in-app documentation, and REST capture try-it, PostgreSQL persistence, Redis-backed queueing, a background worker, and Compose-first local verification. The contracts should still be treated as early-stage.

## Summary

Vocky is a feedback layer for agent products and the product surfaces around them. It aims to capture user feedback from agent conversations, websites, and product experiences, structure it into usable signals, and help teams understand what customers are asking for, praising, or struggling with.

## First MVP

The first MVP is intentionally narrow:

- Self-hosted and single-tenant
- MCP ingestion for agent-decided VoC capture in agent workflows and server-to-server REST ingestion for explicit product/UI-triggered website or product feedback
- Async capture that accepts quickly over MCP or REST and persists in the background
- Explicit user action feedback capture, including like/dislike values, optional comments, conversation context, and basic metadata
- MCP review/query tools for record retrieval, simple counts, trends, and liked-conversation retrieval
- Optional exact-target metadata for the message, conversation, or product surface being reviewed
- Dedicated Admin REST endpoints for human/operator review and management of stored feedback
- A self-hosted operator Admin Web UI that loads from the Vocky app, uses Admin REST as its protected data boundary, and includes dashboard metrics, feedback list/filter/detail/edit/delete workflows, in-app operator documentation, and an operator-only REST capture try-it flow
- Nullable channel category assignment for review workflows, using the built-in MVP categories `web`, `mobile`, and `support`
- PostgreSQL storage with Redis-backed background persistence

The MVP does not need automated classification, managed-cloud capabilities, or a production-grade analytics workspace.

## Target Users

- Teams building agent-based products
- Developers integrating feedback capture into agent workflows
- Product and operations teams reviewing customer voice from agent interactions

## Problem

- Agent conversations contain product feedback that usually gets buried in logs.
- Teams need structured feedback, not raw transcript noise.
- Feedback should be reviewable, trendable, and usable for prioritization.

## Goals

- Capture agent-decided VoC events through MCP and explicit product/UI-triggered feedback through server-to-server REST without making clients wait on persistence
- Store explicit user action feedback with enough summary text, exact target, surrounding context, comment, and metadata detail for later review
- Make stored feedback reviewable through a minimal query surface
- Surface simple counts and trends without building a full analytics product
- Provide a first browser-based operator entry point for self-hosted review and documentation workflows
- Keep the first release practical for community and self-hosted use
- Keep the self-hosted release path verifiable with local smoke checks, packaged Admin UI asset checks, and public custom-domain smoke checks when an external URL is configured

## Non-Goals for Now

- Automatic classification or taxonomy assignment
- A production-ready analytics suite
- Browser-direct unauthenticated ingestion paths
- Broad public REST review, query, summary, or management APIs. The only public read is a narrowly scoped end-user self-read (`GET /api/feedback`) that returns a single caller-identified user's own feedback plus operator comments, scoped by required `user_id` and `source_product`; all other review, query, summary, job-status, and management stays on MCP or Admin REST.
- Custom channel category management, deployment-configured channel lists, or automatic channel classification
- Multi-tenant managed-cloud architecture
- Enterprise-grade compliance or admin workflows
- SaaS account, organization, billing, or tenant-selection UI concepts
- Finalized public API commitments

## Product Direction

- Community and self-hosted usage are part of the base direction.
- The first MVP should optimize for self-hosted deployment before managed concerns.
- Self-hosted deployments may be local/private or publicly reachable behind an operator-managed custom domain, provided public MCP, REST capture, and Admin REST access are protected where exposed.
- The Admin Web UI is an operator surface for self-hosted deployments. It should stay same-origin with the app, use Admin REST for protected data, include practical dashboard metrics, feedback review management, operator documentation, and an operator-only REST capture try-it flow, and avoid managed-SaaS assumptions.
- The Admin Docs REST capture try-it flow should send a real same-origin `POST /api/feedback` request for operator verification. A successful try intentionally creates queued feedback, uses the separate `/api/*` bearer token when `VOCKY_API_AUTH_TOKEN` is configured, and must not imply a browser-direct unauthenticated product ingestion pattern.
- The default local workflow should stay loopback-first and Compose-first, while public custom-domain access should be operator-managed through an HTTPS reverse proxy such as Cloudflare Tunnel and verified separately from local checks.
- The capture path should acknowledge accepted work quickly and complete persistence asynchronously in the background.
- The MCP capture path should stay optimized for agent workflows where the agent or agent runtime decides that a user interaction is useful VoC, especially feedback on an exact message, conversation, or context-bearing agent response.
- The REST capture path should be the first-choice ingestion path for explicit product/UI-triggered feedback, such as like/dislike controls, page feedback, widgets, surveys, or other product-surface feedback, using the existing capture fields instead of REST-only aliases or a separate endpoint.
- The REST capture path remains capture-only, with one deliberate exception: a narrowly scoped end-user self-read (`GET /api/feedback`) that returns a single user's own feedback plus operator comments, scoped by required `user_id` and `source_product`. In-app try tooling may exercise capture, but broad review, query, summary, job-status, and management remain MCP or Admin REST concerns rather than new public REST endpoints.
- Operator comments are a first-class concept distinct from the end user's own `comment`: operators add and list them through Admin REST, and the scoped end-user read surfaces them read-only to the originating user as one-way operator-to-user visibility.
- End users can attach images (such as screenshots) to feedback. Images are uploaded synchronously to obtain an attachment id that the capture call references, and the worker links them to the feedback record after persist. Attachments appear in both the operator-review and scoped end-user-read responses and are served through authenticated downloads: an end user can download only their own attachments (scoped by `user_id` + `source_product`), while operators can download all attachments for the feedback they review. Allowed types and size are operator-configurable; the default is common raster image types up to a few megabytes.
- The initial high-signal capture path should focus on explicit user actions, such as like/dislike clicks and optional comments, rather than trying to infer feedback from every conversation turn.
- Optional caller-owned user identity and trigger context fields preserve who the product associates with the event and which action, control, survey, or manual workflow caused capture.
- Feedback capture should not assume that the latest message is the reviewed item. Callers should identify the exact reviewed message, conversation, or product surface when that information is available.
- Message, conversation, and non-message surface feedback should stay in the same canonical feedback store and be separated for review through `target_type`, not through split tables, renamed tools, or separate capture endpoints.
- `target_type` is an exact-match review filter for separating `message`, `conversation`, and `surface` feedback.
- `channel` should be a nullable review category, not open-ended free text. New captures and Admin edits should leave it unset by default unless the caller or operator explicitly selects one of the built-in MVP categories: `web`, `mobile`, or `support`.
- Existing stored records with older arbitrary channel text should remain reviewable and filterable, but new writes should not create new arbitrary channel values.
- A managed offering may exist later around convenience, operations, and richer workflows.
- The repo should stay honest about what is planned versus what is already implemented.

## Product Surface Roles

Vocky uses one canonical feedback store and one shared capture field set, but the public-facing surfaces have different jobs:

- MCP is for agent/runtime capture and MCP reads. `capture_feedback` is the agent-workflow ingestion path when an agent or agent runtime decides an interaction should be captured as VoC. MCP read tools serve agent, script, or operator review workflows that prefer MCP.
- Public REST is for trusted server-to-server product integrations: capture plus a single scoped end-user read. `POST /api/feedback` is the preferred path for explicit product-surface actions such as likes, dislikes, page feedback, widgets, or surveys, and `POST /api/feedback/attachments` uploads an image to reference from a capture call. `GET /api/feedback` returns one end user's own feedback (scoped by required `user_id` + `source_product`) together with operator comments and image attachments, and `GET /api/feedback/{feedback_id}/attachments/{attachment_id}` downloads one of the caller's own attachments under the same scope. It does not expose broad query, summary, job-status, or management endpoints.
- Admin REST is for human/operator review and management. `/admin/api/*` powers dashboards, list/detail inspection, review-field editing, metrics, and deletion over the same stored feedback records.

## Current Field Taxonomy

Current feedback fields are grouped by responsibility, not by transport. MCP capture and public REST capture use the same field set; Admin REST reviews and manages the stored record shape.

- Display and action fields: `message`, `feedback_value`, and `comment` describe the visible feedback record and explicit like/dislike/comment action.
- Source identity fields: `source.product` and `source.integration` identify the product and integration that sent the feedback. Stored records expose them as `source_product` and `source_integration`.
- Caller identity fields: `user_id` optionally identifies the caller-owned end user, account member, or product user associated with the feedback. It is distinct from `session_id`, which remains runtime, browser, or session correlation.
- Trigger fields: `trigger_type`, `trigger_message`, and `trigger_metadata` describe the user action, UI control, survey, manual workflow, or other product event that caused capture. They do not replace the primary feedback `message`, optional user `comment`, target fields, process context, or source metadata.
- Review category fields: `channel` and `tags` support operator filtering and review organization without changing the target of the feedback.
- Exact target fields: `target_type`, `target_id`, `target_role`, and `target_text` identify the reviewed message, conversation, or product surface when the caller knows it.
- Conversation and session context fields: `conversation_id`, `session_id`, and `messages` group feedback with surrounding runtime or conversation context.
- Agent and process context fields: `used_context` preserves context the agent used while generating the reviewed response.
- Metadata fields: `event_at`, `ingested_at`, `source_metadata`, `attributes`, and generated record identifiers preserve timing, source-specific details, product-specific dimensions, and storage identity.

## Terminology

- `VoC`: voice of customer
- `message`: the required human-readable feedback summary or display text. It is the text Vocky shows as the primary feedback record label, not an implicit pointer to the reviewed agent message.
- `comment`: the end user's own optional comment captured at feedback time. It is distinct from an operator comment.
- `operator comment`: an operator-authored note attached to a stored feedback event, kept in a separate store keyed by feedback id. Operators add and list operator comments through Admin REST; the scoped end-user read returns them read-only to the originating user. `author` is an optional caller-supplied operator label because Vocky has no native operator accounts.
- `conversation_id`: caller-provided conversation or thread identifier used to group feedback from the same conversation.
- `session_id`: optional caller-provided runtime, browser, or user-session identifier. It can help correlate repeated interactions without replacing `conversation_id`.
- `user_id`: optional caller-owned user or account-member identifier associated with the feedback event. Vocky treats it as an opaque string and does not infer authentication, tenancy, or identity semantics from it.
- `trigger_type`: optional category for the action or workflow that caused capture. Accepted P1 values are `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, and `other`.
- `trigger_message`: optional human-readable action label, prompt copy, button text, survey question, or event description that caused capture. It explains why capture happened; it is not the primary feedback `message` or the user's `comment`.
- `trigger_metadata`: optional structured object for trigger-specific context, such as rating scale, selected option, control id, experiment id, or redacted UI/runtime details.
- `channel`: optional nullable review category for where the feedback came from. The MVP built-in categories are `web`, `mobile`, and `support`; `null` means no channel category was assigned.
- `feedback target`: the exact reviewed item, when known. It may be a message, a whole conversation, or a non-message product surface.
- `target_type`: optional feedback target category. The MVP target categories are `message`, `conversation`, and `surface`; `null` means the caller did not identify an exact target category.
- `target_id`: optional stable caller-provided identifier for the target, such as a message id or UI surface id.
- `target_role`: optional role for message targets. The MVP roles are `user`, `assistant`, `system`, and `tool`.
- `target_text`: optional snapshot of the exact reviewed message or product surface text at capture time.
- `messages`: optional surrounding conversation context supplied by the caller. It is context for review, not the authoritative target by itself.
- `used_context`: optional context the agent used while generating the reviewed response, such as retrieved documents, snippets, or tool context.
- `surface feedback`: REST-captured explicit product/UI feedback about a page, widget, screen, or other non-message product surface. It should use `target_type="surface"` when the exact surface is known, plus optional `target_id`, `target_text`, `source_metadata`, and `attributes` for product-specific context.
- `phase`: a grouped unit of work in `works/backlog.md`
- `slice`: a concrete step inside a phase
- `work item`: a timestamped execution folder under `works/current/` or `works/archives/work_items/`
