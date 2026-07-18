# P5.S5 result — Agent-readable guide docs + README refresh

**Status: done.** Made vocky usable without the website by documenting the finished CLI + corrected API model, for both humans and coding agents. Docs/CLI-help only — no server/model/endpoint change, no source edits.

## What I wrote

### `README.md` (refreshed — the public "Docs" landing target)
Full rewrite off the stale single-tenant/static-token framing to the current **free multi-tenant SaaS**:
- **Top matter** reframed: accounts (email+password) → tenant/workspace → projects → per-project `vk_` keys; four surfaces named up front — the **web app**, the **`vocky` CLI**, **`/api/*` REST capture**, and write-only **`/mcp`**. Notes the packaged Admin Web UI is superseded by the web app (removal is P6). Dropped all "single-tenant" language.
- **New prominent "Quickstart — the `vocky` CLI"** section placed high: install (`uv run vocky` in-repo / `uv tool install .` / `uvx --from . vocky`; PyPI publish is P6), then the spine as real commands — `vocky signup` → `vocky projects create` → `vocky keys mint --project <id>` (show-once `vk_…`) → `curl POST /api/feedback` with `Authorization: Bearer vk_…` → `vocky feedback search` / `list` / `usage`. Includes a **"For coding agents"** subsection: `--password-stdin`, `--base-url`, `VOCKY_CONFIG_DIR`, the `~/.config/vocky/config.json` `0600` token, and exit-code/stderr semantics.
- **`/api/*` auth corrected everywhere**: every capture/read example now uses a per-project `vk_` key; states auth is mandatory per-project credential; the only remaining `VOCKY_API_AUTH_TOKEN` mentions are the explicit "is retired" notes. `VOCKY_ADMIN_AUTH_TOKEN` kept for `/admin/api/*`.
- **"Running The App Directly"** endpoint list updated to `/auth/*`, `/app/*`, `/api/feedback`, `/api/project/*`, `/mcp`, `/admin/api/*`, `/admin`; server entry is `uv run vocky-server` (+ `vocky-worker`), with a note distinguishing it from the bare `vocky` CLI.
- Fixed the **smoke** description (now signs up + provisions a real `vk_` key, no static token) and the **Cloudflare `.env`** snippet (dropped `VOCKY_API_AUTH_TOKEN`; added `VOCKY_MCP_ALLOWED_HOSTS` for a public `/mcp`). Kept the still-valid Compose/Cloudflare mechanics. Added a "Documentation" section linking `docs/cli.md`.

### `docs/cli.md` (new — the agent-readable guide)
Self-contained CLI & coding-agent guide: install; base-URL resolution + the session store (`VOCKY_CONFIG_DIR`, `0600`); a **"For coding agents"** contract (`--password-stdin`, isolated sessions, stdout/stderr + exit codes, generic-401, show-once key); a **full command reference** (auth / projects / keys / usage / feedback) as tables mapping each `vocky` command to its endpoint and response shape; an **end-to-end walkthrough** showing the `vocky` command **and** the equivalent raw HTTP for every step (signup → project → key → capture → read); and an **MCP cross-reference** (point the client at `<base>/mcp` with a project `vk_` key; single write-only `capture_feedback` tool). Linked from the README.

### `--help`
No change. Skimmed root + every group + representative leaf help; every string is still accurate to live behavior — nothing became wrong this slice. Kept the slice source-free.

## Key decisions
- **Docs-only, zero source edits** — leaves `pytest` unaffected and keeps the slice clean (the plan allowed trivial `--help` tweaks only "if now wrong"; none were).
- **`docs/cli.md` is a hand-written product doc** (like `docs/reference/*`), not a versioned `docs/current/*`. The durable-truth deltas are recorded as a `phase.md` "Doc impact" note for REVIEW to version into `product.md`/`experience.md`/`operations.md` — I did **not** run `doc-new-version`.
- **Kept the honest, thorough self-hosting body** of the README (Compose, Cloudflare, Admin REST) and fixed only what the new model made wrong, rather than gutting it.

## Verification (all run, all clean)

- **`--help` cross-check**: `uv run vocky --help`, `... projects/keys/feedback --help`, `... usage/keys mint/feedback search/signup --help` — every documented command/flag exists and matches the guide (`keys mint` requires `--project`; `usage` takes `--project/--start/--end`; `feedback search` takes `QUERY` + `--project/--limit/--cursor`; `signup`/`login` take `--email` + `--password-stdin`).
- **Live end-to-end spot-run — RAN, passed** against the running local server (`GET /healthz` → `{"service":"vocky","status":"ok"}`), with a throwaway `VOCKY_CONFIG_DIR`:
  - `vocky signup --email … --password-stdin` → signed up + workspace auto-created; `vocky whoami` confirmed.
  - `vocky projects create` → project id returned; `vocky projects list` shows it.
  - `vocky keys mint --project <id>` → show-once `vk_…` printed; `vocky keys list` shows the prefix/metadata.
  - `curl -X POST /api/feedback -H "Authorization: Bearer vk_…"` with a Korean message → `202 {status:"accepted"}`.
  - No-key `POST /api/feedback` → `401` (mandatory-auth confirmed).
  - After worker persistence: `vocky feedback search "결제"` (Korean), `vocky feedback list`, `vocky feedback show <id>`, `vocky usage` all returned the captured record / totals. The documented quickstart works verbatim.
- **Grep for stale strings**: no `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` in any `/api/*` example; no "single-tenant" framing in `README.md` (the two `VOCKY_API_AUTH_TOKEN` hits are the "is retired" notes). `Bearer vk_` present in the capture examples.
- **`uv run pytest`** → `187 passed in ~8s` (green).
- **`python3 scripts/workflow.py validate`** → `Workflow validation passed.`

## Doc impact
Appended an `[S5]` entry to the phase's "Doc impact" list (`product.md` — CLI as a first-class user surface alongside the web app; `experience.md` — the CLI onboarding journey + commands as a documented path; `operations.md` — the `vocky-server` rename + CLI install/config + `VOCKY_CONFIG_DIR`) and explicitly noted **no `api.md`/`architecture.md` contract change** (the CLI is a pure client). REVIEW consolidates these into versioned docs.

## Deviations from plan
None. Executed the plan as written; the one discretionary item (`--help` polish) was correctly a no-op because nothing was inaccurate.

## Files changed
- `README.md` (refreshed)
- `docs/cli.md` (new)
- `works/phases/active/P5/phase.md` (Doc-impact + S5 cross-slice notes)
- `works/phases/active/P5/slices/P5.S5/result.md` (this file)
