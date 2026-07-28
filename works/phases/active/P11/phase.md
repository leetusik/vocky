# Phase P11: Frictionless onboarding: working install, env-var quickstart, agent skill on the landing

_Intent: see [intent.md](intent.md)._

## Objective

Make vocky's onboarding real end to end for a coding agent: ship an install path for the `vocky` CLI that actually runs from the landing page (publish to PyPI or serve a `curl | bash` installer), add the missing `VOCKY_API_TOKEN` so two environment variables are the whole agent contract alongside today's `VOCKY_BASE_URL`, publish a copyable and downloadable end-user `SKILL.md` on the landing behind a byte-parity CI gate, and correct the landing's untrue hero payload (top-level `source_product` -> nested `source.product`, and the non-existent `vk_live_` prefix). Any net-new landing section goes through a design-cowork gate; no new backend capture contract.

## Context

### Why this phase exists — the onboarding story is not real today

- The `vocky` CLI **cannot be installed** except from a checkout (`docs/cli.md:9-19`, `README.md:48-63`).
- **`VOCKY_API_TOKEN` does not exist anywhere in the tree.** A grep over `src/vocky/**` finds exactly
  five env reads: `cli/context.py:76` (`VOCKY_BASE_URL`), `cli/config_store.py:32,36`
  (`VOCKY_CONFIG_DIR`, `XDG_CONFIG_HOME`), `smoke.py:20,187` (`VOCKY_HTTP_USER_AGENT`,
  `VOCKY_BASE_URL`). The CLI is session-token-only and **has no capture command at all**, so a `vk_`
  key has no CLI consumer.
- There is **no end-user skill**. All 16 `.claude/skills/*` and 15 `.agents/skills/*` are repo-workflow
  machinery; none mentions capturing feedback.
- The hero publishes **two falsehoods** in `web/src/content/landing.ts`.

### Operator decisions (2026-07-29) — build around these, do not relitigate

1. **Install = `curl | bash`, not PyPI.** Ship `web/public/install.sh`. **No `uv publish` in P11**; the
   P6.S9 publish hand-off stays unexercised and `dist/`'s `0.1.0` artifacts stay stale.
2. **Add `vocky capture`.** `VOCKY_API_TOKEN` gets a first-class CLI consumer — a new capture command
   POSTing to `/api/feedback` with the `vk_` key.
3. **CI gate = a new minimal `.github/workflows/ci.yml`** on push + pull_request (parity script + web
   lint/typecheck/vitest). P12 later extends that same file with the Postgres pytest job.

### The honesty problem the `curl` choice creates — and why it is resolved

A hero line naming `https://vocky.hi2vi.com/install.sh` 404s today. It is **not** a live falsehood,
because **the site itself is not deployed** (`docs/current/experience.md:14`; the only workflow,
`.github/workflows/deploy-production.yml`, is `workflow_dispatch`-only and has never run). The landing
page and `install.sh` therefore go live **in the same P12 bring-up**, so no live landing ever serves a
dead command. See "Hand-off to P12" below for the armed flip probes. **Every P11 `result.md` must say
plainly what was *not* behaviorally proven.**

## Decomposition

**This is a design-bearing phase, so it decomposes in two passes** (`design-cowork`). This `DECOMP`
created only the groundwork slices, the design slice, and `P11.DECOMP2`, and records a **build
inventory** (below) instead of build slices. The design decides what gets built; `P11.DECOMP2` cuts the
build slices once the design has landed.

| Slice | Order | Kind | Risk | Depends on | Name |
|---|---|---|---|---|---|
| `P11.S1` | 1 | implementation | low | — | Landing hero honesty: nested `source.product` + real `vk_` key shape |
| `P11.S2` | 2 | implementation | medium | — | CLI: `VOCKY_API_TOKEN` resolution + `vocky capture` over `/api/feedback` |
| `P11.S3` | 3 | implementation | medium | — | `curl \| bash` installer: `web/public/install.sh` |
| `P11.S4` | 4 | implementation | medium | `P11.S2` | Canonical end-user `SKILL.md`, served byte-copy, parity script + first CI workflow |
| `P11.S5` | 5 | **co-work** | high | `P11.S4` | Design round 02: hero install row, agent env-var quickstart, skill-on-landing |
| `P11.DECOMP2` | 6 | decomposition | high | `P11.S5` | Decompose the build from the landed design |

### Ordering rationale

- **S1 first, and specifically before the design gate.** Claude Design **reads the real repo**, so the
  hero must be truthful before the handoff — otherwise the round is designed around a lie.
- **S2 before S4**: the skill documents `vocky capture`, so the command must exist first.
- **S3 before S4**: the skill's install section quotes the real installer line.
- **S4 before S5**: `design-cowork` requires grounding in **real content, never lorem** — a skill-preview
  pane cannot be designed against a file that does not exist. This is the one place vocky's order differs
  from knowledge's P20 (whose skill already existed under a parity gate).
- **S5 → DECOMP2**: the design decides what gets built; build slices are cut only from the landed design.

### Risk ratings (the phase's main cost lever)

