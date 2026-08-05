---
doc_id: experience
version: v0013
created_at: 2026-08-05T15:39:32+09:00
source: P14.REVIEW
summary: P14: the public agent-capture contract - sentiment, note, and the recorded_by marker
previous: v0012_p12_the_hosted_install_line_is_live_not_a_promise_curl_bash_from_vocky.hi2vi.com_works_today
---

# Action Feedback Integration

This guide describes how a product can integrate Vocky for explicit human-triggered user feedback actions over REST.

> **Read this against a self-hosted Vocky.** There is no hosted vocky yet: `https://vocky.hi2vi.com` is not live (the production deploy kit exists but was never executed — bring-up is **P12**), so every base URL below is your own deployment. **P11 settled distribution: the install path is a `curl | bash` installer served from the site, not PyPI** — so today, before the site is deployed, the CLI still installs from a checkout of this repo, and the hosted one-liner becomes true the moment P12 brings the site up (the landing page and `install.sh` ship in the same deploy). See `operations.md`.

There are two ways to do the account/project/credential setup below: **the web app** (point-and-click — see "The Web App" at the end of this guide) or the **REST calls** shown here. They are the same operations against the same API; use whichever suits you. Everything after setup — capture and reads — is API-only.

## Onboarding: Get a Project Credential

`/api/*` ingestion is authenticated by a **`vk_` ingest credential** — there is no unauthenticated or shared-token path (the old optional `VOCKY_API_AUTH_TOKEN` is retired). As of **P10 this is two steps, not three**: signup already gives you a project.

1. **Sign up** (or log in) for a Vocky account. You get a session token, an **org**, **and a project named `"default"`** — you do not have to create one:

   ```sh
   curl -X POST "https://vocky.example.com/auth/signup" \
     -H "Content-Type: application/json" \
     -d '{"email":"you@example.com","password":"a-strong-password"}'
   # -> 201 { "token": "<session-token>", "user": {...}, "tenant": {...},
   #          "project": { "id": "<project-id>", "name": "default", ... } }
   ```

   (Already have an account? `POST /auth/login` with the same body returns a fresh `token` and your `tenants`. Note the org keeps a friendly name like `"you's workspace"` — it is the *project* that is called `"default"`.)

2. **Mint a key.** Choose the scope — this is the decision that matters:

   **(a) A project key** — the narrow default. Works for exactly one project:

   ```sh
   curl -X POST "https://vocky.example.com/app/projects/<project-id>/credentials" \
     -H "Authorization: Bearer <session-token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"web-backend"}'
   # -> 201 { "credential": { "project_id": "<project-id>", ... }, "key": "vk_..." }
   ```

   **(b) An org key (P10)** — one key for **every** project in your org, including ones you create later. Note there is **no project in the path**:

   ```sh
   curl -X POST "https://vocky.example.com/app/credentials" \
     -H "Authorization: Bearer <session-token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"all-products"}'
   # -> 201 { "credential": { "project_id": null, ... }, "key": "vk_..." }
   ```

   **Which to pick.** Use a **project key** when one backend feeds one project — it is the smaller blast radius, and it is still the recommended default. Use an **org key** when one client captures into several projects, or when you would otherwise be juggling a key per project. The trade is explicit: an org key is more convenient and a **bigger secret** — leaking it exposes every project in the org, and revoking it cuts every project at once.

   **Both kinds start with `vk_`**, deliberately — you cannot tell them apart by looking at the key. The way to tell is `credential.project_id`: a UUID for a project key, **`null`** for an org key. The dashboard and `vocky keys list` both label the scope for you.

   The `vk_…` **`key` is shown exactly once** at either scope — store it as a secret in your product backend. Vocky keeps only a hash and cannot show it again.

3. **Managing keys later.** The two scopes have separate, non-overlapping surfaces:

   | | project keys | org keys |
   |---|---|---|
   | list | `GET /app/projects/<project-id>/credentials` | `GET /app/credentials` |
   | revoke | `DELETE /app/projects/<project-id>/credentials/<id>` | `DELETE /app/credentials/<id>` |

   A revoked key of either kind stops working immediately. The surfaces are strictly separate: trying to revoke a **project** key through `/app/credentials/<id>` answers `404` even though it is your own key — use the per-project route for those.

Your product backend then sends the `vk_…` key as `Authorization: Bearer` on every `/api/*` request below. Keep the session token for account/project management; keep the ingest key for ingestion.

