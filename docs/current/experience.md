---
doc_id: experience
version: v0002
created_at: 2026-07-15T16:35:55+09:00
source: P1.REVIEW
summary: REST-only capture flow; remove MCP capture-surface choice and liked-conversation MCP tool
previous: v0001_bootstrap
---

# Action Feedback Integration

This guide describes how a product can integrate Vocky for explicit human-triggered user feedback actions over REST. It is intentionally generic: use it for local, private-network, or public self-hosted Vocky deployments.

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
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>" \
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

When `VOCKY_API_AUTH_TOKEN` is unset in a trusted local or private deployment, omit the bearer header. Public deployments should set it before exposing `/api/*`.

## Read Back A User's Own Feedback

After your backend has authenticated a user, you can render that user's own feedback with the scoped end-user read. Call `GET /api/feedback` with the required `user_id` and `source_product` (the `source.product` you sent at capture); Vocky returns only that user's own records, newest-first, together with operator comments and image attachment links.

```sh
curl "https://vocky.example.com/api/feedback?user_id=user_456&source_product=marketing-site" \
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>"
```

Optional filters (`feedback_value`, `channel`, `target_type`, `trigger_type`, `source_integration`, `conversation_id`, `session_id`, `tag`, `start_ingested_at`, `end_ingested_at`, `limit`, and `cursor`) are AND-combined with the required `user_id` + `source_product` scope, so the read never returns another user's data. Operator comments are surfaced read-only as one-way operator-to-user visibility; there are no end-user replies. Broad review, query, summary, and management stay on Admin REST.

## Human Review Boundary

Public REST is capture plus a single scoped end-user read: `POST /api/feedback` ingests feedback and `GET /api/feedback` returns one user's own records plus operator comments. Human operators and dashboards should use the dedicated Admin REST API endpoints, not the public capture or scoped-read endpoints. When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`.
