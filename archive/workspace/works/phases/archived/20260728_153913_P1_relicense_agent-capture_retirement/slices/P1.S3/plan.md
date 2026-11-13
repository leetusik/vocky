# P1.S3 — Scrub MCP from README (REST-only)

> Native plan for slice **P1.S3** (`implementation`, risk **medium** → `slice-executor-mid`).
> Prose-accuracy work, no code. Rewrite `README.md` to describe the **post-S2, REST-only** system
> truthfully. You never commit and never transition slice/phase status; write `result.md`, append
> a note to `phase.md`, and return your verdict. Do **not** run `doc-new-version` (durable docs are
> versioned at P1.REVIEW). **Only file in scope: `README.md`.**

## Context

S2 already retired MCP from the code: the `/mcp` endpoint, the four MCP tools
(`capture_feedback`, `list_feedback`, `summarize_feedback`, `list_liked_conversations`), the
`mcp[cli]` dependency, and the `VOCKY_MCP_*` settings are all **gone**; `vocky-smoke` is now a REST
smoke. `README.md` still documents all of that and must be brought in line. **Operator decision:**
the two private, gitignored docs (`docs/local-public-access.md`, `docs/changple5-apply.md`) are
**left untouched** — out of scope. The durable docs (`docs/current/{product,experience,
architecture,api}.md`) are **not** edited here; they're versioned at P1.REVIEW from the Doc-impact
list. `README.md` is a tracked source file (not a durable doc), so edit it directly.

## Ground truth — the surface as it exists now (write only what's true)

- **Capture (sole surface):** `POST /api/feedback` — human/product-triggered, server-to-server;
  bearer `VOCKY_API_AUTH_TOKEN` when set. Returns `202` with `{request_id, accepted_at,
  status:"accepted"}`; the worker persists asynchronously.
- **End-user scoped read:** `GET /api/feedback?user_id=<id>&source_product=<product>` — returns
  that user's own records (plus operator comments and attachment links); `user_id` +
  `source_product` are **required**; bearer `VOCKY_API_AUTH_TOKEN`. This is the REST replacement for
  the old MCP read tools for an end user's own feedback.
- **Attachment download:** `GET /api/feedback/{feedback_id}/attachments/{attachment_id}` (same scope).
- **Admin REST:** `/admin/api/*` (healthz, feedback list/metrics/detail, PATCH, DELETE, comments) —
  the operator review/query surface; bearer `VOCKY_ADMIN_AUTH_TOKEN`. **Unchanged.**
- **Admin Web UI:** `/admin` — unchanged.
- **Smoke:** `make smoke`/`make verify` now run the **REST** capture→persist→read smoke (health →
  `POST /api/feedback` → poll `GET /api/feedback`). No MCP smoke.
- **Env (public exposure):** only `VOCKY_API_AUTH_TOKEN` and `VOCKY_ADMIN_AUTH_TOKEN` remain
  relevant (plus `VOCKY_EXTERNAL_BASE_URL`). **Removed:** `VOCKY_MCP_ALLOWED_HOSTS`,
  `VOCKY_MCP_ALLOWED_ORIGINS`, `VOCKY_MCP_AUTH_TOKEN`, and the FastMCP DNS-rebinding Host/Origin
  allowlist concept entirely.
- **Gone:** `/mcp`, FastMCP/Streamable-HTTP, the four MCP tool names, MCP Python client code.

## README rewrite — section by section

Rewrite so nothing references MCP and everything is accurate. Keep the doc's voice and structure;
keep valid REST/Admin content. Specifics:

- **Title/tagline (line 3) & "What Vocky Is" (7–11):** reframe from "for agents / MCP capture" to
  human-/product-triggered feedback capture and operator review (page/widget/survey/like-dislike
  actions via server-to-server REST). Align the tagline with the new pyproject description
  ("Human-triggered feedback capture REST API"). Drop the "MCP capture is for agent-decided VoC…"
  framing. VoC/voice-of-customer stays.
- **"Why It Exists" (13–17):** reframe around product/customer feedback moments in general (not
  "agent conversations via MCP"). A light mention that a product's own backend can forward feedback
  is fine; no MCP.
- **"What The Current Pre-MVP Does" (19–28)** and **"Current Status" (42–52):** rewrite the bullets
  — remove all MCP capture/tool/liked-conversation bullets. Keep: REST capture (`POST
  /api/feedback`), async worker persistence, storage of value/comment/identity/trigger/target/
  context/metadata, the **scoped end-user read** (`GET /api/feedback`), Admin REST review, Admin Web
  UI, nullable channel categories, self-hosted single-tenant. In "Current Status," fix "the MCP app
  process" → "the app process" (runtime = Postgres + Redis + app + worker).
