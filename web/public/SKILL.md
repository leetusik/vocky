---
name: vocky-feedback
description: Use when the user wants a specific piece of product feedback captured and sent to vocky — a bug report, a reaction, or a feature request the user has explicitly asked to record. NOT for general note-taking, drafting tickets for another tracker, or capturing anything the user has not asked to send anywhere.
allowed-tools: Bash(curl:*), Bash(vocky capture:*), Bash(vocky keys:*), Read
---

# vocky-feedback

Capture one piece of end-user feedback into vocky, the shared feedback-ingest service. Every command below is meant to be copied and run exactly as written, substituting only the bracketed values.

## 1. Set up the two-variable contract

Every capture path below — CLI, REST, or MCP — needs exactly two environment variables:

```bash
export VOCKY_BASE_URL="https://vocky.hi2vi.com"
export VOCKY_API_TOKEN="vk_..."
```

Put these in `~/.zshenv`, never a repo `.env`:

- A repo `.env` is **never** auto-loaded by Claude Code or Codex, and a secret committed to a repo risks an accidental leak. `~/.zshenv` is sourced by every zsh invocation, so every Bash call, every Codex `exec`, and every repo you work in inherits it — the key never touches a repo.
- **Codex only**: the `workspace-write` sandbox denies outbound network by default, so the POST below would silently fail. Add `[sandbox_workspace_write] network_access = true` to `~/.codex/config.toml`. Claude Code needs no equivalent change.
- If `VOCKY_API_TOKEN` is not set yet, mint one with `vocky keys mint` (its output ends with an `export VOCKY_API_TOKEN=<the key below>` hint immediately before the key itself — the key is shown only once, copy it now), or ask the operator for one from the vocky dashboard.
- **Know what the key can do — it is not capture-only.** A `vk_` key is a full ingest credential: within its scope it can capture **and** read **and** edit (PATCH) **and** delete feedback. Its scope is fixed when it is minted — `vocky keys mint --project <project-id>` binds it to exactly one project, while a bare `vocky keys mint` mints an **org** key that reaches every project in the org. For anything running as an agent runtime, or on a machine the operator does not control, mint a **project-bound** key and never an org key, and store it as you would a read-write API secret.

## 2. Verify before you capture anything

