# Phase P5: CLI & Agent-First Onboarding

_Intent: see [intent.md](intent.md)._

## Objective

Ship a vocky CLI so a user can sign up, log in, and configure credentials from Claude Code or Codex, with agent-readable help/guide docs so vocky is fully usable without visiting the website.

## Context

P5 delivers a **vocky CLI** so a user working inside Claude Code or Codex can sign up, log in, set up credentials, and use vocky **without visiting the website**, plus **agent-readable guide docs** so a coding agent can drive that whole flow on the user's behalf.

Key framing: the backend (Starlette, all `Authorization: Bearer`, no cookies) already exposes the complete flow. **The CLI is a pure client — no backend change** (mirrors how P4's web app was built). `src/vocky/smoke.py` (`_provision_ingest_key` + `run_rest_smoke`) is a **working headless reference** for the `signup → create project → mint vk_ key → capture → read` spine using `httpx`.

The live landing page's public **"Docs" link points at the repo README** (`web/src/content/landing.ts`, `DOCS_URL = "https://github.com/leetusik/vocky#readme"`), and that README is **stale** (documents the retired single-tenant static-token model). Refreshing it is part of P5's goal and is durable-truth doc work. No `llms.txt` / agent-usage doc exists yet — clean gap.

**Not a design-gate phase** — CLI terminal output + text docs, not product visual design. `design-cowork` does not apply.

## Operator decisions

Recorded verbatim from the DECOMP plan — these are the confirmed operator decisions that shape every middle slice:

1. **Auth flow** → direct email + password (no device/browser flow; **no backend change**).
2. **CLI command name** → `vocky`; **rename the existing server console entry `vocky` → `vocky-server`** (update README / Makefile / Dockerfile / docker-compose references to `uv run vocky` as the server).
3. **CLI framework** → **Typer**, promoted from transitive (via `mcp[cli]`) to a **direct** dependency.
4. **CLI surface scope** → onboarding **+ feedback read** (no `capture` command in P5).
5. **Distribution** → `[project.scripts]` console script + `uv tool install` / `uvx`; **PyPI publish deferred to P6**.

## Decomposition

Five implementation slices, all `risk: medium` (client code with real UX/error/security judgment — none fully mechanical, none architecturally risky). All build on the S1 foundation.

| Slice | Order | Kind | Risk | Depends on | Name |
|-------|-------|------|------|-----------|------|
| P5.S1 | 1 | implementation | medium | P5.DECOMP | CLI foundation: Typer app, `vocky` script + server→`vocky-server` rename, config/credential store, httpx API client |
| P5.S2 | 2 | implementation | medium | P5.S1 | Auth commands: signup/login/logout/whoami over `/auth/*` |
| P5.S3 | 3 | implementation | medium | P5.S1 | Projects, credentials & usage commands over `/app/*` (show-once key UX) |
| P5.S4 | 4 | implementation | medium | P5.S1 | Feedback read commands: feedback list/search/show over `/app/feedback` |
| P5.S5 | 5 | implementation | medium | P5.S2 | Agent-readable guide docs + README refresh (public Docs target) |

**Rationale.** S1 is the spine — the Typer app, the packaging rename, the on-disk config/credential store, and the shared httpx client that every command reuses; it carries the packaging-rename blast radius and the on-disk token, so it is the riskiest slice and everything else depends on it. S2/S3/S4 each layer one coherent command group on top of that foundation (auth, then projects/keys/usage, then feedback read), split by API surface (`/auth/*`, `/app/*` project side, `/app/feedback`) so each is independently reviewable and none is a giant catch-all. S5 comes last because the guide docs must describe the real, finished command surface — it depends on S2 (the auth entry point of the walkthrough) and in practice references all of S1–S4. Keeping all five `medium` routes them to `slice-executor-mid`: real judgment on UX copy, error mapping, and token-file security, but no architectural risk that would warrant `high`, and nothing mechanical enough for `low`.

### Slice intents (do NOT pre-fill their plan.md — recorded here for the orchestrator to plan each slice at its turn)

- **P5.S1 — Foundation.** New `src/vocky/cli/` Typer app. Add `typer` as a direct dependency. Register console script `vocky = "vocky.cli:app"` and **rename** the server entry to `vocky-server = "vocky.main:main"`, updating every server `uv run vocky` reference (README / Makefile / Dockerfile / docker-compose). Config/credential store under `~/.config/vocky/` (XDG-aware, `VOCKY_CONFIG_DIR` override) holding base URL + session token, written `0600`. Shared httpx client: base-URL resolution (`--base-url` → `VOCKY_BASE_URL` env → config → `http://127.0.0.1:8000`), Bearer injection, uniform error mapping (any `401` → "run `vocky login`"). Root `vocky --help` + `--version`. Riskiest slice (packaging rename ops blast radius + on-disk token).
- **P5.S2 — Auth.** `vocky signup|login|logout|whoami` over `/auth/*`; store token in the config store, clear on logout. Mirror web copy (password ≥ 8; generic `401`; auto-created workspace).
- **P5.S3 — Projects/keys/usage.** `vocky projects list|create|show`, `vocky keys mint|list|revoke`, `vocky usage` (tenant + per-project) over `/app/*`. `keys mint` prints the `vk_` key once with the show-once warning.
- **P5.S4 — Feedback read.** `vocky feedback list|search|show` over `/app/feedback` (cross-project, Korean-safe substring `q`, keyset pagination `--cursor`/`next_cursor`, `--project` narrowing). Read-only — management stays on `/api/project/feedback`.
- **P5.S5 — Guide docs + README.** Refresh the stale README to the accounts/`vk_` flow; add a dedicated agent-readable onboarding guide (walks signup→project→key→capture→read with real `vocky` commands + equivalent raw HTTP, cross-references `/mcp`). Self-documenting `--help`. Append **"Doc impact"** notes to `phase.md` (experience/product) for REVIEW to consolidate — never run `doc-new-version` here.

## Findings & Notes

The shared context every later slice reads. Seeded by DECOMP; each slice appends its own durable notes when it finishes.

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

## Constraints

- **Pure client, no backend change.** The Starlette backend already exposes the complete flow; the CLI is a client only (mirrors P4's web app). Do not modify server endpoints, auth, or models in this phase.
- **`uv` conventions.** Application Python runs through `uv` (`uv run`, `uv add typer`, `uv lock`, `uv sync`) — no `pip`/`venv`/bare `python`. The workflow manager is the only `python3` exception.
- **Token file `0600`.** The on-disk session token under `~/.config/vocky/` is written with `0600` permissions; base URL + token live in the config store, not env-only.
- **Keep tests small.** Terse, high-value cases only — no fixture/scaffolding sprawl. Prefer running the code / a small smoke check; grow a suite only if risk warrants.
- **Leave the stale packaged admin docs to P6.** `src/vocky/admin_assets/docs.json` is stale but slated for P6 removal — do not touch it in P5. Only the public README (the landing "Docs" target) and the new agent-usage guide are P5's doc scope.
- **Docs versioned once, at REVIEW.** Middle slices that change durable truth append a one-line "Doc impact" note here; never run `doc-new-version` outside the REVIEW slice.

## Doc impact

_Running list of durable-truth changes for the REVIEW slice to consolidate into doc versions. Middle slices append here; do not version docs per slice._

-

## Open Questions

-
