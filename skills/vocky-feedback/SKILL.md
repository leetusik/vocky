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

## 2. Verify before you capture anything

This makes no write — it only proves the two variables are correct, without submitting real feedback:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $VOCKY_API_TOKEN" "$VOCKY_BASE_URL/api/feedback"
```

- **`400`** — the token authenticated fine; the endpoint only rejected the bare `GET` for a missing filter. You are ready to capture.
- **`401`** — the key is wrong, revoked, or `VOCKY_API_TOKEN` is unset/blank. Stop; do not retry or fall back to another path. Tell the user the key needs fixing.
- Anything else (connection refused, timeout, DNS failure) — `VOCKY_BASE_URL` is wrong or the service is unreachable. Say so and stop.

## 3. Path A — capture with the CLI (primary, one command)

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
- Success prints exactly one line: `Captured — request_id <full uuid>`. Report that id back to the user.
- Failure exits non-zero (`1`, always — see the table in step 6). Every failure prints the server's error verbatim to stderr, **except**:
  - `401`, which is remapped to `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).`
  - a missing/blank `VOCKY_API_TOKEN`, which prints `VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.` with no HTTP call made at all.
  - an unreachable server, which prints `Could not reach vocky at <base_url> (<exc>).`

## 4. Path B — raw REST (no vocky install required)

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

- `message` and `source.product` are the only required fields; every other field above (`feedback_value`, `comment`, `channel`, `target_type`, `tags`, `session_id`, `user_id`, …) is a legitimate **top-level** field — only `source` nests. REST also accepts `attachment_ids` (previously uploaded attachment ids) and `project` (destination project for an org-level key — CLI-only otherwise, same rule as Path A).
- Success is **`202`** with exactly `{"request_id": "...", "accepted_at": "...", "status": "accepted"}`.
- Every failure body is a flat `{"detail": "<string>"}` — there is no error code and no `request_id` on failure. See the table in step 6 for how to react to each one.

## 5. Path C — `/mcp` (alternative transport, not detailed here)

`https://<host>/mcp` is a single POST-able FastMCP Streamable-HTTP endpoint (stateless, JSON responses); the same `vk_` bearer guards the whole transport including `initialize`. The one tool is `capture_feedback`, taking the same nested `source` object as REST (`attachment_ids` is REST-only). Add it to a client with:

```bash
claude mcp add --transport http vocky "$VOCKY_BASE_URL/mcp" --header "Authorization: Bearer $VOCKY_API_TOKEN"
```

Self-hosting gotcha: DNS-rebinding protection allows only `localhost`/`127.0.0.1` origins by default — a self-hosted origin needs its hostname added to `VOCKY_MCP_ALLOWED_HOSTS`, or every `/mcp` call 401s regardless of the key.

## 6. Error handling — branch by branch

Every failure body (CLI and REST alike) is either a CLI-remapped message or the server's `{"detail": "..."}` verbatim. React like this:

| Status | `detail` | What to do |
|---|---|---|
| `401` | `Unauthorized` | The key is wrong or revoked. Say so, name `VOCKY_API_TOKEN`, **stop** — never retry, never fall back to another path. |
| `400` | `request body must be valid JSON` / `request body must be a JSON object` | The payload you built is malformed. Fix it once and retry once. |
| `400` | `<dotted.loc>: <message>` (e.g. `source.product: Field required`) | A schema violation. **Only the first error is reported** — fixing one may reveal another underneath it. |
| `400` | `message must not be blank` / `source.product must not be blank` | Both are required and non-blank. |
| `400` | `channel must be one of: web, mobile, support`, `project must not exceed 200 characters`, … | A semantic normalization failure — the `detail` string is actionable verbatim. |
| `503` | `capture queue unavailable` | Transient. Tell the user their feedback was **not** captured — do not silently drop it. |
| `500` | `project resolution failed` / `credential scope unavailable` | Server-side. Report it verbatim; do not retry. |

For the CLI specifically: the **exit code is always `1`** on any failure — it never encodes the HTTP status — and stderr carries the mapped/verbatim message above.

## 7. Report back

Tell the user plainly whether the feedback was captured:

- **Captured**: quote the full `request_id`.
- **Not captured**: name the failure (from the table above) and what, if anything, they need to do (usually: fix `VOCKY_API_TOKEN`, or nothing — it was a transient server error and can be retried later).

Never claim a capture succeeded without a `202` response or a `Captured —` line to point to.
