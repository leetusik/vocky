# P1.S3 result — README scrubbed to REST-only

## Outcome

Rewrote `README.md` so it truthfully describes the post-S2, REST-only system. All MCP surface,
tool names, env vars, and the FastMCP DNS-rebinding concept are gone; the doc now presents
human-/product-triggered REST capture plus operator review as the product identity. No code, test,
config, or durable-doc files were touched — `README.md` was the only file in scope and the only
content file edited.

## What changed, section by section

- **Title/tagline & "What Vocky Is":** reframed from "feedback capture for agents / MCP capture" to
  human-triggered feedback capture and review over server-to-server REST (page/widget/survey/like-
  dislike actions). Tagline aligned with the pyproject description. VoC framing kept.
- **"Why It Exists":** reframed around product/customer feedback moments in general; added a light
  note that a product's own backend forwards feedback over REST (no MCP).
- **"What The Current Pre-MVP Does" & "Current Status":** dropped every MCP capture/tool/liked-
  conversation bullet; kept REST capture (`POST /api/feedback`), async worker persistence, the field
  storage list, the scoped end-user read (`GET /api/feedback`), Admin REST, Admin Web UI, nullable
  channel categories, single-tenant self-hosting. Fixed "the MCP app process" → "the app process"
  (runtime = Postgres + Redis + app + worker).
- **"Local Development":** `make verify`/smoke text now describes the REST smoke (POST then poll the
  scoped GET). Dropped the three `VOCKY_MCP_*` public-exposure bullets and the FastMCP DNS-rebinding
  wording; kept `VOCKY_API_AUTH_TOKEN` + `VOCKY_ADMIN_AUTH_TOKEN`. Rewrote the `make smoke` line to
  the REST flow with the `VOCKY_API_AUTH_TOKEN` bearer note.
- **"Running The App Directly":** removed the `/mcp` Streamable HTTP bullet and the canonical-`/mcp`
  line; endpoint list is now `GET /healthz`, `POST /api/feedback`, scoped `GET /api/feedback`, Admin
  REST `/admin/api/*`, Admin Web UI `/admin`. Kept the transport-neutral field-guidance paragraphs
  (generalized the "agent/process context" lead to "conversation or process context").
- **"Access Modes":** public-deploy bullet no longer requires `VOCKY_MCP_AUTH_TOKEN` or the public
  Host/Origin allowlist — now sets `VOCKY_API_AUTH_TOKEN`/`VOCKY_ADMIN_AUTH_TOKEN` + `VOCKY_EXTERNAL_BASE_URL` and runs `make external-verify`.
- **"Public Custom Domain With Cloudflare":** removed the three `VOCKY_MCP_*` lines from the `.env`
  block and the "Public MCP clients should use …/mcp" line; kept the REST + Admin client lines and
  all Cloudflare tunnel steps. `make external-smoke` reworded to the public REST smoke flow.
- **"MCP Surface" section:** deleted entirely; moved the `docs/current/experience.md` integration
  pointer into the Web Capture REST Surface section.
- **"Web Capture REST Surface":** kept; dropped the "same core capture fields as MCP" comparison;
  added the 202 receipt shape note; changed the review pointer to the scoped end-user read / Admin
  REST. curl example retained.
- **"Admin REST Surface":** kept; "separate from MCP" → "separate from the public capture/read API".
- **"Self-Hosted Usage":** removed the `/mcp` client-pointing lines; replaced the two Python MCP
  client code blocks with REST examples — a `POST /api/feedback` curl, an `httpx` POST, and a scoped
  `GET /api/feedback?user_id=…&source_product=…` curl (with the note that `source_product` is the
  `source.product` sent at capture), all with the bearer-token guidance. Read-back guidance now polls
  the scoped GET or uses Admin REST / the Admin Web UI. Caddy reverse-proxy example kept.
- **"License":** left as MIT (already set in S1).

## Truthfulness checks against the ground-truth surface

Verified against `src/vocky/api.py` and `src/vocky/capture.py`: `POST /api/feedback` returns `202`
with `{request_id, accepted_at, status:"accepted"}` (capture.py:70-72, 302); the scoped read
`GET /api/feedback` requires non-blank `user_id` + `source_product` and returns `{records, next_cursor?}`
newest-first with comments + attachment links (api.py:126-253); `source_product` in the read equals
`source.product` at capture (capture.py:258). Only surviving env vars named: `VOCKY_API_AUTH_TOKEN`,
`VOCKY_ADMIN_AUTH_TOKEN`, `VOCKY_EXTERNAL_BASE_URL`, `VOCKY_BASE_URL`, and the publish/port vars.

## Validation

- `grep -inE "\bmcp\b|/mcp|fastmcp|streamable|capture_feedback|list_feedback|summarize_feedback|list_liked_conversations|VOCKY_MCP" README.md`
  → **empty** (exit 1, no matches). Pass.
- Read the whole rewritten README for coherence: no dangling links. The two links
  (`docs/current/experience.md`, `LICENSE`) both resolve. Every endpoint/env var named still exists.
  Pass.
- `git diff --stat` → the only content file changed is `README.md`; the other entries are the
  orchestrator's start-slice workflow bookkeeping under `works/`. No `docs/`, `src/`, `tests/`, or
  config changes. Pass.
- Residual "agent" appears once (line 119) in transport-neutral `target_type: message` field
  guidance — a still-valid field value, not an MCP reference. Intentionally kept.

## Deviations from plan

None of substance. Two judgment calls within the plan's intent: (1) generalized the "agent/process
context" field-guidance lead to "conversation or process context" so it reads truthfully for the
REST-only surface while keeping the still-valid `messages`/`used_context` guidance; (2) kept the one
"agent message" phrase in the `target_type` guidance because that field value still exists.

## Out of scope, untouched (per operator + plan)

`docs/current/*` (versioned at P1.REVIEW), the two private gitignored docs
(`docs/local-public-access.md`, `docs/changple5-apply.md`), and all source/test/config files.