This makes no write — it only proves the two variables are correct, without submitting real feedback:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $VOCKY_API_TOKEN" "$VOCKY_BASE_URL/api/feedback"
```

- **`400`** — the token authenticated fine; the endpoint only rejected the bare `GET` for a missing filter. You are ready to capture.
- **`401`** — the key is wrong, revoked, or `VOCKY_API_TOKEN` is unset/blank. Stop; do not retry or fall back to another path. Tell the user the key needs fixing.
- Anything else (connection refused, timeout, DNS failure) — `VOCKY_BASE_URL` is wrong or the service is unreachable. Say so and stop.

## 3. What goes in which field (read this before you build a payload)

This applies to every path below. Vocky keeps **the user's voice** and **your note about it** in two different fields, both free text — there is no sentiment enum and vocky will not invent one:

| What you send | Field | Rule |
|---|---|---|
| The user's feedback or sentiment, in **their** words, verbatim where you can (`답답함`, `감사`, `긍정`, `부정`, `짜증`, or a whole sentence) | `message` | **Required, non-blank.** Do not paraphrase it into your own voice and do not compress it into a label. |
| Your own note about that feedback — what happened, what the user was doing, why you recorded it | `comment` | Optional in the schema, but **treat it as required whenever an agent is the one recording**: a marked capture with no note is one a human reviewer cannot act on. |
| `agent` when you (the agent runtime) decided to record this; `human` when you are relaying an explicit human action such as a like/dislike button or a submitted form | `recorded_by` | Optional, closed vocabulary — `agent` or `human`, nothing else. See below for what omitting it means. |
| Labels you want to slice the data by later | `tags` | Optional; omit entirely rather than sending an empty list. |
| Your runtime | `source.integration` (e.g. `"langchain-mcp"`, `"claude-code"`) | Free text, a hint only — it is **not** the marker. `recorded_by` is. |

`recorded_by` answers *who recorded this*, which is a different question from `trigger_type` (*why capture happened*) — send both when both are known. It is captured once and is not editable afterwards.

**Omitting `recorded_by` does not mean `human`.** It stores `null`, which means *unspecified*, and it is what every capture made before this marker existed reads back as. Two transport rules:

- On **`/mcp`** (Path C) — the agent-runtime surface by construction — an omitted `recorded_by` is stored as `"agent"`.
- On **REST** (Path B) and the **CLI** (Path A) an omitted `recorded_by` stays `null`. The CLI has no marker flag at all, so every `vocky capture` lands unspecified; when the marker matters, capture over REST or `/mcp` instead.
- An explicit value always wins, on every transport.

A value outside the vocabulary is rejected, never coerced: `recorded_by must be one of: agent, human`.

An agent-recorded body looks like this — the user's words verbatim in `message`, your note in `comment`, the marker explicit (Path B below shows how to POST exactly this shape):

```json
{
  "message": "답답함",
  "comment": "User retried the export three times and said this while the job was still queued.",
  "recorded_by": "agent",
  "source": { "product": "<product>", "integration": "<your runtime>" },
  "tags": ["export"]
}
```

## 4. Path A — capture with the CLI (primary, one command)

If `vocky` is installed, this is the one command to run:

```bash
vocky capture "<the user's words>" --product <product> [--value 1|2] [--comment "..."] [--tag <tag>] [--session-id <id>] [--user-id <id>] [--project <project>]
```

- `--product` is the **only required** option — it maps to `source.product`.
- `--tag` is repeatable (`--tag a --tag b`); omit it entirely when there is nothing to tag — never pass an empty list.
- Pass `-` as the message to read the whole thing from stdin instead of fighting shell quoting — the right move for multi-line or quote-heavy user text:

  ```bash
  printf '%s' "<the user's words, verbatim, may span lines>" | vocky capture - --product <product>
  ```

- `--project` is honored **only** when the `vk_` key is an **org-level** key; a project-bound key ignores it.
- There is **no** `recorded_by` flag here: every `vocky capture` lands with the marker unspecified (`null`), though `--comment` still carries your note. When the marker matters, use Path B or Path C (step 3).
- Success prints exactly one line: `Captured — request_id <full uuid>`. Report that id back to the user.
- Failure exits non-zero (`1`, always — see the table in step 7). Every failure prints the server's error verbatim to stderr, **except**:
  - `401`, which is remapped to `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).`
  - a missing/blank `VOCKY_API_TOKEN`, which prints `VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.` with no HTTP call made at all.
  - an unreachable server, which prints `Could not reach vocky at <base_url> (<exc>).`

## 5. Path B — raw REST (no vocky install required)

`POST $VOCKY_BASE_URL/api/feedback` with the bearer key. **The nested `source` object is the single most important shape here** — a top-level `source_product` field is rejected outright.

Write the body to a temp file rather than inlining it as a shell argument — this keeps quotes, newlines, and non-ASCII text (e.g. Korean) out of argv entirely:

```bash
cat > /tmp/vocky-capture.json <<'JSON'
{
  "message": "<the user's words>",
  "source": { "product": "<product>", "integration": "claude-code" },
  "feedback_value": 2,
  "tags": ["<tag>"]
}
JSON

curl -sS -X POST "$VOCKY_BASE_URL/api/feedback" \
  -H "Authorization: Bearer $VOCKY_API_TOKEN" \
  --json @/tmp/vocky-capture.json