- **"What The First MVP Will Not Do" (30–36)** and **"Open Source + Managed Direction" (38–40):**
  keep (still accurate).
- **"Local Development" (54–99):** line 75 "runs the MCP smoke flow / accepted `capture_feedback`" →
  the REST smoke (POST then poll GET). Lines 81–88 "Public custom-domain access… additional
  settings": drop the three `VOCKY_MCP_*` bullets and the FastMCP DNS-rebinding wording; keep
  `VOCKY_API_AUTH_TOKEN` and `VOCKY_ADMIN_AUTH_TOKEN`. Line 99 "smoke target checks … MCP
  `capture_feedback`, `list_feedback`, `summarize_feedback` … If `VOCKY_MCP_AUTH_TOKEN` is set…" →
  REST smoke wording (`POST /api/feedback` then poll `GET /api/feedback`; bearer via
  `VOCKY_API_AUTH_TOKEN` when set).
- **"Running The App Directly" (101–127):** remove the `MCP Streamable HTTP at /mcp` bullet and the
  "Use `/mcp` exactly as the canonical MCP endpoint" line. The endpoint list becomes: `GET
  /healthz`, `POST /api/feedback`, `GET /api/feedback` (scoped), Admin REST `/admin/api/*`, Admin Web
  UI `/admin`. Keep the field-guidance paragraphs (channel/target/user_id/trigger) — they're
  transport-neutral and still valid.
- **"Access Modes" (129–136):** line 134 — drop the "require `VOCKY_MCP_AUTH_TOKEN` / allow the
  public Host and Origin" clause; public exposure now means set `VOCKY_API_AUTH_TOKEN` (and
  `VOCKY_ADMIN_AUTH_TOKEN` for admin), set `VOCKY_EXTERNAL_BASE_URL`, `make external-verify`.
- **"Public Custom Domain With Cloudflare" (138–202):** in the `.env` block (177–184) remove the
  three `VOCKY_MCP_*` lines (keep `VOCKY_EXTERNAL_BASE_URL`, `VOCKY_API_AUTH_TOKEN`,
  `VOCKY_ADMIN_AUTH_TOKEN`). Remove line 198 "Public MCP clients should use …/mcp …". Keep the REST
  + Admin client lines. Line 202 "`make external-smoke` runs only the public MCP smoke flow" → REST
  smoke wording. Cloudflare tunnel steps stay (they proxy the whole app).
- **"MCP Surface" section (204–215):** **delete the entire section.** Its content (capture receipt,
  read/summary/liked tools) is either gone or replaced by the REST surface already documented below
  it. If the "For client integration guidance, see docs/current/experience.md" pointer is worth
  keeping, move it into the REST capture section.
- **"Web Capture REST Surface" (217–255):** keep — this becomes the primary capture doc. Line 219
  "REST uses the same core capture fields as MCP" → drop the "as MCP" comparison. Line 253 "use MCP
  read tools or Admin REST for review" → "use the scoped end-user read (`GET /api/feedback`) or
  Admin REST for review". The curl example stays.
- **"Admin REST Surface" (257–274):** keep. Line 259 "separate from MCP" → "separate from the
  public capture/read API".
- **"Self-Hosted Usage" (276–341):** remove the `/mcp` client-pointing lines (278–288). **Replace
  the two Python MCP client code blocks (296–364)** with REST usage: a `POST /api/feedback` example
  (curl or httpx) and a scoped `GET /api/feedback?user_id=…&source_product=…` example, with the
  bearer-token note. Line 366 "poll `list_feedback` or `summarize_feedback`" → "poll `GET
  /api/feedback` (scoped) or use Admin REST / the Admin Web UI." Keep the Caddy reverse-proxy example.
- **"License" (378–380):** already MIT (from S1) — leave as is.

## Out of scope
Durable docs `docs/current/*` (→ P1.REVIEW). The two private gitignored docs (operator: leave
untouched). No source/test/config changes.

## Verification
- `grep -inE "\bmcp\b|/mcp|fastmcp|streamable|capture_feedback|list_feedback|summarize_feedback|list_liked_conversations|VOCKY_MCP" README.md`
  → **empty** (no MCP surface, no MCP tool names, no MCP env).
- Read the rewritten README end-to-end for coherence and truthfulness against the ground-truth
  surface above; confirm no dangling links and that every endpoint/env var named still exists.
- Sanity: `git diff --stat README.md` shows only `README.md` changed (nothing else in scope).

## phase.md note (append when done)
One line under Findings & Notes, e.g. "S3 done: README scrubbed to REST-only (MCP surface/tools/env
removed, self-hosted usage examples rewritten to REST); private gitignored docs left untouched per
operator. Durable docs deferred to REVIEW."