**Creating more projects (optional).** `POST /app/projects` still works, and as of P10 it is **get-or-create**: project names are unique within an org, and re-posting a name you already have returns the existing project instead of creating a duplicate or failing. That makes "ensure this project exists" safe to run repeatedly from a script.

```sh
curl -X POST "https://vocky.example.com/app/projects" \
  -H "Authorization: Bearer <session-token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"marketing-site"}'
# -> 201 { "project": { "id": "<project-id>", ... } }   (created, or the one that already existed)
```

## Capture Over REST

Use REST capture from a trusted server-side web or product backend when a real user explicitly triggers a feedback action. REST is the ingestion path for page feedback, widget feedback, surveys, ratings, and UI like/dislike controls; capture stays a deliberate server-to-server product action rather than a browser-direct call.

`target_type` is the review discriminator: use `message` for a specific message, `conversation` for a whole thread, and `surface` for a concrete page, widget, screen, or other non-message product UI. Older captures can omit `target_type`; those records remain visible in unfiltered review lists and are excluded only when an exact `target_type` filter is provided. Successful capture means Vocky accepted the job for background persistence; the record becomes queryable after the worker writes it to PostgreSQL.

**Choosing the destination project with an org key (P10).** A **project key** always captures into its own project — nothing you send can change that. With an **org key** you say where the feedback goes by adding an optional `project` **name** to the capture body (or the `project` argument on the MCP tool):

```sh
curl -X POST "https://vocky.example.com/api/feedback" \
  -H "Authorization: Bearer vk_<your-org-key>" \
  -H "Content-Type: application/json" \
  -d '{"message":"...","source":{"product":"marketing-site"},"project":"marketing-site"}'
```

- The name is **get-or-created inside your own org** — you never send an id, and you can never reach another org's project.
- **Omit it and the feedback lands in `"default"`** — which is exactly the project signup already made for you, so an org key works with zero setup.
- A **project key ignores the field entirely** — it is not compared, not rejected, and does not error. That is deliberate, so a client that starts sending `project` keeps working unchanged against an existing project key.

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
- `recorded_by`: optional marker for **who recorded this event** — `agent` or `human`. Omitting it stores `null` = *unspecified*, which is **not** the same as `human`; only the `/mcp` transport infers a value (see "Agent Capture Over MCP" below)
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

Trigger fields describe why capture happened; `recorded_by` describes **who recorded it** — two different questions, so an agent recording a survey response can say both. Target fields describe what was reviewed. Existing integrations can omit all of these, but integrations with message-level feedback should send `target_type: "message"` plus the exact message context so reviewers do not have to infer which message the user judged. REST integrations with product-surface feedback should use `target_type: "surface"` when the exact page, widget, screen, or feature is known.

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

### What goes in which field (read this before building a payload)

Agent capture uses fields that already exist — there is **no sentiment enum and no separate note column**, deliberately, so operators hear the customer's actual words:

| What you are recording | Field | Notes |
| --- | --- | --- |
| The **user's** feedback or sentiment, free text, **verbatim** where possible (`답답함`, `감사`, `긍정`, `부정`, `짜증`, or a whole sentence) | **`message`** | Required and non-blank. This is the voice of the customer — do not paraphrase it into your own voice. |
| **Your** note about that feedback — what happened, what the user was doing, why you recorded it | **`comment`** | Optional in the schema, but **treat it as required whenever an agent is the one recording**. Vocky does not reject a capture without it; the record is simply much less useful. |
| Who recorded it | **`recorded_by`** | `"agent"` or `"human"`. |
| Labels you want to slice by later | `tags` | Optional, unchanged meaning. |
| Your runtime | `source.integration` (e.g. `"langchain-mcp"`) | A free-text hint. **It is not the marker** — do not use it as one. |

Both `message` and `comment` sit inside vocky's free-text search expression, so an agent's sentiment **and** its note are searchable — Korean substrings included — through `/app/feedback?q=` (or `vocky feedback search`) with no extra setup.

### The `recorded_by` marker, and the one place it is inferred

`recorded_by` answers *who recorded this feedback*, orthogonal to `trigger_type`'s *why capture happened*. It is set once at capture and can never be edited afterwards — it is provenance, not a review field.

