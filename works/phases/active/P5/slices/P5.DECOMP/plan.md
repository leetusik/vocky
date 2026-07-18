# P5.DECOMP — decompose "CLI & Agent-First Onboarding"

You are executing the **DECOMP slice** of phase **P5**. Your job is **only** to (a) create the bare middle-slice folders with `new-slice`, and (b) seed `works/phases/active/P5/phase.md`. Do **not** pre-fill any middle slice's `plan.md`, write **no** implementation code, do **not** commit, do **not** transition slice/phase status, and do **not** run `doc-new-version`. Write your `result.md` and append cross-slice notes to `phase.md`, then return a structured verdict.

Read first: `works/phases/active/P5/intent.md`, the current `phase.md`, and `AGENTS.md`. The orchestrator has already done the research below — record it; don't re-derive it.

## Context (record in phase.md → Context)

P5 delivers a **vocky CLI** so a user working inside Claude Code or Codex can sign up, log in, set up credentials, and use vocky **without visiting the website**, plus **agent-readable guide docs** so a coding agent can drive that whole flow on the user's behalf.

Key framing: the backend (Starlette, all `Authorization: Bearer`, no cookies) already exposes the complete flow. **The CLI is a pure client — no backend change** (mirrors how P4's web app was built). `src/vocky/smoke.py` (`_provision_ingest_key` + `run_rest_smoke`) is a **working headless reference** for the `signup → create project → mint vk_ key → capture → read` spine using `httpx`.

The live landing page's public **"Docs" link points at the repo README** (`web/src/content/landing.ts`, `DOCS_URL = "https://github.com/leetusik/vocky#readme"`), and that README is **stale** (documents the retired single-tenant static-token model). Refreshing it is part of P5's goal and is durable-truth doc work. No `llms.txt` / agent-usage doc exists yet — clean gap.

## Operator decisions (record verbatim in phase.md under a clear heading)

1. **Auth flow** → direct email + password (no device/browser flow; **no backend change**).
2. **CLI command name** → `vocky`; **rename the existing server console entry `vocky` → `vocky-server`** (update README / Makefile / Dockerfile / docker-compose references to `uv run vocky` as the server).
3. **CLI framework** → **Typer**, promoted from transitive (via `mcp[cli]`) to a **direct** dependency.
4. **CLI surface scope** → onboarding **+ feedback read** (no `capture` command in P5).
5. **Distribution** → `[project.scripts]` console script + `uv tool install` / `uvx`; **PyPI publish deferred to P6**.

**Not a design-gate phase** — CLI terminal output + text docs, not product visual design. `design-cowork` does not apply.

## Findings & Notes (record in phase.md → Findings & Notes — the shared context every later slice reads)

- **API contract the CLI drives** (all `Authorization: Bearer`, no cookies; base default `http://127.0.0.1:8000`):
  - `/auth/*`: `POST /auth/signup {email,password}` → `201 {token,user,tenant}`; `POST /auth/login {email,password}` → `200 {token,user,tenants}`; `POST /auth/logout` (bearer) → `204` idempotent; `GET /auth/me` (bearer) → `{user,tenants}`. Session token: opaque no-prefix `token_urlsafe(32)`, JSON body, **30-day TTL**. Password `min_length=8`. `401` is generic (`invalid email or password`) — no enumeration.
  - `/app/*` (session bearer): `GET /app/tenant`; `GET|POST /app/projects` (`{name}` 1–200 chars); `GET /app/projects/{id}`; `POST /app/projects/{id}/credentials` (opt `{name}`) → `201 {credential, key:"vk_…"}` **key shown once**; `GET /app/projects/{id}/credentials` (metadata only); `DELETE /app/projects/{id}/credentials/{cid}` → `204` soft-revoke. `GET /app/usage` (tenant volume + projects); `GET /app/projects/{id}/usage` (project volume + credentials). Cross-tenant id → **404 (never 403)**.
  - `/app/feedback` (session bearer): `GET /app/feedback` cross-project list/search (`q` Korean-safe substring, `project_id` narrow, standard filters, `limit`, `cursor` keyset → `next_cursor`); `GET /app/feedback/{id}`; attachment download. Records include `project_id`.
  - `vk_` key authorizes `/api/*` (capture/read) + `/mcp` — the external-service/agent path; the CLI mints it for the user but the CLI itself authenticates to `/app/*` with the **session** token.
- **Packaging**: single root `pyproject.toml`, src-layout, package `vocky`, `hatchling`, Python `>=3.12,<3.14`, `[tool.uv]` present. `httpx` (sync `httpx.Client`) already a **direct** dep and already used in `smoke.py`. `pydantic-settings` config via `get_settings()` (`env_prefix`/`VOCKY_` alias convention). Existing `[project.scripts]`: `vocky = "vocky.main:main"` (server), `vocky-smoke`, `vocky-worker`. `typer`/`click` present **transitively only** (via `mcp[cli]`) — promote `typer` to a direct dep. Tests: pytest + pytest-asyncio (`asyncio_mode=auto`), `fakeredis`; `tests/` flat. **No linter/formatter configured.**
- **No home-dir config convention exists** (`grep` for XDG / `Path.home` / `expanduser` was empty) — the CLI introduces `~/.config/vocky/` (XDG-aware, `VOCKY_CONFIG_DIR` override), token file `0600`.
- **Server-rename blast radius**: `uv run vocky` as the server appears in README ("Running The App Directly"), Makefile, Dockerfile CMD, docker-compose. All must move to `vocky-server`.
- **UX copy to mirror** (from `web/src/content/*`): show-once key panel — "This is the only time this key will ever be shown. It cannot be recovered — if you lose it, revoke it and create a new one." Signup: "A workspace is created for you automatically." Generic `401`: "Incorrect email or password."
- **Docs gap**: stale README is the public Docs target; packaged `src/vocky/admin_assets/docs.json` is also stale but slated for **P6** removal — leave it. No agent-usage/`llms.txt` doc — S5 creates one.

## Middle slices to create (run `new-slice` for each)

```
python3 scripts/workflow.py new-slice --phase P5 --slice P5.S1 --name "CLI foundation: Typer app, vocky script + server->vocky-server rename, config/credential store, httpx API client" --kind implementation --risk medium --order 1 --depends-on P5.DECOMP
python3 scripts/workflow.py new-slice --phase P5 --slice P5.S2 --name "Auth commands: signup/login/logout/whoami over /auth/*" --kind implementation --risk medium --order 2 --depends-on P5.S1
python3 scripts/workflow.py new-slice --phase P5 --slice P5.S3 --name "Projects, credentials & usage commands over /app/* (show-once key UX)" --kind implementation --risk medium --order 3 --depends-on P5.S1
python3 scripts/workflow.py new-slice --phase P5 --slice P5.S4 --name "Feedback read commands: feedback list/search/show over /app/feedback" --kind implementation --risk medium --order 4 --depends-on P5.S1
python3 scripts/workflow.py new-slice --phase P5 --slice P5.S5 --name "Agent-readable guide docs + README refresh (public Docs target)" --kind implementation --risk medium --order 5 --depends-on P5.S2
```

(Use `--depends-on` exactly as above; it is advisory. `--risk` selects the executor tier, so keep all five `medium` — client code with real UX/error/security judgment, none fully mechanical, none architecturally risky.)

### Slice intents (record in phase.md → Decomposition; do NOT pre-fill their plan.md)

- **P5.S1 — Foundation.** New `src/vocky/cli/` Typer app. Add `typer` as a direct dependency. Register console script `vocky = "vocky.cli:app"` and **rename** the server entry to `vocky-server = "vocky.main:main"`, updating every server `uv run vocky` reference (README / Makefile / Dockerfile / docker-compose). Config/credential store under `~/.config/vocky/` (XDG-aware, `VOCKY_CONFIG_DIR` override) holding base URL + session token, written `0600`. Shared httpx client: base-URL resolution (`--base-url` → `VOCKY_BASE_URL` env → config → `http://127.0.0.1:8000`), Bearer injection, uniform error mapping (any `401` → "run `vocky login`"). Root `vocky --help` + `--version`. Riskiest slice (packaging rename ops blast radius + on-disk token).
- **P5.S2 — Auth.** `vocky signup|login|logout|whoami` over `/auth/*`; store token in the config store, clear on logout. Mirror web copy (password ≥ 8; generic `401`; auto-created workspace).
- **P5.S3 — Projects/keys/usage.** `vocky projects list|create|show`, `vocky keys mint|list|revoke`, `vocky usage` (tenant + per-project) over `/app/*`. `keys mint` prints the `vk_` key once with the show-once warning.
- **P5.S4 — Feedback read.** `vocky feedback list|search|show` over `/app/feedback` (cross-project, Korean-safe substring `q`, keyset pagination `--cursor`/`next_cursor`, `--project` narrowing). Read-only — management stays on `/api/project/feedback`.
- **P5.S5 — Guide docs + README.** Refresh the stale README to the accounts/`vk_` flow; add a dedicated agent-readable onboarding guide (walks signup→project→key→capture→read with real `vocky` commands + equivalent raw HTTP, cross-references `/mcp`). Self-documenting `--help`. Append **"Doc impact"** notes to `phase.md` (experience/product) for REVIEW to consolidate — never run `doc-new-version` here.

## Definition of done for this slice
- Five `todo` slices `P5.S1..P5.S5` exist between `P5.DECOMP` and `P5.REVIEW` with the orders/kinds/risks above.
- `phase.md` seeded: Context, Decomposition (slice table + rationale + slice intents), Findings & Notes (all bullets above), Constraints (pure client / no backend change; keep tests small; `uv run` conventions; token file `0600`; leave stale packaged admin docs to P6), and the 5 operator decisions.
- No `plan.md` pre-filled for any middle slice; no source/doc changes; nothing committed.
- `python3 scripts/workflow.py validate` passes.
