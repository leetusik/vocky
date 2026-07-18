# vocky CLI & coding-agent guide

This is the complete, self-contained guide to the **`vocky` command-line client** — enough to sign up, set up a project, mint a capture key, capture feedback, and read it back **without ever visiting the website**. It is written to be driven either by a human at a terminal or by a coding agent (Claude Code, Codex, or any runtime) acting on a user's behalf. Every step shows both the `vocky` command and the **equivalent raw HTTP**, so an agent can drive whichever it prefers.

The `vocky` CLI is a pure client of vocky's existing HTTP API. It authenticates to the account control-plane (`/auth/*`, `/app/*`) with a **session token**; it mints the per-project `vk_` **credential** that a product backend (or an agent's MCP client) later uses to capture feedback on `/api/*` + `/mcp`.

> Server vs. client: the `vocky` command is the **user/agent CLI**. The **server** console script is the separate `vocky-server` (with `vocky-worker`). Don't confuse the two.

## Install

The console script is `vocky`. PyPI publishing is planned (P6); until then install from a checkout:

```sh
uv run vocky --help          # run straight from a repo checkout, no install
uv tool install .            # install the `vocky` command onto your PATH
uvx --from . vocky --help    # run ephemerally from the checkout
```

Check the version any time with `vocky --version`.

## Configuration & the session store

**Base URL resolution** (highest precedence first):

1. `--base-url <url>` flag on the invocation
2. `VOCKY_BASE_URL` environment variable
3. the base URL stored in the config file
4. the default `http://127.0.0.1:8000`

A trailing slash is stripped. Resolve it once per invocation; every command in that invocation uses the same base URL.

**The session store.** After `signup`/`login`, the CLI writes your 30-day session token to a small JSON config file:

- Path: `~/.config/vocky/config.json` by default. Precedence: `VOCKY_CONFIG_DIR` (override) > `$XDG_CONFIG_HOME/vocky` > `~/.config/vocky`.
- Permissions: the directory is `0700` and the file is `0600` — the token never lands world-readable.
- Contents: the session `token` and an optional preferred `base_url`. This is the only session state; there is no server-side CLI state beyond the token itself.

`vocky logout` best-effort revokes the token server-side, then removes it from the file.

## For coding agents — the contract

The CLI is designed to be run headlessly, with no interactive prompts and no secret ever landing on `argv`:

- **Passwords via stdin.** Pass `--password-stdin` and pipe exactly one line to stdin. The password never appears on `argv` or in shell history:

  ```sh
  printf '%s\n' "$VOCKY_PASSWORD" | vocky signup --email you@example.com --password-stdin
  printf '%s\n' "$VOCKY_PASSWORD" | vocky login  --email you@example.com --password-stdin
  ```

  Omit `--email` to be prompted for it; supply `--email` to stay fully non-interactive. Without `--password-stdin`, the password is read from a hidden prompt (confirmed on signup).

- **Target a server per invocation** with `--base-url https://vocky.example.com` (or set `VOCKY_BASE_URL`).

- **Isolate sessions** with `VOCKY_CONFIG_DIR` — point it at a throwaway directory so parallel or ephemeral agent sessions never share or clobber a token:

  ```sh
  export VOCKY_CONFIG_DIR="$(mktemp -d)"
  printf '%s\n' "$VOCKY_PASSWORD" | vocky login --email you@example.com --password-stdin
  ```

- **Streams and exit codes.** Success output goes to **stdout**; errors go to **stderr** and the process exits **non-zero**. Parse stdout for results.

- **Generic-401 semantics.** Any authenticated command that hits a `401` (expired/invalid session) prints `Not signed in — run \`vocky login\`.` to stderr and exits non-zero — re-authenticate and retry. A bad login is deliberately generic (`Incorrect email or password.`): vocky never reveals whether the email or the password was wrong, so you cannot enumerate accounts.

- **The `vk_` key is shown once.** `vocky keys mint` prints the plaintext key exactly once, on its own line (the last line of output). Capture it then — vocky stores only a hash and cannot show it again. If you lose it, revoke it and mint a new one.

## Command reference

Global options (on `vocky` itself): `--base-url URL`, `--version`, `--help`. Every sub-command also accepts `--help`.

Auth summary: `signup` and `login` are unauthenticated; `logout`, `whoami`, and everything under `projects` / `keys` / `usage` / `feedback` send your stored **session** token as `Authorization: Bearer <session-token>`.

### Account auth (`/auth/*`)