- Allowed values are exactly `agent` and `human`. Anything else is rejected with `recorded_by must be one of: agent, human` (a `400` on REST; over MCP the same string comes back as an `isError` **tool result**, not an HTTP status).
- **Omitting it does not mean `human`.** It stores `null` = *unspecified*, which is also what every record captured before this feature reads back as. Never infer a human from a `null`.
- **`/mcp` is the only surface that fills it in**: omit it there and vocky stamps `"agent"`, because the MCP endpoint is by construction the agent-runtime transport — so an agent that never learns the argument is still marked correctly. An explicit value always wins (pass `"human"` when you are relaying a judgement a person made).
- **REST and the CLI never infer it.** `POST /api/feedback` without the field stores `null`, and `vocky capture` has **no marker flag at all**, so CLI captures are always unspecified. Use REST or `/mcp` when the marker matters.

### Key scope, stated plainly

The `vk_` key you hand an agent runtime is **not capture-only**: within its scope it can capture, read, PATCH, and DELETE feedback, and an **org** key spans every project in the org, including ones created later. Per-credential capture-only scopes are not implemented yet. So **mint a project-bound key for an agent runtime, never an org key** — especially one running outside infrastructure you control.

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
  "message": "감사합니다 정말 도움이 되었어요",
  "comment": "User said this after finishing the export flow — relief and thanks, unprompted.",
  "source": {"product": "my-agent", "integration": "langchain-mcp"},
  "recorded_by": "agent",
  "user_id": "user_123",
  "conversation_id": "conv_123",
  "target_type": "message",
  "target_role": "assistant",
  "target_text": "Try clicking Export again."
}
```

A successful call returns a capture receipt (`{ request_id, accepted_at, status: "accepted" }`) — the same async semantics as REST: the record becomes queryable after the worker persists it. Use MCP capture only when the agent runtime is intentionally deciding to capture voice-of-customer feedback; explicit human UI actions (like/dislike buttons, page/widget feedback) should still go through REST capture.

A public `/mcp` deployment must also add its public host to `VOCKY_MCP_ALLOWED_HOSTS` (DNS-rebinding protection is on by default). If it is not listed, every `/mcp` call answers **`421 Invalid Host header`** — a transport-level check on the `Host` header, before the key is ever examined, so it is **not** an auth problem and a different key will not fix it. `VOCKY_MCP_ALLOWED_ORIGINS` normally needs nothing: `Origin` is only checked when the header is present, and non-browser MCP clients send none.

## Read Back A User's Own Feedback

After your backend has authenticated a user, you can render that user's own feedback with the scoped end-user read. Call `GET /api/feedback` with the required `user_id` and `source_product` (the `source.product` you sent at capture); Vocky returns only that user's own records, newest-first, together with operator comments and image attachment links.

```sh
curl "https://vocky.example.com/api/feedback?user_id=user_456&source_product=marketing-site" \
  -H "Authorization: Bearer vk_<your-project-key>"
```

Optional filters (`feedback_value`, `channel`, `target_type`, `trigger_type`, `recorded_by`, `source_integration`, `conversation_id`, `session_id`, `tag`, `start_ingested_at`, `end_ingested_at`, `limit`, and `cursor`) are AND-combined with the required `user_id` + `source_product` scope, so the read never returns another user's data. Operator comments are surfaced read-only as one-way operator-to-user visibility; there are no end-user replies. Broad review, query, summary, and management stay on Admin REST.

**Telling agent-recorded feedback apart (P14).** Every feedback read surface — this one, `/api/project/feedback`, `/app/feedback`, and Admin REST — returns `recorded_by` in each record (`"agent"`, `"human"`, or `null`), and every list surface accepts `?recorded_by=agent` or `?recorded_by=human` as an exact filter:

```sh
curl "https://vocky.example.com/app/feedback?recorded_by=agent&limit=50" \
  -H "Authorization: Bearer <your-session-token>"
