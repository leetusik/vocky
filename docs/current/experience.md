---
doc_id: experience
version: v0005
created_at: 2026-07-16T18:48:22+09:00
source: P7.REVIEW
summary: P7: agents capture feedback via the write-only capture_feedback MCP tool at a project's /mcp endpoint, authed by the project's vk_ key
previous: v0004_p3_read_manage_your_project_s_feedback_via_vk__key_on_api_project_feedback_search_across_your_projects_via_session_on_app_feedback_korean_view_usage_via_app_usage
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

## Agent Capture Over MCP (write-only)

If your product is an **AI agent**, the agent can save feedback at its own judgement through Vocky's **write-only** MCP endpoint instead of (or alongside) REST. Point the agent's MCP client at the project's `/mcp` URL and authenticate with the **same `vk_` project key** — the whole endpoint (the `initialize` handshake included) requires it, so an unauthenticated agent cannot even open a session. The captured event feeds the same queue/store as REST and is scoped to the key's project automatically; there is no project parameter.

There is exactly **one** tool, `capture_feedback` (write-only — no read/query/liked-conversation tools). Its inputs are the same capture fields as REST **minus** `attachment_ids` (agents have no upload flow), with `source` as the only nested object.

LangChain-style client shape (send the key as a Bearer header):

```python
client = MultiServerMCPClient({
    "vocky": {
        "transport": "streamable_http",
        "url": "https://vocky.example.com/mcp",
        "headers": {"Authorization": "Bearer vk_<your-project-key>"},
    }
})
```

Then call the tool when the agent decides an interaction is worth capturing:

```json
{
  "message": "User was frustrated the export kept failing",
  "source": {"product": "my-agent", "integration": "agent-runtime"},
  "feedback_value": 2,
  "user_id": "user_123",
  "conversation_id": "conv_123",
  "trigger_type": "dislike",
  "target_type": "message",
  "target_role": "assistant",
  "target_text": "Try clicking Export again."
}
```

A successful call returns a capture receipt (`{ request_id, accepted_at, status: "accepted" }`) — the same async semantics as REST: the record becomes queryable after the worker persists it. Use MCP capture only when the agent runtime is intentionally deciding to capture voice-of-customer feedback; explicit human UI actions (like/dislike buttons, page/widget feedback) should still go through REST capture. A public `/mcp` deployment must also add its public host to `VOCKY_MCP_ALLOWED_HOSTS` (DNS-rebinding protection is on by default).

## Read Back A User's Own Feedback

After your backend has authenticated a user, you can render that user's own feedback with the scoped end-user read. Call `GET /api/feedback` with the required `user_id` and `source_product` (the `source.product` you sent at capture); Vocky returns only that user's own records, newest-first, together with operator comments and image attachment links.

```sh
curl "https://vocky.example.com/api/feedback?user_id=user_456&source_product=marketing-site" \
  -H "Authorization: Bearer vk_<your-project-key>"
```

Optional filters (`feedback_value`, `channel`, `target_type`, `trigger_type`, `source_integration`, `conversation_id`, `session_id`, `tag`, `start_ingested_at`, `end_ingested_at`, `limit`, and `cursor`) are AND-combined with the required `user_id` + `source_product` scope, so the read never returns another user's data. Operator comments are surfaced read-only as one-way operator-to-user visibility; there are no end-user replies. Broad review, query, summary, and management stay on Admin REST.

## Read & Manage Your Project's Feedback (Feedback API v2)

Your product's own admin panel / operator page can read **and manage** its project's feedback directly, using the **same `vk_` project key** it captures with — send it as `Authorization: Bearer vk_…` on `/api/project/feedback`. The project is implicit in the key; there is no project id in the path. Every id that belongs to another project answers `404` (never `403`).

```sh
# List this project's feedback (newest-first, keyset paging + the usual filters)
curl "https://vocky.example.com/api/project/feedback?feedback_value=2&limit=50" \
  -H "Authorization: Bearer vk_<your-project-key>"
# -> 200 { "records": [ ... ], "next_cursor"?: "..." }

# Get one record (+ operator comments + attachments)
curl "https://vocky.example.com/api/project/feedback/<feedback-id>" \
  -H "Authorization: Bearer vk_<your-project-key>"

# Edit review fields (feedback_value, comment, channel, tags, source_metadata, attributes)
curl -X PATCH "https://vocky.example.com/api/project/feedback/<feedback-id>" \
  -H "Authorization: Bearer vk_<your-project-key>" \
  -H "Content-Type: application/json" \
  -d '{"channel":"support","tags":["triaged"]}'

# Add an operator comment / delete a record
curl -X POST "https://vocky.example.com/api/project/feedback/<feedback-id>/comments" \
  -H "Authorization: Bearer vk_<your-project-key>" \
  -H "Content-Type: application/json" -d '{"body":"Following up","author":"support"}'
curl -X DELETE "https://vocky.example.com/api/project/feedback/<feedback-id>" \
  -H "Authorization: Bearer vk_<your-project-key>"   # -> 204
```

This is the external-admin-panel path: one `vk_` key does capture and full read+manage for its one project (no per-credential scopes in the MVP).

## Search Across All Your Projects (signed-in)

As a signed-in Vocky user you can read and **search** feedback across **all your projects** at once with your **session token** on `/app/feedback` (read + search only — management stays on the `vk_`-key `/api/project/feedback` above). Search (`?q=`) is a case-insensitive substring match and works in **Korean** as well as English — for example `?q=결제` matches both `결제 오류가 있어요` and the particle-attached `결제를 못 했습니다`.

```sh
# Search across every project you own; each record carries its project_id
curl "https://vocky.example.com/app/feedback?q=결제&limit=50" \
  -H "Authorization: Bearer <session-token>"

# Narrow to one of your projects, or add the usual filters
curl "https://vocky.example.com/app/feedback?q=export&project_id=<project-id>&feedback_value=1" \
  -H "Authorization: Bearer <session-token>"
```

Feedback outside your tenant answers `404`; a `?project_id` you do not own also answers `404`.

## View Usage

Check derived capture volume and credential last-used (operational visibility — no billing or metering). With your session token, `GET /app/usage` reports your whole-tenant volume plus a project list, and `GET /app/projects/{project_id}/usage` drills into one project and lists its credentials (with each key's `last_used_at`). A project can also read its own usage with its `vk_` key at `GET /api/project/usage`. The window defaults to the last 30 days when you pass no bounds.

```sh
curl "https://vocky.example.com/app/usage" -H "Authorization: Bearer <session-token>"
curl "https://vocky.example.com/api/project/usage" -H "Authorization: Bearer vk_<your-project-key>"
```

## Human Review Boundary

Feedback review and management are now first-class but always scoped and authenticated: a project's `vk_` key reads/manages its own project's feedback (`/api/project/feedback`); a signed-in user reads/searches across all their projects (`/app/feedback`); the end-user self-read (`GET /api/feedback`) returns one product user's own records. Self-hosted operators can also use the dedicated Admin REST API endpoints; when `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`. There is no unscoped or cross-tenant public query surface.
