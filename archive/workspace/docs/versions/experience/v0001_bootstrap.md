---
doc_id: experience
version: v0001
created_at: 2026-06-10T13:51:20+09:00
source: bootstrap
summary: Initial experience doc
previous: null
---

# Action Feedback Integration

This guide describes how an agent product can integrate Vocky for explicit user feedback actions. It is intentionally generic: use it for local, private-network, or public self-hosted Vocky deployments.

## Choose A Capture Surface

Use MCP when an agent or agent runtime decides that a user interaction is useful voice-of-customer feedback. MCP is the right fit for agent-decided capture about exact messages, whole conversations, or context-bearing agent responses, especially when the same integration may call Vocky's MCP read tools.

Use REST when a trusted server-side web or product backend forwards an explicit user-triggered feedback action without becoming an MCP client. REST is the first-choice path for page feedback, widget feedback, surveys, product-surface feedback, and non-agent UI like/dislike controls.

Both capture surfaces use the same core field set and asynchronous queue, but their integration intent is different. `target_type` is the review discriminator across both surfaces: use `message` for a specific message, `conversation` for a whole thread, and `surface` for a concrete page, widget, screen, or other non-message product UI. Older captures can omit `target_type`; those records remain visible in unfiltered review lists and are excluded only when an exact `target_type` filter is provided. Successful capture means Vocky accepted the job for background persistence; the record becomes queryable after the worker writes it to PostgreSQL.

## Capture Explicit Actions

Submit one capture request when a user explicitly gives feedback, such as clicking like or dislike. Vocky does not need to receive every conversation turn as feedback.

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

MCP `capture_feedback` message-feedback example:

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

MCP clients send this object as the `capture_feedback` tool input. REST clients send explicit website or product UI feedback to `POST /api/feedback`:

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

## Retrieve Liked Conversations For Agents

Use the `list_liked_conversations` MCP tool when an AI agent needs examples of conversations users liked. This tool is intentionally narrow and returns only records with `feedback_value = 1`.

Useful filters:

- `source_product`
- `source_integration`
- `conversation_id`
- `session_id`
- `user_id`
- `trigger_type`
- `channel`
- `target_type`
- `tag`
- `start_ingested_at` and `end_ingested_at`
- `limit` and `cursor`

The response contains `conversations`, each with the stored feedback message, optional comment, `user_id`, trigger fields, target fields, source identifiers, tags, `messages`, `used_context`, metadata, and timestamps. Use these records as few-shot examples or style/context hints inside the caller's agent workflow.

Disliked conversations are stored for review and future learning workflows, but `list_liked_conversations` does not return them.

## Human Review Boundary

MCP tools are optimized for agent workflows, and `/api/feedback` is capture-only for server-to-server ingestion. Human operators and dashboards should use the dedicated Admin REST API endpoints, not the liked-only MCP few-shot tool or public capture endpoint. When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`.