```

Omitting the filter returns everything, including the unspecified rows. There is deliberately **no** filter value that selects only the `null` rows, so a three-way agent / human / unspecified split has to be done client-side over an unfiltered read.

## Read & Manage Your Project's Feedback (Feedback API v2)

Your product's own admin panel / operator page can read **and manage** feedback directly, using the **same `vk_` key** it captures with — send it as `Authorization: Bearer vk_…` on `/api/project/feedback`. The scope is implicit in the key; there is no project id in the path. Every id outside that scope answers `404` (never `403`).

**With an org key (P10) this surface spans your whole org** — one call reads and manages feedback across every project. Two consequences worth knowing before you wire a client to it:

- **Records carry a `project_id` only when the caller's key is org-level.** A project key's response is unchanged and still omits the field (you already know your project). Decide which shape to expect from the key you hold, not from sampling one response.
- The verbs are the same at both scopes: an org key can PATCH and DELETE feedback in **any** of your org's projects.

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

Everything above is the API. As of **P4** there is also a **web app** — Vocky's authenticated browser surface, and the replacement for the packaged self-hosted operator Admin Web UI (which **P6 deleted**, so the web app is now the only browser surface). It does the account/project/credential work and the cross-project feedback reading **without curl**. (It runs locally today; `vocky.hi2vi.com` is **not live** — the deploy kit is authored but unexecuted, and bring-up is P12.)

It is a signed-in **tenant owner's** surface, not an end-user one: you see your own tenant, your own projects, and your own feedback. Anything belonging to someone else answers "not found" — never "forbidden" — so you cannot even probe what exists.

### The landing page (`/`)

As of **P9**, the app's root `/` is a **public marketing landing** for signed-out visitors, not a bare redirect. It explains what Vocky is — a server-to-server feedback layer where your backend sends explicit user reactions (likes, dislikes, comments) over a single `POST /api/feedback` call, and Vocky turns them into structured, Korean- and English-searchable signal — and how to start: create a project, mint a `vk_` key (shown once), send feedback from your backend, then search and review it. Its calls to action are **Start free** (`/signup`) and **Read the docs** (the real `github.com/leetusik/vocky` repo). If you are already signed in, visiting `/` **bounces you straight to `/dashboard`** — the landing is the signed-out front door only, and no session token is ever exposed to it.

As of **P11** the landing also carries the onboarding path itself, so "sees the landing page" → "an agent is capturing feedback" happens without leaving it: a **hero install row** with the one-line `curl | bash` installer, a **`Get started` section** (`#quickstart`) walking the two-variable contract — install, export into `~/.zshenv`, verify, capture — with the Codex sandbox trap called out and the `400`/`401` readings spelled out, and a **skill section** (`#skill`) that shows the real `/SKILL.md`, copies it, and offers it as a download. Every command shown is real and shipped; the hero's request payload was corrected first (nested `source.product`, and no `vk_live_` tier — vocky has never had one) so that copy-pasting it actually works.

### Sign up, sign in, sign out

Sign up with an email and password and you land straight in the app — signup provisions your account, your tenant (workspace, auto-named from your email), and your session in one step. Logging in later takes you to the same place. Wrong password and unknown email give the **identical** error, so nobody can use the login form to discover which emails are registered.

Your session lives in a secure cookie the app sets for itself; the browser never holds your Vocky token, and no page ever renders it. Signing out revokes the session at Vocky and clears the cookie. Visiting any signed-in page while signed out simply bounces you to the login form; a session revoked out from under you does the same, without any redirect loop.

### The shell

Every signed-in page shares one layout: a topbar (your workspace and email, and the sign-out button) and a left rail with **Dashboard** and **Feedback**. The rail collapses to a horizontal strip on narrow screens. There is no dark-mode toggle.

### The tenant dashboard (`/dashboard`)

Your post-login home, and the whole-tenant view:

- **Usage totals** for the window — total records, likes, dislikes, unrated. The window is the last 30 days unless you say otherwise. This is operational visibility, not billing; Vocky has no metering.
- **A daily trend chart** of capture volume across the window, zero-filled so quiet days read as zero rather than vanishing. A tenant that has never captured anything shows an explicit empty state instead of an empty chart.
- **Your projects**, with a create-project form. A new project appears in the list immediately. **Project names are unique within your org (P10)** — submitting a name you already have returns that project rather than creating a second one. (This corrects an earlier statement in these docs that names were not unique; that was true before P10 and is false now.)
- **Your org keys (P10)** — a panel beside the projects list, since an org key does not belong to any one project. Mint one (optionally named), see the show-once key, and revoke one, exactly like the per-project keys panel. There is no separate route or nav entry; org keys live on the dashboard because that is the org-level page.
- Each project name **links into its detail page**. **Project detail shows only that project's own keys** — org keys never appear there, by design.

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

### Installing it — the hosted `curl | bash` line (P11), lean CLI vs the `server` extra (P6)

