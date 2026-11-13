# P5.S5 — Agent-readable guide docs + README refresh

## Context

Final middle slice of **P5**. The CLI (S1–S4) is fully built and verified; now make vocky **usable without visiting the website** by documenting it — for both humans and coding agents. The intent's headline: "gives proper help docs or guide docs so that a user don't even [need] to visit our website but use the vocky feature," with agent-readable onboarding as a first-class scenario.

Read `works/phases/active/P5/phase.md` first (Findings, Constraints, S1–S4 notes). Two problems to fix:
1. **`README.md` is comprehensively stale** and it is the **live public "Docs" link** (`web/src/content/landing.ts` `DOCS_URL = ...#readme`). It still describes a single-tenant, static-`VOCKY_API_AUTH_TOKEN` service with no accounts, no `vk_` keys, no CLI, no web app, no MCP. Every `/api/*` example uses the retired static token.
2. **There is no agent-readable onboarding guide** — no `llms.txt`, no "how to use vocky" doc. Clean gap.

Ground the refresh in the durable docs already consolidated (which S5 must **not** contradict): read `docs/current/product.md`, `experience.md`, `api.md`, `architecture.md`. The real command surface to document is now fixed (verify against `src/vocky/cli/`): `vocky signup|login|logout|whoami`, `vocky projects list|create|show`, `vocky keys mint|list|revoke`, `vocky usage`, `vocky feedback list|search|show`.

## Approach

**1. Refresh `README.md`** — reframe to current reality, correct the auth model, add the CLI. Keep the still-valid Compose/Cloudflare self-hosting mechanics; fix what's wrong:
- **Top matter** ("What Vocky Is", "Current Pre-MVP", "What It Will Not Do", "Access Modes"): free **multi-tenant SaaS** — accounts (email+password) → tenant/workspace → projects → per-project `vk_` keys; surfaces are the **web app**, the **`vocky` CLI**, server-to-server **`/api/*` REST capture**, and write-only **`/mcp`** agent capture. Drop "single-tenant"; note the packaged Admin Web UI is **superseded by the web app** (removal is P6).
- **New prominent section "Quickstart — the `vocky` CLI"** (the headline addition, placed high): install (`uv tool install .` / `uvx --from . vocky` / `uv run vocky` in-repo; PyPI publish is P6), then the spine as real commands — `vocky signup` → `vocky projects create "<name>"` → `vocky keys mint --project <id>` (show-once `vk_…`) → send that key as `Authorization: Bearer vk_…` to `POST /api/feedback` → `vocky feedback search "<q>"`. Include a **"For coding agents"** subsection: fully headless via `--password-stdin`, per-invocation `--base-url`, and an isolated `VOCKY_CONFIG_DIR`; note the 30-day session token lives at `~/.config/vocky/config.json` (`0600`).
- **Correct the `/api/*` auth model everywhere**: replace `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` in the curl/httpx examples with a per-project `vk_` key, and state that `/api/*` auth is now **mandatory per-project credential** (the static `VOCKY_API_AUTH_TOKEN` is retired; `VOCKY_ADMIN_AUTH_TOKEN` still guards `/admin/api/*`). Update the "Running The App Directly" endpoint list to include `/auth/*`, `/app/*`, `/mcp` (the `vocky-server` rename already landed in S1).
- Keep it honest and accurate — cross-check each claim against the durable docs; don't re-introduce retired-model language and don't over-claim (e.g. deployment is still P6).

**2. New agent-readable guide `docs/cli.md`** — the complete, self-contained onboarding walkthrough, linked from the README:
- Full command reference (every group, with example invocations and output shape).
- The end-to-end agent walkthrough (signup → project → key → capture via `/api/feedback` → read via `vocky feedback`), each step showing the `vocky` command **and** the equivalent raw HTTP so an agent can drive either.
- A short **"For coding agents"** contract: `--password-stdin`, `VOCKY_CONFIG_DIR` for isolated sessions, generic-401 semantics, and a cross-reference to **`/mcp`** for agent-decided write-only capture (point the MCP client at `<base>/mcp` with a project `vk_` key; single `capture_feedback` tool).
- (`docs/` already holds non-versioned `reference/` material, so a hand-written `docs/cli.md` fits; it is a product doc, distinct from the versioned `docs/current/*`.)

**3. `--help` polish** — Typer already auto-generates `--help` for every command (help strings written in S1–S4). Skim the root + each group's help for accuracy; adjust only wording that's now wrong. No structural change.

## Files
- `README.md` — refreshed (top matter, new CLI quickstart + agent section, corrected `/api/*` auth + surface lists).
- `docs/cli.md` — **new**; the agent-readable command reference + walkthrough + `/mcp` cross-ref.
- (Optional, only if trivially clean) minor `--help` string tweaks in `src/vocky/cli/*.py`.

## Tests / verification (docs slice — verify by reading + driving)

- The commands documented must match reality: run `uv run vocky --help`, `uv run vocky projects --help`, `uv run vocky keys --help`, `uv run vocky feedback --help` and confirm every documented command/flag exists and matches the guide.
- Spot-run the README/guide quickstart against the live local server (`http://127.0.0.1:8000`) end-to-end with a throwaway `VOCKY_CONFIG_DIR` (signup → project → key → `curl POST /api/feedback` with the `vk_` key → `vocky feedback search`) to confirm the documented flow actually works as written. If the server is unreachable, say so and rely on `--help` cross-checking.
- Grep the refreshed `README.md` for stale tokens — no remaining `Authorization: Bearer <VOCKY_API_AUTH_TOKEN>` in `/api/*` capture examples, no "single-tenant" framing.
- `uv run pytest` (full suite) stays green; `python3 scripts/workflow.py validate` passes.

## Notes for the executor
- Docs/CLI-help only — **no** server/model/endpoint change, and do not touch `src/vocky/admin_assets/docs.json` (stale, P6 removal).
- Append **"Doc impact"** notes to `phase.md` for REVIEW to consolidate into the versioned durable docs: `experience.md` (the CLI onboarding journey + commands), `product.md` (the CLI as a first-class user surface alongside the web app), `operations.md` (the `vocky-server` rename + CLI install/config + `VOCKY_CONFIG_DIR`), and note that `api.md`/`architecture.md` need **no contract change** (the CLI is a pure client). Do **not** run `doc-new-version` — that's REVIEW's job.
- Write `result.md`; do not commit or transition status (the orchestrator does both).