| Command | HTTP | Notes |
| --- | --- | --- |
| `vocky signup [--email E] [--password-stdin]` | `POST /auth/signup {email,password}` → `201 {token,user,tenant}` | Creates the account + an auto-named workspace, stores the token. Password must be ≥ 8 chars. Duplicate email → the CLI says an account exists; run `login`. |
| `vocky login [--email E] [--password-stdin]` | `POST /auth/login {email,password}` → `200 {token,user,tenants}` | Stores a fresh token. Wrong email/password → generic `Incorrect email or password.` |
| `vocky logout` | `POST /auth/logout` (session bearer) → `204` | Best-effort server revoke, then clears the local token. Idempotent. |
| `vocky whoami` | `GET /auth/me` (session bearer) → `{user,tenants}` | Prints the signed-in email and workspace name(s). |

### Projects (`/app/*`)

| Command | HTTP | Notes |
| --- | --- | --- |
| `vocky projects list` | `GET /app/projects` → `{projects:[…]}` | One compact row per project (`<short-id>  <name>  (created <date>)`). Empty state points you at `projects create`. |
| `vocky projects create <NAME>` | `POST /app/projects {name}` → `201 {project}` | Name is 1–200 chars. Prints the full project id. |
| `vocky projects show <PROJECT_ID>` | `GET /app/projects/{id}` → `{project}` | Prints id / name / created_at. Unknown or cross-tenant id → `404` (never `403`). |

### Keys — per-project `vk_` credentials (`/app/*`)

| Command | HTTP | Notes |
| --- | --- | --- |
| `vocky keys mint --project <PROJECT_ID> [--name LABEL]` | `POST /app/projects/{id}/credentials {name?}` → `201 {credential, key:"vk_…"}` | Prints a show-once warning, then the plaintext `vk_…` key on its own line. Only a hash + 12-char prefix are stored. |
| `vocky keys list --project <PROJECT_ID>` | `GET /app/projects/{id}/credentials` → `{credentials:[…]}` | Metadata only (`<id>  <prefix>…  <label>  (created …, last used …, active|revoked)`). Never the full key. |
| `vocky keys revoke --project <PROJECT_ID> <CREDENTIAL_ID>` | `DELETE /app/projects/{id}/credentials/{cid}` → `204` | Soft-revoke; the key stops working immediately and stays listed as revoked. |

### Usage (`/app/*`)

| Command | HTTP | Notes |
| --- | --- | --- |
| `vocky usage [--project <PROJECT_ID>] [--start ISO8601] [--end ISO8601]` | `GET /app/usage` or `GET /app/projects/{id}/usage` → `{window,totals,daily_counts,projects|credentials}` | Whole-tenant totals + a project list, or one project's totals + its credentials' last-used. `--start`/`--end` map to `start_ingested_at`/`end_ingested_at`; the window defaults to the last 30 days. Derived volume only — no billing/metering. |

### Feedback — cross-project read (`/app/feedback`, read-only)

| Command | HTTP | Notes |
| --- | --- | --- |
| `vocky feedback list [--project P] [--limit N] [--cursor C]` | `GET /app/feedback` → `{records:[…], next_cursor?}` | Newest-first compact rows: `<short-id>  <like/dislike/·>  <short-project-id>  <ingested-date>  <truncated message>`. A `next_cursor` prints a `— more: rerun with --cursor …` hint. |
| `vocky feedback search <QUERY> [--project P] [--limit N] [--cursor C]` | `GET /app/feedback?q=<QUERY>` → `{records:[…], next_cursor?}` | Case-insensitive **substring** match, **Korean-safe** (`결제` matches `결제 오류` and `결제를…`). Same row format as `list`. |
| `vocky feedback show <FEEDBACK_ID>` | `GET /app/feedback/{id}` → `{record + comments[] + attachments[]}` | Full record plus operator comments and attachment links. Unknown/cross-tenant id → `404` (never `403`). |

`--limit` is capped at 100 by the server; `--project` narrows to one owned project (malformed → `400`, not-owned → `404`). Feedback **management** (edit/delete/comment) is deliberately **not** in the CLI — it lives on the `vk_`-keyed `/api/project/feedback` surface for a product's own admin panel.

## End-to-end walkthrough (for an agent)

The full spine, each step showing the `vocky` command and the equivalent raw HTTP. This is the exact flow an agent runs to onboard a user and start capturing feedback. It assumes a local server at `http://127.0.0.1:8000`; add `--base-url` / use the full URL for a remote one.

### 1. Sign up (or log in)

```sh
printf '%s\n' "$VOCKY_PASSWORD" | vocky signup --email you@example.com --password-stdin
```

Equivalent raw HTTP:

```sh
curl -X POST "http://127.0.0.1:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"a-strong-password"}'
# -> 201 { "token": "<session-token>", "user": {...}, "tenant": {...} }
```

The CLI stores `<session-token>` in the config file; a raw-HTTP driver keeps it and sends it as `Authorization: Bearer <session-token>` on every `/app/*` call below. (Already have an account? Use `vocky login` / `POST /auth/login`, which returns a fresh token and your `tenants`.)

### 2. Create a project

```sh
vocky projects create "marketing-site"
# -> Created project "marketing-site" (<project-id>).
```

Equivalent raw HTTP:

```sh
curl -X POST "http://127.0.0.1:8000/app/projects" \
  -H "Authorization: Bearer <session-token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"marketing-site"}'
# -> 201 { "project": { "id": "<project-id>", "name": "marketing-site", ... } }
```

### 3. Mint a per-project `vk_` key (shown once)

```sh
vocky keys mint --project <project-id>
# -> Copy this key now — it is shown only once and cannot be recovered. ...
# -> vk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

Equivalent raw HTTP:

```sh
curl -X POST "http://127.0.0.1:8000/app/projects/<project-id>/credentials" \
  -H "Authorization: Bearer <session-token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"web-backend"}'
# -> 201 { "credential": {...}, "key": "vk_..." }
```

Store the `vk_…` key as a secret in the product backend. It is the credential for `/api/*` capture/read and `/mcp` — **not** the session token.

### 4. Capture feedback with the `vk_` key

Capture is not a CLI command in this release (the CLI does account setup + reads); a product backend or an agent captures directly over `/api/*` with the `vk_` key:

```sh
curl -X POST "http://127.0.0.1:8000/api/feedback" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer vk_<your-project-key>" \
  -d '{
    "message": "Pricing page feedback button was hard to find",
    "source": {"product": "marketing-site", "integration": "web-backend"},
    "feedback_value": 2,
    "channel": "web",
    "user_id": "user_123",
    "trigger_type": "comment",
    "target_type": "surface"
  }'
# -> 202 { "request_id": "...", "accepted_at": "...", "status": "accepted" }
```

`202` means the job was accepted for background persistence; the record becomes queryable once the worker writes it. `message` and `source.product` are required; every other field is optional (see `docs/current/experience.md` for the full field set). A missing/invalid/revoked key → `401`.

### 5. Read it back

```sh
vocky feedback search "pricing"       # Korean-safe substring across all your projects
vocky feedback list                   # newest-first, all projects
vocky feedback show <feedback-id>     # one record in full (+ operator comments, attachments)
vocky usage                           # capture volume for the workspace
```

Equivalent raw HTTP (session token):

```sh
curl "http://127.0.0.1:8000/app/feedback?q=pricing&limit=50" \
  -H "Authorization: Bearer <session-token>"
# -> 200 { "records": [ { "id": "...", "project_id": "...", ... } ], "next_cursor"?: "..." }
```

A product's own admin panel can instead read+manage its project's feedback with the **same `vk_` key** over `/api/project/feedback`, and a product user's own "my feedback" view uses the scoped `GET /api/feedback?user_id=…&source_product=…`. See `docs/current/experience.md`.

## Agent-decided write-only capture over MCP

When the product is an **AI agent**, the agent can decide at its own judgement to capture feedback through vocky's **write-only** MCP endpoint instead of calling `/api/*` directly. Point the agent's MCP client at `<base-url>/mcp` and authenticate with the **same project `vk_` key** you minted above — the whole endpoint (including the `initialize` handshake) requires it.

- There is exactly **one** tool: `capture_feedback` (write-only; there are no read/query tools).
- Its inputs are the same capture fields as REST **minus** `attachment_ids`, with `source` the only nested object; the project is implicit in the key (no `project_id` parameter).
- A successful call returns the same capture receipt as REST (`{request_id, accepted_at, status: "accepted"}`) — the record becomes queryable after the worker persists it.

Use MCP capture only when an agent runtime is intentionally deciding to record voice-of-customer feedback; explicit human UI actions (like/dislike buttons, page/widget feedback) should still go through `/api/*` REST capture. The full MCP client shape and tool inputs are documented in `docs/current/experience.md` ("Agent Capture Over MCP").

## See also

- `docs/current/experience.md` — the product integration guide: REST capture fields, MCP capture, and every read surface.
- `docs/current/api.md` — the authoritative API contracts (`/auth/*`, `/app/*`, `/api/*`, `/mcp`, Admin REST).
- `README.md` — project overview, self-hosting, and the CLI quickstart.