**P11 settled the install question: a `curl | bash` installer, not PyPI.** Once `https://vocky.hi2vi.com` is live, the whole install is one line:

```sh
curl -fsSL https://vocky.hi2vi.com/install.sh | bash
```

It bootstraps `uv` only if it is missing, runs `uv tool install --reinstall`, needs **no sudo** and installs nothing system-wide (everything lands under `$HOME/.local`), and re-running the same line is how you upgrade. The script is short and every step is commented — **read it before piping it into a shell**. Its safety argument is structural: every executable statement lives inside `main()` and `main "$@"` is the last line of the file, so a download that drops mid-transfer defines a function and hits EOF instead of executing a half-written script (proven at two cut points — a mid-function truncation is a bash parse error, a truncation just before the final line exits 0 with no output).

**Today, before the site is deployed, install from a checkout instead** (`uv tool install .`, `uvx --from . vocky`, or `uv run vocky` in-repo). Nothing is published to PyPI and **P11 deliberately did not publish**: `uv publish` stays an unexercised, operator-gated action. Two consequences worth stating plainly:

- The hosted line **is live as of P12** (2026-08-04): `https://vocky.hi2vi.com/install.sh` serves 200, and the installer was proven end to end into a clean container — uv bootstrapped, `vocky 0.2.0` built from the real `git+https://` target, `vocky --version` and `vocky capture --help` both rendering. The landing and `install.sh` deployed together, exactly as designed, so no landing page ever served a dead command. Any "once the site is live" hedging in older copy is now historical. **One standing caveat:** the installer resolves GitHub `main`, so what it delivers is the **pushed** commit — a local commit that has not been pushed is not installable.
- The installer's target is `git+https://github.com/leetusik/vocky`, which resolves **whatever is on GitHub `main`**. Local `main` is far ahead of the remote, so until an operator-gated `git push` lands, that target would deliver a pre-P10 CLI with no org keys and no `vocky capture`. **P12 owns the push and the clean-environment install proof.**

P6's packaging split still describes what a CLI user downloads:

| | |
| --- | --- |
| `pip install vocky` / `uvx vocky` | the **lean CLI** — httpx + typer only (≈15 packages). No database driver, no web server, no MCP SDK. |
| `pip install "vocky[server]"` | the full self-hosted stack, for running Vocky rather than talking to it. |

That split is what makes the agent-first path cheap: a coding agent asked to "set up vocky" pulls a small client, not a server runtime. It holds only because the CLI never imports server code — a stray server-side import in a `vocky.cli.*` module silently breaks the lean install.

The CLI version is **`0.2.0`** as of P11 (it had been a stale `0.1.0` since before P10). Note that `vocky --version` reads *installed* metadata, not the source tree, so it only reflects a bump after a reinstall — the installer reinstalls on every run, so this is a non-issue there.

### The onboarding journey as commands

The signup → key → capture → read spine maps one-to-one onto CLI commands (each mirrors the raw-HTTP step documented under "Onboarding" above). As of **P10** it is shorter, because signup already made you a project:

```sh
# 1. Sign up (or `vocky login`) — provisions your account, your org, AND a "default" project
printf '%s' "$PASSWORD" | vocky signup --email you@example.com --password-stdin
#    -> ... A "default" project was created too.

# 2. Mint a `vk_` key — shown once. Pick the scope:
vocky keys mint                                 # ORG key: works across every project in your org
vocky keys mint --project <project-id>          # PROJECT key: works for that one project
#    Both print the show-once warning, a `Scope:` line saying which you got, then the vk_… key
#    (the plaintext key is always the LAST line, so it stays safe to parse)

# 2b. Only if you want more projects — get-or-create, safe to re-run
vocky projects create marketing-site            # -> Created project "marketing-site" (<project-id>).

# 3. Capture with that vk_ key. Your product backend does it over /api/feedback (the REST path above);
#    from a terminal or a coding agent, `vocky capture` is the same call in one command (P11):
export VOCKY_API_TOKEN=vk_...                   # the key from step 2 — never the session token
vocky capture "결제 단계에서 카드가 거절돼요" --product checkout-web --value 2
#    -> Captured — request_id <uuid>
#    With an org key, --project <name> (or "project" in the REST body) picks the destination;
#    omit it for "default". A project-bound key ignores it.

# 4. Manage keys later — same scope rule
vocky keys list                                 # your org keys
vocky keys list --project <project-id>          # that project's keys
vocky keys revoke <credential-id>               # an org key
vocky keys revoke <credential-id> --project <project-id>

# 5. Read and search what was captured, across all your projects
vocky feedback list
vocky feedback search 결제                       # Korean-safe substring search
vocky feedback show <feedback-id>               # full record + operator comments + attachments
```

