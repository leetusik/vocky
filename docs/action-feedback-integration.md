# Action Feedback Integration

This guide describes how an agent product can integrate Vocky for explicit user feedback actions. It is intentionally generic: use it for local, private-network, or public self-hosted Vocky deployments.

## Capture Explicit Actions

Call the `capture_feedback` MCP tool when a user explicitly gives feedback, such as clicking like or dislike. Vocky does not need to receive every conversation turn as feedback.

Recommended payload fields:

- `message`: concise feedback summary or the assistant message being judged
- `source.product`: stable product or app name
- `source.integration`: client integration name, such as `web-chat`
- `feedback_value`: `1` for like, `2` for dislike
- `comment`: optional user comment; recommended for dislikes when available
- `channel`: user-facing channel, such as `web`, `mobile`, or `support`
- `conversation_id` and `session_id`: stable caller-side IDs when available
- `event_at`: user action timestamp with timezone
- `messages`: JSON array of relevant conversation messages
- `used_context`: JSON array of context or retrieval results used by the agent
- `tags`, `source_metadata`, and `attributes`: optional caller-provided metadata

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

The response contains `conversations`, each with the stored feedback message, optional comment, source identifiers, tags, `messages`, `used_context`, metadata, and timestamps. Use these records as few-shot examples or style/context hints inside the caller's agent workflow.

Disliked conversations are stored for review and future learning workflows, but `list_liked_conversations` does not return them.

## Human Review Boundary

MCP tools are optimized for agent workflows. Human operators and dashboards should use dedicated Admin REST API endpoints once enabled, not the liked-only MCP few-shot tool.