```

- `message` and `source.product` are the only required fields; every other field above (`feedback_value`, `comment`, `channel`, `recorded_by`, `target_type`, `tags`, `session_id`, `user_id`, …) is a legitimate **top-level** field — only `source` nests. REST also accepts `attachment_ids` (previously uploaded attachment ids) and `project` (destination project for an org-level key — CLI-only otherwise, same rule as Path A).
- When you are recording on the user's behalf, add `"recorded_by": "agent"` and the `comment` note — REST does **not** infer the marker (step 3).
- Success is **`202`** with exactly `{"request_id": "...", "accepted_at": "...", "status": "accepted"}`.
- Every failure body is a flat `{"detail": "<string>"}` — there is no error code and no `request_id` on failure. See the table in step 7 for how to react to each one.

## 6. Path C — `/mcp` (the agent-runtime transport)

`https://<host>/mcp` is a single POST-able FastMCP Streamable-HTTP endpoint (stateless, JSON responses); the same `vk_` bearer guards the whole transport including `initialize`. The one tool is `capture_feedback` — write-only, no read or query tools — taking the same fields as REST including `recorded_by` (`attachment_ids` is REST-only), with `source` the only nested object. Add it to a client with:

```bash
claude mcp add --transport http vocky "$VOCKY_BASE_URL/mcp" --header "Authorization: Bearer $VOCKY_API_TOKEN"
```

This is the natural transport for an agent runtime, and it is the one place the marker is inferred: a `capture_feedback` call that omits `recorded_by` is stored as `"agent"`, so an agent that never learns the argument still produces correctly marked data. Pass `"human"` explicitly when you are relaying a human-recorded event. A rejected value comes back as a **tool error result** (`isError`) carrying the same message as REST, not as an HTTP status.

Self-hosting gotcha: DNS-rebinding protection checks the request's **`Host` header** against an allowlist that by default contains only `127.0.0.1`, `localhost`, and `[::1]`. A self-hosted public hostname must be added to `VOCKY_MCP_ALLOWED_HOSTS`, or every `/mcp` call answers **`421 Invalid Host header`** regardless of the key — the key is never even examined, so this is not an auth problem and retrying will not fix it. The parallel `VOCKY_MCP_ALLOWED_ORIGINS` guards the `Origin` header, which is only checked when it is present: non-browser MCP clients send none, so it normally needs no configuration.

## 7. Error handling — branch by branch

Every failure body (CLI and REST alike) is either a CLI-remapped message or the server's `{"detail": "..."}` verbatim. React like this:

| Status | `detail` | What to do |
|---|---|---|
| `401` | `Unauthorized` | The key is wrong or revoked. Say so, name `VOCKY_API_TOKEN`, **stop** — never retry, never fall back to another path. |
| `400` | `request body must be valid JSON` / `request body must be a JSON object` | The payload you built is malformed. Fix it once and retry once. |
| `400` | `<dotted.loc>: <message>` (e.g. `source.product: Field required`) | A schema violation. **Only the first error is reported** — fixing one may reveal another underneath it. |
| `400` | `message must not be blank` / `source.product must not be blank` | Both are required and non-blank. |
| `400` | `recorded_by must be one of: agent, human` | The marker vocabulary is closed. Send `agent` or `human`, or omit the field — never guess a third value. On `/mcp` the same string arrives as a tool error instead of a status. |
| `400` | `channel must be one of: web, mobile, support`, `project must not exceed 200 characters`, … | A semantic normalization failure — the `detail` string is actionable verbatim. |
| `421` | `Invalid Host header` (`/mcp` only, plain text) | The server's `VOCKY_MCP_ALLOWED_HOSTS` does not list the hostname you called. Not a key problem and not retryable — the operator must add the host. |
| `503` | `capture queue unavailable` | Transient. Tell the user their feedback was **not** captured — do not silently drop it. |
| `500` | `project resolution failed` / `credential scope unavailable` | Server-side. Report it verbatim; do not retry. |

For the CLI specifically: the **exit code is always `1`** on any failure — it never encodes the HTTP status — and stderr carries the mapped/verbatim message above.

## 8. Report back

Tell the user plainly whether the feedback was captured:

- **Captured**: quote the full `request_id`.
- **Not captured**: name the failure (from the table above) and what, if anything, they need to do (usually: fix `VOCKY_API_TOKEN`, or nothing — it was a transient server error and can be retried later).

Never claim a capture succeeded without a `202` response or a `Captured —` line to point to.