**One sharp edge, stated plainly (P10).** `--project` used to be **required** on `keys mint|list|revoke`; it is now optional, and omitting it means *org scope*. A script that relied on the old "missing required option" failure to catch a forgotten `--project` will now succeed — with a **broader** key than it intended. The mitigation is announcement, not prevention: `keys mint` always prints the scope it just minted, and `keys list` labels each row's scope. If you script key minting, assert on that scope line.

The command groups mirror the API surfaces: `vocky signup|login|logout|whoami` over `/auth/*`; `vocky projects`, `vocky keys`, and `vocky usage` over the session-authed `/app/*` control plane; and the read-only `vocky feedback list|search|show` over `/app/feedback`. `list`/`search` print each record's **full feedback id** (the copy-pasteable handle `feedback show` consumes) and `projects list` prints the **full project id** (the `--project` / `projects show` handle), so the terminal-only `list → show` and `list → --project` journeys complete without dropping to raw HTTP. Feedback **management** (edit/delete/comment) is deliberately out of the CLI — it stays on the `vk_`-keyed `/api/project/feedback` surface.

### For coding agents (headless contract)

The CLI is built so an agent can drive the whole flow with no interactive prompts and no secret ever landing on a process argv:

- **`--password-stdin`** reads the password from one line of stdin, so signup/login never put the password on the command line.
- **`--base-url`** (or the `VOCKY_BASE_URL` env) points the CLI at any vocky instance; the default is `http://127.0.0.1:8000`.
- **`VOCKY_CONFIG_DIR`** overrides where the session store lives (XDG-aware, defaulting to `~/.config/vocky/`), so an agent can run an isolated, throwaway session per task.
- **Generic 401**: an expired or missing session surfaces a friendly `Not signed in — run \`vocky login\`.` rather than a raw HTTP error.
- **Show-once key**: `keys mint` prints the plaintext `vk_…` exactly once with an explicit "copy it now, it cannot be recovered" warning; it is never shown again. **The key remains the strict last line of the output**, even with P10's added `Scope:` line — that ordering is a parsing contract, not an accident.
- **Errors go to stderr, success to stdout, with non-zero exit codes** — so an agent can branch on outcome. An invalid feedback id, for example, prints a hint pointing at `vocky feedback list` and exits 1.

## The two-variable agent contract (P11)

Before P11 there was **no environment-variable path for a credential at all**: `VOCKY_BASE_URL` and `VOCKY_CONFIG_DIR` existed, `VOCKY_API_TOKEN` did not exist anywhere in the tree, and the CLI was session-token-only with no capture command — so a `vk_` key had no CLI consumer. Both gaps are closed. **Two exports are now the whole agent contract**, and they give every coding agent on the machine the same access with no plugin installed anywhere:

```sh
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."
```

Put them in **`~/.zshenv`, never a repo `.env`.** A repo `.env` is never auto-loaded by Claude Code or Codex, so a resolver would never see it — and a key in a repo file is one commit away from leaking. `~/.zshenv` is sourced by every zsh invocation, so every Bash call, every Codex `exec`, and every repo inherits it. **Codex only:** the `workspace-write` sandbox denies outbound network by default, so the capture POST fails silently until `[sandbox_workspace_write] network_access = true` is set in `~/.codex/config.toml`. Claude Code needs no equivalent change.

**`vocky capture` is `VOCKY_API_TOKEN`'s first-class consumer**, and the shape of the credential split is deliberate:

- `vocky capture MESSAGE --product PRODUCT [--integration] [--value 1|2] [--comment] [--tag …] [--session-id] [--user-id] [--project]`. `--product` is the only required option; `--tag` is repeatable and is omitted from the body entirely when unused (never sent as `[]`); passing `-` as the message reads the whole thing from stdin, which is the right move for multi-line or quote-heavy user text.
- **There is no `--token` flag and never will be** — argv is world-readable via `ps` and lands in shell history, the same reasoning that gave `signup`/`login` their `--password-stdin`. The env var is the only way to supply the key. Unset or blank exits non-zero with `VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.` and makes **no HTTP call**.
- **A `vk_` key is never persisted in the config store.** `config_store` holds only the session `token` and `clear_token()` pops only that key, so a persisted `vk_` key would silently survive `vocky logout` — a leak-shaped bug. The two credentials also cannot cross at the transport: `capture` builds its client as `make_client(token=api_token, use_stored_token=False)`, which is a structural guarantee rather than a convention.
- Success prints exactly `Captured — request_id <full id>`. A `401` is remapped to `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).` — deliberately **not** "run `vocky login`", which is reserved for the session-token commands and would send an agent down the wrong path. Exit code is always `1` on failure; it never encodes the HTTP status.
- `vocky keys mint` now prints an `export VOCKY_API_TOKEN=<the key below>` hint immediately before the show-once key — and **the plaintext key remains the strict last line**, the parsing contract P10 established.

## The published agent skill (P11)

Vocky publishes an end-user agent skill: **`skills/vocky-feedback/SKILL.md`**, served byte-identically at **`/SKILL.md`** and shown on the landing page's `#skill` section (readable, copyable, downloadable). It is deliberately **not** under `.claude/skills/` or `.agents/skills/` — those hold this repo's own workflow machinery and would load into every session here.

The skill is written to be followed verbatim, not interpreted: the two-variable setup, a **zero-side-effect verify step** (a bare `GET /api/feedback` with the bearer key — `400` means the token authenticated and only the missing filter was rejected, `401` means stop and never retry, anything else is a transport/base-URL problem), then — as of **P14** — a **"what goes in which field" step placed *before* the transports**, because the field mapping decides the payload for all of them, then three capture paths — **Path A `vocky capture`** (primary, one command), **Path B raw REST** (no vocky install required; the nested `source` object is the single most important shape, and a top-level `source_product` is rejected outright), and **Path C `/mcp`** as the agent-runtime transport — followed by a branch-by-branch error table and a "report back" rule that forbids claiming a capture succeeded without a `202` or a `Captured —` line.

**P14 grew the skill from 7 numbered steps to 8** and taught it the agent-capture contract end to end: the sentiment-and-note field mapping, the `recorded_by` marker with its per-transport default, the `null` = *unspecified* rule, the plain statement that a `vk_` key is not capture-only (so mint a project-bound one), the fact that `vocky capture` has no marker flag, and two new error rows — the `recorded_by` rejection string and `421 Invalid Host header`. It also **corrected a pre-existing error**: the self-hosting gotcha claimed an unlisted host makes `/mcp` "401 regardless of the key"; it is `421`, the check is on `Host` (not `Origin`), and the key is never examined. The frontmatter `description` was deliberately left untouched — it governs when the skill activates in every installed client, and P14 changed *what to send*, not *when to capture*. Its frontmatter carries a hard negative trigger (not for general note-taking or drafting tickets elsewhere) and a scoped `allowed-tools` allowlist.

**The served copy can never fork from the canonical**: `scripts/skill_parity.py` holds the two files to a full-file byte match and runs in CI on every push and pull request (see `operations.md`), and the landing's preview pane renders the *served* file read at request time rather than a pasted excerpt.

## Human Review Boundary

Feedback review and management are now first-class but always scoped and authenticated: a project's `vk_` key reads/manages its own project's feedback (`/api/project/feedback`); a signed-in user reads/searches across all their projects (`/app/feedback`, or the same thing point-and-click in the web app); the end-user self-read (`GET /api/feedback`) returns one product user's own records. Self-hosted operators can also use the dedicated Admin REST API endpoints; when `VOCKY_ADMIN_AUTH_TOKEN` is set, Admin REST clients must send `Authorization: Bearer <VOCKY_ADMIN_AUTH_TOKEN>`. There is no unscoped or cross-tenant public query surface.

**Admin REST is API-only now.** The packaged browser UI that used to sit over it was removed in **P6**, so operator review over `/admin/api/*` means scripts, curl, or your own dashboard. In the reference production deployment the edge also **404s the whole `/admin` prefix**, keeping Admin REST reachable only from inside the deployment's network.

The **web app** (P4) is the browser expression of the session-authed `/app/*` surface — it adds no capability of its own, and deliberately carries **no** feedback management (that stays on `/api/project/feedback`). It is now vocky's only browser surface.
