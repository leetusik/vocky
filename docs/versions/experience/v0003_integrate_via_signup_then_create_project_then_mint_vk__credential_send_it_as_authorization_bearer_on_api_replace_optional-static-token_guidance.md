---
doc_id: experience
version: v0003
created_at: 2026-07-16T14:21:33+09:00
source: P2.REVIEW
summary: Integrate via signup then create project then mint vk_ credential; send it as Authorization: Bearer on /api/*; replace optional-static-token guidance
previous: v0002_rest-only_capture_flow_remove_mcp_capture-surface_choice_and_liked-conversation_mcp_tool
---

# Action Feedback Integration

This guide describes how a product can integrate Vocky for explicit human-triggered user feedback actions over REST.

## Onboarding: Get a Project Credential

`/api/*` ingestion is authenticated by a **per-project credential** — there is no unauthenticated or shared-token path (the old optional `VOCKY_API_AUTH_TOKEN` is retired). Before capturing feedback, mint a key once:

1. **Sign up** (or log in) for a Vocky account. You get a session token and a tenant (workspace):

   ```sh
   curl -X POST "https://vocky.example.com/auth/signup" \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","password":"a-strong-password"}'
   # -> 201 { "token": "<session-token>", "user": {...}, "tenant": {...} }
   ```

   (Already have an account? `POST /auth/login` with the same body returns a fresh `token` and your `tenants`.)

2. **Create a project** with the session token:

   ```sh
   curl -X POST "https://vocky.example.com/app/projects" \
     -H "Authorization: Bearer <session-token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"marketing-site"}'
   # -> 201 { "project": { "id": "<project-id>", ... } }
   ```

3. **Mint a project credential** for that project:

   ```sh
   curl -X POST "https://vocky.example.com/app/projects/<project-id>/credentials" \
     -H "Authorization: Bearer <session-token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"web-backend"}'
   # -> 201 { "credential": {...}, "key": "vk_..." }
   ```

   The `vk_…` **`key` is shown exactly once** — store it as a secret in your product backend. Vocky keeps only a hash and cannot show it again. You can list credentials (metadata only) with `GET /app/projects/<project-id>/credentials` and revoke one with `DELETE /app/projects/<project-id>/credentials/<credential-id>` (a revoked key stops working immediately).

Your product backend then sends this `vk_…` key as `Authorization: Bearer` on every `/api/*` request below. Keep the session token for account/project management; keep the project key for ingestion.

## Capture Over REST

Use REST capture from a trusted server-side web or product backend when a real user explicitly triggers a feedback action. REST is the ingestion path for page feedback, widget feedback, surveys, ratings, and UI like/dislike controls; capture stays a deliberate server-to-server product action rather than a browser-direct call.

`target_type` is the review discriminator: use `message` for a specific message, `conversation` for a whole thread, and `surface` for a concrete page, widget, screen, or other non-message product UI. Older captures can omit `target_type`; those records remain visible in unfiltered review lists and are excluded only when an exact `target_type` filter is provided. Successful capture means Vocky accepted the job for background persistence; the record becomes queryable after the worker writes it to PostgreSQL.

## Capture Explicit Actions

Submit one capture request when a user explicitly gives feedback, such as clicking like or dislike. Vocky does not need to receive every interaction as feedback.

Recommended payload fields:

- `message`: concise human-readable feedback summary displayed in Vocky
- `source.product`: stable product or app name
- `source.integration`: client integration name, such as `web-chat`
- `feedback_value`: optional; `1` for like, `2` for dislike
- `comment`: optional user comment; recommended for dislikes when available
- `channel`: optional nullable review category; omit it by default, or set `web`, `mobile`, or `support` when the integration can assign one
- `conversation_id`: stable caller-side conversation or thread ID when available
- `session_id`: optional caller-side runtime, browser, or user-session ID
- `user_id`: optional caller-owned product user or account-member ID; use this for stable product identity and keep `session_id` for runtime/session correlation
- `trigger_type`: optional trigger category: `like`, `dislike`, `comment`, `rating`, `survey`, `manual`, or `other`
- `trigger_message`: optional button text, action label, survey question, prompt copy, or workflow description that caused capture
- `trigger_metadata`: optional object for trigger-specific context such as control ID, rating scale, selected option, experiment ID, or redacted runtime details
- `target_type`: optional reviewed target category: `message`, `conversation`, or `surface`
- `target_id`: optional stable ID for the exact reviewed message, conversation, or surface
- `target_role`: optional role for message targets: `user`, `assistant`, `system`, or `tool`
- `target_text`: optional snapshot of the exact reviewed message or surface text
- `event_at`: user action timestamp with timezone
- `messages`: JSON array of surrounding conversation messages for review context
- `used_context`: JSON array of context or retrieval results used by the agent
- `tags`, `source_metadata`, and `attributes`: optional caller-provided metadata; REST product integrations can use these for URL, page, widget, account, locale, rollout, or backend context

Trigger fields describe why capture happened. Target fields describe what was reviewed. Existing integrations can omit both groups, but integrations with message-level feedback should send `target_type: "message"` plus the exact message context so reviewers do not have to infer which message the user judged. REST integrations with product-surface feedback should use `target_type: "surface"` when the exact page, widget, screen, or feature is known.

Use `used_context` for review-safe process context only: retrieved snippets, tool traces, prompt summaries, policy summaries, or redacted execution metadata. Do not send raw hidden chain-of-thought or private model reasoning.

Channel categories are intentionally narrow in the MVP. Blank channel values normalize to `null`, non-null capture values outside `web`, `mobile`, and `support` are rejected, and no default channel is inferred.

Message-feedback capture payload example:

```json
{
  "message": "Assistant answer was helpful for CSV export",
  "source": {"product": "my-agent", "integration": "web-chat"},
  "feedback_value": 1,
  "comment": "This fixed the issue",
  "channel": "web",
  "conversation_id": "conv_123",
  "session_id": "sess_456",
  "user_id": "user_123",
  "trigger_type": "like",
  "trigger_message": "Assistant response thumbs-up",
  "trigger_metadata": {"control_id": "msg_assistant_789_like"},
  "target_type": "message",
  "target_id": "msg_assistant_789",
  "target_role": "assistant",
  "target_text": "Use the export menu and choose CSV.",
  "event_at": "2026-04-24T09:30:00Z",
  "messages": [
    {"role": "user", "content": "Can I export this as CSV?"},
    {"role": "assistant", "content": "Use the export menu and choose CSV."}
  ],
  "used_context": [
    {"source": "help-center", "snippet": "CSV export is available from the export menu."}
  ],
  "tags": ["export"],
  "source_metadata": {"ui_surface": "conversation-toolbar"},
  "attributes": {"plan": "team"}
}
```

Successful capture means Vocky accepted the job for background persistence. The record becomes queryable after the worker writes it to PostgreSQL.

Send explicit website or product UI feedback as the JSON body of `POST /api/feedback`:

```sh
curl -X POST "https://vocky.example.com/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer vk_<your-project-key>" \
  -d '{
    "message": "Pricing page feedback button was hard to find",
    "source": {"product": "marketing-site", "integration": "web-backend"},
    "comment": "I wanted to send feedback but did not notice the button",
    "channel": "web",
    "session_id": "sess_456",
    "user_id": "user_456",
    "trigger_type": "comment",
    "trigger_message": "Pricing page feedback form",
    "trigger_metadata": {"form_id": "pricing-feedback", "placement": "footer"},
    "target_type": "surface",
    "target_id": "pricing-page-feedback-button",
    "target_text": "Feedback",
    "event_at": "2026-04-24T09:30:00Z",
    "tags": ["website", "pricing"],
    "source_metadata": {"path": "/pricing", "referrer": "/"},
    "attributes": {"plan": "team", "locale": "en-US"}
  }'
```

Every `/api/*` request must carry a valid, non-revoked project key as `Authorization: Bearer vk_…` — there is no unauthenticated path. A missing, malformed, unknown, or revoked key returns `401 Unauthorized`.

## Read Back A User's Own Feedback

After your backend has authenticated a user, you can render that user's own feedback with the scoped end-user read. Call `GET /api/feedback` with the required `user_id` and `source_product` (the `source.product` you sent at capture); Vocky returns only that user's own records, newest-first, together with operator comments and image attachment links.

```sh
curl "https://vocky.example.com/api/feedback?user_id=user_456&source_product=marketing-site" \
  -H "Authorization: Bearer vk_<your-project-key>"
```

Optional filters (`feedback_value`, `channel`, `target_type`, `trigger_type`, `source_integration`, `conversation_id`, `session_id`, `tag`, `start_ingested_at`, `end_ingested_at`, `limit`, and `cursor`) are AND-combined with the required `user_id` + `source_product` scope, so the read never returns another user's data. Operator comments are surfaced read-only as one-way operator-to-user visibility; there are no end-user replies. Broad review, query, summary, and management stay on Admin REST.

## Human Review Boundary

Public REST is capture plus a single scoped end-user read: `POST /api/feedback` ingests feedback and `GET /api/feedback` returns one user's own records plus operator comments. Human operators and dashboards should use the dedicated Admin REST API endpoints, not the public capture or scoped-read endpoints. When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`.
