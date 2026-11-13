---
doc_id: experience
version: v0008
created_at: 2026-07-18T11:15:51+09:00
source: P5.REVIEW
summary: P5: the vocky CLI onboarding journey — signup to project to key to capture to read from the terminal (headless --password-stdin, --base-url, VOCKY_CONFIG_DIR, generic-401, show-once key); docs/cli.md is the full reference
previous: v0007_p9_the_public_landing_now_serves_to_signed-out_visitors_signed-in_bounce_to_dashboard_preserved_as_a_real_product_surface
---

# Action Feedback Integration

This guide describes how a product can integrate Vocky for explicit human-triggered user feedback actions over REST.

There are two ways to do the account/project/credential setup below: **the web app** (point-and-click — see "The Web App" at the end of this guide) or the **REST calls** shown here. They are the same operations against the same API; use whichever suits you. Everything after setup — capture and reads — is API-only.

## Onboarding: Get a Project Credential

`/api/*` ingestion is authenticated by a **per-project credential** — there is no unauthenticated or shared-token path (the old optional `VOCKY_API_AUTH_TOKEN` is retired). Before capturing feedback, mint a key once (or do all three steps in the web app):

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

## The Web App

Everything above is the API. As of **P4** there is also a **web app** — Vocky's authenticated browser surface, and the replacement for the packaged self-hosted operator Admin Web UI. It does the account/project/credential work and the cross-project feedback reading **without curl**. (It runs locally today; the public deployment at `vocky.hi2vi.com` is P6.)

It is a signed-in **tenant owner's** surface, not an end-user one: you see your own tenant, your own projects, and your own feedback. Anything belonging to someone else answers "not found" — never "forbidden" — so you cannot even probe what exists.

### The landing page (`/`)

As of **P9**, the app's root `/` is a **public marketing landing** for signed-out visitors, not a bare redirect. It explains what Vocky is — a server-to-server feedback layer where your backend sends explicit user reactions (likes, dislikes, comments) over a single `POST /api/feedback` call, and Vocky turns them into structured, Korean- and English-searchable signal — and how to start: create a project, mint a `vk_` key (shown once), send feedback from your backend, then search and review it. Its calls to action are **Start free** (`/signup`) and **Read the docs** (the real `github.com/leetusik/vocky` repo). If you are already signed in, visiting `/` **bounces you straight to `/dashboard`** — the landing is the signed-out front door only, and no session token is ever exposed to it.

### Sign up, sign in, sign out

Sign up with an email and password and you land straight in the app — signup provisions your account, your tenant (workspace, auto-named from your email), and your session in one step. Logging in later takes you to the same place. Wrong password and unknown email give the **identical** error, so nobody can use the login form to discover which emails are registered.

Your session lives in a secure cookie the app sets for itself; the browser never holds your Vocky token, and no page ever renders it. Signing out revokes the session at Vocky and clears the cookie. Visiting any signed-in page while signed out simply bounces you to the login form; a session revoked out from under you does the same, without any redirect loop.

### The shell

Every signed-in page shares one layout: a topbar (your workspace and email, and the sign-out button) and a left rail with **Dashboard** and **Feedback**. The rail collapses to a horizontal strip on narrow screens. There is no dark-mode toggle.

### The tenant dashboard (`/dashboard`)

Your post-login home, and the whole-tenant view:

- **Usage totals** for the window — total records, likes, dislikes, unrated. The window is the last 30 days unless you say otherwise. This is operational visibility, not billing; Vocky has no metering.
- **A daily trend chart** of capture volume across the window, zero-filled so quiet days read as zero rather than vanishing. A tenant that has never captured anything shows an explicit empty state instead of an empty chart.
- **Your projects**, with a create-project form. A new project appears in the list immediately. Names are not unique — two projects may share a name and remain distinct records.
- Each project name **links into its detail page**.

### Project detail (`/projects/{id}`)

The per-project drill-down:

- **Project info** and that project's own usage totals + trend (the same shapes as the dashboard, scoped to one project).
- **Credentials** — the project's `vk_` keys, each with its 12-character display prefix, its status (Active / Revoked), and its **last-used** time, so you can tell a live key from a forgotten one.
- **Mint a key** (optionally naming it). **The plaintext `vk_…` key is shown exactly once**, right after minting, with an explicit warning that this is the only time you will ever see it. Copy it into your product backend then. Reload the page and it is gone for good — only the prefix stub remains, because Vocky stores only a hash and genuinely cannot show it again.
- **Revoke a key** behind a confirm step. A revoked key stops working immediately and stays listed as Revoked (so the history is auditable) rather than disappearing.

### Feedback: search and read (`/feedback`)

The cross-project read surface — everything your projects have captured, newest-first, in one place:

- **Search (`?q=`) works in Korean.** It is a substring match, not a tokenizer, so `결제` finds both `결제 오류가 있어요` and the 조사-attached `결제를 못 했습니다` — and it matches the operator **comment**, not just the message. English works the same way, case-insensitively.
- **Filter** by project and by feedback value (liked / disliked / unrated); submitting a new query resets you to the first page. Rows show the **project name**, not a raw id.
- **Page forward** through results. Each page is its own URL, so your browser's Back button is Previous. Filters stay applied across pages — page 2 of a search is still that search.
- **Distinct empty states**: "no projects yet" is not the same message as "no feedback matches these filters."
- **Open a record** for the full detail: message, the user's comment, project, integration, trigger, conversation/session/user ids, target text, tags, operator comments, and attachments. **Times are shown in UTC**, labeled as such.
- **Attachments download; they never render inline.** That is deliberate — attachment bytes are uploader-supplied, and displaying them in the page would be a security hole (see `security.md`).

**The web app is read + search only for feedback.** There is no editing, commenting, or deleting here: feedback **management** stays on the `vk_`-keyed `/api/project/feedback` above, for your product's own admin panel. The web app is where a human *finds* feedback across projects.

## The `vocky` CLI (P5)

As of **P5** there is a third front door alongside the web app and raw curl: a **`vocky` command-line client**. It is vocky's **agent-first onboarding path** — a user working inside Claude Code or Codex (or the coding agent acting on their behalf) can sign up, log in, set up credentials, and read feedback **entirely from the terminal, without ever visiting the website**. The CLI is a **pure client** of the same `/auth/*` + `/app/*` surfaces (it holds the session token; it never becomes a new backend capability). The full self-contained reference — every command, flag, and the equivalent raw HTTP — lives in the hand-written **`docs/cli.md`** (linked from the README); this section is the journey-level map.

### The onboarding journey as commands

The signup → project → key → capture → read spine maps one-to-one onto CLI commands (each mirrors the raw-HTTP step documented under "Onboarding" above):

```sh
# 1. Sign up (or `vocky login`) — provisions your account + workspace, stores the session
printf '%s' "$PASSWORD" | vocky signup --email you@example.com --password-stdin

# 2. Create a project
vocky projects create marketing-site           # -> Created project "marketing-site" (<project-id>).

# 3. Mint a per-project `vk_` key — shown once
vocky keys mint --project <project-id>          # prints the show-once warning, then the vk_… key

# 4. Your product backend captures with that vk_ key over /api/feedback (same as the REST path above)

# 5. Read and search what was captured, across all your projects
vocky feedback list
vocky feedback search 결제                       # Korean-safe substring search
vocky feedback show <feedback-id>               # full record + operator comments + attachments
```

The command groups mirror the API surfaces: `vocky signup|login|logout|whoami` over `/auth/*`; `vocky projects`, `vocky keys`, and `vocky usage` over the session-authed `/app/*` control plane; and the read-only `vocky feedback list|search|show` over `/app/feedback`. `list`/`search` print each record's **full feedback id** (the copy-pasteable handle `feedback show` consumes) and `projects list` prints the **full project id** (the `--project` / `projects show` handle), so the terminal-only `list → show` and `list → --project` journeys complete without dropping to raw HTTP. Feedback **management** (edit/delete/comment) is deliberately out of the CLI — it stays on the `vk_`-keyed `/api/project/feedback` surface.

### For coding agents (headless contract)

The CLI is built so an agent can drive the whole flow with no interactive prompts and no secret ever landing on a process argv:

- **`--password-stdin`** reads the password from one line of stdin, so signup/login never put the password on the command line.
- **`--base-url`** (or the `VOCKY_BASE_URL` env) points the CLI at any vocky instance; the default is `http://127.0.0.1:8000`.
- **`VOCKY_CONFIG_DIR`** overrides where the session store lives (XDG-aware, defaulting to `~/.config/vocky/`), so an agent can run an isolated, throwaway session per task.
- **Generic 401**: an expired or missing session surfaces a friendly `Not signed in — run \`vocky login\`.` rather than a raw HTTP error.
- **Show-once key**: `keys mint` prints the plaintext `vk_…` exactly once with an explicit "copy it now, it cannot be recovered" warning; it is never shown again.
- **Errors go to stderr, success to stdout, with non-zero exit codes** — so an agent can branch on outcome. An invalid feedback id, for example, prints a hint pointing at `vocky feedback list` and exits 1.

## Human Review Boundary

Feedback review and management are now first-class but always scoped and authenticated: a project's `vk_` key reads/manages its own project's feedback (`/api/project/feedback`); a signed-in user reads/searches across all their projects (`/app/feedback`, or the same thing point-and-click in the web app); the end-user self-read (`GET /api/feedback`) returns one product user's own records. Self-hosted operators can also use the dedicated Admin REST API endpoints; when `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`. There is no unscoped or cross-tenant public query surface.

The **web app** (P4) is the browser expression of the session-authed `/app/*` surface — it adds no capability of its own, and deliberately carries **no** feedback management (that stays on `/api/project/feedback`). The packaged same-origin Admin Web UI it replaces is superseded but still shipped; it is removed in P6.
