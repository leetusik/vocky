# Action Feedback Integration

This guide describes how an agent product can integrate Vocky for explicit user feedback actions. It is intentionally generic: use it for local, private-network, or public self-hosted Vocky deployments.

## Choose A Capture Surface

Use MCP when the integration already runs inside an agent workflow or wants to call Vocky's MCP read tools. Use REST when a normal server-side web or product backend needs to forward like/dislike clicks without becoming an MCP client.

Both capture surfaces use the same payload shape and asynchronous queue. Successful capture means Vocky accepted the job for background persistence; the record becomes queryable after the worker writes it to PostgreSQL.

## Capture Explicit Actions

Submit one capture request when a user explicitly gives feedback, such as clicking like or dislike. Vocky does not need to receive every conversation turn as feedback.

Recommended payload fields:

- `message`: concise human-readable feedback summary displayed in Vocky
- `source.product`: stable product or app name
- `source.integration`: client integration name, such as `web-chat`
- `feedback_value`: `1` for like, `2` for dislike
- `comment`: optional user comment; recommended for dislikes when available
- `channel`: user-facing channel, such as `web`, `mobile`, or `support`
- `conversation_id`: stable caller-side conversation or thread ID when available
- `session_id`: optional caller-side runtime, browser, or user-session ID
- `target_type`: optional reviewed target category: `message`, `conversation`, or `surface`
- `target_id`: optional stable ID for the exact reviewed message, conversation, or surface
- `target_role`: optional role for message targets: `user`, `assistant`, `system`, or `tool`
- `target_text`: optional snapshot of the exact reviewed message or surface text
- `event_at`: user action timestamp with timezone
- `messages`: JSON array of surrounding conversation messages for review context
- `used_context`: JSON array of context or retrieval results used by the agent
- `tags`, `source_metadata`, and `attributes`: optional caller-provided metadata

Target fields are optional. Existing integrations can omit them, but integrations with message-level feedback should send them so reviewers do not have to infer which message the user judged.

Example:

```json
{
  "message": "Assistant answer was helpful for CSV export",
  "source": {"product": "my-agent", "integration": "web-chat"},
  "feedback_value": 1,
  "comment": "This fixed the issue",
  "channel": "web",
  "conversation_id": "conv_123",
  "session_id": "sess_456",
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

MCP clients send this object as the `capture_feedback` tool input. REST clients send it to `POST /api/feedback`:

```sh
curl -X POST "https://vocky.example.com/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <VOCKY_API_AUTH_TOKEN>" \
  -d '{
    "message": "Assistant answer was helpful for CSV export",
    "source": {"product": "my-agent", "integration": "web-chat"},
    "feedback_value": 1,
    "comment": "This fixed the issue",
    "channel": "web",
    "conversation_id": "conv_123",
    "session_id": "sess_456",
    "target_type": "message",
    "target_id": "msg_assistant_789",
    "target_role": "assistant",
    "target_text": "Use the export menu and choose CSV.",
    "event_at": "2026-04-24T09:30:00Z",
    "tags": ["export"]
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
- `channel`
- `tag`
- `start_ingested_at` and `end_ingested_at`
- `limit` and `cursor`

The response contains `conversations`, each with the stored feedback message, optional comment, target fields, source identifiers, tags, `messages`, `used_context`, metadata, and timestamps. Use these records as few-shot examples or style/context hints inside the caller's agent workflow.

Disliked conversations are stored for review and future learning workflows, but `list_liked_conversations` does not return them.

## Human Review Boundary

MCP tools are optimized for agent workflows, and `/api/feedback` is capture-only for server-to-server ingestion. Human operators and dashboards should use the dedicated Admin REST API endpoints, not the liked-only MCP few-shot tool or public capture endpoint. When `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`.