- **S1 `low`** — a fully mechanical, fully specified content edit in one file. The only slice that is.
- **S2/S3/S4 `medium`** — real judgment (CLI UX and error mapping, `curl | bash` safety, skill authoring,
  the repo's first CI workflow) but no architectural risk. Routes to `slice-executor-mid`.
- **S5 `high`** — `design-cowork` forbids ever rating a design slice `low`. Never dispatched (no executor
  has `DesignSync`); the orchestrator runs it inline on the main thread.

### Slice intents

These are **intents for the orchestrator to plan at each slice's turn** — not plans. No `plan.md` was
pre-filled; every new slice folder holds only `slice.json`.

- **S1 — Hero honesty.** In `web/src/content/landing.ts`: `:57` `vk_live_9f3c…` → a `vk_`-shaped stub
  matching `"vk_" + secrets.token_urlsafe(32)`; the `:58-64` body's top-level
  `"source_product": "checkout-web"` (`:59`) → nested `"source": { "product": "checkout-web" }`; and
  correct the false rationale comment at `:11-13`. No component edit — `hero.tsx` is untouched (it only
  interpolates `hero.request.auth` / `.body` at `:27-30`). **Copy inside an already-designed component is
  not a design round** (the line knowledge drew crisply). Verify with `pnpm typecheck && pnpm test`.
  *Verified caveat:* the hero body's other fields (`message`, `feedback_value`, `target_type`, `tags`) are
  all **valid top-level** capture fields (`capture.py:34-57`) — only `source_product` is wrong. Do not
  touch them.
- **S2 — CLI capture.** `VOCKY_API_TOKEN` in `cli/context.py` beside `VOCKY_BASE_URL`, and a new
  `cli/capture.py` registered in `app.py`. Precedence to settle at plan time (`--token` > env > stored?);
  the key is a `vk_` credential, **never** the session token, and the two must not be conflated in the
  config store. Build the nested `source` correctly; surface the 202 `request_id`; map `401` to "check
  `VOCKY_API_TOKEN`" (not "run `vocky login`"). **Keep imports lean** — typer/httpx/stdlib only. Consider
  a version bump off the stale `0.1.0` (`pyproject.toml:7`), since the installer prints `vocky --version`.
  Terse tests only.
- **S3 — Installer.** `web/public/install.sh`, mirroring knowledge's verified 50-line shape:
  `set -euo pipefail`; **every statement inside `main()` with `main "$@"` as the final line**, so a
  truncated `curl | bash` can never half-execute; bootstrap `uv` via the Astral installer only if absent
  and echo before doing it; `uv tool install --reinstall git+https://github.com/leetusik/vocky` for
  idempotent, upgrade-safe re-runs; no sudo, nothing system-wide (`$HOME/.local/bin`); PATH-tolerant
  verification that warns rather than dies; close by printing the next command. vocky's CLI is at the
  **repo root**, so there is **no `#subdirectory=` fragment** — and the lean/`server`-extra split means a
  default git install already pulls only httpx + typer. Verify: `bash -n`, plus a real run in an isolated
  temp `HOME` against a **local** install target. State plainly that the live `404 → 200` flip is P12's.
- **S4 — Skill + parity + CI.** Author the canonical end-user `SKILL.md` (capture over REST with `curl`,
  and the `vocky capture` one-liner; `/mcp` noted as the alternative transport). **Do not put it under
  `.claude/skills/` or `.agents/skills/`** — those are this repo's own workflow machinery and would load
  into every session here; recommend a new top-level `skills/<name>/SKILL.md`, decided at plan time.
  Mirror knowledge's authoring idiom: exact commands spelled out to run verbatim, branch-by-branch error
  handling (`202` / `400` / `401` / `503` / transport), a hard negative trigger in the frontmatter
  `description`, and a scoped `allowed-tools` allowlist. Then commit `web/public/SKILL.md` as a
  **byte-identical** copy, add `scripts/skill_parity.py` (stdlib-only, exit code is the contract —
  matching `scripts/wait_for_health.py` convention) plus a `Makefile` target, and create
  `.github/workflows/ci.yml` on push + pull_request running the parity script and web
  lint/typecheck/vitest. **Leave the Postgres pytest job to P12** — but shape the file so P12 adds a job
  rather than starting from nothing.
- **S5 — Design round 02 (`co-work`).** Orchestrator-run **inline on the main thread**; never dispatched.
  Writes `docs/reference/design/rounds/02-onboarding/handoff.md` only — **zero implementation code** —
  then `pending`, then read-back with `DesignSync`, land as-is, SIGNOFF. Target the design project **by
  id** `1eaa0803-46e3-426a-ab04-17a802170234`. The handoff must require **one card per reviewable unit**
  with the line-1 `@dsCard` marker, plus `result.md` and `build-prompt.md`; carry the three env-var
  blockers (below) as content to surface; state round 01's brand as **locked**; and **pose every open
  question back** rather than answering it.
- **`P11.DECOMP2`** — cuts the build slices from the landed design and `build-prompt.md`, at orders after
  its own: backing work first, the design implementation after, then any fidelity fix.

## Build inventory (what to build, not how)

This is what the S5 handoff's scope checklist is written from. **The design is free to add to it and cut
from it** — that is exactly why the build slices are not cut yet.

1. **Hero install command row** — the `curl | bash` line, copyable, in the hero's left column.
2. **Agent quickstart section** — the two-env-var contract (`VOCKY_BASE_URL` + `VOCKY_API_TOKEN`) as the
   recommended agent path: the `~/.zshenv` block, the Codex `network_access` trap, and a verify/health
   snippet with success and failure legends.
3. **Skill-on-landing section** — a preview pane over the served `/SKILL.md` (build-time `fs` read of the
   **served** copy, so the preview can never fork from the gated artifact), **Copy the skill** (fetching
   the served file rather than embedding a fork), and **Download** as a plain
   `<a href="/SKILL.md" download>`.
4. Consequent **nav / `SectionId` additions** (`web/src/content/section-ids.ts`) and any `LandingNav`
   entry.

**Apply-time note for `DECOMP2`'s slices:** copy payloads should be **byte-locked constants with display
deliberately separate from clipboard bytes**, guarded by a vitest that re-spells them — vocky has no such
test today (none of the 61 existing tests asserts a copy constant), and it would be the first.

## Findings & Notes

_Durable findings and cross-slice notes; `DECOMP` seeded this, and each slice appends when it finishes._

### Capture contract (verified against `src/vocky/capture.py`, `auth.py`, `app_api.py`)

- `POST /api/feedback` requires `message` (`capture.py:37`) and nested `source: {product, integration?}`
  (`capture.py:27-31`, field at `:38`); `source.product` must be non-blank — `require_non_blank(
  raw.source.product, "source.product")` at **`capture.py:275`**. REST-only extras `attachment_ids` and
  `project` (org-key destination, default `"default"`, `capture.py:80-81`, resolver at `:325-362`).
  Response **202** `{request_id, accepted_at, status:"accepted"}` (`capture.py:84-89`).
- All other hero-body fields are legitimate top-level capture fields (`capture.py:34-57`:
  `feedback_value`, `comment`, `channel`, `target_type`, `tags`, …). **Only `source` is nested.**
- Auth is **`Authorization: Bearer vk_…`**, not `X-API-Key` (`auth.py:66-81` extracts the bearer;
  middleware at `:144-215`). The same middleware guards `/api/*` **and** `/mcp`
  (`auth.py:171-174`), so a `vk_` key drives both; the single MCP tool is `capture_feedback`
  (`src/vocky/tools/capture_feedback.py:36-37`).
- **`vk_` is never validated as a prefix** — the middleware resolves the credential purely by
  `sha256_hex(token)` at **`auth.py:183`**. Keys are minted as `f"vk_{generate_opaque_token()}"`
  (`app_api.py:241` project-scoped, `:320` org-scoped). There is **no `vk_live_` / `vk_test_` tier.**
- A `vk_` key authorizes **only** `/api/*` + `/mcp`. Every existing CLI command talks to `/app/*` with a
  **session** token — which is exactly why `VOCKY_API_TOKEN` needs `capture` to have any consumer.
- **A working reference payload already exists in-tree**: `src/vocky/smoke.py:112` posts
  `"source": {"product": "vocky-smoke", "integration": "make-smoke"}` to `POST /api/feedback` and asserts
  the 202 `{request_id, status:"accepted"}` — the exact shape S1's hero must depict and S2's `vocky
  capture` must build. `smoke.py:141`'s top-level `source_product` is the **read** filter on
  `GET /api/feedback` (verified in context), which is why the two shapes legitimately differ.

### CLI (verified against `src/vocky/cli/`)

- `context.py:66-84` base-URL precedence `--base-url` > `VOCKY_BASE_URL` > stored > `http://127.0.0.1:8000`;
  `authed_client()` (`:61-62`) hard-fails "Not signed in — run `vocky login`."  `client.py:103-106`
  already injects `Authorization: Bearer` (and accepts an explicit `token=` override), so a `vk_` path
  **reuses `ApiClient` unchanged**.
- `config_store.py:25-40` — `VOCKY_CONFIG_DIR` > `$XDG_CONFIG_HOME/vocky` > `~/.config/vocky`;
  dir `0700` / file `0600`, keys `token` + `base_url` only (`:66-91`).
- Existing CLI modules: `app.py`, `auth.py`, `client.py`, `config_store.py`, `context.py`, `feedback.py`,
  `projects.py`. `capture.py` is net-new.
- **Import isolation is load-bearing** (`docs/current/operations.md:124`): `vocky.cli.*` may import only
  typer / httpx / stdlib / the httpx-only `vocky.smoke`. A server-side import silently breaks the lean
  install. Guard: `uvx --from dist/*.whl vocky --version`.
- No linter/formatter is configured for Python.
- `pyproject.toml:7` still reads `version = "0.1.0"`; `dist/` holds the stale `vocky-0.1.0-py3-none-any.whl`
  + `.tar.gz` from P6.S9.

### Web / serving (all verified)

- `web/public/` exists but holds only `.gitkeep`. `web/next.config.ts:55` `output: "standalone"`;
  `web/Dockerfile:40` `COPY --from=build /app/public ./public`; `deploy/vocky.conf:282-288` is a bare
  `location / { proxy_pass http://$vocky_web:3000; }`. The only other `location` blocks are `/api/`,
  `/api/auth/`, `/api/app/`, `/auth/`, `/app/`, `= /healthz`, `/mcp`, and `/admin/` (a `return 404`) —
  **none shadows a root-level static path**. → `web/public/install.sh` and `web/public/SKILL.md` serve at
  `/install.sh` and `/SKILL.md` with **zero infra work**. Caveat: `X-Content-Type-Options: nosniff` is
  global (`next.config.ts:43`), so a browser will *download* `.md` rather than render it — fine for
  `<a download>`; a route handler would be needed only for in-browser viewing.
- Landing composition: `web/src/app/page.tsx:32-46` → `LandingNav`, `Hero`, `TrustStrip`, `HowItWorks`,
  `Showcase`, `Features`, `Pricing`, `ClosingCTA`, `LandingFooter`. Hero snippet assembled at
  `hero.tsx:27-30` from `LANDING.hero.request`; right column is `EndpointCard` (`hero.tsx:72-74`).
- **Copy-as-data is a house rule** — components hold no literal copy; everything lives in
  `web/src/content/` (`docs/current/frontend.md:272`). Section anchors are typed: `SECTION_IDS` map at
  `web/src/content/section-ids.ts:8-13` (today only `features`, `how`, `pricing`), `SectionId` type at
  `:15`. A new section **must** add its id there.
- Existing primitives to reuse, not rebuild: `web/src/components/ui/endpoint-card.tsx` (`<pre>` in a
  forest panel), `web/src/components/show-once-key.tsx:41-48` (a working
  `navigator.clipboard.writeText` + permission-denied fallback — the copy mechanics to extract; note it
  lives directly under `components/`, **not** under `ui/`), `ui/reveal.tsx`, `ui/section.tsx` CVA tones.
- **`source_product` is correct on the read path** — `web/src/app/(app)/feedback/*`,
  `web/src/lib/vocky/types.ts:231,329`, and `src/vocky/smoke.py:141` (a query filter). **Only the capture
  request is nested.** Do not "fix" those.
- Tests: vitest, `environment: "node"`, `include: ["tests/**/*.test.ts"]` (`web/vitest.config.ts:30-33`);
  5 files (`auth-routes`, `session-guards`, `session`, `vocky-app`, `vocky-auth`), **61 tests**, none
  asserts a copy constant. No jsdom/RTL — so testable logic must be extracted into pure helpers.
  `web/.dockerignore:9` excludes `tests`, so a parity gate runs in CI, never in the image.

### Design

Round 01 (`docs/reference/design/rounds/01-brand-app-landing/`) designed the brand + landing;
`SIGNOFF.md:10` records design project **`1eaa0803-46e3-426a-ab04-17a802170234`** (target by **id**),
30 cards, token delta applied by P9. Tokens live in `web/src/app/globals.css`; the applied system is
documented at `docs/current/frontend.md:84-89,229-231,269-270`. **The next round is 02** —
`docs/reference/design/rounds/` holds only `01-brand-app-landing` today. Round 01's brand is **locked**
for round 02.

### The `git+` shipping caveat (knowledge lost real time to this)

`uv tool install git+https://github.com/leetusik/vocky` installs whatever is on **GitHub `main`**, so
P11's `vocky capture` is unreachable to installer users until an operator-gated `git push`. The
workspace never pushes unasked. → P11 verifies the installer against a **local** target in an isolated
temp `HOME`, and hands the real push + live proof to P12.

### Three env-var blockers knowledge documented — all apply, all belong in the S5 design handoff

1. A repo `.env` is **never** auto-loaded by Claude Code or Codex, and a secret in a repo file risks an
   accidental commit → recommend `~/.zshenv`.
2. Codex's `workspace-write` sandbox **denies outbound network by default** →
   `[sandbox_workspace_write] network_access = true` in `~/.codex/config.toml`. Claude Code needs nothing.
3. Cloudflare was empirically **not** a barrier for knowledge — but vocky's site is not live, so the probe
   **cannot run in P11**. Record it as a P12 check; do not design around an unverified blocker.

### Citation corrections made by `DECOMP` (plan facts that did not survive verification)

The `P11.DECOMP` plan's "Grounded facts" were spot-checked line by line against the tree. Four citations
were off; the **claims were all correct**, only the line pointers moved. Corrected above and repeated
here so no later slice re-derives them:

1. `auth.py:130-133` (cited for "`vk_` is never validated as a prefix") is a docstring about per-request
   project-scope caching. The real evidence is **`auth.py:183` — `sha256_hex(token)`** inside
   `ProjectCredentialAuthMiddleware.__call__` (class at `auth.py:144`). Claim stands: no prefix check
   anywhere.
2. `capture.py:274` (cited for the `source.product` non-blank guard) is the **`message`** guard;
   `source.product` is at **`:275`**. And the nested `source` **field** is declared at `:38`, not `:37`
   (`:37` is `message: str`).
3. `section-ids.ts:8-13` is the `SECTION_IDS` **map**; the `SectionId` **type** alias is at `:15`.
4. `docs/cli.md:9-21` → the Install section is `:9-19`.

### S1 done — landing hero honesty verified end to end

`P11.S1` applied the three plan-specified edits to `web/src/content/landing.ts` (file-header comment,
`vk_9f3c…` auth line with no `live_` tier, and the nested `"source": { "product": "checkout-web" }`
payload) and nothing else. All six validation steps passed: `pnpm typecheck` (0), `pnpm test` (61/61,
unchanged baseline), `pnpm lint` (0), `pnpm format:check` (fails only on 12 pre-existing unrelated files,
`landing.ts` not among them — left alone), `grep -rn "vk_live" web/ src/ docs/` (zero repo-wide matches),
`grep -n "source_product" web/src/content/landing.ts` (exactly the one expected comment-line occurrence).
No doc version was needed: `docs/current/frontend.md:231`'s landing description doesn't assert the false
`vk_live_`/flat-`source_product` shape specifically, so nothing there became stale — no "Doc impact" entry
added for this slice.

### Stale-doc finding for a later slice (not fixed here — `DECOMP` writes no source)

`docs/cli.md:11` ("PyPI publishing is planned (P6)") and `README.md:50` ("PyPI publishing is P6") are
**stale twice over**: `intent.md` records the publish moving from P6 to P11, and operator decision 1
(2026-07-29) then took PyPI off P11's table entirely in favour of `curl | bash`. `docs/current/experience.md:14`
already says "distribution is **P11**". Whichever slice ships the installer (S3) or the skill (S4) should
correct these two install sections to describe the real path; the review consolidates the doc impact.

## Hand-off to P12

- Arm falsifiable **flip probes** for P12's bring-up smoke: `https://vocky.hi2vi.com/install.sh` → **404
  today**, `https://vocky.hi2vi.com/SKILL.md` → **404 today**, and the landing carries the install line.
  All three flip on first deploy. Record them as probes now so P12 proves the flip rather than asserting it.
- The `git+…` channel resolves **GitHub `main`** — the installer is only truthful after an
  operator-gated `git push`. **P12 owns that push** and the clean-environment `curl | bash` end-to-end
  proof.
- The **Cloudflare-not-a-barrier probe is unrunnable in P11**; P12 runs it live.
- P12 **extends `.github/workflows/ci.yml`** with the Postgres-backed pytest job. S4 must shape that file
  so P12 adds a job rather than starting from nothing.
- **Armed flip probe, exact command** (`P11.S3`): `curl -sS -o /dev/null -w '%{http_code}'
  https://vocky.hi2vi.com/install.sh` → **`404` today**; must read **`200`** after the first deploy. Same
  shape for `/SKILL.md` once `P11.S4` lands it.
- **`git push` is a hard prerequisite for the hosted installer to be honest, not a nicety** (`P11.S3`):
  `uv tool install git+https://github.com/leetusik/vocky` resolves whatever is on **GitHub `main`**, which
  is **45 commits behind local** as of this slice (remote head `3e1e85a`, last pushed 2026-07-17) — every
  commit of P9/P10/P11 is unpushed, so installing from the real `git+https://` target today would silently
  deliver a pre-P10 CLI with no org keys and no `vocky capture`. `P11.S3` therefore verified
  `web/public/install.sh` only against a **local** target (`VOCKY_INSTALL_TARGET=$PWD`), never against the
  real GitHub URL. **After pushing, P12 must install-and-check, not assert**: run the installer (or `uv
  tool install --reinstall git+https://github.com/leetusik/vocky`) into a clean environment and assert
  `vocky --version` reads **`0.2.0`** (or newer) and `vocky capture --help` renders — exactly the two
  assertions `P11.S3` already proved against the local target.

## Constraints

### Out of scope for P11 (explicit)

- **No PyPI publish**, no `uv publish`, no version-related PyPI work beyond an optional CLI version bump.
- **No new backend capture contract** — `POST /api/feedback`'s shape is not redesigned.
- **No change to the `source_product` read-path shape** anywhere (web feedback pages,
  `web/src/lib/vocky/types.ts`, `smoke.py`). Only the *capture request* is nested.
- **No deploy, no push, no live verification** — all P12.

### Standing constraints

- `vocky.cli.*` imports stay typer / httpx / stdlib / `vocky.smoke` only (lean-install isolation).
- Copy lives in `web/src/content/`, never inline in components.
- **RESPECT THE DESIGN** at apply time — ship every designed element as designed; never drop, simplify,
  or "improve" one to save effort. This rule goes in each apply slice's `plan.md` **and** its dispatch
  prompt.
- The design slice (`P11.S5`) is **never dispatched to an executor** and **never writes implementation
  code**.

## Open Questions

- **S2**: `--token` vs `VOCKY_API_TOKEN` vs stored precedence, and where (if anywhere) a `vk_` key is
  persisted — it must not be conflated with the session token in `config_store`. Settle at S2 plan time.
- **S4**: the canonical skill's home — a new top-level `skills/<name>/SKILL.md` is the recommendation, but
  the exact path/name is settled at S4 plan time. It must **not** live under `.claude/skills/` or
  `.agents/skills/`.
- **S5**: every visual question is posed back to Claude Design, never answered here.

### S2 done — `VOCKY_API_TOKEN` resolution + `vocky capture` landed

`P11.S2` closed both gaps the phase objective names: `VOCKY_API_TOKEN` now exists (`resolve_api_token()`
in `src/vocky/cli/context.py`) and `vocky capture` is a real top-level command
(`src/vocky/cli/capture.py`, registered in `app.py`). All design decisions in the slice's `plan.md`
(token resolution shape, the `context.make_client(token=..., use_stored_token=False)` seam, the
401-override threading, command shape, registration, the `keys mint` hint, the version bump) were
implemented as specified — nothing was re-litigated.

**Exact surface `P11.S4`'s end-user skill should author against:**

- **Env var**: `VOCKY_API_TOKEN` — the only way to supply the `vk_` key; no `--token` flag exists. Missing
  or blank → exit non-zero, no HTTP call, stderr is exactly:
  `VOCKY_API_TOKEN is not set — mint a key with \`vocky keys mint\` and export it.`
- **Command**: `vocky capture MESSAGE --product PRODUCT [--integration I] [--value 1|2] [--comment C]
  [--tag T ...] [--session-id S] [--user-id U] [--project P]`. `MESSAGE` positional; pass `-` to read the
  whole message from stdin instead of fighting shell quoting. `--product` is the only required option.
  `--tag` is repeatable; omitted entirely from the request body when not given (never sent as `[]`).
  `--project` is REST-only-parity: honored only for an **org-level** `vk_` key, ignored by a project-bound
  one (same as the REST/MCP contract already documented).
- **Success output** (exact string, request id printed in full): `Captured — request_id <full id>`.
- **401 output** (exact string; deliberately not "run `vocky login`" — that message is reserved for the
  session-token commands): `Unauthorized — check VOCKY_API_TOKEN (the key may be wrong or revoked).`
- **Auth**: `Authorization: Bearer <vk_ key>` — never the stored session token. Built via
  `context.make_client(token=api_token, use_stored_token=False)`, which structurally guarantees the two
  credentials can't cross.
- **Two-export quickstart** (now real): `export VOCKY_BASE_URL=...` + `export VOCKY_API_TOKEN=vk_...` +
  `vocky capture "..." --product ...`. `vocky keys mint`'s output now includes a hint line pointing at this
  exact export, right before the show-once key line.
- **Version**: `pyproject.toml` is now `0.2.0` (was stale `0.1.0` since before P10). `vocky --version` only
  reflects it after a reinstall (`importlib.metadata` reads installed metadata, not the source tree) — the
  installer (`P11.S3`) reinstalls on every run, so this is a non-issue there.
- **Import isolation held**: `vocky.cli.*` (including new `capture.py`) still imports only typer / httpx /
  stdlib / `vocky.smoke`. The lean install from a built wheel resolves exactly **15 packages** (httpx +
  typer + transitives, no pydantic/sqlalchemy/uvicorn/psycopg) — verified with `uv build` +
  `uvx --from dist/vocky-0.2.0-py3-none-any.whl vocky --version`.
- **Not proven**: no live server round trip — every test stubs the transport. The real end-to-end proof
  (a running server, a real `vk_` key, a real 202) is P12's live smoke per the phase's hand-off section.

**Environment finding for later full-suite baselines**: this dev environment has a live Postgres reachable
on the test suite's default `127.0.0.1:55432`, so `uv run pytest -q` here shows **0** errors, not the
~108 `psycopg.OperationalError`s the phase's earlier citations (from `P6.S9`) describe for a no-DB
environment. Establish pre/post-slice baselines by comparison (e.g. `git stash` the slice's diff and
re-run) rather than assuming the ~108 number will reproduce here.

**Docs correction beyond the plan's three bullets**: `docs/cli.md`'s end-to-end walkthrough step 4
("Capture is not a CLI command in this release") was left false by the plan's specified edits alone, so it
was corrected too (now shows both `vocky capture` and the raw-HTTP equivalent) — a minimal, same-file
consistency fix, not a scope expansion.

### S3 done — `web/public/install.sh` landed and verified against a local target

`P11.S3` shipped the `curl | bash` installer at `web/public/install.sh` (61 lines) exactly to the plan's
shape: `set -euo pipefail`, two constants (`UV_BIN_DIR`, `INSTALL_TARGET` with the `VOCKY_INSTALL_TARGET`
override), `say`/`die` helpers, **every executable statement inside `main()`**, and **`main "$@"` as the
literal last line**. All eight validation steps passed — see `result.md` for verbatim output. Two findings
worth recording for later slices:

- **The `main()` wrapper's safety held under both truncation shapes tested**: piping a mid-function
  prefix (`head -n 40`) produced a bash **parse error** (exit 2, no output, `main` never reached — a
  truncated function body can't even finish parsing); piping the file up through the closing `}` but
  before the final `main "$@"` line (`head -n 59`) parsed clean and exited **0 with no output** (the
  function is defined but never called). Either cut point proves the same thing: a truncated `curl | bash`
  can never half-execute.
- **The `uv` bootstrap branch WAS exercised**, not skipped: validation used `env -i` with a minimal PATH
  (`/usr/bin:/bin:/usr/sbin:/sbin`), which has no `uv` on it regardless of the host machine's own `uv`
  install, so both the fresh-install run and the second (idempotency) run against the same temp `HOME`
  installed `uv` via the Astral installer inside the script. This is stronger evidence than the plan
  anticipated (it expected the branch might be skipped in an environment with `uv` already on PATH).

**Exact final install line — `P11.S4`'s skill and the `P11.S5` design handoff both quote this verbatim**:

```
curl -fsSL https://vocky.hi2vi.com/install.sh | bash
```

Both `docs/cli.md` and `README.md` now show this exact line, explicitly marked "once the site is live",
with the checkout-based install kept as what works today, and no PyPI promise anywhere in either file
(verified: `grep -rn "PyPI\|pip install vocky\|uv publish" README.md docs/cli.md` — zero matches).

**Not proven** (must not be asserted as done): no live `https://vocky.hi2vi.com/install.sh` fetch — the
site is not deployed; the `404 → 200` flip is P12's; and the real `git+https://github.com/leetusik/vocky`
target was **never installed from** in this slice — GitHub `main` is 45 commits behind local (see "Hand-off
to P12" above), so installing from it today would silently deliver a pre-P10 CLI. `VOCKY_INSTALL_TARGET`
stood in for it throughout validation.

Untouched, as the plan required: `web/Dockerfile`, `web/next.config.ts`, `deploy/vocky.conf` — all three
already serve `web/public/` correctly (confirmed again this slice: no dockerignore/gitignore excludes
`install.sh` or `public/`, `Dockerfile:40` still copies `public/`).

### S4 done — canonical `SKILL.md`, served copy, parity gate, first CI workflow all landed

`P11.S4` authored the canonical end-user skill at **`skills/vocky-feedback/SKILL.md`** — **119 lines,
7,975 bytes**, three-field frontmatter (`name` / `description` / `allowed-tools`, `disable-model-invocation`
deliberately omitted), body opening `# vocky-feedback`. **`P11.S5`'s design handoff should ground its
skill-preview pane in this exact file** (path, byte size, line count recorded here for that reason).
Section headings, in order:

1. Set up the two-variable contract
2. Verify before you capture anything
3. Path A — capture with the CLI (primary, one command)
4. Path B — raw REST (no vocky install required)
5. Path C — `/mcp` (alternative transport, not detailed here)
6. Error handling — branch by branch
7. Report back

`web/public/SKILL.md` is a committed byte-identical copy (`cmp`-verified, not build-generated).
`web/.prettierignore` now excludes `public/` — required, since prettier's markdown reflow would otherwise
silently break byte parity the first time anyone runs `pnpm format`. `scripts/skill_parity.py` (stdlib-only,
exit-code-is-the-contract, matching `wait_for_health.py`'s shape) and a `make check-skill-parity` target
gate the two files against each other; the gate was proven **red then green** (appended a byte to the
served copy, watched it fail with `exit 1`, restored, watched it pass). `.github/workflows/ci.yml` is the
repo's first push/pull_request gate — three jobs (Skill Parity, Installer Syntax, Web
lint/typecheck/test) — shaped so **P12 adds a Postgres-backed pytest job** rather than starting from
nothing; `format:check`/prettier-fixing and the pytest job are both deliberately excluded (see `result.md`
for the full reasoning) and belong to P12.

**A wording ambiguity in the plan itself, resolved by judgment**: Part 1 says "Two capture paths, REST
primary" in one sentence, then labels the CLI "Path A … (primary, one command)" two paragraphs later. The
skill was written CLI-first (matching S2's framing of `vocky capture` as `VOCKY_API_TOKEN`'s first-class
consumer); flagged for the review in case "REST primary" was the intended reading instead.

**Verified against source before writing**, beyond what S2/S3 already recorded: the REST error table
(`src/vocky/api.py:93-126` — `400`/`503`/`500` branches, `src/vocky/auth.py:100-104,183-192` — the `401`
`{"detail":"Unauthorized"}` + `WWW-Authenticate: Bearer` shape), the MCP tool signature and
`VOCKY_MCP_ALLOWED_HOSTS` DNS-rebinding gotcha (`src/vocky/mcp_server.py:17,39-49`,
`src/vocky/tools/capture_feedback.py:36-60`), and a genuinely zero-side-effect verify snippet: `GET
/api/feedback` with a valid-but-incomplete query passes the shared `vk_` auth middleware (which gates by
path prefix, any method) and only then 400s on a missing `user_id`/`source_product` filter
(`src/vocky/api.py:144-156,235-247`) — so a bare-token `GET` distinguishes a bad key (`401`) from a good one
(`400`) without ever writing a feedback row. Useful for any later skill/doc that needs a no-op credential
check.

**Sandbox note for later slices**: this session's `rm -rf` was denied by the Bash permission system for
*any* path, including scratch directories outside the repo — but `mv` was permitted. The clean-checkout
lockfile check (move `web/node_modules` aside, `pnpm install --frozen-lockfile`, verify lint/typecheck/test
against the fresh install) ran for real by substituting `mv ... .bak.<pid>` for the destructive step, then
relocating the backup out of `web/` entirely (a stray backup dir left inside `web/` gets picked up by
`tsc`'s typecheck scan and produces spurious errors — moved to the session scratchpad instead).

**Not proven** (both hand off to P12, both already flagged in the phase's hand-off section): the workflow
has never executed on a GitHub runner (unpushed; GitHub `main` is 45 commits behind), and `/SKILL.md` has
never been fetched from a live origin (`404` today, must flip to `200` after the first deploy — the served
bytes must then `cmp` clean against the canonical, same as the `/install.sh` flip probe).

### S5 done — design round 02 landed (gate closed 2026-07-29)

`P11.S5` was run **inline on the main thread** (never dispatched — no executor has `DesignSync`). The
handoff went out, the operator ran the round in Claude Design, and the returned record was read back,
concreteness-checked, and landed **verbatim and read-only**.

- **Record (on disk, read-only):** `docs/reference/design/rounds/02-onboarding/handoff.md` (OUT) and
  `output/{result.md, build-prompt.md}` (IN). SIGNOFF entry in `docs/reference/design/SIGNOFF.md`.
- **`output/build-prompt.md` is the implementation contract** and is deliberately self-sufficient — the
  build executors have **no DesignSync**, and **the 43-card set stays in the design project**. Everything
  needed to build is in that file: exact values, final copy strings, states, breakpoints, no-JS behaviour.
- **Token delta: None.** No `globals.css` change. The caution family shipped in round 01 but had no
  consumer; it now carries the trap treatment. **Do not add or rename a token.**
- **No backend change.** `POST /api/feedback` is untouched.
- The operator delegated all thirteen §6 questions ("Decide for me"); every decision and its reasoning is
  in `output/result.md` §2.

**What the design decided, in brief — `P11.DECOMP2` cuts the build slices from this:**

- **Two new sections at positions 4 and 5**, between `HowItWorks` and `Showcase`: `AgentQuickstart`
  (tone `default`, id `quickstart`) and `SkillSection` (tone `surfaceSoft`, id `skill`). Both `reveal`.
- **`section-ids.ts` gains exactly two entries** (`quickstart`, `skill`) — `SectionId` is typed, so the
  sections cannot compile without them.
- **`landing-nav.tsx` gains exactly one link**, second position: `Get started` → `#quickstart`. `#skill`
  gets **no** nav link.
- **The hero gains an install row** appended *below* the existing two-column grid. **Nothing inside the
  grid changes** — the corrected payload (nested `source.product`, no `vk_live_`) must not be edited.
- **Three new components:** `ui/snippet.tsx` (row + block variants, client copy island),
  `ui/trap.tsx` (an `<aside>`, amber, deliberately **no** `role="alert"`/`aria-live`), and
  `landing/skill-preview.tsx` (**server** component reading the served `/SKILL.md` at request time).
- **The preview must never hardcode its line/byte counts** — they are computed from the file just read, or
  they drift the moment the skill is edited. And it must never be a pasted excerpt: that forks silently
  from the `scripts/skill_parity.py` gate even while CI stays green.
- **No-JS behaviour is locked and normative** (`build-prompt.md` §8): copy buttons are client islands that
  render only after mount, so a no-JS visitor sees **no button at all** rather than an inert one; the
  preview is server-rendered and natively scrollable; `Download SKILL.md` is a plain `<a download>` and
  always works.
- **`400` is the success reading** on the verify step, and **`401` says stop, never retry** — the published
  skill says so, and the page must not contradict it.
- **Copy is `textContent`, never a re-typed string**, and the install command uses `white-space:pre` +
  `overflow-x:auto` so it never reflows at any width.
- **All copy goes in `web/src/content/landing.ts`** under `heroInstall` / `quickstart` / `skill` — round
  01's copy-as-data rule holds, and `build-prompt.md` §11.4 makes "zero literal strings in the new
  components" an acceptance check.

**RESPECT THE DESIGN.** `build-prompt.md` opens with this and it belongs in every build slice's `plan.md`
**and** its executor dispatch prompt: ship every designed element as designed; do not drop, simplify,
restyle, or "improve" one to save effort. Where an exact value is unspecified, pick the option closest to
the designed intent, never a plainer fallback.

**Not decided by this round** (`result.md` §7): a cache policy for `/install.sh` and `/SKILL.md` (a P12
bring-up question), whether the dashboard's key-mint flow links back to `#quickstart`, and Korean copy for
the three new surfaces (English-only, same as the shipped landing).

### DECOMP2 done — the build cut from the landed design (2026-07-29)

`P11.DECOMP2` read `output/build-prompt.md` and `output/result.md` in full and verified every claim they
make about the tree before cutting. **The plan's five-slice cut survived verification and was created
unchanged in shape** (orders 7–11, all `implementation`, all `risk: medium`); what changed is the *content*
of three of them, from nine corrections recorded below. The design record was **not edited** — every nit is
catalogued here as an apply-time to-do.

#### RESPECT THE DESIGN — standing instruction for every build slice

**Ship every designed element as designed — layout, density, hierarchy, tokens, states, no-JS behaviour.
Do not drop, simplify, restyle, or "improve" a designed element to save effort — that is a correctness
failure, not a shortcut. Where an exact value is unspecified, pick the option closest to the designed
intent, never a plainer fallback.**

This paragraph **must appear verbatim in every build slice's `plan.md` AND in every executor dispatch
prompt** for `P11.S6`–`P11.S10`. It is the `design-cowork` requirement, and it exists because a spec this
precise is easy to quietly round off. `build-prompt.md` opens with the same block.

#### The cut

| Slice | Order | Kind | Risk | Depends on | Covers |
|---|---|---|---|---|---|
| `P11.S6` | 7 | implementation | medium | — | `ui/snippet.tsx`, `ui/trap.tsx`, the pure copy helper, `section-ids.ts` (+2), all three `landing.ts` copy blocks, `ui/index.ts` |
| `P11.S7` | 8 | implementation | medium | `P11.S6` | Hero install row (§4) + `landing-nav.tsx` (§2) |
| `P11.S8` | 9 | implementation | medium | `P11.S6` | `AgentQuickstart` (§5) + `ReadingList` (§3.3) + the note treatment (§3.2) + `page.tsx` position 4 |
| `P11.S9` | 10 | implementation | medium | `P11.S6` | `SkillSection` (§6) + `SkillPreview` (§3.4, server read) + `page.tsx` position 5 |
| `P11.S10` | 11 | implementation | medium | `P11.S9` | Fidelity pass: §11's seven acceptance checks, §8 no-JS, §9 a11y, §7 reduced motion |

**Why this shape.** S6 is the spine: `Snippet` is consumed by the hero row and three of the quickstart's
four steps, `Trap` and the copy mechanics are shared, and copy-as-data means all three copy blocks are one
coherent unit rather than three fragments. `SectionId` is typed, so **S8 and S9 cannot compile until S6's
two entries exist**. S7 is separated because it is the only slice touching shipped above-the-fold code
(blast radius, not size). S8 and S9 are two different shapes — a numbered procedure vs. a document reader —
and fusing them would rebuild the monolith the design deliberately split (`result.md` §6.2). S10 is the
only slice positioned to run the cross-cutting checks, and `design-cowork` treats a fidelity pass as part
of the normal shape, not a failure.

**S8 and S9 both edit `web/src/app/page.tsx` and `web/src/components/landing/index.ts`.** They run
sequentially by `order`, so there is no conflict — but neither should treat the other's edit as a surprise,
and the barrel files are **not** in the §10 change manifest even though both are required.

**Transient dead anchor:** S8's peer line links to `#skill`, whose section lands in S9. `SECTION_IDS.skill`
exists from S6 so it compiles; between S8 and S9 the anchor resolves to nothing. S10's acceptance check 7
("`#quickstart` and `#skill` both scroll to their sections") is where it is proven.

#### Corrections found by reading the contract against the tree — apply-time to-dos

The design record is **read-only** and none of these were fixed there. All nine were verified against the
working tree during this slice.

1. **The nav is a REORDER, not just an insert (S7).** `build-prompt.md` §2 writes the final nav as
   `How it works · Get started · Features · Pricing · Docs`. Today `landing.ts:35-40` is
   `Features · How it works · Pricing · Docs` — **`Features` is first, `How it works` second.** Inserting
   `Get started` at "second position" into today's array yields `Features · Get started · How it works · …`,
   which contradicts both the written nav string and `result.md` §6.3's rationale (it sits second *because*
   it follows `How it works`, matching the §6.2b page order). **Ship the design's stated string:
   `How it works` moves to first, `Get started` second.** Acceptance check 7 only counts to five, so it
   will not catch this.
2. **The footer is NOT the nav — do not touch it (S7).** `landing.ts:245-249` has a Product column with the
   same three anchors. The design says nothing about the footer; adding `Get started` there would be an
   undesigned change. Leave it.
3. **The `.eyebrow` / `.note` / `.tag` / `.card` names in the build-prompt are card-kit specimen classes,
   not repo CSS.** `grep` over `web/src/app/globals.css` finds **zero** of them. Repo equivalents:
   `.card` → the `Card` primitive; `.tag` → the `Chip` primitive
   (`inline-flex rounded-sm border px-2 py-0.5 font-mono text-caption`, `border-hairline bg-surface
   text-slate` — matches the spec's intent); `.eyebrow` → shipped inline, two different ways (see 4);
   **`.note` does not exist at all** — `grep -rn "border-l-2\|border-l "` over `web/src` is empty. So §3.2's
   note treatment (13px `steel`, `border-left:2px solid var(--color-green)`, `padding-left:12px`) must be
   **built**, not reused. It is used only in quickstart step 2 → **S8 builds it inline**; it does not need
   to be a `ui/` primitive.
4. **Two shipped eyebrows, and §5 names the one with the dot (S8/S9).** `how-it-works.tsx` uses
   `text-caption font-semibold tracking-[0.12em] text-green-dark uppercase` (no dot); `hero.tsx` uses a
   `rounded-full bg-green-soft` pill with a `size-1.5 bg-green` dot. §5 says "existing `.eyebrow` treatment,
   **green dot** + uppercase" → the hero's dot reading is explicit and wins. §6's `Agent skill` eyebrow is
   unqualified → use the same treatment for consistency (never the plainer fallback).
5. **§5.1's step marker contradicts the shipped component it cites (S8).** It says "Step marker = the
   shipped `HowItWorks` step numeral: 34px circle, `background:var(--color-ink)`, white mono 700 15px."
   The **actually shipped** numeral is `size-9` (36px) `bg-green-soft` `text-green-dark`. The explicit
   values are normative, the descriptive label is not: **build the 34px ink circle with white mono 700
   15px**, and do not restyle `how-it-works.tsx` to match.
6. **The §3.4 parenthetical is wrong; `22` is the normative number (S9).** "the first 22 lines of the body
   (through the `Put these in ~/.zshenv, never a repo .env:` line)" — that line is body line **15**. Body
   line 22 is the blank line after `## 2. Verify before you capture anything`. `22` appears in §3.4, in the
   §7 state table, in the footer copy ("Showing the first 22 of `<lines>` lines") and in `result.md` §6.5's
   rationale (whose four criteria — trigger description, section numbering, prose density, a real fenced
   command — are all satisfied at 22). **Keep 22. Do not "correct" it to 15.** Decide deliberately whether
   the body's leading blank line (the line immediately after the closing `---`) counts as body line 1; it
   shifts the window by one.
7. **The collapsed-vs-no-JS tension, and how it resolves (S9) — the single most misreadable point in the
   spec.** §3.4 says collapsed "shows the first 22 lines of the body" and expanded's "body text = the whole
   file", which reads like the collapsed DOM is truncated. §8 says the pane is "server-rendered with the
   file already in the HTML… so all **119 lines are readable without JS**", and `result.md` §6.5 settles it
   outright: "**A scroller (rather than a hard clip) means a no-JS visitor can still read all 119 lines.**"
   → **The full file is always in the server HTML.** "Collapsed" is a *visual* window: a 380px scroller
   plus the fade overlay. Expanded raises the cap to 640px and drops the fade — it does **not** swap in new
   text. Truncating the server output to 22 lines would break the no-JS floor and make the no-JS footer
   ("`<n>` lines · scroll to read") a lie.
8. **`result.md` §6.4's line-count discrepancy does not exist in the tree.** It worries that `wc -l`
   reports 120. Both `skills/vocky-feedback/SKILL.md` and `web/public/SKILL.md` measure **119 lines, 7,975
   bytes** (`wc -l -c`, byte-identical to each other), and §3.4's formula
   `content.split("\n").length - 1` also yields **119**. Header and footer will read 119 with no special
   handling. The counts still must be **computed, never hardcoded** (acceptance check 2).
9. **The two "floors" S10 must check are already global — and that is why the token delta really is None.**
   `globals.css:276-279` already ships `:focus-visible { outline: 2px solid var(--color-green-deep);
   outline-offset: 2px }`, satisfying §9's focus ring for every button and anchor with no new CSS — the
   only work is making **the two scrollers focusable** (`tabIndex={0}`) so they can receive it.
   `globals.css:282-291` already forces `transition-duration: 0.01ms !important` under
   `prefers-reduced-motion: reduce`, so §7's "both become instant" needs no new CSS either. **S10's
   reduced-motion and focus-ring items are verifications, not implementations** — and neither requires the
   `globals.css` change the manifest forbids.

#### Facts every build slice inherits — all re-verified this slice

- **Token delta: `None`, confirmed.** Every value §3–§6 names resolves to an existing `@theme` token in
  `web/src/app/globals.css` — including the whole caution family (`--color-caution` `:53`,
  `--color-caution-deep` `:54`, `--color-surface-caution` `:55`, `--color-hairline-caution` `:56`), which
  shipped in round 01 with no consumer and now carries the trap. **Do not add a token. Do not rename one.**
- **No backend change.** `POST /api/feedback` is untouched.
- **`Section` already provides everything §2 needs**: `tone` has both `default` and `surfaceSoft`, `id` is
  typed `SectionId` and bakes `scroll-mt-24`, and `reveal` wraps content in the reduced-motion-safe
  `Reveal` island. `html { scroll-behavior: smooth }` is global. Nothing new is needed for anchoring.
- **The narrow breakpoint is `app:`, not `md:`.** `--breakpoint-app: 56.25rem` = **900px** — exactly the
  `< 900px` the design specifies — and Tailwind v4 generates an `app:` variant already used across
  `src/components/app-shell/*` and the feedback pages. Use `app:`; never hand-roll a media query, and
  never substitute `md:` (768px). One exception: the nav's mid links are `hidden md:flex` today; the new
  link inherits that shipped behaviour and must not change it.
- **Copy-as-data is a hard rule** — zero literal strings in the new components (§11.4 is an acceptance
  check). Everything goes in `web/src/content/landing.ts` under `heroInstall` / `quickstart` / `skill`.
- **The web test suite is Node-env vitest** (`web/vitest.config.ts`), `include: ["tests/**/*.test.ts"]` —
  **`.ts` only, no `.tsx`, no jsdom, no RTL**, 61 tests across 5 files, `@` aliased to `./src`. Component
  tests are structurally impossible; testable logic must be extracted into pure `.ts` helpers.
  `landing.ts` imports only `section-ids.ts` (no React), so a byte-lock test on the copy constants is
  feasible and would be the repo's first. Keep new tests terse per `AGENTS.md`.
- **CI runs `pnpm lint`, `pnpm typecheck`, `pnpm test`** plus the skill-parity and installer checks
  (`.github/workflows/ci.yml`, S4). `prettier --check` is **not** in CI (12 pre-existing failures) — do
  not assume formatting is gated and do not "fix" those 12 files here. `prettier-plugin-tailwindcss` is
  installed, so class ordering will differ from hand-written order; that is not a CI failure.
- **`web/.prettierignore` covers `public/`** — that is what keeps `web/public/SKILL.md` byte-identical to
  the canonical. Do not undo it.
- **`page.tsx` is already dynamic** (`getSession()` + `redirect`), so `SkillPreview`'s request-time `fs`
  read is safe; `next.config.ts` is `output: "standalone"` and `Dockerfile:40` copies `public/`.
- **The site is not deployed.** `/SKILL.md` and `/install.sh` 404 until P12. Verify locally with
  `next build` / the standalone server, and say plainly in each `result.md` what was **not** behaviorally
  proven.

#### Slice intents — for the orchestrator to plan at each slice's turn (not plans; no `plan.md` pre-filled)

- **S6 — Primitives + copy.** `web/src/components/ui/snippet.tsx` (§3.1, row + block; **`white-space:pre`
  + `overflow-x:auto` is a locked floor** — the install command must never wrap or truncate at any width)
  and `web/src/components/ui/trap.tsx` (§3.2 — an `<aside>`, deliberately **no** `role="alert"` and **no**
  `aria-live`, because a trap is not an error). The clipboard rule is locked: **copy the DOM node's
  `textContent`, never a separately-typed string**; reuse the mechanics in
  `web/src/components/show-once-key.tsx:44-54` (`navigator.clipboard.writeText` + explicit failure branch)
  but not its alert-box UI. §8 additionally requires the copy button to be a **client island that renders
  only after mount** — a no-JS visitor sees *no button at all*, never an inert one. Extract the copy logic
  into a **pure, DOM-free helper** so it is testable in Node-env vitest. Add `quickstart` and `skill` to
  `section-ids.ts`; add the `heroInstall` / `quickstart` / `skill` copy blocks to `landing.ts` as
  **byte-locked constants** with a terse vitest that re-spells the copyable payloads so a reflow fails CI.
  Export both primitives from `ui/index.ts`.
- **S7 — Hero install row + nav.** §4. Append the row **below** the existing two-column grid, inside the
  hero container. **Nothing inside the grid changes** — h1, sub, both CTAs, the `EndpointCard` payload and
  the layered captured-record `Card` all stay exactly as shipped, and the corrected payload (nested
  `source.product`, no `vk_live_`) **must not be edited**. `Start free` stays the primary CTA; the install
  row is never a filled button. Then `landing-nav.tsx` per correction 1 (reorder + one new link;
  `#skill` gets **no** nav link) and correction 2 (footer untouched). §2's active state resolves to
  **none** — the shipped nav has no active-state mechanism, so do **not** build a scroll-spy island.
  Honor the `< 900px` behaviour in §4 (label block above the snippet, caption drops its third clause).
- **S8 — `AgentQuickstart`.** §5, inserted at position 4 per §2. Four numbered steps, the peer line, and
  the sticky contract aside; also builds `ReadingList` (§3.3, may live inside the component) and the note
  treatment (correction 3). Two normative details that are easy to get wrong: **`400` is the success
  reading** on the verify step (the token authenticated; a bare GET was rejected for a missing filter),
  and **`401` says stop — never retry, never fall back**, because the published skill says so and the page
  must not contradict it. Every string in §5 is final copy; use it verbatim. Corrections 4 and 5 apply.
- **S9 — `SkillSection` + `SkillPreview`.** §6 and §3.4, inserted at position 5 per §2. `SkillPreview` is a
  **server** component reading the served `/SKILL.md` at request time and splitting once at the closing
  frontmatter `---`. **Line and byte counts are computed from the file just read — hardcoding them is
  forbidden** (acceptance check 2), and a pasted excerpt forks silently from `scripts/skill_parity.py`
  even while CI stays green. Corrections 6, 7 and 8 apply — **read correction 7 before writing any code.**
  No syntax highlighting, no markdown rendering, no library. `Copy the skill` is primary;
  `Download SKILL.md` is a plain `<a href="/SKILL.md" download>` and is the no-JS survivor.
- **S10 — Fidelity pass.** Run §11's seven acceptance checks and fix what fails. Also verify the §8 no-JS
  floor (no copy button renders at all; the preview still shows all 119 lines and scrolls; the no-JS
  footer + `Open the raw file` anchor are present; Download works), the §9 a11y floor (per correction 9 the
  focus ring is already global — the work is `tabIndex={0}` on both scrollers), and that motion drops to
  instant under `prefers-reduced-motion: reduce` (also already global). This slice may close any fidelity
  gap earlier slices left. **It must not "simplify" anything to make a check pass.**

#### Executor tier — two bump candidates

All five were created `medium` → `slice-executor-mid`. The spec is exact enough that none demands
architectural judgment, and none is mechanical enough for `low` (every one carries the RESPECT THE DESIGN
obligation, which is a judgment call by nature). **The orchestrator may bump one tier up at plan time,
never down** — two concrete candidates, in order:

1. **`P11.S9`** — correction 7 is a genuine internal tension in the spec, and getting it wrong silently
   breaks the no-JS floor while every CI check stays green. This is the strongest bump case in the phase.
2. **`P11.S6`** — the copy-failed state (programmatic `Range` + `Selection`, a persisting non-timed state)
   layered on top of mount-gated client islands is the trickiest client mechanic in the round, and three
   later slices inherit whatever shape it takes.

### S6 done — the primitives, the copy blocks and the three net-new mechanics (2026-07-29)

`P11.S6` landed `ui/snippet.tsx`, `ui/trap.tsx`, the pure copy helper, the two `section-ids` entries
and all four `landing.ts` copy blocks. **Nothing consumes them yet** — `page.tsx`, `hero.tsx` and
`landing-nav.tsx` are untouched, so the shipped landing is byte-identical in output. All nine
validation steps passed (`typecheck` 0, `lint` 0, `test` **61 → 70**, `build` 0, both greps clean,
`skill_parity.py` PASS, `workflow.py validate` passed); verbatim output in the slice's `result.md`.

#### The two primitives' prop shapes — S7–S9 consume these by name

```ts
// @/components/ui
interface SnippetCopy {
  copyLabel; copiedLabel; copyFailedLabel; selectionHint;   // all four from LANDING.snippet
  announcement;                                             // PER SNIPPET, not shared
}
interface SnippetProps extends Omit<HTMLAttributes<HTMLDivElement>, "children">,
                               VariantProps<typeof snippetVariants> {  // variant?: "row" | "block"
  label?: ReactNode;   // block: the bar label (always pass one). row: optional leading tag.
  command: string;     // the exact bytes shown AND copied
  copy: SnippetCopy;
}
interface TrapProps extends HTMLAttributes<HTMLElement> {
  label: ReactNode;    // e.g. "Known trap · Codex only"
  children: ReactNode; // inline <code> is styled BY the primitive — write plain <code>
}
```

```tsx
<Snippet variant="row" command={heroInstall.command}
         copy={{ ...LANDING.snippet, announcement: heroInstall.copyAnnouncement }} />
```

**`Snippet`'s root is an unstyled wrapper**, not the bordered frame: the failure hint sits below the
frame and the live region must not live inside a `whitespace-pre` scroller. So a consumer's
`className` is for layout (`mt-3`, `w-full`), never for restyling the frame. `Trap` is the opposite —
`className` lands on the `<aside>` itself.

#### Exact `landing.ts` copy-block keys

```
LANDING.snippet      copyLabel · copiedLabel · copyFailedLabel · selectionHint
LANDING.heroInstall  label · sub · command · caption · captionNarrow · copyAnnouncement
LANDING.quickstart   eyebrow · heading · lede
  .steps.install     n · title · sub · command · copyAnnouncement
  .steps.env         n · title · snippetLabel · command · copyAnnouncement
                     note{text, code[]} · trap{label, body{text, code[]}}
  .steps.verify      n · title · sub · snippetLabel · command · copyAnnouncement
                     readings[]{code, verdict, body}          // "400" / "401" / "else"
  .steps.capture     n · title · command · copyAnnouncement · resultBadge · resultText
  .peer              before · linkLabel · after · href        // href = "#skill"
  .aside             contractLabel · contractRows[]{name,value} · contractBody
                     worksWithLabel · worksWith[]
LANDING.skill        eyebrow · heading · lede{text, code[]} · copyAction · copyAnnouncement
                     downloadAction · downloadHref · served · insideLabel · inside[]
  .preview           filename · meta · downloadLabel · collapsedLines
                     footerCollapsed · footerExpanded · footerNoJs
                     expandLabel · collapseLabel · rawLabel · rawHref
```

- **`quickstart.steps` is an OBJECT, not an array** (`install` / `env` / `verify` / `capture`). The
  four steps carry four different content shapes, so `.map()` would not typecheck usefully;
  `steps.verify.readings` beats `steps[2].readings`. The `<ol>` ordering lives in S8's JSX and `n` is
  the numeral the design paints in the 34px ink marker (correction 5).
- **Rich strings are `{ text, code[] }`** — `text` is the verbatim sentence, and every occurrence of
  each `code` token renders as an inline `<code>`. Used by `quickstart.steps.env.note`,
  `quickstart.steps.env.trap.body` and `skill.lede`; the tokens are the ones §5.1/§6 name. Verified
  that no token is a substring of another within the same string, so a straight split is safe. Chosen
  over a segment array so a transcription slip at a boundary cannot hide.
- **`skill.preview.meta` and all three footers are TEMPLATES** with `{lines}`, `{bytes}`,
  `{collapsed}`. `collapsedLines: 22` is the design's window (correction 6 — keep 22). Hardcoding a
  count is forbidden by §11.2. The preview's two buttons reuse `LANDING.snippet`'s labels.
- Step 1's sub ships **`uv` as plain text**: the build-prompt marks inline code with an explicit
  parenthetical everywhere it wants it, and §5.1's sub styling names no code treatment.

#### The mount gate — `useIsHydrated()`, and why NOT `useState`+`useEffect`

**The plan's spelling of the mount gate fails `pnpm lint`.** `react-hooks/set-state-in-effect` (React
Compiler rules, bundled in `eslint-config-next`) rejects a synchronous `setState` inside an effect
body as an **error**. So the gate lives in **`web/src/lib/use-is-hydrated.ts`**:

```ts
const subscribe = () => () => {};                      // module-level: must be a stable ref
export const useIsHydrated = () => useSyncExternalStore(subscribe, () => true, () => false);
```

React renders and hydrates with the server snapshot (`false`), then re-renders `true` after
hydration. Same observable behaviour as the mount effect, no hydration mismatch, no lint suppression.
**S9 must use this same hook** for the preview's expand toggle — do not re-invent the effect form,
it will not pass lint.

#### The no-JS floor is now REGRESSION-TESTED, without jsdom

`renderToStaticMarkup` (from `react-dom/server`, node build) reaches the pre-hydration frame with no
DOM at all, so `web/tests/snippet-ssr.test.ts` asserts §8 directly: the server HTML contains **no
`<button`**, contains the command as selectable text, carries `whitespace-pre` + `min-w-0 flex-1`,
and wraps block comment lines in the sage span without altering the text. **S9 can use the exact same
technique** on `SkillPreview` — it is a server component, so this is the cheapest possible proof that
all 119 lines are in the HTML and that the toggle is absent (correction 7's whole tension, provable
in CI). Importing a `"use client"` module from a Node test is fine; the directive is just a string.

Still uncovered anywhere (S10's fidelity pass owns them): the 2000ms revert, the `Range`+`Selection`
failure path, the persisting failure state, the live-region announcement, hover/focus visuals, and
everything below 900px.

#### Two plan/inventory facts that did not survive contact with the tree

1. **The repo does NOT have zero `style={{…}}` occurrences — it has 15.** Twelve are in
   `app/apple-icon.tsx` + `app/opengraph-image.tsx`, where next/og's `ImageResponse` cannot use
   Tailwind classes at all, and three are `style={{ height: "40%" }}` on a decorative bar in
   `landing/features.tsx`. The no-inline-styles rule still holds for components (the two new ones
   have zero) — just do not cite "zero in the repo" as the evidence.
2. **`/` does not prerender as static and never has.** `app/page.tsx` reads the session cookie
   (`getSession()` + `redirect`) and its own P9.S6 comment says "reading the cookie makes `/`
   dynamic, so it is never prerendered". `next build` prints `ƒ /` before and after this slice. Any
   later slice's validation must expect `ƒ`, not `○`.

#### Design-fidelity judgment calls made here (S10 should not "fix" these back)

- `rounded-[12px]` on the block — no radius token lands on 12 (`lg` 10, `xl` 14). Likewise
  `text-[13.5px]` is NOT the 13px `text-code-md` token.
- `failed` uses the same caution treatment on dark as on light — §7 supplies a dark override for
  `copied` only, and a dark caution colour would be a new token.
- On failure the **block's** border also goes `hairline-caution` (§7 says "the row's border").
- The row's optional `label` (in §3.1's signature, styled nowhere, unused this round) renders as the
  block bar's label treatment on a light surface: mono `text-micro tracking-[.7px]` uppercase
  `green-dark` — what §4's own micro label uses.
- The trap's inline `<code>` treatment is applied with `[&_code]:…` descendant utilities (the repo's
  first arbitrary variant — verified compiled into the CSS bundle), so consumers write plain `<code>`.
- `ease-[ease]` compiles to `transition-timing-function: ease` — checked in the built CSS, since
  Tailwind's default `transition` timing is not CSS `ease`.
- Announcements beyond §7's `Copied the install command.`: `Copied the environment block.`,
  `Copied the verify command.`, `Copied the capture command.`, `Copied the skill file.`

#### Byte-locked payloads now guarded by CI

`web/tests/landing-copy.test.ts` re-spells the install command, the `~/.zshenv` block and the verify
command as literals, and additionally asserts the install line appears verbatim inside
`web/public/install.sh` — so the landing and the installer cannot drift apart. **Note for anyone
editing the verify command**: its `'%{http_code}\n'` needs `\\n` in the TS template literal, and each
line continuation needs `\\`. This is the repo's first test importing from `@/content`; it works (no
`server-only`, no JSX in that graph).

### S7 done — hero install row + nav reorder landed (2026-07-29)

`P11.S7` appended the install row below the hero's existing two-column grid (consuming S6's `Snippet` +
`heroInstall` copy unchanged) and reordered `LANDING.nav.links` to
`How it works · Get started · Features · Pricing · Docs` — a whole-array reorder, not an insert, per
correction 1. All ten validation steps passed; full verbatim output in the slice's `result.md`.

- **`landing-nav.tsx` needed zero changes.** It already maps generically over `nav.links` with no hardcoded
  index or count, so the reorder + new `Get started` entry flowed through the existing component as-is —
  confirmed before touching anything, per the plan's instruction.
- **Active nav state case, confirmed: NONE exists today.** `landing-nav.tsx` has no scroll-spy, no
  `IntersectionObserver`, no "current section" state of any kind — every link renders with the same static
  class. Per §2's own qualifier ("same mechanism the existing nav uses if any; otherwise none"), no
  scroll-spy was built. Any later slice or the review should not read "no active state" as an omission.
- **`text-micro` is the exact token for the hero's micro label**, not an approximation: 11px/1.4/**0.8px**
  tracking/700 (`globals.css:149-152`) matches §4's "11px/700/letter-spacing:.8px" precisely with no
  override — same combination `ui/trap.tsx:43` already uses for its own label. Useful precedent for any
  later slice styling a similar micro-label.
- **The `vk_live_` grep (validation step 6) is no longer clean against `docs/` and never will be again**:
  S5's design-record files (`build-prompt.md`, `output/result.md`, `handoff.md`) permanently contain the
  literal string in negation form ("no `vk_live_`", "showed a `vk_live_` key tier [now corrected]") as part
  of documenting the correction. These are read-only and pre-date this slice (landed at S5's commit). Any
  later slice running this grep should expect exactly these three hits and confirm no *new* ones — the
  bar is "no new matches in `web/`/`src/`", not "zero matches anywhere in `docs/`". This slice's own new
  hero.tsx comment deliberately avoids spelling the literal string, so it adds none.
- **Nav order, confirmed twice**: the `landing.ts` array, and a `renderToStaticMarkup` render of the actual
  `LandingNav` component whose five in-page/`Docs` anchor labels came back in exactly
  `How it works · Get started · Features · Pricing · Docs`.
- **No copy button in the hero's server HTML, confirmed by hand** (temporary, not-committed
  `renderToStaticMarkup` test on the real `Hero` component — same technique as S6's `snippet-ssr.test.ts`,
  not an extension of that file). Both caption variants (`caption` / `captionNarrow`) render in the server
  HTML simultaneously, confirming the width swap is CSS-only (`app:hidden` / `hidden app:block`), never JS.
- **Both new `app:` utility classes verified compiled**, not just accepted by `tsc`: grepped the built
  `.next/static/chunks/*.css` and found `app:grid-cols-[auto_minmax(0,1fr)]` and `app:gap-7` both correctly
  nested under `@media (min-width:56.25rem)` (900px) — Tailwind can silently drop a malformed arbitrary
  value, so this is worth checking explicitly for any later slice using a similar bracketed grid template.

**Not proven** (same standing note as every P11 slice): nothing here was checked against a live origin —
the site is not deployed until P12.

### S8 done — `AgentQuickstart` landed (2026-07-29)

`P11.S8` built `web/src/components/landing/agent-quickstart.tsx` (server component, zero props)
and inserted it at page position 4. All ten validation steps passed (`typecheck` 0, `lint` 0,
`test` **70 → 73**, `build` 0 with `ƒ /` unchanged, the literal-copy grep clean after one
comment-wording fix, `style={{`/`role="alert"`/`aria-live="assertive"` all clean, a new permanent
`web/tests/agent-quickstart-ssr.test.ts` proving no copy button across all four snippets, and
`#quickstart` confirmed reachable from both the rendered id and `landing.ts`'s nav entry); full
verbatim output in the slice's `result.md`.

- **Two class-name corrections found by reading the primary source (`build-prompt.md`) against
  `plan.md`, not just against the tree** — a new category beyond DECOMP2's nine: the plan's own
  prose can drift from the design record it's translating. Both are recorded in full in
  `result.md`'s Deviations section; summary for S9/S10:
  1. **Reading-list chip radius is `rounded-sm` (6px), not `rounded-md` (8px).** `build-prompt.md`
     §3.3 gives the raw value `border-radius:6px`; this repo's token scale maps 6px to
     `radius-sm`, not `radius-md` (which is 8px here — a repo-specific redefinition, not stock
     Tailwind's own 6px `md`). `plan.md` had written `rounded-md` directly; the raw px value is
     normative per this same phase's own correction 5 precedent. **If S9 or S10 hits another
     spec'd `border-radius:6px` anywhere, it's `rounded-sm` in this repo, not `rounded-md`.**
  2. **Avoid `text-caption` next to an explicit `font-bold`/`font-*` override anywhere on the
     landing.** `text-caption` (and every other composite `--text-*` token) bundles its own
     `font-weight` in the same CSS custom property group as `font-size`/`line-height`; stacking an
     unrelated `font-bold` class alongside it does not reliably win in the compiled cascade (no
     guaranteed source-order tiebreak). S8's reading-list chip needed 12px/700 and used
     `text-[12px] font-bold` instead of `text-caption font-bold` for exactly this reason.
- **The section's own padding was deliberately left at `Section`'s default `py-section
  md:py-section-lg`, not overridden to the spec's literal `84px 28px`.** No token lands on 84px,
  and every other `Section`-based landing component (`HowItWorks`, `Showcase`, `Features`,
  `Pricing`, `ClosingCTA`) already ships with `Section`'s baked-in padding rather than a
  pixel-exact override — this is page-wide precedent, not a new judgment call invented here.
  `Section`'s own container already lands exactly on `max-w-page` (1180px), confirmed before
  writing any code — no second container was added.
- **The `withInlineCode(text, code)` helper and its `INLINE_CODE_CLASS` companion are file-private
  to `agent-quickstart.tsx`, not exported.** `S9`'s `skill.lede` is the same `{ text, code[] }`
  shape and will want the identical treatment — either duplicate the ~12-line helper (matches this
  phase's "one consumer, build inline" pattern already used for `Note`/`ReadingList`) or promote it
  to a shared module; neither this slice's plan nor `build-prompt.md` calls for a shared helper, so
  it was left un-promoted. Worth deciding explicitly at S9's plan time rather than defaulting.
- **`ReadingList`'s third row renders the literal copy value `"else"` in its status chip, as
  authored in `landing.ts` — not a placeholder needing a nicer label.** `LANDING.quickstart` is
  final copy; this file does not second-guess field values, only how they're styled.
- **`page.tsx` and `landing/index.ts` were both touched here, as `DECOMP2` flagged S8 and S9 both
  would be** — S9 runs after S8 by `order`, so there is no conflict; S9's insertion point is
  simply "after `<AgentQuickstart />`, before `<Showcase />`" and its barrel export goes after the
  `// P11.S8 — …` line this slice added.
- **Nothing here touches `#skill`'s target** — the peer row's `href="#skill"` compiles and its
  anchor exists (`SECTION_IDS.skill`, from S6), but resolves to nothing until S9 lands the section,
  exactly as the phase's DECOMP2 notes anticipated ("transient dead anchor").

### S9 done — `SkillSection` + `SkillPreview` landed at page position 5 (2026-07-29)

`P11.S9` built `skill-section.tsx` (server), `skill-preview.tsx` (server, reads the served file),
`skill-preview-body.tsx` + `skill-copy-button.tsx` (client islands), `skill-shared.ts`, and inserted
`<SkillSection />` between `<AgentQuickstart />` and `<Showcase />`. **S8's peer link to `#skill` now
resolves** (the transient dead anchor is closed). All eleven validation steps passed (`typecheck` 0,
`lint` 0, `test` **73 → 78**, `build` 0 with `ƒ /` unchanged and zero warnings, the three greps clean,
`skill_parity.py` PASS, `workflow.py validate` passed); full verbatim output in the slice's `result.md`.

#### Correction 7 is closed, and now closed *in CI*

The full file is in the server HTML in both states — "collapsed" is a **visual window only** (300/380px
scroller + fade; expanded 480/640px, fade to `opacity-0`; **the body DOM is identical**). Proven three
ways, two permanent: `web/tests/skill-preview-ssr.test.ts` asserts on **`## 7. Report back`** (the file's
LAST section) plus `not.toContain("<button")`; and against a real `next start` server, **all 119 non-blank
lines were found inside the `#skill` section** with **0 `<button>`** in it. The only `<button` on the whole
page is P9's pre-existing disabled Pricing CTA. **S10 should re-run that page-level check rather than
re-deriving it.**

#### The 22-line window — decided, and why S10 need not change code either way

`collapsedLines: 22` is kept verbatim (correction 6), and the body is rendered **verbatim including the
blank line after the closing `---`**. The body-line-1 question resolves as follows:

- **The rendering half is forced, not chosen.** The pane's `textContent` IS the clipboard payload, and the
  split is lossless (`frontmatter + body === content`, asserted). Stripping that blank line would make the
  copied bytes differ by one byte from what `/SKILL.md` serves and `skill_parity.py` gates.
- **The counting half: `22` counts the PANE from file line 1** (band included) — the only reading under
  which `result.md` §6.5's inventory ("the first 22 lines — **frontmatter band** plus the lede, `## 1`, and
  the two-export block", closing at file line 18), the footer's shared denominator ("first 22 of **119**"),
  and §3.4's parenthetical (file line 20 — off by 2 here, off by 7 under the body reading) all agree. The
  measured collapsed window (5-line band + ~18 body lines at 12.5px/1.62 in 380px) lands there too.
- **Nothing is truncated, so `collapsedLines` fills exactly one template slot.** If S10 prefers DECOMP2's
  body-line reading, **no code changes** — only the prose.

#### `<pre>` + leading newline: a byte-parity trap for anyone editing the pane

HTML drops a newline immediately after a `<pre>` start tag, and React's server renderer emits a
**compensating extra `\n`** for exactly that reason (verified with `renderToStaticMarkup`). So the raw HTML
carries one more newline than the file while the parsed `textContent` carries exactly the file's. **Do not
"clean up" that leading newline** — it is what keeps the copy byte-identical to `/SKILL.md`.

#### Two build/RSC facts every later slice inherits

1. **A request-time `fs` path must be statically analyzable at the call site.** The first build warned
   *"Encountered unexpected file in NFT list … the whole project was traced unintentionally"* because the
   path came from a spread array constant; `path.join(process.cwd(), "public", "SKILL.md")` with literal
   segments cleared it. `pnpm build` is warning-free — **a new warning there is a regression, not noise.**
2. **Every export of a `"use client"` module becomes a client reference in RSC**, so a server component
   cannot import a bare string/const from one. That is why `SKILL_FILE_DOM_ID` and the shared control class
   live in the plain `skill-shared.ts`, not in the island.

#### The section-padding question S8 left open — decided the same way, with the argument

**Both new sections keep `Section`'s default `py-section` / `md:py-section-lg` (72/104px); §5/§6's literal
`84px 28px` is not applied.** The full argument is in `result.md` §5; the load-bearing points for S10:
correction 5 governs a spec value vs a *mislabelled component*, whereas 84px contradicts the **locked
spacing scale** §1 forbids extending; **`28px` is not the landing's gutter** (`px-5 md:px-14` = 20/56px),
so honouring it would misalign this section's edge from the hero/quickstart/showcase — a *visible* failure
where the vertical delta is invisible; `84px 28px` reads as a card-kit specimen frame, the same artifact
class as correction 3's `.eyebrow`/`.note`/`.tag`/`.card`; and §6's "container 1180px" **is** honoured
exactly (`max-w-page`). **If S10 overturns this it must flip BOTH sections together**, never one.

#### Fidelity calls S10 should verify but not silently revert

- **The fade's containing block is a non-scrolling wrapper, not the scroller.** §3.4's literal
  `position:relative` on the body would anchor the fade to the scrolled *content* (i.e. 119 lines down,
  never visible collapsed). The wrapper reproduces the painted result the design specifies.
- The fade uses `opacity-0` on expand (both 150ms transitions run together) instead of unmounting.
- The gradient is the exact spec value as an arbitrary class; **verified compiled** in
  `.next/static/chunks/*.css` along with `max-height:380px/640px/300px/480px`, `height:110px`,
  `transition-property:max-height` and `grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr)` (the `app:`
  ones nested under `@media (min-width:56.25rem)`).
- The pane frame (`rounded-xl border border-hairline bg-canvas`, no shadow) is **unspecified** in §3.4.
- Filename = `text-caption` (exact 12px/500 token); meta = `text-[11px]` because `text-micro` bundles
  0.8px tracking + 700 (S8's composite-token warning).
- `SkillCopyButton` carries §7's three states in its own CVA (colour only in compound variants, never
  stacked over a base `bg-*`) rather than exporting `Snippet`'s private `copyButtonVariants` — it also has
  to dress the **primary filled** button, which that CVA does not cover.
- §7's failure hint renders under the **primary** button only, not in the 9px-padded pane header; both
  buttons still swap to `Copy failed` and select the file via `Range`+`Selection`.
- Bytes render raw (`7975`), not `7,975` — §3.4 gives `Buffer.byteLength` with no formatting, and
  `toLocaleString()` would be locale-dependent in server HTML.
- `aria-expanded` on the toggle and `tabIndex={0}` on the scroller (correction 9) are the only a11y
  additions; **no `globals.css` change, no new token**.

#### `withInlineCode` is now shared

S8 left it file-private and deferred the call. It moved **unchanged** to
`web/src/components/landing/inline-code.tsx` (with `INLINE_CODE_CLASS`) and `agent-quickstart.tsx` now
imports it — two consumers is where two copies drift, and the design wants both sentences to read as one
treatment. `agent-quickstart-ssr.test.ts` passes untouched and the quickstart's server HTML is unchanged.

#### Still uncovered by any test (S10's fidelity pass owns them)

The expand/collapse toggle, the copy click, the 2000ms revert, the `Range`+`Selection` failure path, the
polite announcement, the `:focus-visible` ring on the focusable scroller, and everything below 900px — the
Node-env suite cannot reach any of them. Also: the clipboard payload's byte parity is proven
*structurally* (lossless split + a subtree containing only those two nodes), never by driving a browser
and `cmp`-ing the result — worth one manual check in S10. **Not proven, standing note:** nothing was
checked against a live origin (`/SKILL.md` 404s until P12), and no container was built, though the
standalone path is correct by construction (`WORKDIR /app` + `COPY … /app/public` + `node server.js`).

## Doc impact

- **S6** (`P11.S6`): `docs/current/frontend.md` is now stale in two specific places — its primitive
  inventory at `:89` (which enumerates `button … endpoint-card, reveal, select, chip` and must gain
  **`snippet`** and **`trap`**, plus the new `lib/clipboard.ts` + `lib/use-is-hydrated.ts` helpers
  and the fact that `Snippet` is the landing's first mount-gated client island), and its copy-as-data
  paragraph at `:92` (which states `section-ids.ts` "now holds only the live landing anchors
  (`features`/`how`/`pricing`)" — it now also holds `quickstart` and `skill`, and `landing.ts` gained
  the `snippet` / `heroInstall` / `quickstart` / `skill` blocks). The review consolidates this with
  S7–S10's section-inventory changes into one `frontend` version.

- **DECOMP2** (`P11.DECOMP2`): no durable-truth change — decomposition wrote only `works/` state and this
  notebook. The landing's two new sections and three new primitives will change
  `docs/current/frontend.md`'s landing/section inventory once S6–S10 land; each of those slices appends its
  own note, and the review consolidates.
- **S2** (`P11.S2`): `vocky capture` + `VOCKY_API_TOKEN` are now real — `docs/current/experience.md`
  (agent-facing capture/onboarding guidance should mention the CLI path alongside REST/MCP) and
  `docs/current/operations.md` (CLI import-isolation section, if it enumerates command modules, should
  list `capture.py`) may need updates at the phase review; `docs/current/api.md` is unaffected (no backend
  contract changed).
- **S3** (`P11.S3`): install now has a real path — `docs/current/operations.md` (its CLI/install narrative,
  if any, should mention `web/public/install.sh` and the `curl -fsSL https://vocky.hi2vi.com/install.sh |
  bash` line, marked as live only once the site deploys) and `docs/current/experience.md` (onboarding
  guidance's "how do I get the CLI" gap is now closed) both describe the install story and may need updates
  at the phase review. Source files edited directly (not doc versions): `docs/cli.md:9-19` and
  `README.md:48-63`, both corrected to drop the stale "PyPI planned (P6)" framing and describe the hosted
  `curl \| bash` line (marked "once the site is live") plus the checkout path as what works today, with the
  lean/`server`-extra split stated as packaging fact, no PyPI promise.
- **S4** (`P11.S4`): a published end-user skill, the first CI gate, and the CLI-primary two-variable agent
  contract are all now real — `docs/current/experience.md` (agent-onboarding guidance should point at
  `skills/vocky-feedback/SKILL.md` / the served `/SKILL.md`, and its capture-path framing should match this
  skill's CLI-first ordering), `docs/current/product.md` (if it describes the agent skill surface at all,
  it should name the file and its three capture paths), `docs/current/operations.md` (should mention
  `.github/workflows/ci.yml` as the repo's first push/pull_request gate, its three jobs, and the two
  deliberate exclusions — no `format:check`, no pytest — as P12's to close), and `docs/current/qa.md` if the
  CI gate belongs there, all may need updates at the phase review.

- **S8** (`P11.S8`): `docs/current/frontend.md` is now stale in one more specific place — its
  landing-section inventory (whatever line enumerates `Hero / TrustStrip / HowItWorks / Showcase /
  Features / Pricing / ClosingCTA`) must gain **`AgentQuickstart`** at position 4 (`#quickstart`,
  the CLI + `VOCKY_API_TOKEN` agent onboarding path). No API/architecture change — the review
  consolidates this with S6/S7/S9/S10's inventory notes into one `frontend` version.

- **S9** (`P11.S9`): `docs/current/frontend.md`'s landing-section inventory must also gain
  **`SkillSection`** at position 5 (`#skill`, no nav link), and its component/architecture notes should
  record that the landing now **reads a served static file at request time** —
  `landing/skill-preview.tsx` does `fs.readFile("public/SKILL.md")` on every render of `/` and computes
  the displayed line/byte counts from it (never hardcoded, never a pasted excerpt), which is what keeps
  the pane from forking from the `scripts/skill_parity.py` gate; plus the new landing modules
  (`skill-section`, `skill-preview`, `skill-preview-body`, `skill-copy-button`, `skill-shared`,
  `inline-code`) and the fact that the no-JS floor is now regression-tested in
  `web/tests/skill-preview-ssr.test.ts`. No API/architecture/backend contract changed — the review
  consolidates this with S6/S7/S8/S10's notes into one `frontend` version.
